from odoo import *
import logging
_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = 'stock.move'

    remaining_transfer_quantity = fields.Integer(string='Số lượng điều chuyển còn lại', compute='_compute_remaining_transfer_quantity', store=True)

    @api.depends('quantity')
    def _compute_remaining_transfer_quantity(self):
        for rec in self:
            if rec.state != 'done':
                rec.remaining_transfer_quantity = rec.quantity

