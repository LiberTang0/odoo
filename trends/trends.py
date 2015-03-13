# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp import addons
import logging
from openerp.osv import fields, osv
from openerp import tools
from openerp.tools.translate import _
import time
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta 
import httplib
import urllib
import urllib2
import base64
from xml.dom.minidom import parse, parseString

#Only some information can be save
#This filter give us the code we can show
FILTER = {'R012','R015','R070','R071','R026','R034','R072','RA01','RA02','RA25','RA05'}

class trends_config(osv.osv):
    _name = "trends.config"
    _description = "Configuration for trends"
    
    __currentNode__ = None
    
    _columns = {
        'name':fields.char('Login', size=512, required=True),
        'pwd': fields.char('Password', size=512, required=True),
        'api_key': fields.char('API Key', size=512, required=True),
        'language': fields.selection([('fr', 'FR'),('nl', 'NL'),('en', 'EN')], 'Language',required=True),
        'url': fields.char('URL', size=1024, required=True),
        'type': fields.selection([('xml', 'XML'),], 'Type',required=True),
        'states':fields.char('States', size=1024,), 
        'user_id': fields.many2one('res.users', 'User'),
        'credit':fields.integer('credit'),
        'save':fields.boolean('Save data', help='If checked, we save data after the importation (only if you have enough credit)'),

    }
    
    _defaults = {
        'type': 'xml',
        'language': 'fr',
        'url': 'https://webapi.trendstop.be/api1/',
        'save':1,
                 
    }
    
    def _check_login(self, cr, uid, ids, context=None):
        if ids:
            current = self.browse(cr, uid, ids[0])
            vals_ids = self.search(cr,uid,[('name','=',current.name)])
            if vals_ids:
                vals_ids.remove(ids[0])
                if vals_ids:
                    return False
        return True

    _constraints = [                                                                                                                                                                                                                         
        (_check_login, 'The login must be unique.', ['name'])
    ]  
    
    def create(self, cr, uid, vals, context=None):                                                                                                                                                           
        #check if there is already an account for this user
        user_ids = self.search(cr, uid, [('user_id','=',vals.get('user_id'))])       
        if user_ids:
            raise osv.except_osv(_('Warning!'),_("You can't have two trends account for the same user"))  
        try:                                                                                                                                                                       
            #create base url
            url = vals.get('url') 
            url = url+"/credits"  
            #call Web service
            name = vals.get('name')
            pwd = vals.get('pwd')
            authKey = base64.b64encode( name+":"+ pwd)
            type= vals.get('type')
            api_key=vals.get('api_key')
            lang = vals.get('language')
            headers = {"Content-Type":"application/"+ type , "Authorization":"Basic " + authKey, "X-AuthKey" : api_key, "Accept-Language":lang.upper()}
            request = urllib2.Request(url)
             
            for key,value in headers.items():
                request.add_header(key,value)
             
            response = urllib2.urlopen(request)
            res= response.read()    
            #call method to read the answer
            vals['credit']=self.conf_readxml(cr, uid, [], res, "credit")   
                      
        except:
            vals['states']=_('Connection Impossible')                             
        return super(trends_config, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):              
        try:      
            conf_brw = self.browse(cr ,uid, ids[0])                  
            user_id = vals.get('user_id') or conf_brw.user_id.id
            user_ids = self.search(cr, uid, [('user_id','=',user_id)])
        except:
            vals['states']=_('Connection Impossible')  
        #we can't count the one we are writting on
        if ids[0] in user_ids:
            user_ids.remove(ids[0])
        if len(user_ids)>=1:
            
            raise osv.except_osv(_('Warning!'),_("You can't have two trends account for the same user"))                 
        try:                                                                                                                     
            #create base url
            url = vals.get('url') or conf_brw.url 
            url = url+"/credits"  
            #call Web service
            name = vals.get('name') or conf_brw.name
            pwd = vals.get('pwd')or conf_brw.pwd
            authKey = base64.b64encode( name+":"+ pwd)
            type= vals.get('type') or conf_brw.type
            api_key=vals.get('api_key') or conf_brw.api_key
            lang = vals.get('language') or conf_brw.language
            headers = {"Content-Type":"application/"+ type , "Authorization":"Basic " + authKey, "X-AuthKey" : api_key, "Accept-Language":lang.upper()}
            request = urllib2.Request(url)
             
            for key,value in headers.items():
                request.add_header(key,value)
             
            response = urllib2.urlopen(request)
            res= response.read()    
            if not vals.get('credit'):
                #call method to read the answer
                vals['credit']=self.conf_readxml(cr, uid, ids[0], res, "credit")         
        except:
            vals['states']=_('Connection Impossible')    
        return super(trends_config, self).write(cr, uid, ids, vals, context=context)

        
    def action_load_sectorlist(self, cr, uid, ids, *args):
        try:
            r=self.browse(cr, uid, ids[0]) 
            #create base url
            url = r.url +"/sectorlist"  
            #call Web service
            authKey = base64.b64encode(r.name+":"+r.pwd)
            headers = {"Content-Type":"application/"+r.type , "Authorization":"Basic " + authKey, "X-AuthKey" : r.api_key, "Accept-Language":r.language.upper()}
            request = urllib2.Request(url)
             
            for key,value in headers.items():
                request.add_header(key,value)
             
            response = urllib2.urlopen(request)
            res= response.read()
            #call method to read the answer
            self.conf_readxml(cr, uid, r.id, res, "sectorlist") 
            self.write (cr ,uid, ids, {'states': _('Sector list loaded'),})      
            
        except:
            self.write (cr ,uid, ids, {'states': _('Impossible to load sector list'),})
                             
        return True    
    
    def action_load_nacebellist(self, cr, uid, ids, *args):
        try:
            r=self.browse(cr, uid, ids[0])
            #create base url
            url = r.url +"/nacebellist"  
            #call Web service
            authKey = base64.b64encode(r.name+":"+r.pwd)
            headers = {"Content-Type":"application/"+r.type , "Authorization":"Basic " + authKey, "X-AuthKey" : r.api_key, "Accept-Language":r.language.upper()}
            request = urllib2.Request(url)
             
            for key,value in headers.items():
                request.add_header(key,value)
             
            response = urllib2.urlopen(request)
            res= response.read()
            #call method to read the answer
            self.conf_readxml(cr, uid, r.id, res, "nacebellist")   
            self.write (cr ,uid, ids, {'states': _('Nacerbel list loaded'),})             
        except:
            self.write (cr ,uid, ids, {'states': _('Impossible to load nacebel list'),})
                                                 
        return True   
     
    def action_load_figurelist(self, cr, uid, ids, *args):
        try:
            r=self.browse(cr, uid, ids[0])   
            #create base url
            url = r.url +"/figurelist"  
            #call Web service
            authKey = base64.b64encode(r.name+":"+r.pwd)
            headers = {"Content-Type":"application/"+r.type , "Authorization":"Basic " + authKey, "X-AuthKey" : r.api_key, "Accept-Language":r.language.upper()}
            request = urllib2.Request(url)
             
            for key,value in headers.items():
                request.add_header(key,value)
             
            response = urllib2.urlopen(request)
            res= response.read()          
            # call method to read the answer
            self.conf_readxml(cr, uid, r.id, res, "figurelist")     
            self.write (cr ,uid, ids, {'states': _('Figure list loaded'),})                
        except:
            self.write (cr ,uid, ids, {'states': _('Impossible to load Figure list'),})                   
        return True  
      
    def action_load_functionlist(self, cr, uid, ids, *args):
        try:
            r=self.browse(cr, uid, ids[0]) 
            #create base url
            url = r.url +"/functionlist"  
            #call Web service
            authKey = base64.b64encode(r.name+":"+r.pwd)
            headers = {"Content-Type":"application/"+r.type , "Authorization":"Basic " + authKey, "X-AuthKey" : r.api_key, "Accept-Language":r.language.upper()}
            request = urllib2.Request(url)
             
            for key,value in headers.items():
                request.add_header(key,value)
             
            response = urllib2.urlopen(request)
            res= response.read()
            #call method to read the answer
            self.conf_readxml(cr, uid, r.id, res, "functionlist")    
            self.write (cr ,uid, ids, {'states': _('Function list loaded'),})             
        except:
            self.write (cr ,uid, ids, {'states': _('Impossible to load function list'),})     
        return True 
        
    def action_update_credit(self, cr, uid, ids, *args):
        try:
            r=self.browse(cr, uid, ids[0]) 
            #create base url
            url = r.url +"/credits"  
            #call Web service
            authKey = base64.b64encode(r.name+":"+r.pwd)
            headers = {"Content-Type":"application/"+r.type , "Authorization":"Basic " + authKey, "X-AuthKey" : r.api_key, "Accept-Language":r.language.upper()}
            request = urllib2.Request(url)
             
            for key,value in headers.items():
                request.add_header(key,value)
             
            response = urllib2.urlopen(request)
            res= response.read()
            #call method to read the answer
            remaining = self.conf_readxml(cr, uid, ids[0], res, "credit")
            self.write (cr ,uid, ids, {'credit':remaining,'states': _('Credit refreshed'),})             
        except:
            self.write (cr ,uid, ids, {'states': _('Impossible to interract with your credit'),})     
        return True                 
    
    def conf_readxml(self, cr, uid, ids,response, element, *args):
        self.doc = parseString(response)
        self.__currentNode__ = None          
        if element == "sectorlist":
            search_ids = self.pool.get('trends.sectorlist').search(cr, uid, [])
            self.pool.get('trends.sectorlist').unlink(cr, uid, search_ids)             
            for sector in self.getRootElement().getElementsByTagName("Sector"):
                if sector.nodeType == sector.ELEMENT_NODE:                                                          
                    self.pool.get('trends.sectorlist').create(cr, uid,{                                                               
                            'name' : self.getText(sector.getElementsByTagName("Description") or ''),
                            'description_long' : self.getText(sector.getElementsByTagName("DescriptionLong") or ''),
                            'code': self.getText(sector.getElementsByTagName("SectorCode") or ''),
                        })          

                    
        elif element == "nacebellist":
            search_ids = self.pool.get('trends.nacebellist').search(cr, uid, [])
            self.pool.get('trends.nacebellist').unlink(cr, uid, search_ids)             
            for nacebel in self.getRootElement().getElementsByTagName("Nacebel"):
                if nacebel.nodeType == nacebel.ELEMENT_NODE:                                                          
                    self.pool.get('trends.nacebellist').create(cr, uid,{                                                               
                            'name' : self.getText(nacebel.getElementsByTagName("Description") or ''),
                            'code': self.getText(nacebel.getElementsByTagName("NaceCode") or ''),
                        })          

                    
        elif element == "figurelist":
            search_ids = self.pool.get('trends.figurelist').search(cr, uid, [])
            self.pool.get('trends.figurelist').unlink(cr, uid, search_ids)             
            for figure in self.getRootElement().getElementsByTagName("FigureDescription"):
                if figure.nodeType == figure.ELEMENT_NODE:
                    if self.getText(figure.getElementsByTagName("FigureCode")) in FILTER:                                                         
                        self.pool.get('trends.figurelist').create(cr, uid,{                                                               
                                'name' : self.getText(figure.getElementsByTagName("Description") or ''),
                                'code': self.getText(figure.getElementsByTagName("FigureCode") or ''),
                            })   
                    
        elif element == "functionlist":
            search_ids = self.pool.get('trends.functionlist').search(cr, uid, [])
            self.pool.get('trends.functionlist').unlink(cr, uid, search_ids)             
            for function in self.getRootElement().getElementsByTagName("FunctionDescription"):
                if function.nodeType == function.ELEMENT_NODE:                                                          
                    self.pool.get('trends.functionlist').create(cr, uid,{                                                               
                            'name' : self.getText(function.getElementsByTagName("Description") or ''),
                            'code': self.getText(function.getElementsByTagName("FunctionCode") or ''),
                        })                                

        elif element == "credit":                                                         
            return self.getText(self.getRootElement().getElementsByTagName("Remaining") or 0)
              
                                          
        else:
            self.write (cr ,uid, ids, {'states': _('The type is not defined'),})
        self.__currentNode__ = None  
        return True 
    
    def getRootElement(self):
        if self.__currentNode__ == None:
            self.__currentNode__ = self.doc.documentElement
        return self.__currentNode__
            

    def getText(self, node):
        if node and node[0] and node[0].childNodes and node[0].childNodes[0] and node[0].childNodes[0].nodeValue:
            return node[0].childNodes[0].nodeValue
        else:
            return False        
      
