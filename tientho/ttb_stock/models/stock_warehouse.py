from odoo import *


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    ttb_branch_id = fields.Many2one(string='Cơ sở', comodel_name='ttb.branch', required=True, default=lambda self: self.env['ttb.branch'].search([], limit=1))
    ttb_type = fields.Selection(string='Loại kho', selection=[
        ('sale', 'Hàng hóa'),
        ('material', 'Nguyên vật liệu'),
        ('product', 'Thành phẩm'),
        ('not_sale', 'Không kinh doanh')
    ], required=True, default='sale')
    code_augges = fields.Char(string='Mã kho Augges')
    id_augges = fields.Integer(string='ID kho Augges')
    consume_location_id = fields.Many2one('stock.location', string='Địa điểm xuất dùng', help='Địa điểm dùng cho xuất kho phục vụ sử dụng nội bộ')

    @api.constrains('code_augges')
    def _check_code_augges(self):
        for rec in self:
            check_code_augges = self.search([('id', '!=', rec.id), ('code_augges', '=', rec.code_augges), ('code_augges', '!=', False)])
            if check_code_augges:
                raise exceptions.UserError(f"Mã kho hàng hệ thống Augges đã được gắn với kho hàng {', '.join(check_code_augges.mapped('display_name'))}")
