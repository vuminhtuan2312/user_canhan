from odoo import api, fields, models
from odoo.exceptions import ValidationError


class InventoryProductRecheck(models.Model):
    _name = 'inventory.product.recheck'
    _description = 'Inventory Product Recheck'

    branch_id = fields.Many2one('ttb.branch', string='Cơ sở')
    product_id = fields.Many2one('product.product', string='Sản phẩm')
    barcode = fields.Char(string='Mã vạch sản phẩm', related='product_id.barcode', store=True)
