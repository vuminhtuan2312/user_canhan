from odoo import fields,models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    last_price = fields.Float(string='Đơn giá gần nhất')
