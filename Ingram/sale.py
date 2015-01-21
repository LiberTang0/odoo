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

from openerp import models, fields, api, _
from openerp.exceptions import Warning
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import logging
_logger = logging.getLogger(__name__)
import time
from xml.dom.minidom import Node
from xml.dom.minidom import parse, parseString
import xml.dom.minidom
import ssl
import socket
import httplib
import ftplib
import os
import os.path
import csv, math
import thread
import smtplib
import sys
from datetime import date,datetime, timedelta

class sale_order(models.Model):
    _inherit = 'sale.order'
    
    @api.one
    def button_check(self):
        sale_order_line=self.env['sale.order.line']
        ingram_config=self.env['ingram_config']
        config=ingram_config.search([('xml_active','=','True')])
        if config:
            supplier = config.supplier_id
        else:
            raise Warning(_('Xml request inactive!'))
        line_ids=sale_order_line.search([('order_id','=',self.id)])
        for i in line_ids:
            if i.product_id:
                idprod=i.product_id
                idprodtmpl=idprod.product_tmpl_id
                if idprodtmpl.ingram:
                    if idprod.default_code:
                        prix,quantite=i.actualisationPrix(config,idprod)
                        prix = prix.replace(',','.')
                        if (idprodtmpl.standard_price!=float(prix))|(int(i.stockingr) != int(quantite)):
                            if (idprodtmpl.standard_price!=float(prix)):
                                suppinfo_ids=idprodtmpl.seller_ids
                                for b in suppinfo_ids:
                                    if b.name == supplier:
                                        for c in b.pricelist_ids:
                                            if c.name=='INGRAM' and c.min_quantity==1:
                                                c.price = prix
                                if (int(i.stockingr) > int(quantite)):
                                    i.stockingr = quantite
                                    i.verif = '1'
                                    idprodtmpl.standard_price = prix
                                elif  (idprodtmpl.standard_price>float(prix)):
                                    i.verif = '2'
                                    idprodtmpl.standard_price = prix
                                else:
                                    i.verif = '3'
                                    idprodtmpl.standard_price = prix
                            else:
                                if (int(i.stockingr) > int(quantite)):
                                    i.stockingr = quantite
                                    i.verif = '1'
                                else:
                                    i.stockingr = quantite
                                    i.verif = '0'
                        else:
                            i.verif = '0'
    
sale_order()

