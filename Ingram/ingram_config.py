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
from osv import fields, osv
import ftplib
import os
import time
import mx.DateTime
import os.path
import os
import csv, math
import datetime
import thread
import netsvc
import tools
import smtplib
import sys
from tools.translate import _
from datetime import date,datetime, timedelta
from dateutil.relativedelta import relativedelta

class ingram_rel_tax(osv.osv):
    _description = "Tax relation with configuration"    
    _columns={
               'id_tax' : fields.integer("id taxe"),
               'id_conf' : fields.integer("id conf"),
    }

class ingram_rel_tax_purchase(osv.osv):
    _name = "ingram_rel_tax_purchase"
    _description = "Tax relation with configuration"    
    _columns={
               'id_tax' : fields.integer("id taxe"),
               'id_conf' : fields.integer("id conf"),
    }

class ingram_config(osv.osv):
    _name = "ingram_config"
    _description = "Configuration Management Produces Ingram"    
    _columns={'name' : fields.char("Name",255,help="Name associated with the configuration", required=True),
              'xml_address' : fields.char('Server Xml address',255,help="server Xml address"),
              'xml_login' : fields.char('Login',255,help="Login for Xml request "),
              'xml_passwd' : fields.char('Password',255,help="Password for Xml Request"),
              'xml_active' : fields.boolean('XMl Request',help="Active the Xml Request"),
              'server_address' : fields.char('Server address',255,help="server ip address",required=True),
              'server_login' : fields.char('Login',255,help="Login database"),
              'server_passwd' : fields.char('Password',255,help="Password database"),
              'date_synchro' : fields.char('Date of last synchronization',255,readonly=True),
              'date_import' : fields.char('Date of last importation',255,readonly=True),
              'chemin' : fields.char("Path",255,help="Path where the files is stored", required=True),
              'mailto' : fields.char("Warning Mail",255,help="Encode the adresses e-mail separated by ';'.\nThose e-mail will receive the warnings", required=True),
              'synchro_active' : fields.boolean('Synchro active'),
              'taxes_iden' : fields.integer('taxe id'),
              'id_synchro' : fields.many2one('ir.cron','Cronjob', required=True, ondelete='cascade',help="Cronjob in OpenERP for automatic synchronization. To bind the Cronjob with the configuration, click the button"),
              'categorie_name' : fields.char('Category',255,help="Name of the product categorie"),
              'location_id': fields.many2one('stock.location', 'Location', required=True, domain="[('usage', '=', 'internal')]",help=" Location of new product"),
              'categorie_id':fields.many2one('product.category','Category', required=True, change_default=True, domain="[('type','=','normal')]" ,help="Select category for the current product"),
              'supplier_id' : fields.many2one('res.partner', 'Supplier', required=True,domain = [('supplier','=',True)], ondelete='cascade', help="Supplier of this product"),
              'taxes_id': fields.many2many('account.tax', 'product_taxes_rel',
                                    'prod_id', 'tax_id', 'Customer Taxes',
                                    domain=[('parent_id','=',False),('type_tax_use','in',['sale','all'])]),
              'supplier_taxes_id': fields.many2many('account.tax',
                                    'product_supplier_taxes_rel', 'prod_id', 'tax_id',
                                    'Supplier Taxes', domain=[('parent_id', '=', False),('type_tax_use','in',['purchase','all'])]),
              'taxes_ventes': fields.many2many('account.tax',
                                    'ingram_rel_tax', 'id_tax', 'id_conf',
                                    'ingram_config',domain=[('parent_id', '=', False),('type_tax_use','in',['sale','all'])]),
              'taxes_achats': fields.many2many('account.tax',
                                    'ingram_rel_tax_purchase', 'id_tax', 'id_conf',
                                    'ingram_config',domain=[('parent_id', '=', False),('type_tax_use','in',['purchase','all'])]),
    }
    
    def create(self, cr, uid, vals, context=None):
        ids=self.search(cr,uid,[])
        if len(ids)>0:
            raise osv.except_osv(_('Error !'), _('You can have only one configuration'))
        return super(ingram_config, self).create(cr, uid, vals, context)
    
    def sendTextMail(self,cr,uid,ids,title,mess):
        _from = 'Ingram Error <Ingram@bhc.be>'
        to=self.browse(cr,uid,ids[0]).mailto
        dest=''
        for i in to:
            dest+=i[0]
        dest=dest.split(';')
        _to = [] 
        for i in dest:
	        _to.append(i)
        _subject = title
        txt = "From:%s\r\nTo:%s\r\nSubject:%s\r\n" % (_from,_to,_subject)
        if mess:
            txt += "\r\n"
            txt += mess
            txt += "\r\n"
        s = smtplib.SMTP('relay.skynet.be')
        s.sendmail(_from, _to, txt)
        s.quit()

    def write(self, cr, uid, ids, values, context=None):
        idtaxevente=self.pool.get('ingram_config').browse(cr,uid,1).taxes_ventes
        idtaxeAchat=self.pool.get('ingram_config').browse(cr,uid,1).taxes_achats
        result = super(ingram_config, self).write(cr, uid, ids, values, context=context)
        if ('taxes_ventes' in values ):
                tab=[]
                tab2=[]
                tab3=[]
                for i in idtaxevente:
                    tab.append(i.id)
                for j in values['taxes_ventes'][0][2]:
                    if not ( j in tab ):
                        tab2.append(j)
                for i in idtaxevente:
                    if not ( i.id in values['taxes_ventes'][0][2] ):
                        tab3.append(i.id)
                if tab2:
                    idProd=self.pool.get('product.template').search(cr,uid,[('ingram','=',True),])
                    for j in idProd:
                        empl = self.pool.get('product.product').search(cr,uid,[('product_tmpl_id','=',j),])
                        for k in values['taxes_ventes'][0][2]:
                            self.pool.get('product.product').write(cr,uid,empl,{'taxes_id': [(4,k)]})
                if tab3:
                    idProd=self.pool.get('product.template').search(cr,uid,[('ingram','=',True),])
                    for j in idProd:
                        empl = self.pool.get('product.product').search(cr,uid,[('product_tmpl_id','=',j),])
                        for i in tab3:
                            self.pool.get('product.product').write(cr,uid,empl,{'taxes_id': [(3,i)]})
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
                    idProd=self.pool.get('product.template').search(cr,uid,[('ingram','=',True),])
                    for j in idProd:
                        empl = self.pool.get('product.product').search(cr,uid,[('product_tmpl_id','=',j),])
                        for i in values['taxes_achats'][0][2]:
                            self.pool.get('product.product').write(cr,uid,empl,{'supplier_taxes_id': [(4,i)]})
                if tab3:
                    idProd=self.pool.get('product.template').search(cr,uid,[('ingram','=',True),])
                    for j in idProd:
                        empl = self.pool.get('product.product').search(cr,uid,[('product_tmpl_id','=',j),])
                        for i in tab3:
                            self.pool.get('product.product').write(cr,uid,empl,{'taxes_id': [(3,i)]})
        return result 
    
    def cron_function(self,cr,uid,context=None):
        id_config = self.search(cr,uid,[('xml_active','=',True),])
        if not id_config:
            self.ajoutlog('no config')
            return False 
        config = self.read(cr,uid,id_config,['server_address','server_login','server_passwd','chemin'])
        chm=str(config[0]['chemin'])
        val=self.browse(cr,uid,id_config)[0].synchro_active
        if not val :
            self.write(cr,uid,id_config,{'synchro_active':True})
            self.ajoutlog('Debut téléchargement du catalogue')
            result=self.import_data(cr,uid,id_config,context)
            if result==True:
                self.ajoutlog('Téléchargement effectué')
            else:
                self.write(cr,uid,id_config,{'synchro_active':False})
                self.ajoutlog('Erreur lors du téléchargement')
                return False
            self.ajoutlog('Debut de la synchronisation des catégories')
            result2=self.synchro_categ(cr,uid,id_config,context)
            if result2==True:
                self.ajoutlog('Fin de la synchronisation des catégories')
            else:
                self.write(cr,uid,id_config,{'synchro_active':False})
                self.ajoutlog('Erreur lors de la synchronisation des catégories')
                return False
            self.ajoutlog('Debut de la synchronisation des produits')
            result3=self.synchronisation(cr,uid,id_config,context)
            if result3==True:
                self.ajoutlog('Fin de la synchronisation des produits')
            else:
                self.write(cr,uid,id_config,{'synchro_active':False})
                self.ajoutlog('Erreur lors de la synchronisation des produits')
                return False
            self.ajoutlog('Debut du nettoyage des produits')
            result4=self.clean_data(cr,uid,id_config,context)
            if result4==True:
                 self.ajoutlog('Fin du nettoyage des produits')
            else:
                self.ajoutlog('Erreur lors du nettoyage des produits')
                self.write(cr,uid,id_config,{'synchro_active':False})
                return False
            self.write(cr,uid,id_config,{'synchro_active':False})
        return True
    
    def button_import_data(self,cr,uid,ids,context=None):
        view = self.browse(cr,uid,ids)
        name_config = view[0].name        
        val=self.browse(cr,uid,ids)[0].synchro_active
        if not val :
            self.write(cr,uid,ids,{'synchro_active':True})
            id_config = self.search(cr,uid,[('name','=',name_config),])
            self.ajoutlog('Telechargement des fichiers')
            result=self.import_data(cr,uid,id_config,context)
            if result==True:
                self.ajoutlog('Fin du téléchargement')
                self.write(cr,uid,ids,{'synchro_active':False})
            else:
                self.ajoutlog('Erreur lors du téléchargement')
                self.write(cr,uid,ids,{'synchro_active':False})
                return False
        return True
    
    def import_data(self,cr,uid,id_config,context=None):
        config = self.read(cr,uid,id_config,['server_address','server_login','server_passwd','chemin'])
        ip = config[0]['server_address']
        login = config[0]['server_login']
        passwd = config[0]['server_passwd']
        chm=str(config[0]['chemin'])
        try:
            ftp=ftplib.FTP()
        except:
            logger = netsvc.Logger()
            logger.notifyChannel('BHC_Ingram', netsvc.LOG_CRITICAL,"Erreur Connexion")
            self.sendTextMail(cr,uid,id_config,"Erreur connexion","Une erreur est apparue lors de connexion au serveur FTP.\n\nDetail de cette erreur: \n\t %s" %(sys.exc_info()[0]))
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
            self.download(cr,uid,'.',chm,ftp)
            ftp.close()
            id_conf = self.search(cr,uid,[])
            self.write(cr,uid,id_conf,{'date_import' : time.strftime("%Y-%m-%d %H:%M:%S")})
            return True
        except:
           logger = netsvc.Logger()
           logger.notifyChannel('BHC_Ingram', netsvc.LOG_CRITICAL,"Erreur Téléchargement")
           self.sendTextMail(cr,uid,id_config,"Erreur Importation","Une erreur est apparue lors de l'importation du catalogue Ingram.\n\nDetail de cette erreur: \n\t %s" %(sys.exc_info()[0]))
           return False

    def clean_data(self,cr,uid,ids,context=None):
        try:
            aujourdhui = datetime.today()
            semaine=timedelta(weeks=1)
            date=aujourdhui - semaine
            idProd=self.pool.get('product.template').search(cr,uid,[('ingram','=',True),('last_synchro_ingram','<',date)])
            if idProd :
                for i in idProd:
                    print "n°",i
                    val=self.pool.get('product.product').search(cr,uid,[('product_tmpl_id','=',i)])
                    if val:
                        print val
                        self.pool.get('product.product').write(cr,uid,val[0],{'active':False})
            self.ajoutlog('donnnee nettoyee')
            return True
        except:
            logger = netsvc.Logger()
            logger.notifyChannel('BHC_Ingram', netsvc.LOG_CRITICAL,"Erreur Clean_data")
            self.sendTextMail(cr,uid,ids,"Erreur Nettoyage Produits","Une erreur est apparue lors du nettoyage des produits.\n\nDetail de cette erreur: \n\t %s" %(sys.exc_info()[0]))
            return False
    
    def delete_data(self,cr,uid,ids,context=None):
       idProd=self.pool.get('product.template').search(cr,uid,[('ingram','=',True),])
       for i in idProd:
           print "n ",i
           val=self.pool.get('product.product').search(cr,uid,[('product_tmpl_id','=',i)])
           if val:
               self.pool.get('product.product').write(cr,uid,val[0],{'active':False})
       self.ajoutlog('produits supprimés') 
       return True
   
    def synchro_data(self,cr,uid,ids,context=None):
        view = self.browse(cr,uid,ids)
        name_config = view[0].name        
        id_config = self.search(cr,uid,[('name','=',name_config),])
        val=self.browse(cr,uid,ids)[0].synchro_active
        if not val :
            self.write(cr,uid,ids,{'synchro_active':True})
            self.ajoutlog('Debut Synchronisation')
            result=self.synchro_categ(cr,uid,id_config,context)
            if result==True:
                self.ajoutlog('Fin de la synchronisation des categories')
            else:
                self.ajoutlog('Erreur lors de la synchronisation des categories')
                self.write(cr,uid,ids,{'synchro_active':False})
                return False
            result2=self.synchronisation(cr,uid,id_config,context)
            if result2==True:
                self.ajoutlog('Fin de la synchronisation des produits')
            else:
                self.ajoutlog('Erreur lors de la synchronisation des produits')
                self.write(cr,uid,ids,{'synchro_active':False})
                return False
            self.write(cr,uid,ids,{'synchro_active':False})
        return True 
        
    def synchronisation(self,cr,uid,id_config,context=None):   
        config = self.read(cr,uid,id_config,['server_address','server_login','server_passwd','location_id','categorie_id','supplier_id','chemin'])
        location = config[0]['location_id']
        categ = config[0]['categorie_id']
        supplier= config[0]['supplier_id']
        chm=str(config[0]['chemin'])
        listefich = os.listdir(chm+'/')
        date=datetime.now()    
        try:
            compteur=0
            for i in listefich:
                if str(i)=="Price2.txt" :
                    fichier = open(chm+'/'+i,'rb')
                    fichiercsv = csv.reader(fichier, delimiter=',')
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

                            desc=ligne[13]
                            descr=''
                            lgt=len(desc)
                            j=0
                            while (j < lgt):
                            	try:
                                    desc[j].decode('latin-1')
                                    descr +=desc[j]
                                    j+=1
                                except:
                                    j+=1
                            desc=descr

                            print "n:",compteur , nom

                            empl = self.pool.get('product.product').search(cr,uid,[('default_code','=',ligne[0]),])
                            if empl:
                                resultas =self.pool.get('product.product').read(cr,uid,empl,['product_tmp'])
                                idprod = resultas[0]['product_tmpl_id']
                                categ_ingram=self.pool.get('product.category').search(cr,uid,[('code_categ_ingram','=',ligne[7])])
                                if not categ_ingram:
                                    categ_ingram=categ
                                if ligne[8]=='X' or not ligne[8]:
                                    ligne[8]='0.0'
                                self.pool.get('product.template').write(cr,uid,[idprod],{'name':nom,'type':'consu','standard_price':float(ligne[8]),'weight_net':float(ligne[6]),'description':desc,'categ_id':categ_ingram[0],'type':'product','ingram':True,'last_synchro_ingram':time.strftime("%Y-%m-%d %H:%M:%S")})
                                idtaxesvente=self.pool.get('ingram_config').browse(cr,uid,1).taxes_ventes
                                for i in idtaxesvente:
                                    val=self.pool.get('product.product').browse(cr,uid,empl)
                                    for k in val:
                                        val2=k.taxes_id
                                        if not val2:
                                            self.pool.get('product.product').write(cr,uid,empl,{'taxes_id': [(4,i.id)]})    
                                idtaxesAchat=self.pool.get('ingram_config').browse(cr,uid,1).taxes_achats
                                for i in idtaxesAchat:
                                    val=self.pool.get('product.product').browse(cr,uid,empl)
                                    for k in val:
                                        val2=k.supplier_taxes_id
                                        if not val2:
                                            self.pool.get('product.product').write(cr,uid,empl,{'supplier_taxes_id': [(4,i.id)]})
                                
                                if (len(ligne[2])==12):
                                    ligne[4]="0"+ligne[4]
                                if len(ligne[2]) == 13 :
                                     self.pool.get('product.product').write(cr,uid,empl,{'default_code':ligne[0],'name_template':nom,
                                        'price_extra':0.00,'active':'TRUE','ean13':ligne[2],'vpn':ligne[1],'manufacturer':ligne[5],'active':True})
                                else:
                                    self.pool.get('product.product').write(cr,uid,empl,{'default_code':ligne[0],'name_template':nom,
                                        'price_extra':0.00,'active':'TRUE','vpn':ligne[1],'manufacturer':ligne[5],'active':True})
                                compteur+=1
                            else:
                                if(True):
                                    categ_ingram=self.pool.get('product.category').search(cr,uid,[('code_categ_ingram','=',ligne[7])])
                                    if not categ_ingram:
                                        categ_ingram=categ
                                    if ligne[8]=='X' or not ligne[8]:
                                        ligne[8]='0.0'
                                    id=self.pool.get('product.template').create(cr,uid,{'name':nom,'type':'consu',
                                    'standard_price':float(ligne[8]),'weight_net':float(ligne[6]),
                                    'description':desc,'categ_id':categ_ingram[0],'procure_method':'make_to_order',
                                    'ingram':True,'type':'product','last_synchro_ingram':time.strftime("%Y-%m-%d %H:%M:%S")})
                                    idtaxesvente=self.pool.get('ingram_config').browse(cr,uid,1).taxes_ventes
                                    idtaxesAchat=self.pool.get('ingram_config').browse(cr,uid,1).taxes_achats                               
                                    if (len(ligne[2])==12):
                                         ligne[4]="0"+ligne[4]
                                    if len(ligne[2]) == 13 :
                                        
                                        id_prod=self.pool.get('product.product').create(cr,uid,{'default_code':ligne[0],'name_template':nom,
                                                            'price_extra':0.00,'active':'TRUE','product_tmpl_id':id,'ean13':ligne[2],'vpn':ligne[1],'manufacturer':ligne[5],
                                                            })

                                        for i in idtaxesvente:
                                            self.pool.get('product.product').write(cr,uid,id_prod,{'taxes_id': [(4,i.id)]})
                                        for i in idtaxesAchat:
                                            self.pool.get('product.product').write(cr,uid,id_prod,{'supplier_taxes_id': [(4,i.id)]})
                                                                           
                                    else:
                                        id_prod=self.pool.get('product.product').create(cr,uid,{'default_code':ligne[0],'name_template':nom,
                                                            'price_extra':0.00,'active':'TRUE','product_tmpl_id':id,'vpn':ligne[1],'manufacturer':ligne[5],
                                                            })
                                        for i in idtaxesvente:
                                            self.pool.get('product.product').write(cr,uid,id_prod,{'taxes_id': [(4,i.id)]})
                                        for i in idtaxesAchat:
                                            self.pool.get('product.product').write(cr,uid,id_prod,{'supplier_taxes_id': [(4,i.id)]})
                                    self.pool.get('product.supplierinfo').create(cr,uid,{'name':supplier[0],'min_qty':0,'product_id':id})
                                    compteur+=1
                    fichier.close()
            id_conf = self.search(cr,uid,[])
            self.write(cr,uid,id_conf,{'date_synchro' : time.strftime("%Y-%m-%d %H:%M:%S")}) 
            return True       
        except:
            logger = netsvc.Logger()
            logger.notifyChannel('BHC_Ingram', netsvc.LOG_CRITICAL,"Erreur Synchro_produit")
            self.sendTextMail(cr,uid,id_config,"Erreur Synchronisation Produits","Une erreur est apparue lors de la synchronisation des produits.\n \nDetail de cette erreur: \n\t %s" %(sys.exc_info()[0]))
            return False    
       
    def download(self,cr,uid,pathsrc, pathdst,ftp):
        try:
            lenpathsrc = len(pathsrc)
            l = ftp.nlst(pathsrc)
            for i in l:
                tailleinit=ftp.size(i)
                if (str(i)=="PCAT_GENERIC.TXT") | (str(i)=="PRICE_GENERIC.TXT") | (str(i)=="FEES_GENERIC.TXT") | (str(i)=="Price2.txt"):
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
   
    def product_qty(self, cr, uid, ids,qty,prod_id,location,context=None):
        date = time.strftime("%Y-%m-%d %H:%M:%S")
        listid = self.pool.get('stock.inventory').search(cr,uid,[('name','=','INV Ingram'+str(time.strftime("%Y-%m-%d")))])
        if (listid):
            id_Inv=listid[0]
        else:            
            id_Inv=self.pool.get('stock.inventory').create(cr,uid,{'state':'draft','name':'INV Ingram'+str(time.strftime("%Y-%m-%d")),'date_done':date,'write_date':date})
        self.pool.get('stock.inventory.line').create(cr,uid,{'compagny_id':1,'inventory_id':int(id_Inv),'product_qty':qty,'location_id':location,'product_id': int(prod_id),'product_uom' : 1})
        return True
    
    def synchro_categ(self,cr,uid,id_config,context=None):
        config = self.read(cr,uid,id_config,['server_address','server_login','server_passwd','location_id','categorie_id','supplier_id','chemin'])
        categ = config[0]['categorie_id']
        categ = categ[0]
        chm=str(config[0]['chemin'])
        listefich = os.listdir(chm+'/')
        try:
            compteur=0
            for i in listefich:
                if str(i)=="PCAT_GENERIC.TXT" :
                    fichier = open(chm+'/'+i,'rb')
                    fichiercsv = csv.reader(fichier, delimiter=';')
                    idparent=-1
                    idenf=-1
                    idparOpen=0
                    idenfOpen=0
                    for ligne in fichiercsv:
                        print "n:",compteur
                        if not(self.pool.get('product.category').search(cr,uid,[('code_categ_ingram','=',ligne[1])])):
                            if (ligne[1]!= idparent):
                                idparOpen=self.pool.get('product.category').create(cr,uid,{'name':ligne[2],'parent_id':categ,'categ_ingram':ligne[2],'code_categ_ingram':ligne[1]})
                                idparent=ligne[1]    
                        else:
                            if (ligne[1]!= idparent):
                                idparOpen=self.pool.get('product.category').search(cr,uid,[('code_categ_ingram','=',ligne[1])])[0]
                                idparent=ligne[1]    
                                if (ligne[3] != idenf):
                                    if (self.pool.get('product.category').search(cr,uid,[('code_categ_ingram','=',ligne[3])])):
                                        idenfOpen=self.pool.get('product.category').search(cr,uid,[('code_categ_ingram','=',ligne[3])])[0]
                                    else:
                                        idenfOpen=self.pool.get('product.category').create(cr,uid,{'name':ligne[4],'parent_id':idparOpen,'categ_ingram':ligne[4],'code_categ_ingram':ligne[3]})
                                    idenf=ligne[3]
                                    if not (self.pool.get('product.category').search(cr,uid,[('code_categ_ingram','=',ligne[5])])):
                                            self.pool.get('product.category').create(cr,uid,{'name':ligne[6],'parent_id':idenfOpen,'categ_ingram':ligne[6],'code_categ_ingram':ligne[5]})
                                else:
                                    if not (self.pool.get('product.category').search(cr,uid,[('code_categ_ingram','=',ligne[5])])):
                                        self.pool.get('product.category').create(cr,uid,{'name':ligne[6],'parent_id':idenfOpen,'categ_ingram':ligne[6],'code_categ_ingram':ligne[5]})
                            else:
                                if (ligne[3] != idenf):
                                    if (self.pool.get('product.category').search(cr,uid,[('code_categ_ingram','=',ligne[3])])):
                                        idenfOpen=self.pool.get('product.category').search(cr,uid,[('code_categ_ingram','=',ligne[3])])[0]
                                    else:
                                        idenfOpen=self.pool.get('product.category').create(cr,uid,{'name':ligne[4],'parent_id':idparOpen,'categ_ingram':ligne[4],'code_categ_ingram':ligne[3]})
                                    idenf=ligne[3]
                                    if not (self.pool.get('product.category').search(cr,uid,[('code_categ_ingram','=',ligne[5])])):
                                        self.pool.get('product.category').create(cr,uid,{'name':ligne[6],'parent_id':idenfOpen,'categ_ingram':ligne[6],'code_categ_ingram':ligne[5]})
                                else:
                                    if not (self.pool.get('product.category').search(cr,uid,[('code_categ_ingram','=',ligne[5])])):
                                        self.pool.get('product.category').create(cr,uid,{'name':ligne[6],'parent_id':idenfOpen,'categ_ingram':ligne[6],'code_categ_ingram':ligne[5]})
                        compteur+=1
        except:
            logger = netsvc.Logger()
            logger.notifyChannel('BHC_Ingram', netsvc.LOG_CRITICAL,"Erreur Synchro_categorie")
            self.sendTextMail(cr,uid,id_config,"Erreur Categories","Une erreur est apparue lors de la synchronisation des categories.\n \nDetail de cette erreur: \n\t %s" %(sys.exc_info()[0]))
            return False
        return True

    def ajoutlog(self,txt):
        logger = netsvc.Logger()
        logger.notifyChannel('BHC_Ingram', netsvc.LOG_INFO, txt)
ingram_config()