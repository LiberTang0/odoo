# -*- coding: utf-8 -*-

import time
from osv import fields
from osv import osv
from osv.orm import except_orm
from tools.translate import _
import pooler

class res_partner(osv.osv):
    _inherit = "res.partner"
    
    def _check_categ(self, cr, uid, ids, name, args, context):
        res={}
        bl=self.pool.get('res.partner.category').search(cr,uid,[('blacklist','=',True)])
        if bl and len(ids)==1:
            for i in self.browse(cr,uid,ids):
                for j in i.category_id:
                    if j.blacklist==True:
                        res[i.id]=1
                    else:
                        res[i.id]=0
                idss=self.search(cr,uid,[('parent_id','=',i.id)])
                for z in self.browse(cr,uid,idss):
                    self.write(cr,uid,z.id,{'blacklist':1,'sale_warn':i.sale_warn,'sale_warn_msg':i.sale_warn_msg,'category_id':[(4,bl[0])]})
        return res
    
    _columns = {
        'blacklist': fields.function(_check_categ, method=True, string=_('Blacklist'), type='boolean', store=True ),
    }
res_partner()

class category(osv.osv):
    _inherit = "res.partner.category"
    _columns = {
        'blacklist': fields.boolean(_('Blacklist')),
    }
category()