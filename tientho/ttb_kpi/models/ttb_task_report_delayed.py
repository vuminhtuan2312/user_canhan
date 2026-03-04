from odoo import models, fields, api

class TtbTaskReportDelayed(models.Model):
    _name = 'ttb.task.report.delayed'
    _description = 'Task Report Delayed Schedule'

    period = fields.Integer(string='Kỳ', required=True, help='Kỳ 1-4 trong tháng')
    creation_month = fields.Integer(string='Tháng', required=True)
    creation_year = fields.Integer(string='Năm', required=True)
    execution_date = fields.Date(string='Ngày thực thi', required=True, index=True)
    group_ids = fields.Char(string='Danh sách nhóm', required=True, help='VD: 1,2,3')
    is_weekend_task = fields.Boolean(string='Phiếu cuối tuần', default=False)
    state = fields.Selection([
        ('pending', 'Chờ xử lý'),
        ('done', 'Đã xử lý')
    ], default='pending', required=True, index=True)