trends_config()

class trends_search(osv.osv):
    _name = "trends.search"
    _description = "Search on trends"
    
    __currentNode__ = None

    _columns = {
        'configuration': fields.many2one('trends.config', 'Configuration', required=True),
        'name': fields.char('name',size=512),
        'search_type':fields.selection([('who', 'who'),('vat', 'vat'),], 'Search type',),
        'who': fields.char('Who', size=512,),
        'where': fields.char('Where', size=512),
        'vat': fields.char('VAT', size=512),        
        'vat_type': fields.selection([('empty', 'Empty'),('ranking', 'Ranking'),('management', 'Management'),('ratios', 'Ratios'),('figures', 'Figures'),('social', 'Social')], 'Type VAT search',),
        'res_who': fields.one2many('trends.who', 'trends_search_id', "Who answer"),
        'res_tva_management': fields.one2many('trends.tva.management', 'trends_search_id', "VAT management answer"),
        'res_tva_empty': fields.one2many('trends.tva.empty', 'trends_search_id', "VAT answer"),   
        'res_tva_ranking': fields.one2many('trends.tva.ranking', 'trends_search_id', "VAT ranking answer"),     
        'res_tva_figures': fields.one2many('trends.tva.figures', 'trends_search_id', "VAT figures answer"),     
        'res_tva_ratios': fields.one2many('trends.tva.ratios', 'trends_search_id', "VAT ratios answer"),  
        'res_tva_social': fields.one2many('trends.tva.social', 'trends_search_id', "VAT social answer"),  
        'states': fields.char('States', size=1024,),                                     
    }
    _defaults = {
        'search_type':"who",
    }
    
    def action_search_trends(self, cr, uid, ids, *args):
        try:
            r=self.browse(cr, uid, ids[0]) 
            #create base url
            url = r.configuration.url
            #different url for who or vat
            if r.search_type == 'who':
                url = url+"/companies/?who="+r.who
                if r.where:
                    url = url+"&where="+r.where
            elif r.search_type == 'vat':
                url = url+"/company/"+r.vat
                if r.vat_type and r.vat_type != "empty":            
                    url=url+"/"+str(r.vat_type)+"/"
            else:
                raise osv.except_osv(_('Error !'),_('You need to define a search type'))
            #call Web service
            authKey = base64.b64encode(r.configuration.name+":"+r.configuration.pwd)
            headers = {"Content-Type":"application/"+r.configuration.type , "Authorization":"Basic " + authKey, "X-AuthKey" : r.configuration.api_key, "Accept-Language":r.configuration.language.upper()}
            request = urllib2.Request(url)
             
            for key,value in headers.items():
                request.add_header(key,value)        
            response = urllib2.urlopen(request)
            res= response.read()
            #read the answer
            if r.vat_type:
                self.readxml(cr, uid, r.id, res, r.search_type, r.vat_type,"search")
            else:
                self.readxml(cr, uid, r.id, res, r.search_type, "")
        except:
            self.write (cr ,uid, ids, {'states': _('Impossible to do this action'),})   
        return True



    def readxml(self, cr, uid, ids,response, trends_type, vat_type,object, *args):
        self.doc = parseString(response)
        if trends_type == "who":
            search_ids = self.pool.get('trends.who').search(cr, uid, [('trends_search_id','=',ids)])
            self.pool.get('trends.who').unlink(cr, uid, search_ids)             
            for who in self.getRootElement().getElementsByTagName("CompanySearchResult"):
                if who.nodeType == who.ELEMENT_NODE:     
                    #find the sector name from the code 
                    sector = ''
                    sector_ids = self.pool.get('trends.sectorlist').search(cr ,uid, [('code','=',self.getText(who.getElementsByTagName("SectorCode") or ''))])
                    if sector_ids:
                        sector = self.pool.get('trends.sectorlist').browse(cr ,uid, sector_ids[0]).name                                                                           
                    self.pool.get('trends.who').create(cr, uid,{ 
                            'city' : self.getText(who.getElementsByTagName("City") or ''),                                                                    
                            'name' : self.getText(who.getElementsByTagName("Name") or ''),
                            'zip' : self.getText(who.getElementsByTagName("PostalCode") or ''),
                            'sectore_code': self.getText(who.getElementsByTagName("SectorCode") or ''),
                            'vat' : self.getText(who.getElementsByTagName("Vat") or ''),    
                            'trends_search_id': ids,
                            'sectore': sector,
                        })   
          

                
        elif trends_type == "vat":
            if vat_type == "management":
                #search_ids = self.pool.get('trends.tva.management').search(cr, uid, [('trends_search_id','=',ids)])
                if object =='partner':
                    search_ids = self.pool.get('trends.tva.management').search(cr, uid, [('partner_search_id','=',ids)])
                elif object =='crm':
                    search_ids = self.pool.get('trends.tva.management').search(cr, uid, [('crm_search_id','=',ids)])  
                elif object =='who_search':                
                    search_ids = self.pool.get('trends.tva.management').search(cr, uid, [('trends_whoo_id','=',ids)])
                else:
                    search_ids = self.pool.get('trends.tva.management').search(cr, uid, [('trends_search_id','=',ids)])                                                        
                self.pool.get('trends.tva.management').unlink(cr, uid, search_ids) 
                for vat_management in self.getRootElement().getElementsByTagName("CompanyManagement"):
                    if vat_management.nodeType == vat_management.ELEMENT_NODE:   
                        val = { 
                                'vat' : self.getText(vat_management.getElementsByTagName("Vat") or ''),                                                                                   
                                'email' : self.getText(vat_management.getElementsByTagName("Email") or ''),                                                                    
                                'name' : self.getText(vat_management.getElementsByTagName("Name") or ''),
                                'function' : self.getText(vat_management.getElementsByTagName("Function") or ''),
                                'function_code': self.getText(vat_management.getElementsByTagName("FunctionCode") or ''),
                                'language_code' : self.getText(vat_management.getElementsByTagName("LanguageCode") or ''),   
                                'gender' : self.getText(vat_management.getElementsByTagName("Gender") or ''),   
                                'last_name' : self.getText(vat_management.getElementsByTagName("LastName") or ''),                                                                                                   
                                #'trends_search_id': ids,                               
                        } 
                        if object == 'partner':
                            val['partner_search_id']= ids,
                        elif object =='crm':
                            val['crm_search_id'] = ids, 
                        elif object =='who_search':
                            val['trends_whoo_id']=ids,
                        else:
                            val['trends_search_id'] =ids,                                                        
                        self.pool.get('trends.tva.management').create(cr, uid,val)     
                                           
            elif vat_type == "social":
                #search_ids = self.pool.get('trends.tva.social').search(cr, uid, [('trends_search_id','=',ids)])
                if object =='partner':
                    search_ids = self.pool.get('trends.tva.social').search(cr, uid, [('partner_search_id','=',ids)])
                elif object =='crm':
                    search_ids = self.pool.get('trends.tva.social').search(cr, uid, [('crm_search_id','=',ids)])  
                elif object =='who_search':                
                    search_ids = self.pool.get('trends.tva.social').search(cr, uid, [('trends_whoo_id','=',ids)])                    
                else:
                    search_ids = self.pool.get('trends.tva.social').search(cr, uid, [('trends_search_id','=',ids)])                                    
                self.pool.get('trends.tva.social').unlink(cr, uid, search_ids)                    
                vat_social = self.getRootElement()  
                if vat_social: 
                    val = { 
                            'vat' : self.getText(vat_social.getElementsByTagName("Vat") or ''),                                                                                   
                            'balancetype' : self.getText(vat_social.getElementsByTagName("BalanceType") or ''),                                                                    
                            'durationmonths' : self.getText(vat_social.getElementsByTagName("DurationMonths") or ''),    
                            'financial_year' : self.getText(vat_social.getElementsByTagName("FinancialYear") or ''),                                                                                                                                                                                                            
                        }
                    if object == 'partner':
                        val['partner_search_id']= ids,
                    elif object =='crm':
                        val['crm_search_id'] = ids,
                    elif object =='who_search':
                        val['trends_whoo_id'] = ids,                        
                    else:
                        val['trends_search_id'] = ids,                                                                                                                      
                    social_id = self.pool.get('trends.tva.social').create(cr, uid,val)    
                    
                    for fig in self.getRootElement().getElementsByTagName("CompanyFigure"):
                        if fig.nodeType == fig.ELEMENT_NODE:      
                            description = ''
                            description_ids = self.pool.get('trends.figurelist').search(cr ,uid, [('code','=',self.getText(fig.getElementsByTagName("Code") or ''))])
                            if description_ids:
                                description = self.pool.get('trends.figurelist').browse(cr ,uid, description_ids[0]).name                                                  
                            self.pool.get('trends.figures.social').create(cr, uid,{ 
                                    'name' : self.getText(fig.getElementsByTagName("Code") or ''),                                                                                   
                                    'value' : self.getText(fig.getElementsByTagName("Value") or ''),                                                                                                                                                                                                                        
                                    'trends_figures_id': social_id,
                                    'description':description,
                                })                            

                                            
            elif vat_type == "ratios":
                if object =='partner':
                    search_ids = self.pool.get('trends.tva.ratios').search(cr, uid, [('partner_search_id','=',ids)])
                elif object =='crm':
                    search_ids = self.pool.get('trends.tva.ratios').search(cr, uid, [('crm_search_id','=',ids)]) 
                elif object =='who_search':                
                    search_ids = self.pool.get('trends.tva.ratios').search(cr, uid, [('trends_whoo_id','=',ids)])                        
                else:
                    search_ids = self.pool.get('trends.tva.ratios').search(cr, uid, [('trends_search_id','=',ids)])                                  
                self.pool.get('trends.tva.ratios').unlink(cr, uid, search_ids)                    
                vat_ratios = self.getRootElement()  
                if vat_ratios:    
                    val = { 
                            'vat' : self.getText(vat_ratios.getElementsByTagName("Vat") or ''),                                                                                   
                            'balancetype' : self.getText(vat_ratios.getElementsByTagName("BalanceType") or ''),                                                                    
                            'durationmonths' : self.getText(vat_ratios.getElementsByTagName("DurationMonths") or ''),    
                            'financial_year' : self.getText(vat_ratios.getElementsByTagName("FinancialYear") or ''),                                                                                                                                                                                                            
                        }
                    
                    if object == 'partner':
                        val['partner_search_id']= ids,
                    elif object =='crm':
                        val['crm_search_id'] = ids,  
                    elif object =='who_search':  
                        val['trends_whoo_id'] = ids,                      
                    else:
                        val['trends_search_id'] = ids,                                                                                        
                    ratios_id = self.pool.get('trends.tva.ratios').create(cr, uid,val)    
                    for fig in self.getRootElement().getElementsByTagName("CompanyFigure"):
                        if fig.nodeType == fig.ELEMENT_NODE: 
                            description = ''
                            description_ids = self.pool.get('trends.figurelist').search(cr ,uid, [('code','=',self.getText(fig.getElementsByTagName("Code") or ''))])
                            if description_ids:
                                description = self.pool.get('trends.figurelist').browse(cr ,uid, description_ids[0]).name                                                       
                                self.pool.get('trends.figures.ratios').create(cr, uid,{ 
                                        'name' : self.getText(fig.getElementsByTagName("Code") or ''),                                                                                   
                                        'value' : self.getText(fig.getElementsByTagName("Value") or ''),                                                                                                                                                                                                                        
                                        'trends_figures_id': ratios_id,
                                        'description':description,
                                    })                       
                                           
                                                                    

            elif vat_type == "figures":
                if object =='partner':
                    search_ids = self.pool.get('trends.tva.figures').search(cr, uid, [('partner_search_id','=',ids)])
                elif object =='crm':
                    search_ids = self.pool.get('trends.tva.figures').search(cr, uid, [('crm_search_id','=',ids)])  
                elif object =='who_search':                
                    search_ids = self.pool.get('trends.tva.figures').search(cr, uid, [('trends_whoo_id','=',ids)])                    
                else:
                    search_ids = self.pool.get('trends.tva.figures').search(cr, uid, [('trends_search_id','=',ids)])                                     
                #search_ids = self.pool.get('trends.tva.figures').search(cr, uid, [('trends_search_id','=',ids)])
                #search_ids = self.pool.get('trends.tva.figures').search(cr, uid, [('partner_search_id','=',ids)])                
                self.pool.get('trends.tva.figures').unlink(cr, uid, search_ids)                    
                vat_figures = self.getRootElement()  
                if vat_figures: 
                    val = { 
                            'vat' : self.getText(vat_figures.getElementsByTagName("Vat") or ''),                                                                                   
                            'balancetype' : self.getText(vat_figures.getElementsByTagName("BalanceType") or ''),                                                                    
                            'durationmonths' : self.getText(vat_figures.getElementsByTagName("DurationMonths") or ''),    
                            'financial_year' : self.getText(vat_figures.getElementsByTagName("FinancialYear") or ''),                                                                                                                                                                                                         
                    }
                    if object == 'partner':
                        val['partner_search_id']= ids,
                    elif object =='crm':
                        val['crm_search_id'] = ids, 
                    elif object =='who_search':
                        val['trends_whoo_id'] = ids,                             
                    else:
                        val['trends_search_id'] = ids,                                                                                                               
                    figure_id = self.pool.get('trends.tva.figures').create(cr, uid,val)    
                    for fig in self.getRootElement().getElementsByTagName("CompanyFigure"):
                        if fig.nodeType == fig.ELEMENT_NODE: 
                            description = ''
                            description_ids = self.pool.get('trends.figurelist').search(cr ,uid, [('code','=',self.getText(fig.getElementsByTagName("Code") or ''))])
                            if description_ids:
                                description = self.pool.get('trends.figurelist').browse(cr ,uid, description_ids[0]).name                                                       
                                self.pool.get('trends.figures').create(cr, uid,{ 
                                        'name' : self.getText(fig.getElementsByTagName("Code") or ''),                                                                                   
                                        'value' : self.getText(fig.getElementsByTagName("Value") or ''),                                                                                                                                                                                                                        
                                        'trends_figures_id': figure_id,
                                        'description':description,
                                    })                       
                                            
                      
            elif vat_type == "ranking":
                #search_ids = self.pool.get('trends.tva.ranking').search(cr, uid, [('partner_search_id','=',ids)])
                #search_ids = self.pool.get('trends.tva.ranking').search(cr, uid, [('trends_search_id','=',ids)])  
                if object =='partner':
                    search_ids = self.pool.get('trends.tva.ranking').search(cr, uid, [('partner_search_id','=',ids)])
                elif object =='crm':
                    search_ids = self.pool.get('trends.tva.ranking').search(cr, uid, [('crm_search_id','=',ids)])  
                elif object =='who_search':
                    search_ids = self.pool.get('trends.tva.ranking').search(cr, uid, [('trends_whoo_id','=',ids)])                      
                else:
                    search_ids = self.pool.get('trends.tva.ranking').search(cr, uid, [('trends_search_id','=',ids)])                                                    
                self.pool.get('trends.tva.ranking').unlink(cr, uid, search_ids)                    
                vat_ranking = self.getRootElement()  
                if vat_ranking:   
                    val = { 
                        'name' : self.getText(vat_ranking.getElementsByTagName("Vat") or ''),                                                                                   
                        'sectorrankingrddedvalue' : self.getText(vat_ranking.getElementsByTagName("SectorRankingAddedValue") or ''),                                                                    
                        'sectorrankingturnover' : self.getText(vat_ranking.getElementsByTagName("SectorRankingTurnover") or ''),
                        'toprankingaddedvalue' : self.getText(vat_ranking.getElementsByTagName("TopRankingAddedValue") or ''),
                        'toprankingturnover': self.getText(vat_ranking.getElementsByTagName("TopRankingTurnover") or ''),                                                                                                                                                                                     
                                                    
                    }   
                    if object == 'partner':
                        val['partner_search_id']= ids,
                    elif object =='crm':
                        val['crm_search_id'] = ids,
                    elif object =='who_search':
                        val['trends_whoo_id'] = ids,                        
                    else:
                        val['trends_search_id'] = ids,                                                                                                               
                    self.pool.get('trends.tva.ranking').create(cr, uid,val)                          
                     
            elif vat_type == "empty" or vat_type == "":
                #search_ids = self.pool.get('trends.tva.empty').search(cr, uid, [('trends_search_id','=',ids)])
                #search_ids = self.pool.get('trends.tva.empty').search(cr, uid, [('partner_search_id','=',ids)])
                if object =='partner':
                    search_ids = self.pool.get('trends.tva.empty').search(cr, uid, [('partner_search_id','=',ids)])
                elif object =='crm':
                    search_ids = self.pool.get('trends.tva.empty').search(cr, uid, [('crm_search_id','=',ids)])    
                elif object =='who_search':
                    search_ids = self.pool.get('trends.tva.empty').search(cr, uid, [('trends_whoo_id','=',ids)])                      
                else:
                    search_ids = self.pool.get('trends.tva.empty').search(cr, uid, [('trends_search_id','=',ids)])                                                    
                self.pool.get('trends.tva.empty').unlink(cr, uid, search_ids)      
                vat_empty = self.getRootElement()  
                if vat_empty:     
                    #find the sector name from the code 
                    sector = ''
                    sector_ids = self.pool.get('trends.sectorlist').search(cr ,uid, [('code','=',self.getText(vat_empty.getElementsByTagName("SectorCode") or ''))])
                    if sector_ids:
                        sector = self.pool.get('trends.sectorlist').browse(cr ,uid, sector_ids[0]).name 
                    #find the nacebel name from the code 
                    nacebel = ''
                    nacebel_ids = self.pool.get('trends.nacebellist').search(cr ,uid, [('code','=',self.getText(vat_empty.getElementsByTagName("NacebelCode") or ''))])
                    if nacebel_ids:
                        nacebel = self.pool.get('trends.nacebellist').browse(cr ,uid, nacebel_ids[0]).name
                    val = { 
                            'vat' : self.getText(vat_empty.getElementsByTagName("Vat") or ''),                                                                                   
                            'email' : self.getText(vat_empty.getElementsByTagName("EmailAddress") or ''),                                                                    
                            'name' : self.getText(vat_empty.getElementsByTagName("Name") or ''),
                            'city' : self.getText(vat_empty.getElementsByTagName("City") or ''),
                            'company_number': self.getText(vat_empty.getElementsByTagName("CompanyNumber") or ''),
                            'fax' : self.getText(vat_empty.getElementsByTagName("Fax") or ''),   
                            'house_number' : self.getText(vat_empty.getElementsByTagName("HouseNumber") or ''),   
                            'house_number_suffix' : self.getText(vat_empty.getElementsByTagName("HouseNumberSuffix") or ''),      
                            'nacebel_code' : self.getText(vat_empty.getElementsByTagName("NacebelCode") or ''),   
                            'official_name' : self.getText(vat_empty.getElementsByTagName("OfficialName") or ''),   
                            'postal_code' : self.getText(vat_empty.getElementsByTagName("PostalCode") or ''),   
                            'rating' : self.getText(vat_empty.getElementsByTagName("Rating") or ''),   
                            'sector_code' : self.getText(vat_empty.getElementsByTagName("SectorCode") or ''),      
                            'street' : self.getText(vat_empty.getElementsByTagName("Street") or ''),   
                            'telephone' : self.getText(vat_empty.getElementsByTagName("Telephone") or ''),   
                            'website' : self.getText(vat_empty.getElementsByTagName("WebsiteUrl") or ''),                                                                                                                                                             
                            'nacebel': nacebel,
                            'sectore':sector,
                            
                    }   
                    if object == 'partner':
                        val['partner_search_id']= ids,
                    elif object =='crm':
                        val['crm_search_id'] = ids,     
                    elif object =='who_search':
                        val['trends_whoo_id'] = ids,                           
                    else:
                        val['trends_search_id'] = ids,                                                                                                                                               
                    self.pool.get('trends.tva.empty').create(cr, uid,val)                           
                    
                                                 
            else:    
                self.write (cr ,uid, ids, {'states': _('This point is not implemented yet'),})                
        else:
            self.write (cr ,uid, ids, {'states': _('The type is not defined'),})
        self.__currentNode__ = None            
        return True
            
    def getRootElement(self):
        if self.__currentNode__ == None:
            self.__currentNode__ = self.doc.documentElement
        return self.__currentNode__
            

    def getText(self, node):
        if node and node[0] and node[0].childNodes and node[0].childNodes[0] and node[0].childNodes[0].nodeValue:
            return node[0].childNodes[0].nodeValue
        else:
            return False     
           
