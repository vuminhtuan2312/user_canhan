from odoo import *


class ResCompany(models.Model):
    _inherit = 'res.company'

    po_lock_from_date_approve = fields.Integer(string='Từ ngày xác nhận', default=0)
    po_lock_from_date_receipt = fields.Integer(string='Từ ngày nhập kho đầu tiên', default=0)
    po_lock = fields.Selection(compute='_compute_ttb_po_lock', store=False, readonly=True)
    shipping_warehouse_id = fields.Many2one('stock.location', 'Kho đi đường nhập khẩu',)
    import_warehouse_id = fields.Many2one('stock.warehouse', 'Kho nhập khẩu',)


    @api.depends('name')
    def _compute_ttb_po_lock(self):
        self.po_lock = 'edit'
