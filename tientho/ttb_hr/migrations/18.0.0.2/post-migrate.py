from odoo import api, SUPERUSER_ID, _

def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    employees = env['hr.employee'].search([('user_id','!=',False)])
    for employee in employees:
        employee.write({'ttb_code':employee.user_id.login})
