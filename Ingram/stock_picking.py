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

class history_command(models.Model):
    _name = "history.command"

    name = fields.Char(string='Name')
    date = fields.Date(string="Expected Date",help="Expected Date")
    datemaj = fields.Date(string="Updated date",help="Updated date")
    idmani = fields.Many2one("stock.picking",string="idLabel")
    description = fields.Char(string='Description')
    
history_command()

class stock_picking(models.Model):
    _inherit = 'stock.picking'
    
    date_ingr = fields.Date(string="Delivry date",help="Delivry date")
    history_lineb = fields.One2many('history.command', 'idmani',string="idLabel")
    min_date = fields.Datetime(compute ='get_min_max_date', multi="min_max_date", store=True, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},string='Scheduled Date', select=1, help="Scheduled time for the first part of the shipment to be processed. Setting manually a value here would set it as expected date for all the stock moves.", track_visibility='onchange')

    @api.multi
    @api.depends('move_lines.date_expected', 'move_lines.picking_id')
    def get_min_max_date(self):
        history_command=self.env['history.command']
        res = {}
        for id in self:
            res[id] = {'min_date': False, 'max_date': False}
        if not self.id:
            return res
        ids=[]
        for x in self:
            ids.append(x.id)
        self._cr.execute("""select
                picking_id,
                min(date_expected),
                max(date_expected)
            from
                stock_move
            where
                picking_id IN %s
            group by
                picking_id""",(tuple(ids),))
        for pick, dt1, dt2 in self._cr.fetchall():
            if len(self) == 1:
                val=history_command.search([('idmani','=',self[0].id)])#             
                if len(val):
                    if len(val)>0:
                        indice=len(val)-1
                    else:
                        indice=0
                    result=val[indice]
                    if (result):
                        self.min_date = result.date #time.strftime('%Y-%m-%d %H:%M:%S')#
                    else:
                        self.min_date = dt1
                else:
                    self.min_date = dt1
            else:
                self.min_date = dt1
            self.max_date = dt2

    @api.multi
    def button_status(self):
        return self.statusCommande()
    
    @api.multi
    def statusCommande(self):        
        return self.checkCom()
    
    @api.multi
    def checkCom(self):
        ingram_config=self.env['ingram_config']
        config=ingram_config.search([('xml_active','=','True')])
        if config:
            supplier = config.supplier_id
            if self.partner_id.id == supplier.id:
                if self.origin:
                    numpo=self.origin.split(':')
                    if numpo:
                        requete=self.requeteCode(config,numpo[0])
                    else:
                        raise Warning(_('Warning!'),_('No purchase order reference'))
                    try:
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
                            conn.request("POST",chm,requete ) 
                    except:
                        raise Warning(_('Warning!'),_('Connexion failed'))
                    response = conn.getresponse()
                    data = response.read()
                    _logger.info(data) 
                    conn.close()
                    return  self.traitement(data)
                else:
                    raise Warning(_('Warning!'),_('Incomming isn\'t link to an order'))
    
    @api.multi  
    def requeteCode(self,config,numIngram):
        requete = "<?xml version=\"1.0\" encoding=\"UTF-8\" ?>" 
        requete += "<BusinessTransactionRequest xmlns=\"http://www.ingrammicro.com/pcg/in/OrderInquiryRequest\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" xsi:schemaLocation=\"http://www.ingrammicro.com/pcg/in/OrderInquiryRequest ../../13th%20Nov/EGT%20Transactions%20Design/IMXML%20Transactions/Done/Finalized/Inbound%20Order%20Inquiry%20-%20ODE%20-%20OST%20-%20OTR%20-%20OSE%20Merged/IMXML%205.0%20Schema/Request/OrderInquiryRequestSchema.xsd\">"
        requete += "<RequestPreamble>"
        requete += "<TransactionClassifier>1.0</TransactionClassifier> "
        requete += "<TransactionID>Status</TransactionID> "
        requete += "<TimeStamp>2010-04-07T18:39:09</TimeStamp> "
        requete += "<UserName>"+str(config.xml_login)+"</UserName>" 
        requete += "<UserPassword>"+str(config.xml_passwd)+"</UserPassword> "
        requete += "<CountryCode>"+str(config.country_id.code)+"</CountryCode> "
        requete += "</RequestPreamble>"
        requete +=" <OrderStatusRequest IncludeOrderDetails=\"Y\">"
        requete +="<CustomerPurchaseOrderNumber>"+str(numIngram)+"</CustomerPurchaseOrderNumber>"
        requete +="</OrderStatusRequest>"
        requete +="</BusinessTransactionRequest>"  
        return requete
    
    @api.multi
    def traitement(self,reponse):
            dom = xml.dom.minidom.parseString(reponse)            
            return self.handleSlideshow(dom)
    @api.multi
    def handleSlideshow(self,ResponsePreamble):     
        if(self.verifConexion(ResponsePreamble.getElementsByTagName("ResponsePreamble")[0])):
            return self.handleSlideshowItemDetails(ResponsePreamble.getElementsByTagName("OrderStatusResponse")[0])
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
        elements=noeud.getElementsByTagName("StatusDetails")[0]
        date =[]
        skuliste=[]
        for i in elements.getElementsByTagName("DeliveryDate"):
            date.append(self.getText(i.childNodes))
        for j in elements.getElementsByTagName("LineDetails"):
            sku=False
            for i in elements.getElementsByTagName("IngramPartNumber"):
                if sku==False:
                    skuliste.append(self.getText(i.childNodes))
                    sku=True          
        statut=[]
        for i in elements.getElementsByTagName("LineStatus"):
            statut.append(i.getAttribute("StatusCode"))
        status=elements.getElementsByTagName("OrderStatus")[0]
        statusstr=status.getAttribute("StatusDescription")
        id=self.miseAjour(date,statusstr,statut,skuliste)
        if id:
            self.history_lineb = [(4,id[0].id)]
        return True
    
    @api.multi
    def miseAjour(self,date,description,statut,skuliste):
        for id in self:
            dateMax=["00","00","00"]
            for i in date:
                k=i.split("-")
                if (k[0]> dateMax[0]):
                    for j in range(len(dateMax)) :
                        dateMax[j]=k[j]
                elif ( int(k[0]) == int(dateMax[0])and  int(k[1])>int(dateMax[1])):
                        for j in range(len(dateMax)) :
                            dateMax[j]=k[j]
                elif(int(k[0]) == int(dateMax[0])and  int(k[1])==int(dateMax[1]) and int(k[2])>int(dateMax[2])):
                        for j in range(len(dateMax)) :
                            dateMax[j]=k[j]
            dateExp=dateMax[0]+"-"+dateMax[1]+"-"+dateMax[2]
            datejour=time.strftime('%Y-%m-%d')
            history_command=self.env['history.command']
            idtrouver=history_command.search([('idmani','=',id.id),('description','=',description)])
            idstock=self.move_lines
            id.min_date = dateExp
            if not idtrouver:
                idt=history_command.create({'idmani':id.id,'description':description,'date':dateExp,'datemaj':datejour})
                idtrouver=[idt]
            return idtrouver
            
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
    
stock_picking()