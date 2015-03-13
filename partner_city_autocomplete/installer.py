# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

import datetime
from dateutil.relativedelta import relativedelta
import logging
from operator import itemgetter
import time
import urllib2
import urlparse
import csv
import os
import glob
try:
    import simplejson as json
except ImportError:
    import json     # noqa
import base64
from openerp.release import serie
from openerp.tools.translate import _
from openerp.osv import fields, osv

_logger = logging.getLogger(__name__)

class account_2(osv.osv_memory):
    _name = 'city.import'
    _columns = {
        'country_id': fields.many2one('res.country','Country',required=True),
        'file': fields.binary('CSV File',required=True),
    }
    def make(self, cr, uid, ids, context=None):
        file=self.browse(cr,uid,ids[0]).file
        country=self.browse(cr,uid,ids[0]).country_id.id
        lines=base64.b64decode(file).split('\r\n')
        obj_city = self.pool.get('zip.city')
        for i in lines:
            row=i.split(';')
            if row[0] and row[1]:
                vals2 = {
                    'name': row[1].decode('latin-1'),
                    'zip': row[0]   ,
                    'country': country,
                }
                obj_city.create(cr, uid, vals2, context=context)
                
        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'partner_city_autocomplete', 'view_country_installer')
        form_id = form_res and form_res[1] or False
        return {
                'name':_("Configure Country data"),
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'country.installer', # your current model
                'res_id': False,
                'view_id': False,
                'target':'new',
                'context': context,
                'views': [(form_id, 'form')],
                'type': 'ir.actions.act_window',
                }
account_2()

class account_installer(osv.osv_memory):
    _name = 'country.installer'
    _inherit = 'res.config.installer'
    _columns = {
        'be' : fields.boolean('Belgium'),
        'fr' : fields.boolean('France'),
    }
    
    def new_import(self, cr, uid, ids, context=None):
        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'partner_city_autocomplete', 'view_cityzip')
        form_id = form_res and form_res[1] or False
        return {
            'name': _('Configure Country data'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'city.import',
            'res_id': False,
            'view_id': False,
            'target':'new',
            'context': context,
            'views': [(form_id, 'form')],
            'type': 'ir.actions.act_window',
        }
    
    def execute(self, cr, uid, ids, context=None):
        self.execute_simple(cr, uid, ids, context)
        return super(account_installer, self).execute(cr, uid, ids, context=context)

    def execute_simple(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        obj_city = self.pool.get('zip.city')
        path=open("/etc/openerp-server.conf","r" )
        for i in path:
            data=i.split('=')
            if data and data[0]:
                data0=data[0].replace(' ','')
                if data0=='addons_path':
                    fs=data[1].replace(' ','')
                    fs=fs.replace('\n','')
                    break
        _logger.info(fs)
        if self.browse(cr,uid,ids[0]).be==1:
            try:
                reader = csv.reader(open(fs +'partner_city_autocomplete/doc/city_BE.csv','rb'),delimiter=';')
            except:
                raise osv.except_osv(_('Error!'),_("Please configure the 'addons_path' in the openerp configuration file"))
            country=self.pool.get('res.country').search(cr,uid,[('code','=','BE')])
            for row in reader:
                vals = {
                    'name': row[2].decode('latin-1'),
                    'zip': row[1],
                    'country': country and country[0],
                }
                obj_city.create(cr, uid, vals, context=context)
        if self.browse(cr,uid,ids[0]).fr==1:
            try:
                reader2 = csv.reader(open(fs +'partner_city_autocomplete/doc/city_FR.csv','rb'),delimiter=';')
            except:
                raise osv.except_osv(_('Error!'),_("Please configure the 'addons_path' in the openerp configuration file"))
            country2=self.pool.get('res.country').search(cr,uid,[('code','=','FR')])
            for row in reader2:
                vals2 = {
                    'name': row[2].decode('latin-1'),
                    'zip': row[1],
                    'country': country2 and country2[0],
                }
                obj_city.create(cr, uid, vals2, context=context)
                
    def modules_to_install(self, cr, uid, ids, context=None):
        return (set([])).difference(
                    self.already_installed(cr, uid, context))

account_installer()