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
from dateutil.relativedelta import relativedelta
import time
import netsvc
from osv import fields, osv
from mx import DateTime
from tools import config
from tools.translate import _
from datetime import datetime, timedelta 
from tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, float_compare

class sale_order(osv.osv):
    _name = 'sale.order'
    _description = "Sale Order line Ingram"
    _inherit = 'sale.order'
    
    def action_ship_create(self, cr, uid, ids, *args):
        wf_service = netsvc.LocalService("workflow")
        picking_id = False
        move_obj = self.pool.get('stock.move')
        proc_obj = self.pool.get('procurement.order')
        company = self.pool.get('res.users').browse(cr, uid, uid).company_id
        for order in self.browse(cr, uid, ids, context={}):
            proc_ids = []
            output_id = order.shop_id.warehouse_id.lot_output_id.id
            picking_id = False
            for line in order.order_line:
                proc_id = False
                date_planned = datetime.now() + relativedelta(days=line.delay or 0.0)
                date_planned = (date_planned - timedelta(days=company.security_lead)).strftime('%Y-%m-%d %H:%M:%S')
                if line.state == 'done':
                    continue
                move_id = False
                if line.product_id and line.product_id.product_tmpl_id.type in ('product', 'consu'):
                    location_id = order.shop_id.warehouse_id.lot_stock_id.id
                    if not picking_id:
                        pick_name = self.pool.get('ir.sequence').get(cr, uid, 'stock.picking.out')
                        picking_id = self.pool.get('stock.picking').create(cr, uid, {
                            'name': pick_name,
                            'origin': order.name,
                            'type': 'out',
                            'state': 'auto',
                            'move_type': order.picking_policy,
                            'sale_id': order.id,
                            'address_id': order.partner_shipping_id.id,
                            'note': order.note,
                            'invoice_state': (order.order_policy=='picking' and '2binvoiced') or 'none',
                            'company_id': order.company_id.id,
                        })
                    move_id = self.pool.get('stock.move').create(cr, uid, {
                        'name': line.name[:64],
                        'picking_id': picking_id,
                        'product_id': line.product_id.id,
                        'date': date_planned,
                        'date_expected': date_planned,
                        'product_qty': line.product_uom_qty,
                        'product_uom': line.product_uom.id,
                        'product_uos_qty': line.product_uos_qty,
                        'product_uos': (line.product_uos and line.product_uos.id)\
                                or line.product_uom.id,
                        'product_packaging': line.product_packaging.id,
                        'address_id': line.address_allotment_id.id or order.partner_shipping_id.id,
                        'location_id': location_id,
                        'location_dest_id': output_id,
                        'sale_line_id': line.id,
                        'tracking_id': False,
                        'state': 'draft',
                        'note': line.notes,
                        'company_id': order.company_id.id,
                    })

                if line.product_id:
                    proc_id = self.pool.get('procurement.order').create(cr, uid, {
                        'name': line.name,
                        'description': line.name,
                        'origin': order.name,
                        'date_planned': date_planned,
                        'product_id': line.product_id.id,
                        'product_qty': line.product_uom_qty,
                        'product_uom': line.product_uom.id,
                        'product_uos_qty': (line.product_uos and line.product_uos_qty)\
                                or line.product_uom_qty,
                        'product_uos': (line.product_uos and line.product_uos.id)\
                                or line.product_uom.id,
                        'location_id': order.shop_id.warehouse_id.lot_stock_id.id,
                        'procure_method': line.type,
                        'move_id': move_id,
                        'property_ids': [(6, 0, [x.id for x in line.property_ids])],
                        'company_id': order.company_id.id,
                        'stockingr':line.stockingr,
                        'note': line.notes,
                    })
                    proc_ids.append(proc_id)
                    self.pool.get('sale.order.line').write(cr, uid, [line.id], {'procurement_id': proc_id})
                    if order.state == 'shipping_except':
                        for pick in order.picking_ids:
                            for move in pick.move_lines:
                                if move.state == 'cancel':
                                    mov_ids = move_obj.search(cr, uid, [('state', '=', 'cancel'),('sale_line_id', '=', line.id),('picking_id', '=', pick.id)])
                                    if mov_ids:
                                        for mov in move_obj.browse(cr, uid, mov_ids):
                                            move_obj.write(cr, uid, [move_id], {'product_qty': mov.product_qty, 'product_uos_qty': mov.product_uos_qty})
                                            proc_obj.write(cr, uid, [proc_id], {'product_qty': mov.product_qty, 'product_uos_qty': mov.product_uos_qty})

            val = {}

            if picking_id:
                wf_service.trg_validate(uid, 'stock.picking', picking_id, 'button_confirm', cr)

            for proc_id in proc_ids:
                wf_service.trg_validate(uid, 'procurement.order', proc_id, 'button_confirm', cr)

            if order.state == 'shipping_except':
                val['state'] = 'progress'
                val['shipped'] = False

                if (order.order_policy == 'manual'):
                    for line in order.order_line:
                        if (not line.invoiced) and (line.state not in ('cancel', 'draft')):
                            val['state'] = 'manual'
                            break
            self.write(cr, uid, [order.id], val)
        return True   
   
    def button_check(self,cr,uid,ids,context=None):
        boolprice=False
        boolquant=False
        txt="" 
        ordreid=self.pool.get('sale.order.line').search(cr,uid,[('order_id','=',ids[0]),])
        for i in ordreid:
            donne=self.pool.get('sale.order.line').browse(cr,uid,i)
            idprod = donne.product_id
            if idprod:
                donnee=self.pool.get('product.template').browse(cr,uid,idprod.id)
                idsearch=self.pool.get('ingram_config').search(cr,uid,[('xml_active','=','True'),])
                config=self.pool.get('ingram_config').read(cr,uid,idsearch,['categorie_id'])
            
                prod_tmpl_id=self.pool.get('product.product').browse(cr,uid,idprod.id).product_tmpl_id.id

                valeur2=self.pool.get('product.template').browse(cr,uid,prod_tmpl_id)
                if valeur2.ingram:
                    donnee=self.pool.get('product.product').browse(cr,uid,idprod.id)
                    if donnee.default_code:
                        prix,quantite,bool=self.pool.get('sale.order.line').actualisationPrix(cr,uid,ids,donnee.default_code,idprod.id)
                        prodtemp=self.pool.get('product.template').browse(cr,uid,prod_tmpl_id)
                        if (prodtemp.standard_price!=float(prix))|(donne.stockingr != quantite):             
                            if (prodtemp.standard_price!=float(prix)):
                                boolprice=True
                                if (donne.stockingr > quantite):
                                    boolquant=True
                                    self.pool.get('sale.order.line').write(cr,uid,[i],{'stockingr':quantite,'verif':'1'})
                                if  (prodtemp.standard_price>float(prix)):
                                    self.pool.get('sale.order.line').write(cr,uid,[i],{'verif':'2'})
                                    self.pool.get('product.template').write(cr,uid,prod_tmpl_id,{'standard_price':prix})
                                else:
                                    self.pool.get('sale.order.line').write(cr,uid,[i],{'verif':'3'})
                                    self.pool.get('product.template').write(cr,uid,prod_tmpl_id,{'standard_price':prix})
                            else:
                                if (donne.stockingr > quantite):
                                    boolquant=True
                                    self.pool.get('sale.order.line').write(cr,uid,[i],{'stockingr':quantite,'verif':'1'})
                                else:
                                    self.pool.get('sale.order.line').write(cr,uid,[i],{'stockingr':quantite,'verif':'0'})
                        else:
                            self.pool.get('sale.order.line').write(cr,uid,[i],{'verif':'0'})
                    
        if boolprice :
            txt= "Prix différents" + str("\n")
        if boolquant :
            txt+="Stock différents "+str("\n")
        if boolprice | boolquant:
            warn_msg = _("warning") 
            warning = {
                    'title': _('Stock and price information !'),
                    'message': txt,
                    }
        return True
