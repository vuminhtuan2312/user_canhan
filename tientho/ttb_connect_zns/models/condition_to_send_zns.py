from odoo import models, fields, _, api
from odoo.exceptions import ValidationError

class ConditionToSendZNS(models.Model):
    _name = 'condition.to.send.zns'
    _description = 'Điều kiện gửi ZNS'

    ttb_branch_id = fields.Many2one('ttb.branch', string='Cơ sở áp dụng', required=True)
    limit_count = fields.Integer(string='Số lượng tối đa', required=True)
    count_sent = fields.Integer(string='Số lần đã gửi', default=0, readonly=True)
    time_from = fields.Float(string='Giờ bắt đầu tạo đơn', required=True)
    time_to = fields.Float(string='Giờ kết thúc tạo đơn', required=True)
    create_by = fields.Many2one('res.users', string='Người tạo', default=lambda self: self.env.user, required=True)
    zalo_shop_config_id = fields.Many2one('zalo.shop.config', string='Cấu hình Zalo Shop')
    date_in_week = fields.Selection(
        selection=[
            ('0', 'Thứ Hai'),
            ('1', 'Thứ Ba'),
            ('2', 'Thứ Tư'),
            ('3', 'Thứ Năm'),
            ('4', 'Thứ Sáu'),
            ('5', 'Thứ Bảy'),
            ('6', 'Chủ Nhật'),
        ],
        string='Thứ trong tuần',
        required=True
    )
    campaign_id =fields.Many2one('period.campaign', string='Chiến dịch')
    template_id = fields.Many2one('zalo.template', string='Mẫu áp dụng')
