from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class AdvanceRequest(models.Model):
    _inherit = 'advance.request'

    # Các trường Binary mới
    supplier_delivery_note = fields.Binary(string='Phiếu giao hàng NCC')
    warehouse_receipt = fields.Binary(string='Phiếu nhập kho')
    handover_record = fields.Binary(string='Biên bản bàn giao')
    acceptance_record = fields.Binary(string='Biên bản nghiệm thu')
    red_invoice = fields.Many2many(string='Hoá đơn đỏ', comodel_name='ttb.nimbox.invoice', copy=False, tracking=True)