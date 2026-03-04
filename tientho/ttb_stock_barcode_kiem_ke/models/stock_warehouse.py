from odoo import models, fields

class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    transit_location = fields.Many2one('stock.location', string='Địa điểm đi đường')
