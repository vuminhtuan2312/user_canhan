from odoo import models, fields, api

class CancelReason(models.Model):
    _name = 'cancel.reason'
    _description = 'Lý do hủy hàng'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Tên lý do', required=True)
    code = fields.Char(string='Mã lý do', readonly=True, default='New')
    type = fields.Selection([
        ('internal', 'Nội bộ'),
        ('customer', 'Khách hàng'),
        ('transport', 'Vận chuyển')
    ], string='Phân loại', required=True)
    description = fields.Text(string='Mô tả chi tiết', required=True)
    impact_level = fields.Selection([
        ('low', 'Thấp'),
        ('medium', 'Trung bình'),
        ('high', 'Cao')
    ], string='Mức độ ảnh hưởng', required=True, tracking=True)
    active = fields.Boolean(default=True, string='Kích hoạt')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code', 'New') == 'New':
                vals['code'] = self.env['ir.sequence'].next_by_code('cancel.reason') or 'New'
        return super().create(vals_list)