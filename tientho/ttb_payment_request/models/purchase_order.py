from odoo import models, fields, api
from odoo.exceptions import UserError

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    payment_request_ids = fields.One2many('ttb.payment.request', 'purchase_order_id', string='Đề nghị thanh toán')
    payment_request_count = fields.Integer('Số phiếu thanh toán', compute='compute_payment_request_count')

    @api.depends('payment_request_ids')
    def compute_payment_request_count(self):
        for rec in self:
            rec.payment_request_count = len(rec.payment_request_ids)

    def _check_payment(self):
        payment_request_ids = self.payment_request_ids.filtered(lambda payment: payment.state == 'approved')
        amount_paid = sum(payment_request_ids.mapped('amount_total'))

        if amount_paid >= self.amount_total:
            raise UserError('Đã đề xuất thanh toán toàn bộ số tiền đơn hàng.')

    def _prepare_payment_request_action(self, payment_type):
        """Hàm helper để tạo action, tránh lặp code."""
        self.ensure_one()
        return {
            'name': 'Tạo Đề Nghị Thanh Toán',
            'type': 'ir.actions.act_window',
            'res_model': 'ttb.payment.request',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_payment_type': payment_type,
                'default_partner_id': self.partner_id.id,
                # Truyền PO vào trường Many2many
                'default_purchase_order_id': self.id,
            }
        }

    def action_partial_payment(self):
        self._check_payment()
        return self._prepare_payment_request_action('advance')

    def action_remain_payment(self):
        self._check_payment()
        return self._prepare_payment_request_action('request')

    def action_select_payment(self):
        self._check_payment()
        self.ensure_one()
        return {
            'name': 'Chọn Loại Đề Xuất Thanh Toán',
            'type': 'ir.actions.act_window',
            'res_model': 'ttb.payment.request.selector',
            'view_mode': 'form',
            'target': 'new', # Mở dưới dạng popup
            'context': {
                'default_purchase_order_id': self.id,
            }
        }

    def action_view_payment_request(self):
        xml_id = 'ttb_payment_request.action_payment_request'
        result = self.env['ir.actions.act_window']._for_xml_id(xml_id)
        # result['views'] = [(False, 'form')]
        result['domain'] = [('id', 'in', self.payment_request_ids.ids)]

        return result
