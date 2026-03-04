from odoo import *


class StockBackorderConfirmation(models.TransientModel):
    _inherit = 'stock.backorder.confirmation'

    def process(self):
        self = self.sudo()
        return super(StockBackorderConfirmation, self).process()

    def process_cancel_backorder(self):
        self = self.sudo()
        return super(StockBackorderConfirmation, self).process_cancel_backorder()
