## -*- coding: utf-8 -*-
{
    "name": "Company vehicles fleet management",
    "version": "1.0",
    "author": "BHC",
    "category": "Human Resources",
    "website": "http://www.bhc.be",
    "description": """
       This module allows to manage the different vehicles of your company. 
       You can link a car to an employee, manage insurances, suppliers, garage and maintenance.
    
    """,
    'depends': ['hr','hr_contract'],
    'data': ['hr_car.xml','security/ir.model.access.csv'],
    'demo_xml': [],
    'test': [],
    'installable': True,
    'active': False,
    'images': ['images/cars_bhc_01.png','images/cars_bhc_02.png','images/cars_bhc_03.png'],
    
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
