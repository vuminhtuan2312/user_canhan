from odoo import api, fields, models

class NccReturnConfirmWizard(models.TransientModel):
    _name = 'ncc.return.confirm.wizard'
    _description = 'Xác nhận NCC trả hàng'

    return_request_id = fields.Many2one("ttb.return.request", string="Mã đề nghị")
    message = fields.Text(string="Thông tin trả hàng")

    def action_confirm(self):
        self.ensure_one()
        rec = self.return_request_id
        rec._create_ncc_return_entry()
