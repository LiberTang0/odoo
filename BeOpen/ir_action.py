# -*- coding: utf-8 -*-

from email.MIMEText import MIMEText
from email.MIMEBase import MIMEBase
from email.MIMEMultipart import MIMEMultipart
from email.Charset import Charset
from email.Header import Header
from email.Utils import formatdate, make_msgid, COMMASPACE
from email import Encoders
import logging
import re
import smtplib
import threading
from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp.tools import html2text
import openerp.tools as tools
from openerp.loglevels import ustr
_logger = logging.getLogger(__name__)
import urllib
import httplib
from response.sms.SendSMSResponse import SendSMSResponse
from response.sms.RetrieveSMSResponse import RetrieveSMSResponse 
import json
import base64
from foundation.JSONRequest import JSONRequest
from response.sms.SMSSendDeliveryStatusResponse import SMSSendDeliveryStatusResponse
import os
from socket import gethostname
import time
from openerp import SUPERUSER_ID
from openerp import netsvc, tools
from openerp.report.report_sxw import report_sxw, report_rml
from openerp.tools.config import config
from openerp.tools.safe_eval import safe_eval as eval
from datetime import datetime

class actions_server(osv.osv):
    _inherit = 'ir.actions.server'
    _columns = {
        'state': fields.selection([
            ('client_action','Client Action'),
            ('dummy','Dummy'),
            ('loop','Iteration'),
            ('code','Python Code'),
            ('trigger','Trigger'),
            ('email','Email'),
            ('sms','SMS'),
            ('object_create','Create Object'),
            ('object_copy','Copy Object'),
            ('object_write','Write Object'),
            ('other','Multi Actions'),
            ('beopen','BeOpen'),
        ], 'Action Type', required=True, size=32, help="Type of the Action that is to be executed"),
    }
    
    def merge_message(self, cr, uid, keystr, action, context=None):
        if context is None:
            context = {}
        def merge(match):
            obj_pool = self.pool.get(action.model_id.model)
            id = context.get('active_id')
            obj = obj_pool.browse(cr, uid, id)
            exp = str(match.group()[2:-2]).strip()
            result = eval(exp,
                          {
                            'object': obj,
                            'context': dict(context), # copy context to prevent side-effects of eval
                            'time': time,
                          })
            if result in (None, False):
                return str("--------")
            return tools.ustr(result)

        com = re.compile('(\[\[.+?\]\])')
        message = com.sub(merge, keystr)
        return message
    
    # Context should contains:
    #   ids : original ids
    #   id  : current id of the object
    # OUT:
    #   False : Finished correctly
    #   ACTION_ID : Action to launch

    # FIXME: refactor all the eval() calls in run()!
    def run(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        user = self.pool.get('res.users').browse(cr, uid, uid)
        for action in self.browse(cr, uid, ids, context):
            obj = None
            obj_pool = self.pool.get(action.model_id.model)
            if context.get('active_model') == action.model_id.model and context.get('active_id'):
                obj = obj_pool.browse(cr, uid, context['active_id'], context=context)
            cxt = {
                'self': obj_pool,
                'object': obj,
                'obj': obj,
                'pool': self.pool,
                'time': time,
                'cr': cr,
                'context': dict(context), # copy context to prevent side-effects of eval
                'uid': uid,
                'user': user
            }
            expr = eval(str(action.condition), cxt)
            if not expr:
                continue

            if action.state=='client_action':
                if not action.action_id:
                    raise osv.except_osv(_('Error'), _("Please specify an action to launch !"))
                return self.pool.get(action.action_id.type)\
                    .read(cr, uid, action.action_id.id, context=context)
            
            #action server BeOpen
            if action.state == 'beopen':
                try:
                    number= eval(str(action.mobile),cxt)
                except:
                    number = str(action.mobile)
                body = self.merge_message(cr, uid, action.sms, action, context)
                self.pool.get('message.message').action_sendSMS(cr,uid,False,number,body,context)
            
            if action.state=='code':
                eval(action.code, cxt, mode="exec", nocopy=True) # nocopy allows to return 'action'
                if 'action' in cxt:
                    return cxt['action']

            if action.state == 'email':
                email_from = config['email_from']
                if not email_from:
                    _logger.debug('--email-from command line option is not specified, using a fallback value instead.')
                    if user.email:
                        email_from = user.email
                    else:
                        email_from = "%s@%s" % (user.login, gethostname())

                try:
                    address = eval(str(action.email), cxt)
                except Exception:
                    address = str(action.email)

                if not address:
                    _logger.info('No partner email address specified, not sending any email.')
                    continue

                # handle single and multiple recipient addresses
                addresses = address if isinstance(address, (tuple, list)) else [address]
                subject = self.merge_message(cr, uid, action.subject, action, context)
                body = self.merge_message(cr, uid, action.message, action, context)
                ir_mail_server = self.pool.get('ir.mail_server')
                msg = ir_mail_server.build_email(email_from, addresses, subject, body)
                res_email = ir_mail_server.send_email(cr, uid, msg)
                if res_email:
                    _logger.info('Email successfully sent to: %s', addresses)
                else:
                    _logger.warning('Failed to send email to: %s', addresses)

            if action.state == 'trigger':
                wf_service = netsvc.LocalService("workflow")
                model = action.wkf_model_id.model
                m2o_field_name = action.trigger_obj_id.name
                target_id = obj_pool.read(cr, uid, context.get('active_id'), [m2o_field_name])[m2o_field_name]
                target_id = target_id[0] if isinstance(target_id,tuple) else target_id
                wf_service.trg_validate(uid, model, int(target_id), action.trigger_name, cr)

            if action.state == 'sms':
                #TODO: set the user and password from the system
                # for the sms gateway user / password
                # USE smsclient module from extra-addons
                _logger.warning('SMS Facility has not been implemented yet. Use smsclient module!')

            if action.state == 'other':
                res = []
                for act in action.child_ids:
                    context['active_id'] = context['active_ids'][0]
                    result = self.run(cr, uid, [act.id], context)
                    if result:
                        res.append(result)
                return res

            if action.state == 'loop':
                expr = eval(str(action.expression), cxt)
                context['object'] = obj
                for i in expr:
                    context['active_id'] = i.id
                    self.run(cr, uid, [action.loop_action.id], context)

            if action.state == 'object_write':
                res = {}
                for exp in action.fields_lines:
                    euq = exp.value
                    if exp.type == 'equation':
                        expr = eval(euq, cxt)
                    else:
                        expr = exp.value
                    res[exp.col1.name] = expr

                if not action.write_id:
                    if not action.srcmodel_id:
                        obj_pool = self.pool.get(action.model_id.model)
                        obj_pool.write(cr, uid, [context.get('active_id')], res)
                    else:
                        write_id = context.get('active_id')
                        obj_pool = self.pool.get(action.srcmodel_id.model)
                        obj_pool.write(cr, uid, [write_id], res)

                elif action.write_id:
                    obj_pool = self.pool.get(action.srcmodel_id.model)
                    rec = self.pool.get(action.model_id.model).browse(cr, uid, context.get('active_id'))
                    id = eval(action.write_id, {'object': rec})
                    try:
                        id = int(id)
                    except:
                        raise osv.except_osv(_('Error'), _("Problem in configuration `Record Id` in Server Action!"))

                    if type(id) != type(1):
                        raise osv.except_osv(_('Error'), _("Problem in configuration `Record Id` in Server Action!"))
                    write_id = id
                    obj_pool.write(cr, uid, [write_id], res)

            if action.state == 'object_create':
                res = {}
                for exp in action.fields_lines:
                    euq = exp.value
                    if exp.type == 'equation':
                        expr = eval(euq, cxt)
                    else:
                        expr = exp.value
                    res[exp.col1.name] = expr

                obj_pool = self.pool.get(action.srcmodel_id.model)
                res_id = obj_pool.create(cr, uid, res)
                if action.record_id:
                    self.pool.get(action.model_id.model).write(cr, uid, [context.get('active_id')], {action.record_id.name:res_id})

            if action.state == 'object_copy':
                res = {}
                for exp in action.fields_lines:
                    euq = exp.value
                    if exp.type == 'equation':
                        expr = eval(euq, cxt)
                    else:
                        expr = exp.value
                    res[exp.col1.name] = expr

                model = action.copy_object.split(',')[0]
                cid = action.copy_object.split(',')[1]
                obj_pool = self.pool.get(model)
                obj_pool.copy(cr, uid, int(cid), res)

        return False
    
actions_server()