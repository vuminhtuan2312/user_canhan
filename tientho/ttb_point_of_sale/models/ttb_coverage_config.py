from odoo import models, fields

class TTBCoverageConfig(models.Model):
    _name = 'ttb.coverage.config'
    _description = 'Cấu hình tồn tối thiểu theo cơ sở'

    product_id = fields.Many2one('product.product', string="Sản phẩm", required=True)
    branch_id = fields.Many2one('ttb.branch', string="Cơ sở", readonly=1)
    min_qty = fields.Float(string="Số lượng tối thiểu", required=True)
