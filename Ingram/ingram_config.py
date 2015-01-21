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
import logging
_logger = logging.getLogger(__name__)
import time
import ftplib
import os
import os.path
import csv, math
import thread
import smtplib
import sys
from datetime import date,datetime, timedelta

class ingram_config(models.Model):
    _name = "ingram_config"
    _description = "Configuration Management Produces Ingram"  
    
    name = fields.Char(string="Name",help="Name associated with the configuration", required=True)
    xml_address = fields.Char(string='Server Xml address',help="server Xml address")
    xml_login = fields.Char(string='Login',help="Login for Xml request ")
    xml_passwd = fields.Char(string='Password',help="Password for Xml Request")
    xml_active = fields.Boolean(string='XMl Request',help="Active the Xml Request")
    server_address = fields.Char(string='Server address',help="server ip address",required=True)
    file_cat = fields.Char(string='Products Categories file name',default='PCAT_GENERIC.TXT',help="Name of the file for the products categories",required=True)
    file_prod = fields.Char(string='Products File name',default='Price2.txt',help="Name of the file for the products. Must be based on this header: 'Ingram Part Number,Vendor Part Number,EANUPC Code,Plant,Vendor Number,Vendor Name,Weight,Category ID,Customer Price,Retail Price,Availability Flag,BOM Flag,Warranty Flag,Material Long Description,Material Creation Reason code,Material Language Code,Music Copyright Fees,Recycling Fees,Document Copyright Fees,Battery Fees,Availability (Local Stock),Availability (Central Stock),Creation Reason Type,Creation Reason Value,Local Stock Backlog Quantity,Local Stock Backlog ETA,Central Stock Backlog Quantity,Central Stock Backlog ETA'",required=True)
    server_login = fields.Char(string='Login',help="Login database")
    server_passwd = fields.Char(string='Password',help="Password database")
    date_synchro = fields.Datetime(string='Date of last manually synchronization',readonly=True)
    date_import = fields.Datetime(string='Date of last manually importation',readonly=True)
    date_cron = fields.Datetime(string='Date of last cronjob synchronization',readonly=True)        
    chemin = fields.Char(string="Path",help="Path where the files is stored", required=True)
    mailto = fields.Char(string="Warning Mail",help="Encode the adresses e-mail separated by ';'.\nThose e-mail will receive the warnings", required=True)
    pricelist = fields.Many2one('product.pricelist',string='Pricelist for the sales price',)
    id_synchro = fields.Many2one('ir.cron',string='Cronjob', required=True,help="Cronjob in OpenERP for automatic synchronization. To bind the Cronjob with the configuration, click the button")
    categorie_name = fields.Char(string='Category',help="Name of the product categorie")
    location_id = fields.Many2one('stock.location',string='Location', required=True, domain=[('usage', '=', 'internal')],help="Location of new product")
    country_id = fields.Many2one('res.country',string='Country', required=True,help=" Country of Ingram supplier")
    categorie_id = fields.Many2one('product.category',string='Category', required=True, change_default=True, domain=[('type','=','normal')],help="Select category for the current product")
    supplier_id = fields.Many2one('res.partner',string='Supplier', required=True, domain=[('supplier','=',True)], ondelete='cascade', help="Supplier of this product")
    taxes_ventes = fields.Many2many('account.tax',"ingram_taxe_sales",'ingram_config',"taxe_id",string='Sales Taxes',domain=[('parent_id', '=', False),('type_tax_use','in',['sale','all'])])
    taxes_achats = fields.Many2many('account.tax',"ingram_taxe_achat",'ingram_config2',"taxe_id2",string='Purchases Taxes',domain=[('parent_id', '=', False),('type_tax_use','in',['purchase','all'])])
 
    @api.onchange('supplier_id')
    def onchange_supplier_id(self):
        if self.supplier_id:
            self.country_id=self.supplier_id.country_id.id

    @api.one
    def check_ftp(self):
        ip = self.server_address
        login = self.server_login
        passwd = self.server_passwd
        try:
            ftp=ftplib.FTP()
        except:
            raise Warning(_('FTP was not started!'))
            return False
        ip=ip.split('/')
        txt=""
        for i in range(len(ip)):
            if i>0:
                txt+="/"+ip[i]
        try:
            ftp.connect(ip[0])
            if login:
                ftp.login(login,passwd)
            else:
                ftp.login()
        except:
            raise Warning(_('Username/password FTP connection was not successfully!'))
            return False
        ftp.close()
        raise Warning(_('FTP connection was successfully!'))
        return True
    
    @api.model
    def create(self, vals):
        config = self.env['ingram_config'].search([])
        if config:
            raise Warning(_('You can have only one configuration!'))
        res = super(ingram_config, self).create(vals)
        return res
        
    @api.one 
    def sendTextMail(self,ids,title,mess):
        _from = 'Ingram Error <Ingram@bhc.be>'
        to=ids.mailto
        to=to.replace(';',',')
        txt=''
        if mess:
            txt += "\r\n"
            txt += mess
            txt += "\r\n"
        mail_obj=self.env['mail.mail']
        res=mail_obj.create({'subject':title,
                            'email_from':'ingram@openerp.com',
                            'email_to':to,
                            'body_html':txt})
    
    @api.multi
    def write(self, values):
        idtaxevente=self.taxes_ventes
        idtaxeAchat=self.taxes_achats
        super(ingram_config, self).write(values)
        prod_tmpl=self.env['product.template']
        prod_prod=self.env['product.product']
        if ('taxes_ventes' in values ):
            tab=[]
            tab2=[]
            tab3=[]
            for i in idtaxevente:
                tab.append(i.id)
            for j in values['taxes_ventes'][0][2]:
                if not (j in tab ):
                    tab2.append(j)
            for i in idtaxevente:
                if not (i.id in values['taxes_ventes'][0][2] ):
                    tab3.append(i.id)
            if tab2:
                idProd=prod_tmpl.search([('ingram','=',True)])
                for j in idProd:
                    empl = prod_prod.search([('product_tmpl_id','=',j.id)])
                    for k in values['taxes_ventes'][0][2]:
                        empl.taxes_id = [(4,k)]
            if tab3:
                idProd=prod_tmpl.search([('ingram','=',True)])
                for j in idProd:
                    empl = prod_prod.search([('product_tmpl_id','=',j.id)])
                    for i in tab3:
                        empl.taxes_id = [(3,i)]
        if ('taxes_achats' in values ):
            tab=[]
            tab2=[]
            tab3=[]
            for i in idtaxeAchat:
                tab.append(i.id)
            for j in values['taxes_achats'][0][2]:
                if not ( j in tab ):
                    tab2.append(j)
            for i in idtaxeAchat:
                if not ( i.id in values['taxes_achats'][0][2] ):
                    tab3.append(i.id)
            if (tab2):
                idProd=prod_tmpl.search([('ingram','=',True)])
                for j in idProd:
                    empl = prod_prod.search([('product_tmpl_id','=',j.id)])
                    for i in values['taxes_achats'][0][2]:
                        empl.supplier_taxes_id = [(4,i)]
            if tab3:
                idProd=prod_tmpl.search([('ingram','=',True)])
                for j in idProd:
                    empl = prod_prod.search([('product_tmpl_id','=',j.id)])
                    for i in tab3:
                        empl.taxes_id = [(3,i)]
    
    @api.model
    def cron_function(self):
        id_config = self.search([('xml_active','=',True)])
        if not id_config:
            _logger.info('No config!')
            return False 
        _logger.info(_('Download started'))
        result=id_config.import_data(id_config)
        if result[0]==True:
            _logger.info(_('Download ended'))
        else:
            _logger.info(_('Download error'))
            return False
        _logger.info(_('Synchronization started'))
        result2=id_config.synchro_categ(id_config)
        if result2[0]==True:
            _logger.info(_('products categories synchronization ended'))
        else:
            _logger.info(_('products categories synchronization error'))
            return False
        _logger.info(_('Products synchronization started'))
        result3=id_config.synchronisation(id_config)
        _logger.info(result3)
        if result3[0]==True:
            _logger.info(_('Products synchronization ended'))
        else:
            _logger.info(_('Products synchronization error'))
            return False
        _logger.info(_('Clean product started'))
        result4=id_config.clean_data()
        if result4[0]==True:
            _logger.info(_('Clean product ended'))
        else:
            _logger.info(_('Clean product error'))
            return False
        id_config.clean_categ()
        _logger.info(_('end synchronization'))
        try :
            id_config.date_cron = time.strftime("%Y-%m-%d %H:%M:%S")
        except:
            try :
                id_config.date_cron = time.strftime("%Y-%m-%d %H:%M:%S")
            except:pass
        _logger.info('Done')
        return True
    
    @api.one
    def button_import_data(self):
        _logger.info(_('Download started'))
        config_id=self
        result=self.import_data(config_id)
        if result[0]==True:
            _logger.info(_('Download ended'))
            try :
                self.date_import = time.strftime("%Y-%m-%d %H:%M:%S")
            except:
                try :
                    self.date_import = time.strftime("%Y-%m-%d %H:%M:%S")
                except:pass
        else:
            _logger.info(_('Download error'))
            return False
    
        return True
    
    @api.one
    def import_data(self,config_id):
        config = config_id
        ip = config.server_address
        login = config.server_login
        passwd = config.server_passwd
        chm=str(config.chemin)
        try:
            ftp=ftplib.FTP()
        except:
            _logger.error(_('connexion error'))
            self.sendTextMail(config_id,"Connecion error","An error occured during the connection to the server.\n\nDetails: \n\t %s" %(sys.exc_info()[0]))
            return False
        ip=ip.split('/')
        txt=""
        for i in range(len(ip)):
            if i>0:
                txt+="/"+ip[i]
        try:
            ftp.connect(ip[0])
            if login:
                ftp.login(login,passwd)
            else:
                ftp.login()
            ftp.retrlines('LIST')
            ftp.cwd(txt)
            ftp.retrlines('LIST')
            self.download(config_id,'.',chm,ftp)
            ftp.close()
            return True
        except:
            _logger.error(_('Download error'))
            self.sendTextMail(config_id,"Import error","An error occured during the importation.\n\nDetails: \n\t %s" %(sys.exc_info()[0]))
            return False
       
    @api.one
    def download(self,config_id,pathsrc, pathdst,ftp):
        idss=config_id
        try:
            lenpathsrc = len(pathsrc)
            l = ftp.nlst(pathsrc)
            for i in l:
                tailleinit=ftp.size(i)
                if ((str(i)==str(idss.file_cat)) or str(i)==str(idss.file_prod)):
                    try:
                        ftp.size(i)
                        ftp.retrbinary('RETR '+i, open(pathdst+os.sep+i, 'wb').write)                   
                    except:
                        try: os.makedirs(pathdst+os.sep+os.path.dirname(i[lenpathsrc:]))
                        except: pass
                        return False
                    if os.path.isfile(pathdst+'/'+i) :
                        taille=os.path.getsize(pathdst+'/'+i)
                        if (tailleinit!=taille):
                            os.remove(pathdst+'/'+i)
            return True
        except:
            return False    

    @api.one
    def clean_data(self):
        _logger.info("clean_data")
        try:
            product_product=self.env['product.product']
            sale_order_line=self.env['sale.order.line']
            purchase_order_line=self.env['purchase.order.line']
            procurement_order=self.env['procurement.order']
            stock_move=self.env['stock.move']
            account_invoice_line=self.env['account.invoice.line']
            aujourdhui = datetime.today()
            semaine=timedelta(weeks=1)
            date=aujourdhui - semaine
            idProd=product_product.search(['|',('active','=',True),('active','=',False),('product_tmpl_id.ingram','=',True),('product_tmpl_id.last_synchro_ingram','<',date)],order='id')
            delete=0
            undelete=0
            use=0
            for i in idProd:
                ids1=sale_order_line.search([('product_id','=',i.id)])
                ids2=purchase_order_line.search([('product_id','=',i.id)])
                ids3=procurement_order.search([('product_id','=',i.id)])
                ids4=stock_move.search([('product_id','=',i.id)])
                ids5=account_invoice_line.search([('product_id','=',i.id)])
                if not ids1 and not ids2 and not ids3 and not ids4 and not ids5:
                    try:
                        i.unlink()
                        delete+=1
                    except:
                        _logger.info('Delete impossible')
                        undelete+=1
                else:
                    i.active = False
                    use+=1
            _logger.info('Products deleted : %s'%(delete))
            _logger.info('Products non deleted : %s'%(use))
            _logger.info('product cleaned')
            return True
        except:
            _logger.error("Erreur Clean_data")
            self.sendTextMail(self,"Error products cleaning","An error occured during the cleaning.\n\nDetails: \n\t %s" %(sys.exc_info()[0]))
            return False
    
    @api.one
    def delete_data(self):
        _logger.info("delete_data")
        try:
            product_product=self.env['product.product']
            sale_order_line=self.env['sale.order.line']
            purchase_order_line=self.env['purchase.order.line']
            procurement_order=self.env['procurement.order']
            stock_move=self.env['stock.move']
            account_invoice_line=self.env['account.invoice.line']
            idProd=product_product.search(['|',('active','=',True),('active','=',False),('product_tmpl_id.ingram','=',True)],order='id')
            delete=0
            undelete=0
            use=0
            cpt=0
            for i in idProd:
                cpt+=1
                ids1=sale_order_line.search([('product_id','=',i.id)])
                ids2=purchase_order_line.search([('product_id','=',i.id)])
                ids3=procurement_order.search([('product_id','=',i.id)])
                ids4=stock_move.search([('product_id','=',i.id)])
                ids5=account_invoice_line.search([('product_id','=',i.id)])
                if not ids1 and not ids2 and not ids3 and not ids4 and not ids5:
                    try:
                        i.unlink()
                        delete+=1
                    except:
                        _logger.info('Delete impossible')
                        undelete+=1
                else:
                    i.active = False
                    use+=1
            _logger.info('Products deleted : %s'%(delete))
            _logger.info('Products non deleted : %s'%(use))
            _logger.info('product cleaned')
            return True
        except:
            _logger.error("Erreur delete_data")
            self.sendTextMail(self,"Error products deleting","An error occured during the cleaning.\n\nDetails: \n\t %s" %(sys.exc_info()[0]))
            return False
    
    @api.one
    def synchro_data(self):
        config_id=self   
        _logger.info(_('Products categories synchronization started'))
        result=self.synchro_categ(config_id)
        if result[0]==True:
            _logger.info(_('products categories synchronization ended'))
        else:
            _logger.info(('products categories synchronization error'))
            return False
        _logger.info(_('products synchronization started'))
        result3=self.synchronisation(config_id)
        _logger.info(result3)
        if result3[0]==True:
            _logger.info(_('products synchronization ended'))
        else:
            _logger.info(_('products synchronization error'))
            return False
        self.clean_categ()
        try :
            self.date_synchro = time.strftime("%Y-%m-%d %H:%M:%S")
        except:
            try :
                self.date_synchro = time.strftime("%Y-%m-%d %H:%M:%S")
            except:pass
        return True
    
    @api.one    
    def clean_categ(self):
        _logger.info("Clean_categ")
        product_categ=self.env['product.category']
        product_tmpl=self.env['product.template']
        tab=[]
        idss_cat=product_categ.search([('code_categ_ingram','=','-1')])
        for i in idss_cat:
            id_child=product_categ.search([('parent_id','=',i.id)])
            for j in id_child :
                if j in idss_cat and j.id not in tab:
                    id_child2=product_categ.search([('parent_id','=',j.id)])
                    for z in id_child2:
                        if z in idss_cat and z.id not in tab:
                            tab.append(z.id)
                    tab.append(j.id)
            tab.append(i.id)
        if 1==1:
            for j in tab:
                id_prod=product_tmpl.search([('categ_id','=',j)])
                id_cat=product_categ.search([('id','in',tab),('parent_id','=',j)])
                if not id_prod and not id_cat:
                    try:
                        k=product_categ.browse(j)
                        k.unlink()
                    except:pass
        _logger.info("End Clean Categ")
        return True
    
    @api.one
    def synchronisation(self,config_id):  
        categ = config_id.categorie_id
        supplier= config_id.supplier_id
        chm=str(config_id.chemin)
        file_prod=config_id.file_prod
        listefich = os.listdir(chm+'/')
        product_product=self.env['product.product']
        product_categ=self.env['product.category']
        product_tmpl=self.env['product.template']
        pricelist_supplier=self.env['pricelist.partnerinfo']
        product_supplier=self.env['product.supplierinfo']
        product_routes=self.env['stock.location.route']
        taxes_a=[]
        taxes_v=[]  
        for a in config_id.taxes_achats:
            taxes_a.append(a.id)
        for a in config_id.taxes_ventes:
            taxes_v.append(a.id)
        try:
            compteur=0
            for i in listefich:
                if str(i)==str(file_prod):
                    fichier = open(chm+i,'rb')
                    fichiercsv = csv.reader(fichier, delimiter=',',quotechar='|')
                    for ligne in fichiercsv:
                        if ligne[0] != "Ingram Part Number":
                            i=0
                            nom=ligne[13]
                            name=''
                            lgt=len(nom)
                            while (i < lgt):
                                try:
                                    nom[i].decode('latin-1')
                                    name +=nom[i]
                                    i+=1
                                except:
                                    i+=1
                            nom=name[0:127]
                            desc=name
                            print "n:",compteur
                            _logger.info(compteur)
                            empl = product_product.search([('default_code','=',ligne[0])])
                            if empl:
                                idprod = empl.product_tmpl_id
                                categ_ingram=product_categ.search([('code_categ_ingram','=',ligne[7])])
                                if not categ_ingram:
                                    categ_ingram=categ
                                elif len(categ_ingram)>1:
                                    categ_ingram=categ_ingram[0]
                                if ligne[8]=='X' or not ligne[8]:
                                    ligne[8]='0.0'
                                idprod.name =nom
                                idprod.standard_price = float(ligne[8])
                                idprod.weight_net = float(ligne[6])
                                idprod.description = desc
                                idprod.valuation = 'real_time'
                                idprod.description_sale = desc
                                idprod.categ_id = categ_ingram.id
                                idprod.last_synchro_ingram = time.strftime("%Y-%m-%d")
                                suppinfo_id=idprod.seller_ids
                                exist_line=False
                                exist=False
                                for b in suppinfo_id:
                                    if b.name.id == supplier.id:
                                        exist=b.id
                                        if not b.product_name or not b.product_code:
                                            b.product_name = nom
                                            b.product_code = ligne[0]
                                        for c in b.pricelist_ids:
                                            exist_line=True
                                            if c.name=='INGRAM' and c.min_quantity==1:
                                                c.price = float(ligne[8])
                                if exist and exist_line==False:
                                    pricelist_supplier.create({'min_quantity':'1','price':float(ligne[8]),'suppinfo_id':exist,'name':'INGRAM'})
                                if (len(ligne[2])==12):
                                    ligne[2]="0"+ligne[2]
                                if len(ligne[2]) == 13 :
                                    empl.name_template = nom
                                    empl.active = True
                                    empl.ean13 = ligne[2]
                                    empl.vpn = ligne[1]
                                    empl.manufacturer = ligne[5]
                                else:
                                    empl.name_template = nom
                                    empl.active = True
                                    empl.vpn = ligne[1]
                                    empl.manufacturer = ligne[5]
                            else:
                                categ_ingram=product_categ.search([('code_categ_ingram','=',ligne[7])])
                                if not categ_ingram:
                                    categ_ingram=categ
                                elif len(categ_ingram)>1:
                                    categ_ingram=categ_ingram[0]
                                if ligne[8]=='X' or not ligne[8]:
                                    ligne[8]='0.0'
                                mto_ids=product_routes.search(['|',('name','=','Make To Order'),('name','=','Buy')])
                                route=[]
                                for d in mto_ids:
                                    route.append(d.id)
                                tmpl_id=product_tmpl.create({'valuation':'real_time','name':nom,'standard_price':float(ligne[8]),'weight_net':float(ligne[6]),'description':desc,'description_sale':desc,
                                    'categ_id':categ_ingram.id,'route_ids':[(6,0,route)],'ingram':True,'type':'product','last_synchro_ingram':time.strftime("%Y-%m-%d")})
                                id_prod=product_product.search([('product_tmpl_id','=',tmpl_id.id)])
                                if (len(ligne[2])==12):
                                    ligne[2]="0"+ligne[2]
                                if len(ligne[2]) == 13 :
                                    id_prod.default_code = ligne[0]
                                    id_prod.name_template = nom
                                    id_prod.taxes_id = [(6,0,taxes_v)]
                                    id_prod.supplier_taxes_id = [(6,0,taxes_a)]
                                    id_prod.price_extra = 0.00
                                    id_prod.active = True
                                    id_prod.product_tmpl_id = tmpl_id.id
                                    id_prod.ean13 = ligne[2]
                                    id_prod.vpn = ligne[1]
                                    id_prod.manufacturer = ligne[5]
                                else:
                                    id_prod.default_code = ligne[0]
                                    id_prod.name_template = nom
                                    id_prod.taxes_id = [(6,0,taxes_v)]
                                    id_prod.supplier_taxes_id = [(6,0,taxes_a)]
                                    id_prod.price_extra = 0.00
                                    id_prod.active = True
                                    id_prod.product_tmpl_id = tmpl_id.id
                                    id_prod.vpn = ligne[1]
                                    id_prod.manufacturer = ligne[5]
                                supp_info=product_supplier.create({'name':supplier.id,'min_qty':0,'product_tmpl_id':tmpl_id.id,'product_name':nom,'product_code':ligne[0]})
                                pricelist_supplier.create({'min_quantity':'1','price':float(ligne[8]),'suppinfo_id':supp_info.id,'name':'INGRAM'})
                        compteur+=1
                    fichier.close()
            return True       
        except:
            _logger.error("Erreur Synchro_produit")
            self.sendTextMail(config_id,"Error Synchronization","An error occured during the synchronization.\n \nDetails: \n\t %s" %(sys.exc_info()[0]))
            return False   
        
    @api.one
    def synchro_categ(self,config_id):
        categ = config_id.categorie_id
        file_cat = config_id.file_cat
        chm=str(config_id.chemin)
        listefich = os.listdir(chm+'/')
        product_categ=self.env['product.category']
        compteur=0
        for i in listefich:
            if str(i)==str(file_cat) :
                fichier = open(chm+'/'+i,'rb')
                fichiercsv = csv.reader(fichier, delimiter=';')
                cat=[]
                for ligne in fichiercsv:
                    ligne_un=product_categ.search([('code_categ_ingram','=',ligne[1]),('name','=',ligne[2])])
                    if ligne_un:
                        ligne_trois=product_categ.search([('code_categ_ingram','=',ligne[3]),('name','=',ligne[4]),('parent_id','=',ligne_un.id)])
                    else:
                        ligne_trois=product_categ.search([('code_categ_ingram','=',ligne[3]),('name','=',ligne[4])])
                    if ligne_trois:
                        ligne_cinq=product_categ.search([('code_categ_ingram','=',ligne[5]),('name','=',ligne[6]),('parent_id','=',ligne_trois.id)])
                    else:
                        ligne_cinq=product_categ.search([('code_categ_ingram','=',ligne[5]),('name','=',ligne[6])])
                    _logger.info(compteur)
                    if not ligne_un:
                        ligne_un=product_categ.create({'name':ligne[2],'parent_id':categ.id,'code_categ_ingram':ligne[1],'type':'view'})
                        if ligne_un not in cat:
                            cat.append(ligne_un)
                    else:
                        ligne_un.code_categ_ingram = ligne[1]
                        if ligne_un not in cat:
                            cat.append(ligne_un)
                    if not ligne_trois :
                        ligne_trois=product_categ.create({'name':ligne[4],'parent_id':ligne_un.id,'code_categ_ingram':ligne[3],'type':'view'})
                        if ligne_trois not in cat:
                            cat.append(ligne_trois)
                    else:
                        if ligne_trois.parent_id != ligne_un:
                            ligne_trois.parent_id = ligne_un.id
                            ligne_trois.code_categ_ingram = ligne[3]
                        else:
                            ligne_trois.code_categ_ingram = ligne[3]
                        if ligne_trois not in cat:
                            cat.append(ligne_trois)
                    if not ligne_cinq :
                        ligne_cinq = product_categ.create({'name':ligne[6],'parent_id':ligne_trois.id,'code_categ_ingram':ligne[5]})
                        if ligne_cinq not in cat:
                            cat.append(ligne_cinq)
                    else:
                        if ligne_cinq.parent_id != ligne_trois:
                            ligne_cinq.parent_id = ligne_trois.id
                            ligne_cinq.code_categ_ingram = ligne[5]
                        else:
                            ligne_cinq.code_categ_ingram = ligne[5]
                        if ligne_cinq not in cat:
                            cat.append(ligne_cinq[0])
                    compteur+=1
                fichier.close()
                idss=product_categ.search([('code_categ_ingram','!=',False)])
                tab=[]
                for i in idss:
                    if i not in cat:
                        tab.append(i)
                        i.code_categ_ingram = '-1'
        return True
ingram_config()