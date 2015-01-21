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

class purchase_order(models.Model):
    _inherit = 'purchase.order'
    
    ingramsalesordernumber = fields.Char(string="Number of order",help="Numero of order at Ingram")
    ingramsalesorderdate = fields.Char("Date the order",help="Date the order at Ingram")
    sendorder = fields.Boolean(string='Order send')
    sendmanuel = fields.Boolean(string='Send manually')
    skipxml = fields.Boolean(string='Skip XML Ingram request',Help='Confirm the purchase order without Ingram XML request')
    generate_po = fields.Char(string="Order Generated",help="Purchase order generated from the Ingram Module if the PO have other product than the Ingram product.", readonly=True)

    @api.multi
    def check_po(self):
        ingram_config=self.env['ingram_config']
        config=ingram_config.search([('xml_active','=','True')])
        if config:
            supplier = config.supplier_id
            if self.partner_id.id == supplier.id and self.skipxml==False:
                check=self.button_check(config)
                if check != True:
                    data = self.generate_po or ''
                    new_po = check.name
                    if data:
                        data += '/' + new_po
                    else:
                        data += new_po
                    self.generate_po = data
                    return False
        return True
    
    @api.multi
    def button_check(self,config):
        booll=False
        check=False
        created=False
        idss=[]
        ordreid=self.order_line
        for i in ordreid:
            if check==False:
                check=True
                for j in ordreid:
                    idprod = j.product_id
                    if not idprod:
                        idss.append(j)    
                        booll=True
                    else:
                        if not idprod.product_tmpl_id.ingram:
                            idss.append(j)
                            booll=True
                        else:
                            continue
            if booll== False:
                quantite,prix=i.actualisationPrix(config,idprod)[0]
                i.stockingr = quantite
            else:
                if len(idss)==len(ordreid):
                    raise Warning(_('ERROR: '),_('All the purchases lines are invalid for the supplier'))
                if created==False:  
                    id_create=self.copy({'order_line': False, 'generate_po': ''})
                    created=True
                for k in idss:
                    k.copy({'order_id':id_create.id})
                    k.unlink()
                return id_create               
        return True
    
    @api.multi
    def wkf_confirm_order(self):
        todo = []
        for po in self:
            if not po.order_line:
                raise Warning(_('Error!'),_('You cannot confirm a purchase order without any purchase order line.'))
            for line in po.order_line:
                if line.state=='draft':
                    todo.append(line)    
            for j in todo:   
                j.action_confirm()
            ingram_config=self.env['ingram_config']
            config=ingram_config.search([('xml_active','=','True')])
            if config:
                supplier = config.supplier_id
                if self.partner_id.id == supplier.id and self.skipxml==False:
                    result= po.send_order(config)
                    if result==True:
                        po.state = 'confirmed'
                        po.validator =  self._uid
                    else:
                        po.state = 'draft'
                        po.validator =  False
                        po.sendorder= False
                        raise Warning(_('Error'),_("An error occured during the process. Please try later or contact your administrator!"))
                else:
                    po.state = 'confirmed'
                    po.validator =  self._uid
        return True
    
    @api.multi
    def send_order(self,config):
        if self.sendorder == 1 :
            raise Warning(_('Information!'),_('Already send order'))
        create_id = self.envoieCommande(config)
        if not create_id:
            self.sendorder = True
            return True
        else:
            return False
    
    @api.multi  
    def envoieCommande(self,config):
        requete=self.requeteCode(config)
        try:
            ip=str(config.xml_address)
            if ip :
                ip=ip.split('/')
                chm=""
                for i in range(len(ip)):
                    if i>0:
                        chm+="/"+ip[i]
                conn = httplib.HTTPSConnection(ip[0],443)#environment prod
                if sys.version >= '2.7':
                    sock = socket.create_connection((conn.host, conn.port), conn.timeout, conn.source_address)
                else:
                    sock = socket.create_connection((conn.host, conn.port), conn.timeout)
                conn.sock = ssl.wrap_socket(sock, conn.key_file, conn.cert_file, ssl_version=ssl.PROTOCOL_TLSv1)
                conn.request("POST",chm,requete ) 
        except:
            raise Warning(_('Warning!'),_('Connexion failed'))
        response = conn.getresponse()
        if response.status == 200:
            data = response.read()
            _logger.info(data) 
            conn.close()
            return  self.traitement(data)
        else:
            raise Warning(_('Information!'),_('Connexion failed'))
    
    @api.multi    
    def requeteCode(self,config):
        requete = "<?xml version=\"1.0\" encoding=\"UTF-8\" ?>" 
        requete += "<BusinessTransactionRequest xmlns=\"http://www.ingrammicro.com/pcg/in/OrderCreateRequest\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\">"
        requete += "<RequestPreamble>"
        requete += "<TransactionClassifier>1.0</TransactionClassifier> "
        requete += "<TransactionID>Trans-"+self.name+"</TransactionID> "
        requete += "<UserName>"+str(config.xml_login)+"</UserName> "
        requete += "<UserPassword>"+str(config.xml_passwd)+"</UserPassword> "
        requete += "<CountryCode>"+str(config.country_id.code)+"</CountryCode> "
        requete += "<TransactionMode>SYNC</TransactionMode> "
        requete += "</RequestPreamble>"
        requete += "<OrderCreateRequest>"
        requete += "<CustomerPurchaseOrderDetails>"
        requete += "<PurchaseOrderNumber>"+self.name+"</PurchaseOrderNumber> "
        requete += "<PurchaseOrderDate>"+time.strftime('%Y-%m-%d')+"</PurchaseOrderDate> "
        requete += "</CustomerPurchaseOrderDetails>"
        requete += "<IngramSalesOrderType>ZOR</IngramSalesOrderType> "
        dest=self.dest_address_id
        if dest:
            requete += "<ShipToDetails>"
            requete += "<Address>"
            parent = dest.parent_id.name or dest.name or ""
            requete += "<Name1>"+parent+"</Name1> "
            if dest.name:
                requete += "<Name4>"+dest.name+"</Name4> "
            if dest.street:
                requete += "<Address1>"+(dest.street).decode('latin-1')+"</Address1> "
            else:
                raise Warning(_('Warning!'),_('the delivery address must have a Street!'))
            if dest.street2:
                requete += "<Address2>"+dest.street2+"</Address2> "
            if dest.city:
                requete += "<City>"+dest.city+"</City> "
            else:
                raise Warning(_('Warning!'),_('the delivery address must have a City!'))
            if dest.zip:
                requete += "<PostalCode>"+dest.zip+"</PostalCode> "
            else:
                raise Warning(_('Warning!'),_('the delivery address must have a zip!'))
            if dest.country_id:
                requete += "<CountryCode>"+dest.country_id.code+"</CountryCode> "
            else:
                raise Warning(_('Warning!'),_('the delivery address must have a Country!'))
            if dest.email:
                requete += "<Email>"+dest.email+"</Email> "
            requete += "</Address>"
            requete += "</ShipToDetails>"
        elif self.picking_type_id.warehouse_id:
            dest=self.picking_type_id.warehouse_id
            if not dest : 
                raise Warning(_('Error!'),_('Please configure the warehouse in the field "Deliver To"!'))
            if dest.partner_id:
                dest=dest.partner_id
                requete += "<ShipToDetails>"
                requete += "<Address>"
                parent = dest.parent_id.name or dest.name or ""
                requete += "<Name1>"+parent+"</Name1> "
                if dest.name:
                    requete += "<Name4>"+dest.name+"</Name4> "
                if dest.street:
                    requete += "<Address1>"+(dest.street).decode('latin-1')+"</Address1> "
                else:
                    raise Warning(_('Warning!'),_('the delivery address must have a Street!'))
                if dest.street2:
                    requete += "<Address2>"+dest.street2+"</Address2> "
                if dest.city:
                    requete += "<City>"+dest.city+"</City> "
                else:
                    raise Warning(_('Warning!'),_('the delivery address must have a City!'))
                if dest.zip:
                    requete += "<PostalCode>"+dest.zip+"</PostalCode> "
                else:
                    raise Warning(_('Warning!'),_('the delivery address must have a zip!'))
                if dest.country_id:
                    requete += "<CountryCode>"+dest.country_id.code+"</CountryCode> "
                else:
                    raise Warning(_('Warning!'),_('the delivery address must have a Country!'))
                if dest.email:
                    requete += "<Email>"+dest.email+"</Email> "
                requete += "</Address>"
                requete += "</ShipToDetails>"
            else:
                wh=self.env['stock.warehouse']
                dest2=wh.search([('lot_stock_id','=',self.location_id.id)])
                if dest2:
                    dest=dest2.partner_id
                    requete += "<ShipToDetails>"
                    requete += "<Address>"
                    parent = dest.parent_id.name or dest.name or ""
                    requete += "<Name1>"+parent+"</Name1> "
                    if dest.name:
                        requete += "<Name4>"+dest.name+"</Name4> "
                    if dest.street:
                        requete += "<Address1>"+(dest.street).decode('latin-1')+"</Address1> "
                    else:
                        raise Warning(_('Warning!'),_('the delivery address must have a Street!'))
                    if dest.street2:
                        requete += "<Address2>"+dest.street2+"</Address2> "
                    if dest.city:
                        requete += "<City>"+dest.city+"</City> "
                    else:
                        raise Warning(_('Warning!'),_('the delivery address must have a City!'))
                    if dest.zip:
                        requete += "<PostalCode>"+dest.zip+"</PostalCode> "
                    else:
                        raise Warning(_('Warning!'),_('the delivery address must have a zip!'))
                    if dest.country_id:
                        requete += "<CountryCode>"+dest.country_id.code+"</CountryCode> "
                    else:
                        raise Warning(_('Warning!'),_('the delivery address must have a Country!'))
                    if dest.email:
                        requete += "<Email>"+dest.email+"</Email> "
                    requete += "</Address>"
                    requete += "</ShipToDetails>"
        else:
            raise Warning(_('Error!'),_('Please configure the field address for the Warehouse!'))
        requete += "<ShippingDetails>"
        requete += "<RequestedDeliveryDate>"+time.strftime('%Y-%m-%d')+"</RequestedDeliveryDate> "
        requete += "</ShippingDetails>"
        requete += "<ProcessingFlags>"
        requete += "<BackOrderFlag>Y</BackOrderFlag> "
        requete += "<SplitShipmentFlag>Y</SplitShipmentFlag> "
        requete += "<ShipCompleteFlag>N</ShipCompleteFlag> "
        requete += "<HoldOrderFlag>N</HoldOrderFlag> "
        requete += "</ProcessingFlags>"
        compt=0
        for id in self.order_line:
            compt+=1
            requete += "<LineDetails>"
            requete += "<CustomerLineNumber>"+str(compt)+"</CustomerLineNumber> "
            sku=id.product_id and id.product_id.default_code
            requete += "<IngramPartNumber>"+str(sku)+"</IngramPartNumber> "
            requete += "<RequestedQuantity UnitOfMeasure=\"EA\">"+str(id.product_qty)+"</RequestedQuantity> "
            requete += "</LineDetails>"
        requete += "</OrderCreateRequest>"
        requete += "</BusinessTransactionRequest>"
        _logger.info(requete)
        return requete
    
    @api.multi       
    def traitement(self,reponse):
        dom = xml.dom.minidom.parseString(reponse)            
        return self.handleSlideshow(dom)
    
    @api.multi    
    def handleSlideshow(self,ResponsePreamble):
        if(self.verifConexion(ResponsePreamble.getElementsByTagName("ResponsePreamble")[0])):
            return self.handleSlideshowItemDetails(ResponsePreamble.getElementsByTagName("OrderCreateResponse")[0])
        else: 
            return False
     
    @api.multi       
    def getText(self,nodelist):
            rc = []
            for node in nodelist:
                if node.nodeType == node.TEXT_NODE:
                    rc.append(node.data)
            return ''.join(rc)
    
    @api.multi
    def handleSlideshowItemDetails(self,noeud):
        dateCom=self.getText((noeud.getElementsByTagName("IngramSalesOrderDate")[0]).childNodes)
        cpt=-1
        cpt2=0 
        linetext=False
        status=[]
        statut=[]
        id_create=''
        total=""
        if noeud.getElementsByTagName("IngramSalesOrderNumber") and not self.partner_ref:
            self.partner_ref=self.getText((noeud.getElementsByTagName("IngramSalesOrderNumber")[0]).childNodes)
        for i in noeud.getElementsByTagName("OrderStatus"):
            status.append(i.getAttribute("StatusCode"))
            status.append(i.getAttribute("StatusDescription"))
            if status[0]=="OC":
                continue
            if status[0]=="OR" or status[0]=="PR":
                elements=noeud.getElementsByTagName("LineDetails")
                for j in elements:
                    cpt+=1
                    for i in j.getElementsByTagName("LineText"):
                        linetext=True
                        for z in j.getElementsByTagName("LineStatus"):                            
                            statut=[]
                            statut.append(z.getAttribute("StatusCode"))
                            statut.append(z.getAttribute("StatusDescription"))
                            idss=self.order_line
                            prod=idss[cpt].product_id.name
                            total+=" "  + prod + " : " + statut[1] + ' \n'
                    if linetext==False:
                        for z in j.getElementsByTagName("LineStatus"):                            
                            statut=[]
                            statut.append(z.getAttribute("StatusCode"))
                            statut.append(z.getAttribute("StatusDescription"))
                            idss=self.order_line
                            prod=idss[cpt].product_id.name
                            total+=" "  + prod + " : " + statut[1] + ' \n'
                raise Warning(_("Order Rejected"),_(status[1] + total  ))
            else:
                created=False
                tab=[]    
                for i in noeud.getElementsByTagName("LineStatus"):
                    for j in noeud.getElementsByTagName("LineStatus"):
                        statut.append(j.getAttribute("StatusCode"))
                        if statut[0]=="LR":
                            cpt2+=1
                            continue
                    cpt+=1
                    statut.append(i.getAttribute("StatusCode"))
                    statut.append(i.getAttribute("StatusDescription"))
                    if statut[0]=="LR":
                        idss=self.order_line
                        if len(idss)==cpt2:
                            raise Warning(_("Error"),_("All the purchases lines are rejected by the supplier"))
                        statut.append(i.getAttribute("StatusDescription")) 
                        if created==False:  
                            id_create=self.copy({'order_line': False,'generate_po': ''})
                            created=True
                        idss[cpt].copy({'order_id':id_create.id})
                        tab.append(prod.id)
                for x in tab:
                    x.unlink()
            
        self.ingramsalesorderdate = dateCom
        return (id_create)
    
    @api.multi
    def button_check_AV(self):
        purchase_order_line=self.env['purchase.order.line']
        ingram_config=self.env['ingram_config']
        config=ingram_config.search([('xml_active','=','True')])
        if config:
            supplier = config.supplier_id
        else:
            raise Warning(_('Xml request inactive!'))
        line_ids=purchase_order_line.search([('order_id','=',self.id)])
        for i in line_ids:
            if i.product_id:
                idprod=i.product_id
                idprodtmpl=idprod.product_tmpl_id
                if idprodtmpl.ingram:
                    if idprod.default_code:
                        prix,quantite=i.actualisationPrix(config,idprod)[0]
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
    
    @api.one
    def verifConexion(self,noeud):
        returncode=self.getText((noeud.getElementsByTagName("ReturnCode")[0]).childNodes)
        if int(returncode)<20000:
            return True
        elif int(returncode)==20001:
            raise Warning(_('IngramSalesOrderType cannot have value ZRE or ZCR'))
        elif int(returncode)==20002:
            raise Warning(_('Authentication or Authorization has failed; please re-submit your document with correct login credentials.'))
        elif int(returncode)==20003:
            raise Warning(_('Unable to process the document; please try to re-submit your document after sometime. If error persist contact technical support'))
        elif int(returncode)==20000:
            raise Warning(_('No results were found for given search criteria'))
        elif int(returncode)==20004:
            raise Warning(_('Transaction Failed : Data issue'))
        elif int(returncode)==20005:
            raise Warning(_('Real-Time transactions are currently unavailable'))
        else:
            raise Warning(_('ERROR: '),_('Error unknowed'))
purchase_order()


class purchase_order_line(models.Model):
    _inherit = 'purchase.order.line'
    
    stockingr = fields.Char(string='Stock Ingram',help="Legend of the function price and avalability\nBlue = stock decreases\nRed = price of the supplier increases\nGreen =prix of the supplier decreases" )
    verif = fields.Char(string='Check')

    @api.one  
    def actualisationPrix(self,config,product):
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
            conn.request("POST",chm,requete[0],) 
            response = conn.getresponse()
            data = response.read()  
            _logger.info(data) 
            conn.close()
            return  self.traitement(data)[0]
        else :
            return False
    
    @api.one
    def requeteCode(self,config,product):
        code=product.default_code or self.product_id.default_code
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
        else:
            raise Warning(_('ERROR: '),_('Error unknowed'))
    
purchase_order_line()