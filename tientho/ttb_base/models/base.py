import qrcode
import base64
from io import BytesIO
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class Base(models.AbstractModel):
    _inherit = 'base'
    _description = 'Base'

    def generate_qr_code(self, data):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=5,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image()
        temp = BytesIO()
        img.save(temp, format="png")
        qr_img = base64.b64encode(temp.getvalue())
        return qr_img
