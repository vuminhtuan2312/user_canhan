from odoo import fields, models, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    area = fields.Selection([
        ('kbl', 'Khu bán lẻ'),
        ('kvc', 'Khu vui chơi'),
    ], string='Khu vực')

