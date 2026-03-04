from odoo import api, models, fields

class TtbVoucherWizard(models.TransientModel):
    _name = 'ttb.voucher.wizard'
    _description = 'Popup hiển thị mã ưu đãi'

    voucher_code = fields.Char(string='Mã ưu đãi',readonly=True)
    remain_qty = fields.Integer(string='Số lượng còn lại',readonly=True)
    message = fields.Text(string='Thông báo',readonly=True)

    def action_close(self):
        return {'type': 'ir.actions.act_window_close'}
