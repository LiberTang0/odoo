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
        for i in ids:
            compte_pool=pooler.get_pool(cr.dbname).get('res.partner.category')
            id_recup=compte_pool.search(cr,uid,[('name','=', _('Liste noire')),])
            if not id_recup:
                compte_pool.create(cr,uid,{'create_uid':uid,'name':_('Liste noire'),'active':True})
                id_recup=compte_pool.search(cr,uid,[('name','=', _('Liste noire')),])
            partner_id=self.pool.get('res.partner').browse(cr,uid,i).id    
            id_categ=self.pool.get('res.partner').browse(cr,uid,partner_id).category_id
            for j in id_categ:
                if id_recup[0]==j.id:
                    res[i]=1
                    return res
                else:
                    res[i]=0
        return res
    
    _columns = {
        'blacklist': fields.function(_check_categ, method=True, string='Blacklist', type='boolean', store=True ),
        
    }
res_partner()

