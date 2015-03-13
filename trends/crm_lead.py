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

class crm_lead(osv.osv):
    _inherit = 'crm.lead'
    _columns = {
        'vat': fields.char('Vat', size=512),
        'state_trends': fields.char('State trends',size=512),
        'res_tva_management': fields.one2many('trends.tva.management', 'crm_search_id', "VAT management answer"),
        'res_tva_empty': fields.one2many('trends.tva.empty', 'crm_search_id', "VAT answer"),   
        'res_tva_ranking': fields.one2many('trends.tva.ranking', 'crm_search_id', "VAT ranking answer"),     
        'res_tva_figures': fields.one2many('trends.tva.figures', 'crm_search_id', "VAT figures answer"),     
        'res_tva_ratios': fields.one2many('trends.tva.ratios', 'crm_search_id', "VAT ratios answer"),  
        'res_tva_social': fields.one2many('trends.tva.social', 'crm_search_id', "VAT social answer"),               
    }
    
    def _lead_create_contact(self, cr, uid, lead, name, is_company, parent_id=False, context=None):                                                                                                           
        partner = self.pool.get('res.partner')
        vals = {'name': name,
            'user_id': lead.user_id.id,
            'comment': lead.description,
            'section_id': lead.section_id.id or False,
            'parent_id': parent_id,
            'phone': lead.phone,
            'mobile': lead.mobile,
            'email': tools.email_split(lead.email_from) and tools.email_split(lead.email_from)[0] or False,
            'fax': lead.fax,
            'title': lead.title and lead.title.id or False,
            'function': lead.function,
            'street': lead.street,
            'street2': lead.street2,
            'zip': lead.zip,
            'city': lead.city,
            'country_id': lead.country_id and lead.country_id.id or False,
            'state_id': lead.state_id and lead.state_id.id or False,
            'is_company': is_company,
            'type': 'contact',
            'vat': lead.vat or '',
        }    
        partner_id = partner.create(cr, uid, vals, context=context)
        partner.open_trends(cr, uid, [partner_id],context=context)
        return partner_id
    
    
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
                    self.write(cr, uid, ids[0],{'state_trends': _('You need to define a configuration for your user')})
                    return True
                #find all the type
                types_search = self.pool.get('trends.type.list').search(cr, uid,[])
                if types_search:
                    types = self.pool.get('trends.type.list').browse(cr, uid, types_search)
                else:
                    self.write(cr, uid, ids[0],{'state_trends': _('You need to define a type needed')})
                    return True                               
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
                        self.write(cr, uid, ids[0],{'state_trends': _('No Data find for this vat number on trends')})
                        return True                                             
                    #read the answer                    
                    self.pool.get('trends.search').readxml(cr, uid, ids[0], res, 'vat', typ,'crm')
            else:  
                self.write(cr, uid, ids[0],{'state_trends': _('You need to define a vat for this lead')})
                return True                           
        except:
            self.write(cr, uid, ids[0],{'state_trends': _('Impossible to connect to Trends')})
            return True              
        return True 
    
crm_lead()    