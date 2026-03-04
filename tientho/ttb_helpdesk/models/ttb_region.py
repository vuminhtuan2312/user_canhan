from odoo import api, fields, models, _
from odoo.exceptions import UserError


class TTBRegion(models.Model):
    _name = 'ttb.region'
    _description = 'Vùng'

    name = fields.Char(string='Vùng', required=True)
    director_id = fields.Many2one('res.users', string='Giám đốc vùng')

class TTBBranch(models.Model):
    _inherit = 'ttb.branch'

    ttb_region_id = fields.Many2one('ttb.region', string='Vùng')
    director_id = fields.Many2one('res.users', string='Giám đốc cơ sở')
    manager_id = fields.Many2one('res.users', string='Quản lý cơ sở')
    has_report = fields.Boolean(string='Báo cáo', default=False)

class TTBArea(models.Model):
    _inherit = 'ttb.area'

    show_in_crm = fields.Boolean(string='Hiển thị với CRM', default=False)