sale_order()

class sale_order_line(osv.osv):
    _inherit = 'sale.order.line'
    _description = 'Sale Order line'
    _columns = {
      'stockingr': fields.char('Stock Ingram', size=256, select=True,help="Legend of the function price and avalability\nBlue = stock decreases\nRed = price of the supplier increases\nGreen =prix of the supplier decreases" ),
      'verif': fields.char('Check',size=25),
    }
    
    def onchange_sale_order_line_view(self, cr, uid, id, type, context={}, *args):
        temp = {}
        temp['value'] = {}
        if (not type):
            return {}
        if type != 'article':
            temp = {
                'value': {
                'product_id': False,
                'uos_id': False,
                'account_id': False,
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'quantity': 0,
                'discount': 0.0,
                'invoice_line_tax_id': False,
                'account_analytic_id': False,
                'product_uom_qty': 0.0,
                },
            }
            if type == 'line':
                temp['value']['name'] = ' '
            if type == 'break':
                temp['value']['name'] = ' '
            if type == 'subtotal':
                temp={'value':{'name':'Sub Total'},}
            return temp
        return {}
        
    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, context=None):
        context = context or {}
        lang = lang or context.get('lang',False)
        result = {}
        valid=True
        quantite=''
        if product:
            donnee=self.pool.get('product.product').browse(cr,uid,product)
            idsearch=self.pool.get('ingram_config').search(cr,uid,[('xml_active','=','True'),])
            config=self.pool.get('ingram_config').read(cr,uid,idsearch,['categorie_id'])     
            if config:
                categorie = config[0]['categorie_id'][0]
                codecateg=self.pool.get('product.category').browse(cr,uid,donnee.categ_id.id)
                if(codecateg.code_categ_ingram):
                    donnee=self.pool.get('product.product').browse(cr,uid,product)
                    if donnee.default_code:
                        prix,quantite,valid=self.actualisationPrix(cr,uid,ids,donnee.default_code,product)
                        prod=self.pool.get('product.product').browse(cr,uid,product)
                        self.pool.get('product.template').write(cr,uid,prod.product_tmpl_id.id,{'standard_price':prix})
                        result['stockingr']=quantite
                    else:
                        result['stockingr']="N/A"
                else:
                    result['stockingr']="N/A"
        if not partner_id:
            raise osv.except_osv(_('No Customer Defined !'), _('You have to select a customer in the sales form !\nPlease set one customer before choosing a product.'))
        warning = {}
        product_uom_obj = self.pool.get('product.uom')
        partner_obj = self.pool.get('res.partner')
        product_obj = self.pool.get('product.product')
        context = {'lang': lang, 'partner_id': partner_id}
        if partner_id:
            lang = partner_obj.browse(cr, uid, partner_id).lang
        context_partner = {'lang': lang, 'partner_id': partner_id}

        if not product:
            return {'value': {'th_weight': 0, 'name':'' ,'price_unit':0, 'product_packaging': False,
                'product_uos_qty': qty}, 'domain': {'product_uom': [],
                   'product_uos': []}}
        if not date_order:
            date_order = time.strftime(DEFAULT_SERVER_DATE_FORMAT)

        res = self.product_packaging_change(cr, uid, ids, pricelist, product, qty, uom, partner_id, packaging, context=context)
        result = res.get('value', {})
        if quantite:
            result['stockingr']=quantite
        else:
            result['stockingr']="N/A"
            
        warning_msgs = res.get('warning') and res['warning']['message'] or ''
        product_obj = product_obj.browse(cr, uid, product, context=context)

        uom2 = False
        if uom:
            uom2 = product_uom_obj.browse(cr, uid, uom)
            if product_obj.uom_id.category_id.id != uom2.category_id.id:
                uom = False
        if uos:
            if product_obj.uos_id:
                uos2 = product_uom_obj.browse(cr, uid, uos)
                if product_obj.uos_id.category_id.id != uos2.category_id.id:
                    uos = False
            else:
                uos = False
        if product_obj.description_sale:
            result['notes'] = product_obj.description_sale
        fpos = fiscal_position and self.pool.get('account.fiscal.position').browse(cr, uid, fiscal_position) or False
        if update_tax: #The quantity only have changed
            result['delay'] = (product_obj.sale_delay or 0.0)
            result['tax_id'] = self.pool.get('account.fiscal.position').map_tax(cr, uid, fpos, product_obj.taxes_id)
            result.update({'type': product_obj.procure_method})

        if not flag:
            result['name'] = self.pool.get('product.product').name_get(cr, uid, [product_obj.id], context=context_partner)[0][1]
        domain = {}
        if (not uom) and (not uos):
            result['product_uom'] = product_obj.uom_id.id
            if product_obj.uos_id:
                result['product_uos'] = product_obj.uos_id.id
                result['product_uos_qty'] = qty * product_obj.uos_coeff
                uos_category_id = product_obj.uos_id.category_id.id
            else:
                result['product_uos'] = False
                result['product_uos_qty'] = qty
                uos_category_id = False
            result['th_weight'] = qty * product_obj.weight
            domain = {'product_uom':
                        [('category_id', '=', product_obj.uom_id.category_id.id)],
                        'product_uos':
                        [('category_id', '=', uos_category_id)]}

        elif uos and not uom: # only happens if uom is False
            result['product_uom'] = product_obj.uom_id and product_obj.uom_id.id
            result['product_uom_qty'] = qty_uos / product_obj.uos_coeff
            result['th_weight'] = result['product_uom_qty'] * product_obj.weight
        elif uom: # whether uos is set or not
            default_uom = product_obj.uom_id and product_obj.uom_id.id
            q = product_uom_obj._compute_qty(cr, uid, uom, qty, default_uom)
            if product_obj.uos_id:
                result['product_uos'] = product_obj.uos_id.id
                result['product_uos_qty'] = qty * product_obj.uos_coeff
            else:
                result['product_uos'] = False
                result['product_uos_qty'] = qty
            result['th_weight'] = q * product_obj.weight        # Round the quantity up

        if not uom2:
            uom2 = product_obj.uom_id
        compare_qty = float_compare(product_obj.virtual_available * uom2.factor, qty * product_obj.uom_id.factor, precision_rounding=product_obj.uom_id.rounding)
        if (product_obj.type=='product') and int(compare_qty) == -1 \
          and (product_obj.procure_method=='make_to_stock'):
            warn_msg = _('You plan to sell %.2f %s but you only have %.2f %s available !\nThe real stock is %.2f %s. (without reservations)') % \
                    (qty, uom2 and uom2.name or product_obj.uom_id.name,
                     max(0,product_obj.virtual_available), product_obj.uom_id.name,
                     max(0,product_obj.qty_available), product_obj.uom_id.name)
            warning_msgs += _("Not enough stock ! : ") + warn_msg + "\n\n"
        if not pricelist:
            warn_msg = _('You have to select a pricelist or a customer in the sales form !\n'
                    'Please set one before choosing a product.')
            warning_msgs += _("No Pricelist ! : ") + warn_msg +"\n\n"
        else:
            price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist],
                    product, qty or 1.0, partner_id, {
                        'uom': uom or result.get('product_uom'),
                        'date': date_order,
                        })[pricelist]
            if price is False:
                warn_msg = _("Couldn't find a pricelist line matching this product and quantity.\n"
                        "You have to change either the product, the quantity or the pricelist.")

                warning_msgs += _("No valid pricelist line found ! :") + warn_msg +"\n\n"
            else:
                result.update({'price_unit': price})
        if warning_msgs:
            warning = {
                       'title': _('Configuration Error !'),
                       'message' : warning_msgs
                    }
        return {'value': result, 'domain': domain, 'warning': warning}

    def actualisationPrix(self,cr,uid,ids,id_prod,product): 
        return self.checkPrice(cr,uid,ids,id_prod,product)
    
    def checkPrice(self,cr,uid,ids,codeSku,product):
        requete=self.requeteCode(cr,uid,codeSku)
        idsearch=self.pool.get('ingram_config').search(cr,uid,[('xml_active','=','True'),])
        config=self.pool.get('ingram_config').read(cr,uid,idsearch,['xml_address'])#
        ip=str(config[0]['xml_address'])
        if ip :
            ip=ip.split('/')
            chm=""
            for i in range(len(ip)):
                if i>0:
                    chm+="/"+ip[i]
            conn = httplib.HTTPSConnection(ip[0],443)
            conn.request("POST",chm,requete ) 
            response = conn.getresponse()
            data = response.read()  
            self.ajoutlog(data) 
            conn.close()
            return  self.traitement(cr,uid,ids,data,product)# 
        else :
            return False
    
    def requeteCode(self,cr,uid,code):
            idsearch=self.pool.get('ingram_config').search(cr,uid,[('xml_active','=','True'),])
            config=self.pool.get('ingram_config').read(cr,uid,idsearch,['xml_login','xml_passwd'])#
            requete = "<?xml version=\"1.0\" encoding=\"UTF-8\" ?>" 
            requete += "<BusinessTransactionRequest xmlns=\"http://www.ingrammicro.com/pcg/in/PriceAndAvailibilityRequest\">"
            requete += "<RequestPreamble>"
            requete += "<TransactionClassifier>1.0</TransactionClassifier> "
            requete += "<TransactionID>PnA</TransactionID> "
            requete += "<UserName>"+str(config[0]['xml_login'])+"</UserName>" 
            requete += "<UserPassword>"+str(config[0]['xml_passwd'])+"</UserPassword> "
            requete += "<CountryCode>BE</CountryCode> "
            requete += "</RequestPreamble>"
            requete += "<PriceAndAvailabilityRequest>"
            requete += "<PriceAndAvailabilityPreference>3</PriceAndAvailabilityPreference>" 
            requete += "<Item>"
            requete += "<IngramPartNumber>"+str(code)+"</IngramPartNumber>" 
            requete += "<RequestedQuantity UnitOfMeasure=\"EA\">3</RequestedQuantity>" 
            requete += "</Item>"
            requete += "</PriceAndAvailabilityRequest>"
            requete += "</BusinessTransactionRequest>"
            return requete

    def traitement(self,cr,uid,ids,reponse,product):
        dom = xml.dom.minidom.parseString(reponse)            
        return self.handleSlideshow(cr,uid,ids,dom,product)

    def handleSlideshow(self,cr,uid,ids,ResponsePreamble,product):     
           if(self.verifConexion(cr,uid,ids,ResponsePreamble.getElementsByTagName("ResponsePreamble")[0])):
               return self.handleSlideshowItemDetails(cr,uid,ids,ResponsePreamble.getElementsByTagName("ItemDetails")[0],product)
           else: 
               return 0.0,0,False
           
    def getText(self,nodelist):
            rc = []
            for node in nodelist:
                if node.nodeType == node.TEXT_NODE:
                    rc.append(node.data)
            return ''.join(rc)

    def handleSlideshowTitle(self,title):
            return True

    def handleSlideshowItemDetails(self,cr,uid,ids,noeud,product):
            elements=noeud.getElementsByTagName("SKUAttributes")[0]
            if (noeud.getElementsByTagName("AvailabilityDetails")):
                infoprod=noeud.getElementsByTagName("AvailabilityDetails")[0]
                quantite=self.getText((infoprod.getElementsByTagName("AvailableQuantity")[0]).childNodes)
                infoid=infoprod.getElementsByTagName("PlantID")[0]
                descr=infoid.getAttribute("PlantDescription")
                id=self.getText((infoprod.getElementsByTagName("PlantID")[0]).childNodes)
                available=self.getText((elements.getElementsByTagName("IsAvailable")[0]).childNodes)
                unite=infoprod.getElementsByTagName("AvailableQuantity")[0]
                unite=unite.getAttribute("UnitOfMeasure")
            else:
                quantite="N/A"
            prix = noeud.getElementsByTagName("PricingDetails")[0]
            prix=self.getText((prix.getElementsByTagName("UnitNetPrice")[0]).childNodes)
            prix=prix.replace(',','.')
            return prix,quantite,True
        
    def verifConexion(self,cr,uid,ids,noeud):
        returncode=self.getText((noeud.getElementsByTagName("ReturnCode")[0]).childNodes)
        returnMessage=self.getText((noeud.getElementsByTagName("ReturnMessage")[0]).childNodes)
        if int(returncode)<20000:
            return True
        elif int(returncode)==20000:
            raise osv.except_osv(_('ERROR: '),_('No results were found for given search criteria'))
        elif int(returncode)==20001:
            raise osv.except_osv(_('ERROR: '),_('IngramSalesOrderType cannot have value ZRE or ZCR'))
        elif int(returncode)==20002:
            raise osv.except_osv(_('ERROR: '),_(' Authentication or Authorization has failed; please re-submit your document with correct login credentials.'))
        elif int(returncode)==20003:
            raise osv.except_osv(_('ERROR: '),_('Unable to process the document; please try to re-submit your document after sometime. If error persist contact technical support'))
        elif int(returncode)==20004:
            raise osv.except_osv(_('ERROR: '),_(' Transaction Failed : Data issue'))
        elif int(returncode)==20005:
            raise osv.except_osv(_('ERROR: '),_('Real-Time transactions are currently unavailable'))
            
    def ajoutlog(self,txt):
        logger = netsvc.Logger()
        logger.notifyChannel('BHC_Ingram', netsvc.LOG_INFO, txt)
        
sale_order_line()