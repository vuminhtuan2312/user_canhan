from odoo import *


class EInvoiceServiceError(models.Model):
    _name = 'ttb.einvoice.service.error'
    _description = 'Mã lỗi Dịch vụ hóa đơn điện tử'

    service_id = fields.Many2one(string='Dịch vụ hóa đơn điện tử', comodel_name='ttb.einvoice.service', required=True, ondelete='cascade')
    name = fields.Char(string='Mã lỗi', required=True)
    description = fields.Text(string='Mô tả')
