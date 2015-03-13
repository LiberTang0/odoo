# -*- coding: utf-8 -*-
##################################################################################
#
# Copyright (c) 2005-2006 Axelor SARL. (http://www.axelor.com)
# and 2004-2010 Tiny SPRL (<http://tiny.be>).
#
# $Id: hr.py 4656 2006-11-24 09:58:42Z Cyp $
#
#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU Affero General Public License as
#     published by the Free Software Foundation, either version 3 of the
#     License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU Affero General Public License for more details.
#
#     You should have received a copy of the GNU Affero General Public License
#     along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from datetime import datetime, timedelta	
from dateutil.relativedelta import relativedelta
import time	
import _strptime		
import pooler	
from osv import fields, osv
from tools.translate import _	
from tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import decimal_precision as dp
import netsvc
import tools
import math

class hr_holidays(osv.osv):
    _inherit = "hr.holidays"
    _order = 'id desc'
    
    def _compute_number_of_days(self, cr, uid, ids, name, args, context=None):
        result = {}
        for hol in self.browse(cr, uid, ids, context=context):
            if hol.type=='remove':
                result[hol.id] = -hol.number_of_days_temp
            else:
                result[hol.id] = hol.number_of_days_temp
        return result
    
    _columns = {
        'name': fields.char('Description', size=64,readonly=True, states={'draft':[('readonly',False)]}),
        'user_id':fields.related('employee_id', 'user_id', type='many2one', readonly=True, states={'draft':[('readonly',False)]},relation='res.users', string='User', store=True),
        'date_from': fields.datetime('Start Date', readonly=True, states={'draft':[('readonly',False)]}, select=True),
        'date_to': fields.datetime('End Date', readonly=True, states={'draft':[('readonly',False)]}),
        'holiday_status_id': fields.many2one("hr.holidays.status", "Leave Type", required=True,readonly=True, states={'draft':[('readonly',False)]}),
        'employee_id': fields.many2one('hr.employee', "Employee", select=True, invisible=False, readonly=True, states={'draft':[('readonly',False)]}),
        'manager_id': fields.many2one('hr.employee', 'First Approval', invisible=False, readonly=True, states={'draft':[('readonly',False)]}, help='This area is automatically filled by the user who validate the leave'),
        'notes': fields.text('Reasons',readonly=True, states={'draft':[('readonly',False)]}),
        'number_of_days_temp': fields.float('Allocation', readonly=True, states={'draft':[('readonly',False)]}),
        'number_of_days': fields.function(_compute_number_of_days, string='Number of Days', store=True,readonly=True, states={'draft':[('readonly',False)]}),
        'department_id':fields.related('employee_id', 'department_id', string='Department', type='many2one', relation='hr.department', readonly=True, store=True, states={'draft':[('readonly',False)]}),
    }
    
    def _get_number_of_days(self, cr, uid, date_from, date_to):
        """Returns a float equals to the timedelta between two dates given as string."""
        holiday_proxy = self.pool.get('training.holiday.year')
        if not holiday_proxy.search(cr, uid, [('year', '=', time.strftime('%Y'))]):
            return False
        DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
        from_dt = datetime.strptime(date_from, DATETIME_FORMAT)
        to_dt = datetime.strptime(date_to, DATETIME_FORMAT)
        from_date=from_dt
        i=0
        while from_dt < to_dt:
            dayoff=self.pool.get('training.holiday.period').search(cr,uid,[('date_start','<=',from_dt),('date_stop','>=',from_dt)])
            if dayoff:
                i+=1
            from_dt = from_dt + relativedelta(days=1)
        timedelta = to_dt - from_date 
        diff_day = timedelta.days + float(timedelta.seconds) / 86400
        diff_day-=i
        return diff_day

    
    def onchange_date(self, cr, uid, ids, date_to, date_from):
        result = {}
        if date_to and date_from:
            diff_day = self._get_number_of_days(cr, uid,date_from, date_to)
            if not diff_day:
                warning = {
                       'title': _('Configuration Error !'),
                       'message' : _('Please, Can you configure the week-end holidays ?'),
                    }
                return {'warning': warning}

            result['value'] = {
                'number_of_days_temp': math.ceil(diff_day)
            }
            return result
        result['value'] = {
            'number_of_days_temp': 0,
        }
        return result
        
hr_holidays()
