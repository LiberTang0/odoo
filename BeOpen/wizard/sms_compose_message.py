# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010-Today OpenERP SA (<http://www.openerp.com>)
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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

import base64
import re
from openerp import tools

from openerp.osv import osv
from openerp.osv import fields
from openerp.tools.safe_eval import safe_eval as eval
from openerp.tools.translate import _
from datetime import datetime

# main mako-like expression pattern
EXPRESSION_PATTERN = re.compile('(\$\{.+?\})')

class sms_compose_message(osv.TransientModel):
    _name = 'sms.compose.message'
    _inherit = 'mail.message'
    _log_access = True

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        res = super( sms_compose_message, self).default_get(cr, uid, fields, context=context)
        move = self.pool.get('res.partner').browse(cr, uid, context['active_ids'], context=context)
        numer=[]
        n=[]
        for obj in move:
            num= obj.mobile
            if num : 
                numer.append(str(num))
        if 'number' in fields:
            res.update({'number': numer})
        return res

    _columns = {
        'number' : fields.char('phone',required=True),
        'message' : fields.text('Message',required=True),
        'template' : fields.many2one('email.template','Template SMS'),
    }
    
    def onchange_temp(self,cr,uid,ids,tmpl,context=None):
        if not tmpl:
            return {'value' : {}}
        tmpl_obj=self.pool.get('email.template').browse(cr,uid,tmpl)
        val={
             'number' : tmpl_obj.number,
             'message' : tmpl_obj.content,
             }
        return {'value' : val}

    def sendSMS(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        active_ids = context.get('active_ids')
        part_obj=self.pool.get('res.partner')
        sms=[]
        num=""
        for wizard in self.browse(cr, uid, ids, context=context):
            res_ids = active_ids
            for res_id in res_ids:
                if not wizard.template:
                    num=part_obj.browse(cr,uid,res_id).mobile
                    msg=self.pool.get('message.message').create(cr,uid,{'number':num ,
                                                                        'message':wizard.message,
                                                                        'template':wizard.template and wizard.template.id or False,
                                                                        'partner_id':res_id,
                                                                        'state':'send',
                                                                        'datime':datetime.now()})
                    sms.append(msg)
                    self.pool.get('message.message').action_sendSMS(cr,uid,msg,num,wizard.message,context)
                else:
                    sms_dict = self.render_message(cr, uid, wizard, res_id, context=context)
                    msg=self.pool.get('message.message').create(cr,uid,{'number':sms_dict['number'] ,
                                                                        'message':sms_dict['body'],
                                                                        'template':wizard.template and wizard.template.id or False,
                                                                        'partner_id':res_id,
                                                                        'state':'send',
                                                                        'datime':datetime.now()})
                    sms.append(msg)
                    self.pool.get('message.message').action_sendSMS(cr,uid,msg,sms_dict['number'],sms_dict['body'],context)
            if sms:
                 self.pool.get('message.message').check_state(cr,uid,sms)
            return {'type': 'ir.actions.act_window_close'}

    def render_message(self, cr, uid, wizard, res_id, context=None):
        return {
            'number': self.render_template(cr, uid, wizard.number, wizard.template and wizard.template.model_id.model, res_id, context),
            'body': self.render_template(cr, uid, wizard.message, wizard.template and wizard.template.model_id.model, res_id, context),
        }

    def render_template(self, cr, uid, template, model, res_id, context=None):
        if context is None:
            context = {}

        def merge(match):
            exp = str(match.group()[2:-1]).strip()
            result = eval(exp, {
                'user': self.pool.get('res.users').browse(cr, uid, uid, context=context),
                'object': self.pool.get(model).browse(cr, uid, res_id, context=context),
                'context': dict(context), # copy context to prevent side-effects of eval
                })
            return result and tools.ustr(result) or ''
        return template and EXPRESSION_PATTERN.sub(merge, template)
