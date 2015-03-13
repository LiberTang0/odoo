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
_logger = logging.getLogger(__name__)

class menu_paiment(osv.osv):
    _name='paiment.paiment'

        
    _columns={
              
         'telephone' : fields.char('Telephone number',size=50,required=True),
         'transactionOperationStatus' : fields.selection([('charged','CHARGED')],'transaction status'),
         #'transactionOperationStatus' : fields.char('transaction status',size=50,required=True),
         'description' : fields.char('Description',size=80,required=True),
         'currency' : fields.char('Currency', size=20,required=True),
        # 'currency' : fields.many2one('res.currency', 'Currency',required=True),
         'amount' : fields.char('Amount',size=20,required=True),
         'referenceCode' : fields.char('Reference Code',size=80,required=True),
         'purchaseCategoryCode' : fields.char('Purchase Category Code',size=50),
         'channel' : fields.char('Channel',size=20,required=True,help='dans ce cas toujours mettre SMS'),
         'OnBehalfOf' : fields.char('onBehalfOf',size=80),
         'taxAmount' : fields.char('TaxAmount',size=50),
         'response' : fields.char('Response',readonly=True,translate=True,size=80), 
         'clientCorrelator' : fields.char('ClientCorrelator',size=30),
         
         
         
         
   
    }
    
    '''
        charge : charge an amount to the end user's bill. 
        
        Parameters:
        endUserId : 
        referenceCode : (string, unique per charge event) 
        description : is the description  of charge
        currency : the string USD is use for
        amount : (decimal) can be a whole number or decimal
       
        clientCorrelator : (string) 
        onBehalfOf : (string) partners to specify the actual payee.
        purchaseCategoryCode : (string) an indication of the content type. Values meaningful to the billing system would be published by a OneAPI implementation.
        channel : (string) can be 'Wap', 'Web', 'SMS', depending on the source of user interaction
        taxAmount : decimal) tax already charged by the merchant.
        '''
## this function allow to perform operation of paiment(  paimentSMS)  to charge an amount to the end user's bill
# @param self The object pointer             
# @param cr The current row from the database cursor
# @param uid The current user ID
# @param ids the id of the object
# @param context The context
    def paimentSMS(self,cr,uid,ids,context=None):
        
        temp=self.browse(cr, uid, ids, context=context) 
    
        
        connect_obj = self.pool.get('connect.connect')
        
        connect_ids = connect_obj.search(cr,uid,[])
        connect_rec = connect_obj.browse(cr, uid, connect_ids)
        
        '''information from menu authentication  '''
        end=str(connect_rec[0].url_pay)
        #print'end',end
        password=str(connect_rec[0].password) 
        username =str(connect_rec[0].username)
        
        transactionOperationStatus=str(temp[0].transactionOperationStatus)
        description=str(temp[0].description)
        currency=str(temp[0].currency)
        
        amount= float(temp[0].amount)  
        referenceCode=str(temp[0].referenceCode)
        taxAmount=str(temp[0].taxAmount)
        purchaseCategoryCode=str(temp[0].purchaseCategoryCode)
        channel=str(temp[0].channel) 
        onBehalfOf=str(temp[0].OnBehalfOf)
        clientCorrelator=str(temp[0].clientCorrelator)
        
        endUser=str(temp[0].telephone)
        ''' adding the string tel: to endUser which is telephone number of one user ''' 
        num="tel:+" +endUser
        
        endUserId=num 
        baseurl=end
        
        
        if '{endUserId}' in baseurl : baseurl=baseurl.replace('{endUserId}', str(endUserId)) 
        
        
        
        responsetype='application/json'
        
        '''form urlencoded ''' 
        conTyp='application/x-www-form-urlencoded'
       
        
        
        formdata = { 
                     "clientCorrelator" : clientCorrelator,
                     "endUserId" : endUserId, 
                     "amount" : amount ,
                     "currency" : currency,
                     "description" : description,
                     "onBehalfOf" : onBehalfOf,
                     "purchaseCategoryCode" : purchaseCategoryCode,
                     "channel" : channel,
                     "taxAmount" : taxAmount,
                     "referenceCode" : referenceCode,
                     
                     "transactionOperationStatus" : transactionOperationStatus,  
    
                   }
             
        '''turn data into understandable data url '''
        data_encoded = urllib.urlencode(formdata)
        test= data_encoded.replace('+','%20')
        
        
        opener = urllib2.build_opener(urllib2.HTTPHandler)
         
        request = urllib2.Request(baseurl, test)
        print'base',baseurl
        
        if responsetype is not None:
            
            request.add_header('Accept', responsetype)
        if conTyp is not None :
            request.add_header('Content-Type',conTyp)
            
        request.get_method = lambda: 'POST'
    
        base64string=base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
        request.add_header("Authorization", "Basic %s" % base64string)
        
        '''instantiation of the HttpResponse class '''
        response=HTTPResponse(None)
       
        try:
            
            handle = opener.open(request)
            
            ''' convert json object to object python '''
            
            jsondata=json.loads(handle.read())
            
            print'jsondata',jsondata  
            
            
            info=handle.info()
            content=handle.read()
            response.setCode(handle.getcode())
            response.setContent(content)
            
            
            cod=handle.getcode()
            print 'Response code = %d' % (handle.getcode())
            
            ''' if success store it in field define  in openerp '''
            
            if cod==201 or cod==200 : 
                
                self.pool.get('paiment.paiment').write(cr,uid,ids,{'response' : ' Success'})
                
            
             
            else :
                self.pool.get('paiment.paiment').write(cr,uid,ids,{'response' : ' failed'})
                
            if info is not None:
                headers=info.dict
                if headers is not None:
                    if 'location' in headers:
                        response.setLocation(headers['location'])
                    if 'content-type' in headers:
                        
                        response.setContentType(headers['content-type'])
                        
        except HTTPError, e:
            print 'The server couldn\'t fulfill the request.'
            print 'Error code: ', e.code            
            response.setCode(e.code)
            
        return response
        
        
        return True
    
        
        
       
        
    
menu_paiment()
