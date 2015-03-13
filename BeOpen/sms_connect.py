# -*- coding: utf-8 -*-
from osv import fields,osv
import urllib
import httplib
from tools.translate import _    
from response.sms.SendSMSResponse import SendSMSResponse
from response.sms.RetrieveSMSResponse import RetrieveSMSResponse 
import json
import base64
from foundation.JSONRequest import JSONRequest
from response.sms.SMSSendDeliveryStatusResponse import SMSSendDeliveryStatusResponse
import re
import logging
_logger = logging.getLogger(__name__)


class menu_connections_reception(osv.osv): 
    _name='connect.reception'
    _columns={
        'connect_id':fields.many2one('connect.connect','Connections'),
        'name': fields.char('Second keyword',size=200,help="Used in OpenERP. If you want all messages create records for only one model, set value '*'"),
        'link' :fields.many2one('ir.model','Applies to' ,required="True"),
        'subject' :fields.many2one('ir.model.fields','Subject', domain="[('model_id','=',link),('ttype','!=','one2many'),('ttype','!=','many2many')]"),
        'message' :fields.many2one('ir.model.fields','Message', domain="[('model_id','=',link),('ttype','!=','one2many'),('ttype','!=','many2many')]"),
        'mobile' :fields.many2one('ir.model.fields','Mobile', domain="[('model_id','=',link),('ttype','!=','one2many'),('ttype','!=','many2many')]"),
        'sms_id' :fields.many2one('ir.model.fields','Message ID', domain="[('model_id','=',link),('ttype','!=','one2many'),('ttype','!=','many2many')]"),
        'date' :fields.many2one('ir.model.fields','Date', domain="[('model_id','=',link),'|',('ttype','=','date'),('ttype','=','datetime')]"),
        'sequence':fields.integer('Sequence'),
    }
    _order='sequence asc'
    _defaults = {
          'sequence':10,
          }
    def onchange_name(self, cr, uid, ids, name, context=None):
        res={}
        if not name:
            return res
        elif name=='*':
            raise osv.except_osv(_('Warning!'), _('With "*", only this configuration will be used')) 
        else:
            return res
        
    def onchange_link(self, cr, uid, ids, link, context=None):
        return {'value':{'subject':False,'message':False,'mobile':False,'sms_id':False,'date':False}}
        
menu_connections_reception()

class menu_connections(osv.osv): 
    _name='connect.connect'
    _columns={
        'type':fields.selection([('sending', 'Sending'),('reception', 'Reception'),('payment', 'Payment')], 'Type',required=True),
        'username' : fields.char('Username' , size=60, required=True, translate=True),
        'password' : fields.char('Password' , size=30, required=True, translate=True),
        'url': fields.char('Url',size=200,required=True),
        'name': fields.char('Name',size=300,required=True),
        'api': fields.char('Api',size=70,required=True),
        'registration_id' : fields.char('Shortcode',size=20,required=True),
        'keyword': fields.char('First keyword',size=200,help="Used for Belgacom"),
        'type_2' :fields.selection([('shared', 'Shared'),
                                   ('dedicated', 'Dedicated')],'Type',help="If dedicated,OpenERP used the first word in the message; if shared, the second to create record"),
        'connect_ids':fields.one2many('connect.reception', 'connect_id', 'Connections'),
    }
menu_connections()

