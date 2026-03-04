from odoo import *


class PurchaseOrderAddTax(models.TransientModel):
    _name = 'purchase.order.add.tax.wizard'
    _description = 'Chọn Thuế mua hàng'

    taxes_id = fields.Many2many(string='Thuế', comodel_name='account.tax')
    tax_country_id = fields.Many2one(comodel_name='res.country')
    company_id = fields.Many2one(comodel_name='res.company')

    def do(self):
        records = self.env[self._context.get('active_model')].browse(self._context.get('active_ids'))
        records.filtered(lambda x: x.state == 'draft').order_line.write({'taxes_id': [(6, 0, self.taxes_id.ids)]})
        return
