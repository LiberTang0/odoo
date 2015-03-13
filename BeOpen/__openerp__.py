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
    "name" : "BeOpen",
    "version" : "1.0",
    "author" : "BHC",
    "website" : "www.bhc.be",
    "category" : "Generic Modules/Others",
    "depends" : ["base","sale","mail",'email_template'],
    "description" : """
    Integration with the belgian telecom operator Belgacom via its OpenAPI BeOpen.\n
    Currently it allows integration in order to:\n
    * Send SMS: From a predefined template (like the email ones) with dynamic content\n
    * Receive SMS: And create OpenERP objects automatically from the SMS trigger\n
    
    In order to configure your account, you first need to register on http://beopen.belgacom.be

    """,
    "init_xml" : [],
    "demo_xml" : [],
    'images': ['images/01.png','images/02.png','images/03.png'],
    "data":["sms_connect_view.xml",
            "send_sms_view.xml",
            "reception_sms_view.xml",
            'ir_action.xml',
            'wizard/sms_template_preview_view.xml',
            'wizard/sms_compose_message_view.xml',
            "sms_template_view.xml",
            "crm_lead_view.xml",
            ],
    "active": False,
    "installable": True,
}