trends_search()


class trends_who_search(osv.osv):
    _name = "trends.who.search"
    _description = "Search who on trends"
    
    __currentNode__ = None

    _columns = {
        'configuration': fields.many2one('trends.config', 'Configuration', required=True),
        'name': fields.char('name',size=512),
        'who': fields.char('Who', size=512,),
        'where': fields.char('Where', size=512),      
        'res_who': fields.one2many('trends.who', 'trends_search_who_id', "Who answer"),
        'states': fields.char('States', size=1024,),                                     
    }
    

    def action_search_who_trends(self, cr, uid, ids, *args):
        try:
            r=self.browse(cr, uid, ids[0]) 
            #create base url
            url = r.configuration.url
            #different url for who or vat
            url = url+"/companies/?who="+r.who
            if r.where:
                url = url+"&where="+r.where
            #call Web service
            authKey = base64.b64encode(r.configuration.name+":"+r.configuration.pwd)
            headers = {"Content-Type":"application/"+r.configuration.type , "Authorization":"Basic " + authKey, "X-AuthKey" : r.configuration.api_key, "Accept-Language":r.configuration.language.upper()}
            request = urllib2.Request(url)
             
            for key,value in headers.items():
                request.add_header(key,value)          
            response = urllib2.urlopen(request) 
            res= response.read()
            #read the answer
            self.readxml(cr, uid, r.id, res, "who", "")
        except:
            self.write (cr ,uid, ids, {'states': _('Impossible to do this action'),})   
        return True


    
    def readxml(self, cr, uid, ids,response, trends_type, vat_type, *args):
        self.doc = parseString(response)
        search_ids = self.pool.get('trends.who').search(cr, uid, [('trends_search_who_id','=',ids)])
        self.pool.get('trends.who').unlink(cr, uid, search_ids)             
        for who in self.getRootElement().getElementsByTagName("CompanySearchResult"):
            if who.nodeType == who.ELEMENT_NODE:   
                #find the sector name from the code 
                sector = ''
                sector_ids = self.pool.get('trends.sectorlist').search(cr ,uid, [('code','=',self.getText(who.getElementsByTagName("SectorCode") or ''))])
                if sector_ids:
                    sector = self.pool.get('trends.sectorlist').browse(cr ,uid, sector_ids[0]).name                                                                           
                t = self.pool.get('trends.who').create(cr, uid,{ 
                        'city' : self.getText(who.getElementsByTagName("City") or ''),                                                                    
                        'name' : self.getText(who.getElementsByTagName("Name") or ''),
                        'zip' : self.getText(who.getElementsByTagName("PostalCode") or ''),
                        'sectore_code': self.getText(who.getElementsByTagName("SectorCode") or ''),
                        'vat' : self.getText(who.getElementsByTagName("Vat") or ''),    
                        'trends_search_who_id': ids,
                        'sectore': sector,
                    }) 
                                           
                                                 
            else:    
                self.write (cr ,uid, ids, {'states': _('This point is not implemented yet'),})                

        self.__currentNode__ = None            
        return True
            
    def getRootElement(self):
        if self.__currentNode__ == None:
            self.__currentNode__ = self.doc.documentElement
        return self.__currentNode__
            

    def getText(self, node):
        if node and node[0] and node[0].childNodes and node[0].childNodes[0] and node[0].childNodes[0].nodeValue:
            return node[0].childNodes[0].nodeValue
        else:
            return False     
           
