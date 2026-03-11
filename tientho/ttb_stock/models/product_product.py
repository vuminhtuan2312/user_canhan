from odoo import fields, models, api
from odoo.exceptions import ValidationError


class ProductProduct(models.Model):
    _inherit = 'product.product'

    inventory_career = fields.Boolean(string="Kiểm kê hướng nghiệp")
    default_stock_qty = fields.Float(string="Tồn kho mặc định")

    @api.constrains('inventory_career', 'default_stock_qty')
    def _check_default_stock(self):
        for rec in self:
            if rec.inventory_career and rec.default_stock_qty <= 0:
                raise ValidationError("Sản phẩm kiểm kê hướng nghiệp phải có tồn kho mặc định.")