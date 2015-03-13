# -*- encoding: utf-8 -*-
############################################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    Copyright (C) 2008-2009 AJM Technologies S.A. (<http://www.ajm.lu). All Rights Reserved
#    Copyright (C) 2010-2011 Thamini S.à.R.L (<http://www.thamini.com>). All Rights Reserved
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
############################################################################################

{
    'name' : 'Holidays Days Off',
    'version' : '1.0',
    'author' : 'BHC',
    'website' : 'www.bhc.be',
    'description' : """
This module creates the non working days in OpenERP using a generator(for the week-end) or manually.
It's use to improve the holidays requests by taking into account the bank holidays.""",
    'depends' : ['base','hr','hr_holidays'],
    'init_xml' : [],
    'demo_xml' : [],
    'images': ['images/leave.png','images/periods.png'],
    'update_xml' : ['day_off.xml','hr_holidays_view.xml','security/ir.model.access.csv','scheduler.xml'],
    'test': [],
    'active' : False,
    'installable' : True,
}