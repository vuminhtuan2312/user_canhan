from odoo import *
from odoo import api, Command, fields, models, SUPERUSER_ID, _
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    classification_id = fields.Many2one('product.classification', string='Phân loại sản phẩm',
                                        help="Phân loại sản phẩm dựa trên doanh thu lũy kế để áp dụng chiến lược mua hàng phù hợp")
