from odoo import api, fields, models, Command, _
from odoo.exceptions import ValidationError
from odoo.osv import expression
from itertools import product


class ProductCategory2(models.Model):
    _name = "product.category2"
    _description = "Danh mục sản phẩm nhân bản phục vụ map MCH"
    _order = 'parent_id, name asc'

    category_level = fields.Integer('Cấp MCH', compute='_compute_category_level', store=True, recursive=True)
    name = fields.Char('Tên')
    parent_id = fields.Many2one('product.category2', 'Tên cha')

    @api.depends('parent_id', 'parent_id.category_level')
    def _compute_category_level(self):
        for rec in self:
            parent_level = rec.parent_id.category_level or 0
            rec.category_level = parent_level + 1
