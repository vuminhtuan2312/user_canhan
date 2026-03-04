# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class GoodsDistributionConfirmWizard(models.TransientModel):
    _name = 'goods.distribution.confirm.wizard'
    _description = 'Goods Distribution Confirmation Wizard'

    ticket_id = fields.Many2one('goods.distribution.ticket', string='Phiếu chia hàng', required=True, readonly=True)
    message = fields.Html(string='Thông báo', readonly=True,
                          default=lambda self: """
                              <div style="padding: 10px;">
                                  <p style="font-size: 14px; color: #333;">
                                      Khi xác nhận <strong>Phiếu chia hàng</strong> sẽ đồng thời xác nhận <strong>Phiếu nhập kho DC</strong>.
                                  </p>
                                  <p style="font-size: 14px; color: #d9534f; margin-top: 10px;">
                                      <strong>Bạn có chắc chắn thực hiện hành động này?</strong>
                                  </p>
                              </div>
                          """)

    def action_confirm(self):
        self.ensure_one()
        if not self.ticket_id:
            raise UserError(_('Không tìm thấy phiếu chia hàng. Vui lòng kiểm tra lại!'))

        self.ticket_id.write({
            'state': 'confirmed',
            'has_picking': True,
            'user_confirm': self.env.user.id
        })

        return self.ticket_id.stock_picking_id.confirm_shipping_ticket_dc()

    def action_cancel(self):
        """
        Đóng wizard mà không thực hiện gì
        Tất cả thay đổi trước đó sẽ được rollback do đây là transient model
        """
        self.ensure_one()
        return {'type': 'ir.actions.act_window_close'}
