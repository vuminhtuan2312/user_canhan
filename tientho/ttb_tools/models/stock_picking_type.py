from odoo import models, fields, api


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    ttb_augges_dmnx = fields.Many2one('ttb.augges.dmnx', string='Augges DMNX')