trends_who_search()

class trends_who(osv.osv):
    _name = "trends.who"
    _description = "Result for search who on trends"
    
    
    _columns = {
        'name': fields.char('Name',size=512),
        'city':fields.char('City',size=512),
        'zip': fields.char('Zip code', size=512,),
        'sectore_code': fields.char('Sector Code', size=512),
        'sectore': fields.char('Sector', size=512),        
        'vat': fields.char('VAT', size=512),    
        'trends_search_id': fields.many2one('trends.search', 'Trends Search Id'),     
        'trends_search_who_id': fields.many2one('trends.who.search', 'Trends Search Id'),              
        'res_tva_management': fields.one2many('trends.tva.management', 'trends_whoo_id', "VAT management answer"),
        'res_tva_empty': fields.one2many('trends.tva.empty', 'trends_whoo_id', "VAT answer"),   
        'res_tva_ranking': fields.one2many('trends.tva.ranking', 'trends_whoo_id', "VAT ranking answer"),     
        'res_tva_figures': fields.one2many('trends.tva.figures', 'trends_whoo_id', "VAT figures answer"),     
        'res_tva_ratios': fields.one2many('trends.tva.ratios', 'trends_whoo_id', "VAT ratios answer"),  
        'res_tva_social': fields.one2many('trends.tva.social', 'trends_whoo_id', "VAT social answer"), 
        'state':fields.char('States',size=512), 
    }    
    def action_create_lead(self, cr, uid, ids,*args):
        #create lead only if you can save and have credit
        who = self.browse(cr,uid,ids[0])
        conf_brw= who.trends_search_who_id.configuration
        if conf_brw.save == True:
            # lead = self.browse(cr, uid,ids[0])
            #find number of credit to substract
            self.action_search_tva_trends(cr, uid,ids,*args)
            number_contact = len(who.res_tva_management)            
            #check if we have enough credit
            current_credit = who.trends_search_who_id.configuration.credit
            if current_credit >= number_contact:    
                #consumme credit
                try:   
                    url = conf_brw.url+'/credits/'+str(number_contact)
                    name = conf_brw.name
                    pwd = conf_brw.pwd
                    authKey = base64.b64encode( name+":"+ pwd)
                    api_key=conf_brw.api_key
                    type= conf_brw.type                    
                    lang = conf_brw.language
                    headers = {"Content-Type":"application/"+type , "Authorization":"Basic " + authKey, "X-AuthKey" : api_key, "Accept-Language":lang}
        
                    
                    data = ''
                    req = urllib2.Request(url, data, headers)
                    response = urllib2.urlopen(req)
                    res = response.read()
                                    
                    #call method to read the answer
                    remaining = self.pool.get('trends.config').conf_readxml(cr, uid, ids[0], res, "credit") 
                    self.pool.get('trends.config').write(cr, uid, [who.trends_search_who_id.configuration.id], {'credit':remaining}) 
                                        
                except:
                    raise osv.except_osv(_('Warning!'),_("Impossible to interract with your credit"))                     
                    return True
                                                      

                val={
                     'partner_name':who.name or '',             
                     'name':who.name or '',
                     'city':who.city or '',
                     'zip':who.zip or '',
                     'vat':"BE0"+str(who.vat) or '',
                     
                }
                new_lead = self.pool.get('crm.lead').create(cr, uid, val)
                self.pool.get('crm.lead').open_trends(cr, uid, [new_lead],None)
                            
                return True    
            else:
                raise osv.except_osv(_('Warning!'),_("You don't have enought credit /n You need %d credit and you only have %d credit") % (number_contact,current_credit))              
                return True            
        else:
            raise osv.except_osv(_('Warning!'),_("You can't create lead if you don't accept to save the data in your configuration"))              
            return True
    
    def action_search_tva_trends(self, cr, uid, ids, *args):
        try:
            r=self.browse(cr, uid, ids[0]) 
            #create base url
            url = r.trends_search_who_id.configuration.url
            
            vat_to_use= r.vat
            url_src = url+"/company/"+vat_to_use          
            
            #find all the type
            types_search = self.pool.get('trends.type.list').search(cr, uid,[])
            if types_search:
                types = self.pool.get('trends.type.list').browse(cr, uid, types_search)                            
                for t in types:    
                    typ= (t.name.lower()) 
                    if typ and typ != "empty":            
                        url=url_src +"/"+str(typ)+"/"    
                    else:
                        url = url_src               
                    #call Web service
                    authKey = base64.b64encode(r.trends_search_who_id.configuration.name+":"+r.trends_search_who_id.configuration.pwd)
                    headers = {"Content-Type":"application/"+r.trends_search_who_id.configuration.type , "Authorization":"Basic " + str(authKey), "X-AuthKey" : r.trends_search_who_id.configuration.api_key, "Accept-Language":r.trends_search_who_id.configuration.language.upper()}
                    request = urllib2.Request(url)
                    for key,value in headers.items():
                        request.add_header(key,value)
                        
                    
                    response = urllib2.urlopen(request)                  
                    res= response.read()            
                    self.pool.get('trends.search').readxml(cr, uid, r.id, res, 'vat',typ, "who_search")
                    self.write(cr,uid, ids[0],{'state':'Action Done'})

        except:
            self.write(cr,uid, ids[0],{'state':'Impossible to do this action !'})
            return True  
        return True    
