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
    "name" : "Trends",
    "version" : "1.0",
    "author" : "BHC",
    "website" : "http://www.bhc.be/",
    "category" : "Generic Modules/Others",
    "depends" : ["base","base_vat","crm"],
    "description" : """The TrendsTop module allows to:

        - run multi-criteria search from Odoo to TrendsTop
        - convert results in Odoo CRM leads
        - check company's figures (turnover, benefits,...) from the contact form
        - check and import company's contact details""",
    "init_xml" : [],
    "demo_xml" : [],
    "images": ['images/configuration.png','images/partner.png','images/research.png','images/result.png',],    
    "data":["security/security.xml","security/menu.xml","security/ir.model.access.csv","trends_view.xml","res_partner_view.xml","crm_lead_view.xml","trends_data.xml"],
    "active": False,
    "installable": True,
}
