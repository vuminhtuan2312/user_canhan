from odoo import models, fields


class TtbBranch(models.Model):
    _inherit = 'ttb.branch'
    
    invoice_serial_id = fields.Many2one('ttb.einvoice.serial', 'Ký hiệu hoá đơn')
