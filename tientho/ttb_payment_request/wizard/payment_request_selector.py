# ttb_payment_request/wizard/payment_request_selector.py
from odoo import models, fields

class PaymentRequestSelector(models.TransientModel):
    _name = 'ttb.payment.request.selector'
    _description = 'Wizard Chọn Loại Đề Nghị Thanh Toán'

    # Trường này để lưu ID của đơn hàng gốc
    purchase_order_id = fields.Many2one('purchase.order', readonly=True)

    def action_do_partial_payment(self):
        """Hàm được gọi bởi button 'Thanh toán tạm ứng' trên wizard."""
        return self.purchase_order_id.action_partial_payment()

    def action_do_remain_payment(self):
        """Hàm được gọi bởi button 'Thanh toán tất toán' trên wizard."""
        return self.purchase_order_id.action_remain_payment()
