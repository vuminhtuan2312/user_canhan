from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockPickingConfirmWizard(models.TransientModel):
    _name = 'stock.picking.confirm.wizard'
    _description = 'Wizard Xác nhận hàng về'

    picking_id = fields.Many2one('stock.picking', string='Phiếu kho', required=True, readonly=True)
    total_packages = fields.Integer(string='Tổng số kiện thực nhận', required=True)
    received_date = fields.Datetime(string='Ngày nhận hàng', default=fields.Datetime.now, readonly=True)

    def action_confirm(self):
        self.ensure_one()
        if self.total_packages <= 0:
            raise UserError(_("Tổng số kiện phải lớn hơn 0."))

        self.picking_id.write({
            'ttb_received_date': self.received_date,
            'ttb_received_packages': self.total_packages
        })
        return {'type': 'ir.actions.act_window_close'}