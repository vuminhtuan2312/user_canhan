from odoo import *
import re
import xml.sax.saxutils as saxutils

def clean_xml_text(text):
    # Loại bỏ tất cả các ký tự điều khiển không hợp lệ theo XML 1.0 (trừ tab, newline, carriage return)
    if isinstance(text, str):
        # escape & -> &amp;
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', text)
        return saxutils.escape(text, {'"': '&quot;', "'": '&apos;'})
    return text


def object_to_xml(data, root='object', root2=''):
    xml = f'\n<{root}>' if root else ''
    if isinstance(data, dict):
        for key, value in data.items():
            value = clean_xml_text(value)
            if isinstance(value, (list, tuple, set)):
                xml += object_to_xml(value, '', key)
                continue
            xml += object_to_xml(value, key)

    elif isinstance(data, (list, tuple, set)):
        for item in data:
            xml += object_to_xml(item, root2)

    else:
        xml += str(data)

    xml += f'</{root}>' if root else ''
    return xml


class EInvoiceService(models.Model):
    _name = 'ttb.einvoice.service'
    _description = 'Dịch vụ hóa đơn điện tử'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    errors = fields.One2many(string='Bảng mã lỗi', comodel_name='ttb.einvoice.service.error', inverse_name='service_id', copy=True)
    name = fields.Char(string='Tên dịch vụ', required=True, tracking=True)
    vendor = fields.Selection(string='Nhà cung cấp', selection=[('vnpt', 'VNPT')], required=True, default='vnpt')
    host = fields.Char(string='Host', required=True, tracking=True)
    account = fields.Char(string='Account', required=True)
    acpass = fields.Char(string='ACpass', required=True)
    username = fields.Char(string='Username', required=True)
    password = fields.Char(string='Password', required=True)
    active = fields.Boolean(string='Hoạt động', default=True)

    def get_error_by_code(self, code):
        errors = self.errors.filtered(lambda x: x.name == code).mapped('description')
        return '\n'.join(errors) if errors else ''
