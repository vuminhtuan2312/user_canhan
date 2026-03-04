from odoo import models, fields, api


class SkuByAttribute(models.Model):
    _name = 'ttb.sku.attribute'
    _description = 'SKU by attributes'

    category_id = fields.Many2one('product.category', 'MCH', required=True, ondelete='cascade')
    name_attribute = fields.Char('Kết hợp thuộc tính')
    name = fields.Char('Kết hợp giá trị thuộc tính')
    rate = fields.Float('Tỷ lệ')

    sku_number = fields.Integer('Số SKU', compute="compute_sku_number")

    value_ids = fields.Many2many(
        comodel_name='product.attribute.value',
        relation='catetory_attribute_value_combine_rel',
        string="Các giá trị thuộc tính",
        # ondelete='restrict',
        # required=True,
    )
    # number = fields.Integer('Số SKU')

    @api.depends('rate', 'category_id', 'category_id.sku_number')
    def compute_sku_number(self):
        for rec in self:
            rec.sku_number = round(rec.category_id.sku_number * rec.rate)
