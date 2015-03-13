# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-TODAY OpenERP S.A. <http://www.openerp.com>
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

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time

from osv import fields, osv
from tools.translate import _
import decimal_precision as dp
import netsvc

class hr_holidays(osv.osv):
    _inherit = "hr.holidays"
    
    def set_to_draft(self, cr, uid, ids, context=None):
        uid=1
        res=self.write(cr, uid, ids, {
            'state': 'draft',
            'manager_id': False,
            'manager_id2': False,
        })
        wf_service = netsvc.LocalService("workflow")
        for id in ids:
            wf_service.trg_delete(uid, 'hr.holidays', id, cr)
            wf_service.trg_create(uid, 'hr.holidays', id, cr)
        to_unlink = []
        for record in self.browse(cr, uid, ids, context=context):
            for record2 in record.linked_request_ids:
                self.set_to_draft(cr, uid, [record2.id], context=context)
                to_unlink.append(record2.id)
        if to_unlink:
            self.unlink(cr, uid, to_unlink, context=context)
        
        return True
    
hr_holidays()