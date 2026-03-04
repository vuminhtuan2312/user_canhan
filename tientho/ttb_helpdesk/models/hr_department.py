from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError


class HRDepartment(models.Model):
    _inherit = "hr.department"

    show_in_crm = fields.Boolean(string='Hiển thị với CRM', default=False)
