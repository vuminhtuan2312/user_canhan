from odoo import *


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    po_lock_from_date_approve = fields.Integer(related='company_id.po_lock_from_date_approve', string="Từ ngày xác nhận", readonly=False)
    po_lock_from_date_receipt = fields.Integer(related='company_id.po_lock_from_date_receipt', string="Từ ngày nhập kho đầu tiên", readonly=False)
