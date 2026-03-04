from odoo import *


class ProductAllocationSelectPartner(models.TransientModel):
    _name = 'ttb.purchase.allocation.select.partner.wizard'
    _description = 'Chọn NCC'

    partner_id = fields.Many2one(string='Nhà cung cấp', comodel_name='res.partner', required=True)

    def do(self):
        record = self.env[self.env.context.get('active_model')].browse(self.env.context.get('active_ids'))
        for rec in record:
            rec.action_po_created(self.partner_id)
        return
