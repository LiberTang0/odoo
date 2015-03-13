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
	'name': 'blacklist partner',
	'version': '1.0',
	'category': 'Generic Modules/Others',
	'description': """
	This module allows you to add a category 'blacklist' in the form of your customers.
	If a customer is in this category it will appear in red in OpenERP.
	""",
	'author': 'BHC',
	'website': 'www.bhc.be/',
	'depends': ['base','sale','warning'], 
	'images': ['images/customer.png','images/customer_tree.png','images/sale_order.png'],
	'init_xml': [],
	'update_xml': ['partner_listing.xml'],
	'demo_xml': [],
	'installable': True,
	'active': False,
}

