from odoo import fields, models

class ProductCategoryAttributeValue(models.Model):
    _name = 'product.category.attribute.value'
    _description = 'Tỉ lệ % các Giá trị thuộc tính trong MCH 5'
    _order = 'category_id, attribute_id'

    category_id = fields.Many2one('product.category', 'MCH', required=True, ondelete='cascade')
    attribute_id = fields.Many2one('product.attribute', 'Thuộc tính', required=True, ondelete='cascade')
    value_id = fields.Many2one('product.attribute.value', 'Giá trị', ondelete='cascade')

    sku_rate = fields.Float('Tỷ lệ')

    # name = fields.Char('Giá trị')
    # display_type = fields.Selection(
    #     selection=[
    #         ('line_section', "Section"),
    #         # ('line_note', "Note"),
    #     ],
    #     default=False)
