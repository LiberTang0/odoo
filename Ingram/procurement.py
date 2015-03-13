# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import urllib
import urllib2
from xml.dom.minidom import Node
from xml.dom.minidom import parse, parseString
import xml.dom.minidom
import socket
import httplib
import time
import netsvc
from osv import fields, osv
from mx import DateTime
from tools import config
from tools.translate import _
from datetime import datetime, timedelta 

class procurement_order(osv.osv):
    _name = "procurement.order"
    _description = "Procurement"
    _inherit = 'procurement.order'
    _columns = {
        'sendorder':fields.boolean('Sendorder'),
        'stockingr': fields.char('Stock Ingram', size=256, select=True,help="Stock Ingram from the SO." ),
    }

    def action_po_assign(self, cr, uid, ids, context=None):
        """ This is action which call from workflow to assign purchase order to procurements
        @return: True
        """
        purchase_id = False
        company = self.pool.get('res.users').browse(cr, uid, uid, context).company_id
        for procurement in self.browse(cr, uid, ids):
            res_id = procurement.move_id.id
            partner = procurement.product_id.seller_ids[0].name
            partner_id = partner.id
            address_id = self.pool.get('res.partner').address_get(cr, uid, [partner_id], ['delivery'])['delivery']
            pricelist_id = partner.property_product_pricelist_purchase.id
            uom_id = procurement.product_id.uom_po_id.id
            qty = self.pool.get('product.uom')._compute_qty(cr, uid, procurement.product_uom.id, procurement.product_qty, uom_id)
            if procurement.product_id.seller_ids[0].qty:
                qty=max(qty,procurement.product_id.seller_ids[0].qty)
            price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist_id], procurement.product_id.id, qty, False, {'uom': uom_id})[pricelist_id]
            newdate = DateTime.strptime(procurement.date_planned, '%Y-%m-%d %H:%M:%S')
            newdate = newdate - DateTime.RelativeDateTime(days=company.po_lead)
            newdate = newdate - procurement.product_id.seller_ids[0].delay
            product=self.pool.get('product.product').browse(cr,uid,procurement.product_id.id,context=context)
            line = {
                'name': procurement.description,
                'product_qty': qty,
                'product_id': procurement.product_id.id,
                'product_uom': uom_id,
                'price_unit': price,
                'date_planned': newdate.strftime('%Y-%m-%d %H:%M:%S'),
                'move_dest_id': res_id,
                'notes':product.description_purchase,
                'stockingr':procurement.stockingr,
            }

            taxes_ids = procurement.product_id.product_tmpl_id.supplier_taxes_id
            taxes = self.pool.get('account.fiscal.position').map_tax(cr, uid, partner.property_account_position, taxes_ids)
            line.update({
                'taxes_id':[(6,0,taxes)]
            })
            po_exist = self.pool.get('purchase.order').search(cr, uid, [ ('partner_id', '=', partner_id), ('state', '=', 'draft'), ]) #, ('origin', '=',procurement.origin)
            if po_exist:
               if procurement.origin!="SCHEDULER":
                   self.pool.get('purchase.order').write(cr, uid, po_exist[0], {'order_line': [(0,0,line)],}) 
                   origin=self.pool.get('purchase.order').read(cr,uid,po_exist[0],['origin'])
                   if not origin['origin']:
                      origin=procurement.origin
                      self.pool.get('purchase.order').write(cr, uid, po_exist[0], {'origin': origin,})  
                   else:
                       if not procurement.origin in origin['origin']:
                           origin=origin['origin']+":"+procurement.origin
                           self.pool.get('purchase.order').write(cr, uid, po_exist[0], {'origin': origin,}) 
               
            else:
               purchase_id = self.pool.get('purchase.order').create(cr, uid, {
                   'origin': procurement.origin,
                   'partner_id': partner_id,
                   'partner_address_id': address_id,
                   'location_id': procurement.location_id.id,
                   'pricelist_id': pricelist_id,
                   'order_line': [(0,0,line)],
                   'payment_term': partner.property_payment_term and partner.property_payment_term.id or False,
                   'fiscal_position': partner.property_account_position and partner.property_account_position.id or False
               })
            self.write(cr, uid, [procurement.id], {'state':'running', 'purchase_id':purchase_id})
        return purchase_id
    
procurement_order()