from odoo import models, fields, api

class AdvanceRequestShortageWizard(models.TransientModel):
    _name = 'advance.request.shortage.wizard'
    _description = 'Cảnh báo thiếu hàng hoàn ứng'

    advance_request_id = fields.Many2one('advance.request', string='Yêu cầu tạm ứng', required=True)
    shortage_message = fields.Text(string='Thông báo', readonly=True)

    def action_confirm(self):
        self.ensure_one()
        active_ids = self._context.get('active_ids')
        if active_ids:
            records = self.env['advance.request'].browse(active_ids)
            return records._action_start_refund_execute()
        return self.advance_request_id._action_start_refund_execute()

