from odoo import *


class ProductAllocationLine(models.Model):
    _name = 'ttb.product.allocation.line'
    _description = 'Chi tiết sản phẩm phân bổ'

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        res.mapped('allocation_id').filtered(lambda x: x.state == 'new').write({'state': 'selected'})
        return res

    allocation_id = fields.Many2one(string='Sản phẩm phân bổ', comodel_name='ttb.product.allocation', required=True, ondelete='cascade')
    product_code = fields.Char(string='Mã sản phẩm', related='product_id.default_code')
    product_id = fields.Many2one(string='Sản phẩm', comodel_name='product.product', required=True)
    quantity = fields.Float(string='Số lượng', default=0, digits='Product Unit of Measure')
    uom_id = fields.Many2one(string='Đơn vị tính', comodel_name='uom.uom', compute='_compute_uom_id', store=True, readonly=False)

    @api.depends('product_id')
    def _compute_uom_id(self):
        for rec in self:
            rec.uom_id = rec.product_id.uom_id

    order_line = fields.One2many(string='Chi tiết phân bổ', compute='_compute_order_line', comodel_name='ttb.product.allocation.detail', inverse_name='order_id', store=True)

    @api.depends('allocation_id.branch_ids', 'product_id')
    def _compute_order_line(self):
        for rec in self:
            if not rec.product_id:
                rec.order_line = [(5, 0, 0)]
                continue
            branch_ids = rec.allocation_id.branch_ids
            if not branch_ids:
                branch_ids = self.env['ttb.branch'].search([])
            rec.order_line = [(5, 0, 0)] + [(0, 0, {'branch_id': branch.id}) for branch in branch_ids]

    @api.depends('quantity', 'order_line.quantity')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f'{rec.quantity}'
