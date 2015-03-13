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
from datetime import datetime
_logger = logging.getLogger(__name__)
import time
_TASK_STATE = [('send', 'Sended'),('notsend', 'Not sended')]

class sms_check(osv.osv):
    _name = 'sms.check.state'
    
    def check_state_ids(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        active_ids = context.get('active_ids')
        self.pool.get('message.message').check_state(cr,uid,active_ids,context)
        return {'type': 'ir.actions.act_window_close'}
    
sms_check()

class message_send(osv.osv):
    _name='message.message'
    _columns={ 
        'number' : fields.char('Number',readonly=True),
        'deliverystatus' : fields.char('Delivery Status',readonly=True),
        'message' : fields.text('Message',readonly=True),
        'datime' : fields.datetime('Date',readonly=True),
        'template' : fields.many2one('email.template','Template',readonly=True),
        'partner_id': fields.many2one('res.partner','Partner', readonly=True),
        'state': fields.selection(_TASK_STATE, 'Related Status', required=True),
        'mess_id' :fields.char('Message Id', size=30,readonly=True), 
    }
    _order='id desc'
    
    def sms_send(self,cr,uid,ids,context=None):
        for i in self.pool.get('message.message').browse(cr,uid,ids):
            self.action_sendSMS(cr,uid,i.id,i.number,i.message,context)
        return True
    
    def check_state(self,cr,uid,ids,context=None):
        time.sleep(2)
        connect_obj = self.pool.get('connect.connect')
        connect_ids = connect_obj.search(cr,uid,[('type','=',"sending")])
        connect_rec = connect_obj.browse(cr, uid, connect_ids)
        password=str(connect_rec[0].password)
        username=str(connect_rec[0].username)
        url=str(connect_rec[0].url)
        endpoints=url
        registration_id = connect_rec[0].registration_id
        baseurl=endpoints
        ''' instantiantion de la classe JSONRequest() '''
        requestProcessor=JSONRequest()
        for i in ids:
            mess_id=self.browse(cr,uid,i).mess_id
            if '{registration_id}' in baseurl: baseurl=baseurl.replace('{registration_id}',str(registration_id))
            url=baseurl+'/'+str(mess_id)
            time.sleep(0.05)
            sentRessource= url + "/deliveryInfos"
            rawresponse=requestProcessor.get(sentRessource,'application/json', username, password)
            print rawresponse.getContent()
            if rawresponse is not None and rawresponse.getContent() is not None:
                jsondata=json.loads(rawresponse.getContent())
                if jsondata is not None and jsondata['deliveryInfoList'] is not None:
                    self.write(cr,uid,i,{'deliverystatus':jsondata['deliveryInfoList']['deliveryInfo'][0]['deliveryStatus'],'state':'send'})
                else:
                    self.write(cr,uid,i,{'deliverystatus':rawresponse.getCode()})
            else:
                if rawresponse.getCode() == 400:
                    self.write(cr,uid,i,{'deliverystatus':"Error 400 : Bad Request" })
                if rawresponse.getCode() == 401:
                    self.write(cr,uid,i,{'deliverystatus':"Error 401 : Authentification Failure" })
                if rawresponse.getCode() == 403:
                    self.write(cr,uid,i,{'deliverystatus':"Error 403 : Forbidden Authentification Credentials" })
                if rawresponse.getCode() == 404:
                    self.write(cr,uid,i,{'deliverystatus':"Error 404 : Not Found" })
                if rawresponse.getCode() == 405:
                    self.write(cr,uid,i,{'deliverystatus':"Error 405 : Method Not Supported" })
                if rawresponse.getCode() == 500:
                    self.write(cr,uid,i,{'deliverystatus':"Error 500 : Internal Error" })
                if rawresponse.getCode() == 503:
                    self.write(cr,uid,i,{'deliverystatus':"Error 503 : Server Busy And Service Unavailable" })

        return True    
        
    def action_sendSMS(self,cr,uid,ids,number,sms, context=None):
        if not number and ids:
            self.write(cr,uid,ids,{'state':'notsend'})
            return False
        num='tel:' + number
        message=sms
        connect_obj = self.pool.get('connect.connect')
        connect_ids = connect_obj.search(cr,uid,[('type','=',"sending")])
        connect_rec = connect_obj.browse(cr, uid, connect_ids)
        password=str(connect_rec[0].password)
        username=str(connect_rec[0].username)
        url=str(connect_rec[0].url)
        endpoints=url
        registration_id = connect_rec[0].registration_id
        baseurl=endpoints
        ''' instantiantion de la classe JSONRequest() '''
        requestProcessor=JSONRequest()
        if '{registration_id}' in baseurl: baseurl=baseurl.replace('{registration_id}',str(registration_id))
        formdata = { 'message' : str(message.encode('utf-8')) , 'address': num, 'senderAddress' : registration_id}
        data_encoded = urllib.urlencode(formdata)
        rawresponse=requestProcessor.post(baseurl,data_encoded,'application/json',username, password)
        print rawresponse
        if rawresponse is not None and rawresponse.getContent() is not None:
            jsondata=json.loads(rawresponse.getContent())
            if jsondata is not None and jsondata['resourceReference'] is not None:
                mondict=jsondata['resourceReference']
                monEndpoint = str(mondict['resourceURL'])
                datas=monEndpoint.split('/')
                lgt=len(datas)
                mess_id=datas[lgt-1]
                if ids:
                    self.write(cr,uid,ids,{'mess_id':mess_id})
        return True
message_send() 