trends_who()

class trends_tva_social(osv.osv):
    _name = "trends.tva.social"
    _description = "Result for search tva filter by social"
    
    
    _columns = {
        'balancetype':fields.char('Balance Type',size=512),
        'durationmonths': fields.char('Duration Months',size=512),     
        'figures_ids': fields.one2many('trends.figures.social', 'trends_figures_id','Figures'),
        'vat': fields.char('VAT', size=512), 
        'financial_year': fields.char('Financial Year', size=512),                         
        'trends_search_id': fields.many2one('trends.search', 'Trends Search Id'),   
        'trends_whoo_id': fields.many2one('trends.who', 'Trends Who Id'),            
        'partner_search_id': fields.many2one('res.partner', 'Partner Search Id'),  
        'crm_search_id': fields.many2one('crm.lead', 'CRM Search Id'),                   

    }    
trends_tva_social()


class trends_tva_ratios(osv.osv):
    _name = "trends.tva.ratios"
    _description = "Result for search tva filter by ratios"
    
    
    _columns = {
        'balancetype':fields.char('Balance Type',size=512),
        'durationmonths': fields.char('Duration Months',size=512),     
        'figures_ids': fields.one2many('trends.figures.ratios', 'trends_figures_id','Figures'),
        'vat': fields.char('VAT', size=512), 
        'financial_year': fields.char('Financial Year', size=512),                         
        'trends_search_id': fields.many2one('trends.search', 'Trends Search Id'), 
        'trends_whoo_id': fields.many2one('trends.who', 'Trends Who Id'),           
        'partner_search_id': fields.many2one('res.partner', 'Partner Search Id'),  
        'crm_search_id': fields.many2one('crm.lead', 'CRM Search Id'),                  

    }    
