from odoo import *


class ReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    def action_create_returns(self):
        self = self.sudo()
        return super(ReturnPicking, self).action_create_returns()

    def action_create_exchanges(self):
        self = self.sudo()
        return super(ReturnPicking, self).action_create_exchanges()

    def action_create_returns_all(self):
        self = self.sudo()
        return super(ReturnPicking, self).action_create_returns_all()
