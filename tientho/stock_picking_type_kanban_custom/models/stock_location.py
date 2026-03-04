from odoo import models, fields

class StockLocation(models.Model):
    _inherit = 'stock.location'

    augges_id = fields.Char(string='AUGGES ID')
