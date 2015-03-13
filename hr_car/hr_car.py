## -*- coding: utf-8 -*-
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from tools.translate import _
from osv import fields, osv


class hr_car_marque(osv.osv):
    
    #Object Description
    ###################
    _name = 'hr.car.marque'
    _description = "Marque de voitures"
    
    #Field Definitions
    ##################
    _columns = {
        'name': fields.char("Marque", size=64),
    }
hr_car_marque()



class hr_car_modele(osv.osv):
    
    #Object Description
    ###################
    _name = 'hr.car.modele'
    _description = "Modele de voitures"
    _columns = {
        'name': fields.char("Modele", size=64),
        'marque_id': fields.many2one('hr.car.marque', 'Marque'),
    }

hr_car_modele()


class hr_car(osv.osv):

    #Object Description
    ###################
    _name = 'hr.car'
    _description = "Employee Car Description"
    _columns = {
        'name' : fields.char("carname", size=128),
        'immatriculation': fields.char("Immatriculation", size=64, required = True),
        'marque': fields.many2one('hr.car.marque','Marque'),
        'modele': fields.many2one('hr.car.modele','Modele'),
        'couleur': fields.char("Couleur", size=64),
        'num_chassis': fields.char("Numero de chassis", size=64),
        'carburant': fields.selection([('Diesel','Diesel'), 
                                       ('Essence','Essence'), 
                                       ('Electrique','Electrique')], 'Carburant', size=64),
        'moteur' : fields.char("Moteur", size=64),
        'fournisseur_id': fields.many2one('res.partner', 'Fournisseur'),
        'leasing_id': fields.many2one('res.partner', 'Leasing'),
        'employee_id': fields.many2one('hr.employee', "Employe"),
        'co2' : fields.char("co2", size=64),
        
        'entretien_id': fields.one2many('hr.car.sheet', 'line_id'),
        
        'courtier_id': fields.many2one('res.partner', 'Courtier'),
        'compagnie': fields.char("Compagnie", size=64),
        'num_contrat': fields.char("Numero de contrat", size=64),
        'term_insurance' : fields.date("echeance"),
    }
    

    def create(self, cr, uid, values, context=None):
        immat =  values["immatriculation"]
        modele_id =  values["modele"]
        modele_list = self.pool.get('hr.car.modele').read(cr,uid,[modele_id],['name'])
        modele = modele_list[0]['name']
        marque_id =  values["marque"]
        marque_list = self.pool.get('hr.car.marque').read(cr,uid,[marque_id],['name'])
        marque = marque_list[0]['name']
        concat = marque + "-" + modele + "-" + immat
        values["name"] = concat
        
        res = super(hr_car, self).create(cr, uid, values, context=context)
        employee_id = values["employee_id"]
        if employee_id :
            passage = True
            self.pool.get('hr.employee').write(cr, uid, values["employee_id"],{"vehicle_id": res,
                                                                              "passage": passage})
        return res
    
    

    def write(self, cr, uid, ids, values, context=None):
        
        if ("passage") in values :

            result = super(hr_car,self).write(cr, uid, ids, values,context=context)
            return result
            
        else :
            result = super(hr_car,self).write(cr, uid, ids, values,context=context)
            if isinstance(ids, int) :
                objets = self.pool.get('hr.car').browse(cr,uid,ids)
            else :    
                objets = self.pool.get('hr.car').browse(cr,uid,ids[0])
            immat =  objets["immatriculation"]
            modele =  objets["modele"]["name"]
            marque =  objets["marque"]["name"]
            concat = marque + "-" + modele + "-" + immat
            hr_car_id = objets["id"]
            empl_id = objets["employee_id"]["id"]
            res = super(hr_car, self).write(cr, uid, ids, {'name': concat,}, context=context)
            passage = True
            empl_exist = objets["employee_id"]
           
            
            if ("employee_id") in values :
                if empl_id :
                    passage = True
                    self.pool.get('hr.employee').write(cr, uid, empl_id, {"vehicle_id": hr_car_id, 
                                                                  "passage" :passage})
                
                if not empl_exist : 
                    empl_ids = self.pool.get('hr.employee').search(cr,uid,[('vehicle_id','=',hr_car_id)])
                
                    if empl_ids :
                        for j in empl_ids :
                            self.pool.get('hr.employee').write(cr, uid, j, {"vehicle_id": None, 
                                                                  "passage" :passage})
            
            return res
hr_car()

class hr_car_sheet(osv.osv):

    #Object Description
    ###################
    _name = 'hr.car.sheet'
    _table = 'hr_car_sheet'
    _description = "employee Car history"
    _order = "id desc"
    
    #Field Definitions
    ##################
    _columns = {
        'line_id': fields.many2one('hr.car'),
        'garage_id': fields.many2one('res.partner', 'Garage'),
        'km': fields.char("KM", size=64),
        'remarque': fields.char("Remarque", size=64),
        'date_entretien': fields.datetime("date d'entretien"),
        
    }
    
hr_car_sheet()

class hr_employee(osv.osv):
    
    #Object Description
    ###################
    _name = 'hr.employee'
    _inherit = "hr.employee"
    
    #Field Definitions
    ##################
    _columns = {
        'vehicle_id': fields.many2one('hr.car', 'Vehicules'),
    }
    

    def create(self, cr, uid, values, context=None):
        
        res = super(hr_employee, self).create(cr, uid, values, context=context)
        if("vehicle_id") in values :
        
            vehicle_id =  values["vehicle_id"]
            if vehicle_id:
                passage = True
                self.pool.get('hr.car').write(cr, uid, values["vehicle_id"],{"employee_id": res,
                                                                              "passage": passage})
        return res
    

    def write(self, cr, uid, ids, values, context=None):
        if ids:
            if ("passage") in values :
                del values["passage"]
                result = super(hr_employee,self).write(cr, uid, ids, values,context=context)
                return result
            
            else :
                result = super(hr_employee,self).write(cr, uid, ids, values,context=context)
                objets = self.pool.get('hr.employee').browse(cr,uid,ids[0])
                hr_car_id = objets["vehicle_id"]["id"]
                hr_employee_id = objets["id"]
                car_exist = objets["vehicle_id"]
                passage = True
    
            
                if ("vehicle_id") in values :
                    
                    if hr_car_id :
                        self.pool.get('hr.car').write(cr, uid, hr_car_id,{"employee_id": hr_employee_id,
                                                                          "passage" : passage})
                    if not car_exist :
                        car_ids = self.pool.get('hr.car').search(cr,uid,
                                                                   [('employee_id','=',hr_employee_id)]
                                                                   )
                        if car_ids :
                            for j in car_ids :
                                self.pool.get('hr.car').write(cr, uid, j, {"employee_id": None,
                                                                            "passage": passage 
                                                                      })
                return result
            
hr_employee()
