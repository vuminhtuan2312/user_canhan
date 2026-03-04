from odoo import models, fields, api


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    # Thêm domain thuế bán vào trường của base
    tax_ids = fields.Many2many(domain="[('type_tax_use', '=', 'sale')]")

    # Thêm index vào trường base tăng tốc độ
    refunded_orderline_id = fields.Many2one(index=True)
    combo_parent_id = fields.Many2one(index=True)
    tax_case = fields.Selection([
        ('1', 'MCH5'),
        ('2', 'Thuế sản phẩm (Augges)'),
        ('3', 'Kế toán điền ở tab dòng không thuế'),
        ('4', 'Thuế sản phẩm (Odoo)'),
        ('5', 'Thuế cố định 8%'),
        ('6', 'Sửa tay'),
    ], 'Thứ tự thuế')

    tax_ids_amount = fields.Float('% Thuế', compute="compute_tax_ids_amount", store=True)

    @api.onchange('tax_ids')
    def onchange_tax_ids(self):
        for rec in self:
            rec.tax_case = '6'

    @api.depends('tax_ids')
    def compute_tax_ids_amount(self):
        for rec in self:
            rec.tax_ids_amount = rec.tax_ids[:1].amount if rec.tax_ids else 0.0