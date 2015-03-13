# -*- coding: utf-8 -*-

from openerp.osv import osv, fields
from openerp.tools.translate import _
import time
from datetime import datetime

class crm_lead(osv.osv):
    _inherit = 'crm.lead'
    _columns = {
        'vote': fields.char('Vote',size=64),
    }
    
crm_lead()