from odoo import *


class ProductAllocationDetail(models.Model):
    _name = 'ttb.product.allocation.detail'
    _description = 'Chi tiết sản phẩm phân bổ theo cơ sở'

    @api.model
    def grid_update_cell(self, domain, measure_field_name, value):
        self.search(domain).write({measure_field_name: value})

    allocation_id = fields.Many2one(string='Sản phẩm phân bổ', related='order_id.allocation_id')
    order_id = fields.Many2one(string='Chi tiết sản phẩm phân bổ', comodel_name='ttb.product.allocation.line', required=True, ondelete='cascade')
    product_id = fields.Many2one(string='Sản phẩm', related='order_id.product_id', store=True)
    branch_id = fields.Many2one(string='Cơ sở', comodel_name='ttb.branch')
    quantity = fields.Float(string='Số lượng', default=0, digits='Product Unit of Measure')
    max_quantity = fields.Float(string='Số lượng tối đa', related='order_id.quantity')
