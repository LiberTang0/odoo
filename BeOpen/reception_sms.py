# -*- coding: utf-8 -*-
from osv import fields,osv
import urllib
import urllib2
import httplib
from tools.translate import _
from urllib2 import HTTPError
from datetime import datetime
import json
import base64
from response.HTTPResponse import HTTPResponse
from urllib2 import HTTPError
from response.sms.SendSMSResponse import SendSMSResponse
from response.sms.RetrieveSMSResponse import RetrieveSMSResponse 
from foundation.JSONRequest import JSONRequest
from response.sms.SMSSendDeliveryStatusResponse import SMSSendDeliveryStatusResponse
import re
import logging
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
_logger = logging.getLogger(__name__)

class menu_receipt(osv.osv):
    _name='receipt.receipt'
    _columns={
         'config' :fields.many2one('connect.connect','Configuration',readonly=True),
         'link' :fields.many2one('connect.reception','Linked To',readonly=True),
         'sendadres' : fields.char('Sender', size=50, readonly=True),
         'mess' : fields.text('Message',readonly=True),
         'datime' : fields.datetime('Date',readonly=True),
         'mess_id' :fields.char('Message Id', size=30,readonly=True),
    }
    _order='id desc' 
     
    def cron_receiveSMS(self, cr, uid, context=None):
        print "cron"
        connect_obj = self.pool.get('connect.connect')
        connect_recept_obj = self.pool.get('connect.reception')
        receipt_ids = connect_obj.search(cr,uid,[('type','=',"reception")])
        for j in connect_obj.browse(cr, uid, receipt_ids):
            url=str(j.url)
            password=str(j.password) 
            username =str(j.username)
            registration_id =str(j.registration_id)
            if '{registration_id}' in url: url=url.replace('{registration_id}',str(registration_id))
            responsetype='application/json'
            opener = urllib2.build_opener(urllib2.HTTPHandler)
            request = urllib2.Request(url)
            request.add_header('Accept', responsetype)
            request.get_method = lambda: 'GET'
            base64string=base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
            request.add_header("Authorization", "Basic %s" % base64string)
            response=HTTPResponse(None)
   #         try:
            if 1==1:
                handle = opener.open(request)
                jsondata=json.loads(handle.read())
                for i in jsondata['inboundSMSMessageList']['inboundSMSMessage']:
                    mobile=i['senderAddress'].split(':')
                    date=re.sub("T", " ", i['dateTime'])
                    date2=date.split('+')
                    if len(date2)>1:
                        date_d=date2[0]
                        date_final = (datetime.strptime(date_d[:19], "%Y-%m-%d %H:%M:%S"))- relativedelta(hours=int(date2[1][0:2]))
                    else:
                        date2=date.split('-')
                        date_d=date2[0]
                        date_final = (datetime.strptime(date_d[:19], "%Y-%m-%d %H:%M:%S"))+ relativedelta(hours=int(date2[1][0:2]))
                    #Si shortcode Shared
                    if j.type_2 =='shared':
                        print 'hoho'
                        fw=i['message'].split(' ')
                        id_record=False
                        #on boucle sur les second keyword si ALL n'est pas présent
                        for k in j.connect_ids:
                            #si le second keyword est egale a celui de la config
                            if fw[1] == k.name:
                                id_sms=self.create(cr,uid,{'sendadres' : mobile[1] ,
                                                   'mess' :" ".join(i['message'].split()[2:]),
                                                   'datime' : date_final,
                                                   'mess_id' : i['messageId'],
                                                   'config': j.id})
                                id_record=self.pool.get(k.link.model).create(cr,uid,{k.subject.name:j.name,
                                                                   k.message.name:" ".join(i['message'].split()[2:]),
                                                                   k.mobile.name:mobile[1],
                                                                   k.date.name:date_final,
                                                                   })
                                #on verifie qu'on encode le sms_id ou pas
                                if k.sms_id and k.sms_id.name:
                                    self.pool.get(k.link.model).write(cr,uid,id_record,{k.sms_id.name : i['messageId']})
                                #On lie le sms a la config du second keyword  
                                self.write(cr,uid,id_sms,{'link' : k.id})
                                
                            #on verifie si le second keyword est '*' (ALL)
                            elif k.name == '*' and not id_record:
                                id_sms=self.create(cr,uid,{'sendadres' : mobile[1] ,
                                                   'mess' :" ".join(i['message'].split()[1:]),
                                                   'datime' : date_final,
                                                   'mess_id' : i['messageId'],
                                                   'config': j.id})
                                id_record=self.pool.get(k.link.model).create(cr,uid,{k.subject.name:j.name,
                                                                   k.message.name:" ".join(i['message'].split()[1:]),
                                                                   k.mobile.name:mobile[1],
                                                                   k.date.name:date_final,
                                                                   })
                                #on verifie qu'on encode le sms_id ou pas
                                if k.sms_id and k.sms_id.name:
                                    self.pool.get(k.link.model).write(cr,uid,id_record,{k.sms_id.name : i['messageId']})
                                #On lie le sms a la config du second keyword  
                                self.write(cr,uid,id_sms,{'link' : k.id})
                                
                    #si shortcode Dedicated            
                    elif j.type_2=='dedicated':
                        fw=i['message'].split(' ')
                        id_record=False
                        #on boucle sur les seconds keyword si ALL n'est pas présent
                        for k in j.connect_ids:
                            #si le second keyword est egale a celui de la config
                            if fw[0] == k.name:
                                id_sms=self.create(cr,uid,{'sendadres' : mobile[1] ,
                                                   'mess' :" ".join(i['message'].split()[1:]),
                                                   'datime' : date_final,
                                                   'mess_id' : i['messageId'],
                                                   'config': j.id})
                                id_record=self.pool.get(k.link.model).create(cr,uid,{k.subject.name:j.name,
                                                                   k.message.name:" ".join(i['message'].split()[1:]),
                                                                   k.mobile.name:mobile[1],
                                                                   k.date.name:date_final,
                                                                   })
                                #on verifie qu'on encode le sms_id ou pas
                                if k.sms_id and k.sms_id.name:
                                    self.pool.get(k.link.model).write(cr,uid,id_record,{k.sms_id.name : i['messageId']})
                                #On lie le sms a la config du second keyword  
                                self.write(cr,uid,id_sms,{'link' : k.id})
                            #on verifie si le second keyword est '*' (ALL)
                            elif k.name == '*' and not id_record:
                                id_sms=self.create(cr,uid,{'sendadres' : mobile[1] ,
                                                   'mess' :" ".join(i['message'].split()[0:]),
                                                   'datime' : date_final,
                                                   'mess_id' : i['messageId'],
                                                   'config': j.id})
                                id_record=self.pool.get(k.link.model).create(cr,uid,{k.subject.name:j.name,
                                                                   k.message.name:" ".join(i['message'].split()[0:]),
                                                                   k.mobile.name:mobile[1],
                                                                   k.date.name:date_final,
                                                                   })
                                #on verifie qu'on encode le sms_id ou pas
                                if k.sms_id and k.sms_id.name:
                                    self.pool.get(k.link.model).write(cr,uid,id_record,{k.sms_id.name : i['messageId']})
                                #On lie le sms a la config du second keyword  
                                self.write(cr,uid,id_sms,{'link' : k.id})
                    
    #        except HTTPError, e:
     #           response.setCode(e.code)
            return response
menu_receipt()