class sale_order_line(models.Model):
    _inherit = 'sale.order.line'
    
    stockingr = fields.Char(string='Stock Ingram',help="Legend of the function price and avalability\nBlue = stock decreases\nRed = price of the supplier increases\nGreen =prix of the supplier decreases" )
    verif = fields.Char(string='Check')

    @api.v7
    def product_id_change(self,cr,uid,ids, pricelist, product, qty=0,uom=False, qty_uos=0, uos=False, name='', partner_id=False,lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, context=None):
        context = context or {}
        lang = lang or context.get('lang',False)
        partner_obj = self.pool.get('res.partner')
        result = super(sale_order_line, self).product_id_change(cr, uid, ids, pricelist, product, qty=qty,
            uom=uom, qty_uos=qty_uos, uos=uos, name=name, partner_id=partner_id,
            lang=lang, update_tax=update_tax, date_order=date_order, packaging=packaging, fiscal_position=fiscal_position, flag=flag, context=context)
        context = {'lang': lang, 'partner_id': partner_id}
        if partner_id:
            lang = partner_obj.browse(cr, uid, partner_id).lang
        quantite=''
        result['value']['stockingr']=quantite
        if product:
            donnee=self.pool.get('product.product').browse(cr,uid,product)
            if result['value'].get('name'):
                result['value']['name']=donnee.name
            if donnee.description_sale:
                result['value']['name'] = donnee.description_sale
            idsearch=self.pool.get('ingram_config').search(cr,uid,[('xml_active','=','True'),])
            config=self.pool.get('ingram_config').read(cr,uid,idsearch,['categorie_id','supplier_id'])
            if config:
                supplier = config[0]['supplier_id'][0] 
            if config:
                categorie = config[0]['categorie_id'][0]
                codecateg=self.pool.get('product.category').browse(cr,uid,donnee.categ_id.id)
                if(codecateg.code_categ_ingram):
                    donnee=self.pool.get('product.product').browse(cr,uid,product)
                    if donnee.default_code:
                        prix,quantite=self.actualisationPrix(cr,uid,ids,self.pool.get('ingram_config').browse(cr,uid,idsearch[0]),donnee)
                        prix = prix.replace(',','.')
                        prod=self.pool.get('product.product').browse(cr,uid,product)
                        suppinfo_id=prod.product_tmpl_id.seller_ids
                        for b in suppinfo_id:
                            if b.name.id == supplier:
                                for c in b.pricelist_ids:
                                    if c.name=='INGRAM' and c.min_quantity==1:
                                        self.pool.get('pricelist.partnerinfo').write(cr,uid,c.id,{'price':prix})
                        self.pool.get('product.template').write(cr,uid,prod.product_tmpl_id.id,{'standard_price':prix})
                        result['value']['stockingr']=quantite
                    else:
                        result['value']['stockingr']="N/A"
                else:
                    result['value']['stockingr']="N/A"
        if quantite:
            result['value']['stockingr']=quantite
        else:
            result['value']['stockingr']="N/A"
        return result

    
    @api.v7   
    def actualisationPrix(self,cr,uid,ids,config,product):
        recs = self.browse(cr, uid, ids)
        return recs.actualisationPrix(config,product)
    
    @api.v8    
    def actualisationPrix(self,config,product):
        if not self:
            sale_order_line=self.env['sale.order.line']
            self=sale_order_line.browse(1)
        requete=self.requeteCode(config,product)
        ip=str(config.xml_address)
        if ip :
            ip=ip.split('/')
            chm=""
            for i in range(len(ip)):
                if i>0:
                    chm+="/"+ip[i]
            conn = httplib.HTTPSConnection(ip[0],443)
            if sys.version >= '2.7':
                sock = socket.create_connection((conn.host, conn.port), conn.timeout, conn.source_address)
            else:
                sock = socket.create_connection((conn.host, conn.port), conn.timeout)
            conn.sock = ssl.wrap_socket(sock, conn.key_file, conn.cert_file, ssl_version=ssl.PROTOCOL_TLSv1)
            conn.request("POST",chm,requete[0]) 
            response = conn.getresponse()
            data = response.read()  
            _logger.info(data) 
            conn.close()
            return  self.traitement(data)[0]
        else :
            return False
    
    @api.one
    def requeteCode(self,config,product):
        code=product.default_code
        requete = "<?xml version=\"1.0\" encoding=\"UTF-8\" ?>" 
        requete += "<BusinessTransactionRequest xmlns=\"http://www.ingrammicro.com/pcg/in/PriceAndAvailibilityRequest\">"
        requete += "<RequestPreamble>"
        requete += "<TransactionClassifier>1.0</TransactionClassifier> "
        requete += "<TransactionID>PnA</TransactionID> "
        requete += "<UserName>"+str(config.xml_login)+"</UserName>" 
        requete += "<UserPassword>"+str(config.xml_passwd)+"</UserPassword> "
        requete += "<CountryCode>"+str(config.country_id.code)+"</CountryCode> "
        requete += "</RequestPreamble>"
        requete += "<PriceAndAvailabilityRequest>"
        requete += "<PriceAndAvailabilityPreference>3</PriceAndAvailabilityPreference>" 
        requete += "<Item>"
        requete += "<IngramPartNumber>"+str(code)+"</IngramPartNumber>" 
        requete += "<RequestedQuantity UnitOfMeasure=\"EA\">3</RequestedQuantity>" 
        requete += "</Item>"
        requete += "</PriceAndAvailabilityRequest>"
        requete += "</BusinessTransactionRequest>"
        _logger.info(requete) 
        return requete
            
    @api.one
    def traitement(self,reponse):
        dom = xml.dom.minidom.parseString(reponse)            
        return self.handleSlideshow(dom)[0]
    
    @api.one
    def handleSlideshow(self,ResponsePreamble):     
        if(self.verifConexion(ResponsePreamble.getElementsByTagName("ResponsePreamble")[0])):
            return self.handleSlideshowItemDetails(ResponsePreamble.getElementsByTagName("ItemDetails")[0])[0]
        else: 
            return 0.0,0
    
    @api.one
    def getText(self,nodelist):
            rc = []
            for node in nodelist:
                if node.nodeType == node.TEXT_NODE:
                    rc.append(node.data)
            return ''.join(rc)
    
    @api.one
    def handleSlideshowItemDetails(self,noeud):
        if (noeud.getElementsByTagName("AvailabilityDetails")):
            infoprod=noeud.getElementsByTagName("AvailabilityDetails")[0]
            quantite=self.getText((infoprod.getElementsByTagName("AvailableQuantity")[0]).childNodes)
        else:
            quantite="N/A"
        prix = noeud.getElementsByTagName("PricingDetails")[0]
        prix = self.getText((prix.getElementsByTagName("UnitNetPrice")[0]).childNodes)
        return prix[0],quantite[0]
     
    @api.one   
    def verifConexion(self,noeud):
        returncode=self.getText((noeud.getElementsByTagName("ReturnCode")[0]).childNodes)
        returncode=returncode[0]
        if int(returncode)<20000:
            return True
        elif int(returncode)==20000:
            raise Warning(_('No results were found for given search criteria'))
        elif int(returncode)==20001:
            raise Warning(_('IngramSalesOrderType cannot have value ZRE or ZCR'))
        elif int(returncode)==20002:
            raise Warning(_('Authentication or Authorization has failed; please re-submit your document with correct login credentials.'))
        elif int(returncode)==20003:
            raise Warning(_('Unable to process the document; please try to re-submit your document after sometime. If error persist contact technical support'))
        elif int(returncode)==20004:
            raise Warning(_('Transaction Failed : Data issue'))
        elif int(returncode)==20005:
            raise Warning(_('Real-Time transactions are currently unavailable'))
    
sale_order_line()