trends_tva_ratios()

class trends_tva_figures(osv.osv):
    _name = "trends.tva.figures"
    _description = "Result for search tva filter by figures"
    
    
    _columns = {
        'balancetype':fields.char('Balance Type',size=512),
        'durationmonths': fields.char('Duration Months',size=512),     
        'figures_ids': fields.one2many('trends.figures', 'trends_figures_id','Figures'),
        'vat': fields.char('VAT', size=512), 
        'financial_year': fields.char('Financial Year', size=512),                         
        'trends_search_id': fields.many2one('trends.search', 'Trends Search Id'),
        'trends_whoo_id': fields.many2one('trends.who', 'Trends Who Id'),           
        'partner_search_id': fields.many2one('res.partner', 'Partner Search Id'),  
        'crm_search_id': fields.many2one('crm.lead', 'CRM Search Id'),                     

    }    
trends_tva_figures()

class trends_tva_empty(osv.osv):
    _name = "trends.tva.empty"
    _description = "Result for search tva without filter"
    
    
    _columns = {
        'city':fields.char('City',size=512),
        'company_number': fields.char('Company Number',size=512),     
        'email': fields.char('Email', size=512),
        'fax': fields.char('Fax', size=512),       
        'house_number': fields.char('House Number', size=512),          
        'house_number_suffix': fields.char('House Number Suffix', size=512),           
        'nacebel_code': fields.char('Nacebel Code', size=512),            
        'name': fields.char('Name',size=512),
        'official_name':fields.char('Official Name',size=512),
        'postal_code': fields.char('Postal Code', size=512,),       
        'rating': fields.char('Ra',size=512),
        'sector_code':fields.char('Sector Code',size=512),
        'street': fields.char('Street', size=512,),
        'telephone': fields.char('Telephone', size=512), 
        'website': fields.char('Website', size=512),   
        'vat': fields.char('VAT', size=512),           
        'trends_search_id': fields.many2one('trends.search', 'Trends Search Id'),  
        'trends_whoo_id': fields.many2one('trends.who', 'Trends Who Id'),           
        'partner_search_id': fields.many2one('res.partner', 'Partner Search Id'),  
        'crm_search_id': fields.many2one('crm.lead', 'CRM Search Id'),                 
        'nacebel': fields.char('Nacebel', size=512),   
        'sectore': fields.char('Sector', size=512),           

    }    
