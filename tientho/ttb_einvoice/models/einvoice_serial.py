from odoo import *


class EInvoiceSerial(models.Model):
    _name = 'ttb.einvoice.serial'
    _description = 'Ký hiệu hóa đơn điện tử'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Ký hiệu', required=True, tracking=True)
    description = fields.Char(string='Mô tả')
    service_id = fields.Many2one(string='Dịch vụ hóa đơn điện tử', comodel_name='ttb.einvoice.service', required=True, tracking=True)
    pattern = fields.Char(string='Mẫu hóa đơn', required=True, tracking=True)
    type = fields.Char(string='Loại hóa đơn', required=True, tracking=True)
    active = fields.Boolean(string='Hoạt động', default=True)

    branch_ids = fields.One2many('ttb.branch', 'invoice_serial_id', 'Cơ sở')
