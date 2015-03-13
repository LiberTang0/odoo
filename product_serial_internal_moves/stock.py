# -*- encoding: utf-8 -*-
##############################################################################
#
#    Product serial module for OpenERP
#    Copyright (C) 2008 Raphaël Valyi
#    Copyright (C) 2011 Anevia S.A. - Ability to group invoice lines
#              written by Alexis Demeaulte <alexis.demeaulte@anevia.com>
#    Copyright (C) 2011-2013 Akretion - Ability to split lines on logistical units
#              written by Emmanuel Samyn
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields, osv
from openerp.tools.translate import _

class stock_move(osv.osv):
    _inherit = "stock.move"

    def _check_tracking(self, cr, uid, ids, context=None):
        for move in self.browse(cr, uid, ids, context=context):
            if not move.prodlot_id and \
               (move.state == 'done' and \
               ( \
                   (move.product_id.track_production and move.location_id.usage == 'production') or \
                   (move.product_id.track_production and move.location_dest_id.usage == 'production') or \
                   (move.product_id.track_incoming and move.location_id.usage == 'supplier') or \
                   (move.product_id.track_outgoing and move.location_dest_id.usage == 'customer') or \
                   (move.product_id.track_incoming and move.location_id.usage == 'inventory') or \
                   (move.product_id.track_internal and move.location_id.usage == 'internal' ) \
               )):
                return False
        return True

    _constraints = [
        (_check_tracking,'You must assign a serial number for this product.', ['prodlot_id'])
                    ]
stock_move()