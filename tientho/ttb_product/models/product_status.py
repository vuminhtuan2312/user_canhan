from odoo import *


class ProductStatus(models.Model):
    _name = 'ttb.product.status'
    _description = 'Trạng thái sản phẩm'

    product_id = fields.Many2one(string='Sản phẩm', comodel_name='product.template', required=True, ondelete='cascade')
    branch_id = fields.Many2one(string='Cơ sở', comodel_name='ttb.branch', required=True)
    state = fields.Selection(string='Trạng thái', selection=[('zz', 'ZZ- Mở toàn bộ'),
                                                             ('z1', 'Z1 – Đóng bán hàng'),
                                                             ('z0', 'Z0 – Đóng mua hàng'),
                                                             ('za', 'ZA – Đóng toàn bộ'), ],
                             required=True)