trends_tva_empty()

class trends_tva_management(osv.osv):
    _name = "trends.tva.management"
    _description = "Result for search tva filter by management"
    
    
    _columns = {
        'name': fields.char('Name',size=512),
        'last_name':fields.char('Last Name',size=512),
        'language_code': fields.char('Language Code', size=512,),       
        'gender': fields.char('Gender',size=512),
        'function_code':fields.char('Function Code',size=512),
        'function': fields.char('Function', size=512,),
        'email': fields.char('Email', size=512),
        'vat': fields.char('VAT', size=512),    
        'trends_search_id': fields.many2one('trends.search', 'Trends Search Id'),    
        'trends_whoo_id': fields.many2one('trends.who', 'Trends Who Id'),           
        'partner_search_id': fields.many2one('res.partner', 'Partner Search Id'), 
        'crm_search_id': fields.many2one('crm.lead', 'CRM Search Id'),                

    }    
trends_tva_management()

class trends_tva_ranking(osv.osv):
    _name = "trends.tva.ranking"
    _description = "Result for search tva filter by ranking"
    
    
    _columns = {
        'sectorrankingrddedvalue': fields.char('Sector Ranking Added Value',size=512),
        'sectorrankingturnover':fields.char('Sector Ranking Turnover',size=512),
        'toprankingaddedvalue': fields.char('Top Ranking Added Value', size=512,),       
        'toprankingturnover': fields.char('Top Ranking Turnover',size=512),
        'name': fields.char('VAT', size=512),    
        'trends_search_id': fields.many2one('trends.search', 'Trends Search Id'),    
        'trends_whoo_id': fields.many2one('trends.who', 'Trends Who Id'),         
        'partner_search_id': fields.many2one('res.partner', 'Partner Search Id'),    
        'crm_search_id': fields.many2one('crm.lead', 'CRM Search Id'),               

    }    
