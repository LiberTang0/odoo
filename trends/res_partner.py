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
import ast
 


class res_partner(osv.osv):
    __currentNode__ = None
    
    _inherit="res.partner"
    _columns={
        'res_tva_management': fields.one2many('trends.tva.management', 'partner_search_id', "VAT management answer"),
        'res_tva_empty': fields.one2many('trends.tva.empty', 'partner_search_id', "VAT answer"),   
        'res_tva_ranking': fields.one2many('trends.tva.ranking', 'partner_search_id', "VAT ranking answer"),     
        'res_tva_figures': fields.one2many('trends.tva.figures', 'partner_search_id', "VAT figures answer"),     
        'res_tva_ratios': fields.one2many('trends.tva.ratios', 'partner_search_id', "VAT ratios answer"),  
        'res_tva_social': fields.one2many('trends.tva.social', 'partner_search_id', "VAT social answer"),              
              }
    
    def open_trends(self, cr, uid, ids, context=None):
        try:
            partner=self.browse(cr, uid, ids[0]) 
            if partner.vat:
                config_search = self.pool.get('trends.config').search(cr, uid, [('user_id','=',uid)])
                if config_search:
                    config = self.pool.get('trends.config').browse(cr, uid, config_search[0])
                    url= config.url
                    taille=len(partner.vat)
                    vat_to_use= partner.vat[2:taille] 
                    url_src = url+"/company/"+vat_to_use          
        
                else:
                    raise osv.except_osv(_('Error !'),_('You need to define a configuration for your user'))
                #Check if we accept to save data
                if config.save == True:                    
                    #find all the type
                    types_search = self.pool.get('trends.type.list').search(cr, uid,[])
                    if types_search:
                        types = self.pool.get('trends.type.list').browse(cr, uid, types_search)
                    else:
                        raise osv.except_osv(_('Error !'),_('You need to define a type needed'))            
                    for t in types:    
                        typ= (t.name.lower()) 
                        if typ and typ != "empty":            
                            url=url_src +"/"+str(typ)+"/"    
                        else:
                            url = url_src               
                        #call Web service
                        authKey = base64.b64encode(config.name+":"+config.pwd)
                        headers = {"Content-Type":"application/"+config.type , "Authorization":"Basic " + str(authKey), "X-AuthKey" : config.api_key, "Accept-Language":config.language.upper()}
                        request = urllib2.Request(url)
                        for key,value in headers.items():
                            request.add_header(key,value)
                            
                        try:      
                            response = urllib2.urlopen(request)                  
                            res= response.read()
                        except:
                            raise osv.except_osv(_('Error !'),_('No Data find for this vat number on trends'))                      
                        #read the answer
                        self.pool.get('trends.search').readxml(cr, uid, ids[0], res, 'vat', typ,'partner')
                    number_contact = len(partner.res_tva_management)         
                    #check if we have enough credit
                    current_credit = config.credit
                    if current_credit >= number_contact:
                        #consumme credit
                        try:   
                            url = config.url+'/credits/'+str(number_contact)                                          
                            data = ''
                            headers2 = {"Content-Type":"application/json" , "Authorization":"Basic " + str(authKey), "X-AuthKey" : config.api_key, "Accept-Language":config.language.upper()}                                                
                            req = urllib2.Request(url, data, headers2)
                            response = urllib2.urlopen(req)
                            res1 = response.read()
                            res1 =ast.literal_eval(res1)        
                            #call method to read the answer
                            self.pool.get('trends.config').write(cr, uid, [config.id], {'credit':res1['Remaining']}) 
                                                
                        except:
                            raise osv.except_osv(_('Warning!'),_("Impossible to interract with your credit"))                     
                            return True                        
                    else:
                        raise osv.except_osv(_('Warning!'),_("You don't have enought credit /n You need %d credit and you only have %d credit") % (number_contact,current_credit))              
                        return True                          
                else:
                    raise osv.except_osv(_('Warning!'),_("You can't load data if you don't accept to save the data in your configuration"))              
                    return True                    
            else:
                raise osv.except_osv(_('Error !'),_('You need to define a vat for this partner'))                  
        except:
            self.write (cr ,uid, ids, {'states': _('Impossible to do this action'),})   
        return True        
      
res_partner()