# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


{
	'name': 'Partner Blacklist',
	'version': '1.0',
	'category': 'Generic Modules/Others',
	'description': """
	This module adds a ‘Blacklist’ category to partners. If a customer or supplier is set in this category, then it appears in red in the partners list.
    You can also add warnings on some objects (i.e. Sales Order) in order to inform the user that the partner he is trying to use is on the blacklist, and why.
	""",
	'author': 'BHC',
	'website': 'www.bhc.com/',
	'depends': ['base','sale','warning',], 
	'images': ['images/customer_tree.png','images/customer.png','images/sale_order.png'],
	'init_xml': [],
	'update_xml': ['partner_listing.xml'],
	'demo_xml': [],
	'installable': True,
	'active': False,
}