trends_tva_ranking()


class trends_figures(osv.osv):
    _name = "trends.figures"
    _description = "Figure result"
    
    
    _columns = {
        'name':fields.char('Code',size=512),
        'description': fields.char('Description',size=512),
        'value': fields.char('Value',size=512),             
        'trends_figures_id': fields.many2one('trends.tva.figures', 'Trends Search Id'),         

    }    
trends_figures()

class trends_figures_ratios(osv.osv):
    _name = "trends.figures.ratios"
    _description = "Figure result ratios for ratios"
  
    
    _columns = {
        'name':fields.char('Code',size=512),
        'description': fields.char('Description',size=512),        
        'value': fields.char('Value',size=512),             
        'trends_figures_id': fields.many2one('trends.tva.ratios', 'Trends Search Id'),          

    }    
trends_figures_ratios()

class trends_figures_social(osv.osv):
    _name = "trends.figures.social"
    _description = "Figure result for social"
    
    
    _columns = {
        'name':fields.char('Code',size=512),
        'description': fields.char('Description',size=512),        
        'value': fields.char('Value',size=512),             
        'trends_figures_id': fields.many2one('trends.tva.social', 'Trends Search Id'),          

    }    
trends_figures_social()

class trends_sectorlist(osv.osv):
    _name = "trends.sectorlist"
    _description = "Sector list for trends"
    
    
    _columns = {
        'name':fields.char('Description',size=512),
        'description_long': fields.char('Long Description',size=512),             
        'code': fields.char('Code',size=512),    

    }    
trends_sectorlist()


class trends_nacebellist(osv.osv):
    _name = "trends.nacebellist"
    _description = "Nacebel list for trends"
    
    
    _columns = {
        'name':fields.char('Description',size=512),           
        'code': fields.char('Code',size=512),    

    }    
trends_nacebellist()

class trends_figurelist(osv.osv):
    _name = "trends.figurelist"
    _description = "Figure list for trends"
    
    
    _columns = {
        'name':fields.char('Description',size=512),           
        'code': fields.char('Code',size=512),    

    }    
trends_figurelist()

class trends_functionlist(osv.osv):
    _name = "trends.functionlist"
    _description = "Function list for trends"
    
    
    _columns = {
        'name':fields.char('Description',size=512),           
        'code': fields.char('Code',size=512),    

    }    
trends_functionlist()

class trends_type_list(osv.osv):
    _name = "trends.type.list"
    _description = "Trends Type list"
    
    
    _columns = {
        'name':fields.char('Name',size=64),            

    }    
trends_type_list()