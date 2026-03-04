from odoo import api, fields, models, _
from odoo.exceptions import UserError


class GenerateQRCode(models.TransientModel):
    _name = 'generate.qr.code'
    _description = 'Print các loại mã'

    name = fields.Text(string='Nguồn')
    qr_code = fields.Binary(string='QR Code')

    def text_to_qrcode(self):
        if self.name:
            self.qr_code = self.generate_qr_code(self.name)
            return {
                'effect': {
                    'type': 'rainbow_man',
                    'message': "Tạo mã thành công!",
                }
            }
