from odoo import models, fields, api

class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    area = fields.Selection([
        ('entertainment', 'Khu vui chơi'),
        ('retail', 'Khu bán lẻ')
    ], string="Khu vực")


    branch_id = fields.Many2one(
        'ttb.branch',
        string="Cơ sở",
        help="Cơ sở áp dụng bảng giá này"
    )