# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

{
    'name': 'Cancel Holidays requests',
    'version': '1.0',
    'category': 'Generic Modules/Human Ressources',
    'description': """
        This module allow you to "Reset to New" a confirmed or validated request of holiday.
    """,
    'author': 'BHC',
    'website': 'www.bhc.be',
    'depends': ['base','hr_holidays'],
    'init_xml': [],
    'update_xml': ['hr_holidays.xml'],
    'images': ['images/To_Approve.png','images/Approved.png','images/status.png'],
    'demo_xml': [],
    'test': [],
    'installable': True,
    'active': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
