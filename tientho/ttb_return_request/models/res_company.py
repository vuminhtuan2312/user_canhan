from odoo import models, fields, api, _

class ResCompany(models.Model):
    _inherit = 'res.company'

    return_warehouse_id = fields.Many2one('stock.location', 'Kho đi đường trả lại',)