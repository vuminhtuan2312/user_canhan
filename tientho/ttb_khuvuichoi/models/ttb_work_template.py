# -*- coding: utf-8 -*-
from odoo import models, fields

class TtbWorkTemplate(models.Model):
    # Đổi tên từ ttb.task.template thành ttb.work.template để tránh trùng lặp
    _name = 'ttb.work.template'
    _description = 'Mẫu công việc'
    _order = 'name'

    name = fields.Char(string='Tên công việc', required=True)
    description = fields.Html(string='Hướng dẫn thực hiện')
    expected_result = fields.Text(string='Kết quả đầu ra')
    avoid_errors = fields.Text(string='Lỗi cần tránh')
    
    duration_minutes = fields.Integer(string='Số phút thực hiện')
    frequency_minutes = fields.Integer(string='Tần suất lặp lại (phút)', help="Tần suất lặp lại trong ca")
    
    area_ids = fields.Many2many(
        comodel_name='ttb.area',
        string='Khu vực áp dụng'
    )
    
    is_active = fields.Boolean(string='Đang hoạt động', default=True)