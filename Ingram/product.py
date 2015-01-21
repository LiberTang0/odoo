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
import pytz
from openerp import SUPERUSER_ID
import os
import os.path
import csv, math
import thread
import smtplib
import sys
from datetime import date,datetime, timedelta
from dateutil.relativedelta import relativedelta

class product_category(models.Model):
    _inherit = 'product.category'
    
    code_categ_ingram = fields.Char(string='Ingram code category')
    
product_category()

class product_product(models.Model):
    _inherit = 'product.product'
    vpn = fields.Char(string="VPN",help="VPN code")
    manufacturer = fields.Char(string="Manufacturer",help="Manufacturer")

    @api.v7
    def name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=80):
        print 'name_search'
        if not args:
            args=[]
        if not context:
            context={}
        if name:
            ids = self.search(cr, user, [('default_code','like',name)]+ args, limit=limit, context=context)
            if not len(ids):
                ids = self.search(cr, user, [('ean13','=',name)]+ args, limit=limit, context=context)
                ids = self.search(cr, user, [('vpn','like',name)]+ args, limit=limit, context=context)
            if not len(ids):
                ids = self.search(cr, user, [('default_code',operator,name)]+ args, limit=limit, context=context)
                ids += self.search(cr, user, [('name',operator,name)]+ args, limit=limit, context=context)
        else:
            ids = self.search(cr, user, args, limit=limit, context=context)
        result = self.name_get(cr, user, ids, context)
        return result        
product_product()

class product_template(models.Model):
    _inherit = 'product.template'

    ingram = fields.Boolean(string='Ingram Product')
    last_synchro_ingram = fields.Date(string='Date of last synchronization')

product_template()