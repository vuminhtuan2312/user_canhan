from odoo import *
from odoo import _
from odoo.tools import float_repr, float_compare
import pytz


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _prepare_invoice_vals(self):
        # ttb_serial = self.env['ttb.einvoice.serial'].search([], limit=1, order='id desc')
        ttb_serial = self.ttb_branch_origin_id.invoice_serial_id or self.ttb_branch_id.invoice_serial_id
        if not ttb_serial:
            raise exceptions.ValidationError('Chưa có thông tin để đồng bộ Hóa đơn điện tử, không thể thực hiện tạo hóa đơn')
        vals = super()._prepare_invoice_vals()
        ttb_invoice_id = self.company_id.partner_id.address_get(['invoice'])['invoice']
        vals.update({
            'ttb_serial_id': ttb_serial.id,
            'ttb_invoice_id': ttb_invoice_id,
        })
        return vals

    # def action_pos_order_invoice(self):
    #     res = super().action_pos_order_invoice()
    #     self.account_move.button_draft()
    #     if self.account_move.ttb_service_id.vendor == 'vnpt':
    #         self.account_move.ttb_call_api_einvoice()
    #     return res
