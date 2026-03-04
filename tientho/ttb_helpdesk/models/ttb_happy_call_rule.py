from odoo import api, fields, models, _
from odoo.exceptions import UserError


class TTBHappyCallRule(models.Model):
    _name = 'ttb.happy.call.rule'
    _description = 'Điều kiện danh sách Happycall'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Tên')

    number_of_days = fields.Integer(string='Số ngày chưa phát sinh cuộc gọi', required=True)
    amount_total = fields.Float(string='Giá trị đơn hàng tối thiểu', required=True)
    date_from = fields.Datetime(string='Từ ngày', required=True)
    date_to = fields.Datetime(string='Đến ngày', required=True)

