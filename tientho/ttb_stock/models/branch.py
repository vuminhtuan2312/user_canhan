from odoo import *


class Branch(models.Model):
    _name = 'ttb.branch'
    _description = 'Cơ sở'
    _rec_names_search = ['name', 'code']

    name = fields.Char(string='Tên cơ sở', required=True)
    code = fields.Char(string='Mã cơ sở')
    active = fields.Boolean(string='Hoạt động', default=True)
    vat_warehouse_id = fields.Many2one(string='Kho HDT', comodel_name='stock.warehouse', help='Kho hoá đơn. Tăng tồn khi khớp hoá đơn đầu vào, giảm tồn khi xuất hoá đơn đầu ra.')
    snd_location_id = fields.Many2one('stock.location', 'Địa điểm tồn SND')
    branch_director = fields.Many2one('res.users', string='Giám đốc nhà sách')
    @api.ondelete(at_uninstall=False)
    def _unlink_except_linked_to_branch(self):
        models = {
            'ttb.product.status':'branch_id',
            'ttb.product.allocation':'branch_ids',
            'purchase.order':'ttb_branch_id',
            'sale.order':'ttb_branch_id',
            'res.users':'ttb_branch_id',
            'stock.warehouse':'ttb_branch_id',
            'ttb.purchase.request':'branch_id',
        }
        for key, val in models.items():
            if self.env[key].search_count([(val, 'in', self.ids)], limit=1):
                raise exceptions.UserError('“Cơ sở đã được tạo dữ liệu, vui lòng lưu trữ nếu không còn nhu cầu sử dụng')
