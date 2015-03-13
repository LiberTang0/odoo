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

class email_temp(osv.osv):
    _inherit = "email.template"
    _columns = {
            'number' : fields.char('Number',),
            'content' : fields.text('Content',),
            'sms' : fields.boolean('Template SMS'),
            'mail' : fields.boolean('Template Mail'),
            }
    _defaults = {
        'mail': 1
        }
email_temp()