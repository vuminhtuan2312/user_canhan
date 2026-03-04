from odoo import api, fields, models

class ProductCategoryAttributeRel(models.Model):
    _name = 'product.category.attribute'
    _description = 'Category-Attribute Relation'

    category_id = fields.Many2one('product.category', 'MCH', required=True, ondelete='cascade')
    attribute_id = fields.Many2one('product.attribute', 'Thuộc tính', required=True, ondelete='cascade', domain=[('create_variant', '=', 'no_variant')])
    
    sku_flag = fields.Boolean(string='Kết hợp thuộc tính', default=True)

    value_ids = fields.Many2many(
        comodel_name='product.attribute.value',
        relation='product_attribute_value_product_catetory_attribute_line_rel',
        string="Các giá trị thuộc tính",
        domain="[('attribute_id', '=', attribute_id)]",
        ondelete='restrict',
        required=True,
    )

    _sql_constraints = [
        ('category_attribute_uniq', 'unique(category_id, attribute_id)',
         'Một thuộc tính chỉ có thể được gán một lần cho một danh mục.')
    ]

    @api.onchange('attribute_id')
    def _onchange_attribute_id(self):
        if self.attribute_id.create_variant == 'no_variant':
            self.value_ids = self.env['product.attribute.value'].search([
                ('attribute_id', '=', self.attribute_id.id),
            ])
        else:
            self.value_ids = self.value_ids.filtered(
                lambda pav: pav.attribute_id == self.attribute_id
            )
