from odoo import models, fields, api

class ReportCoverageMonth(models.TransientModel):
    _name = 'report.coverage.month'
    _description = 'Báo cáo độ phủ theo tháng'

    branch = fields.Char('Cơ sở')
    sales_month = fields.Float('Doanh số tháng')
    sales_same_month = fields.Float('Doanh số cùng kỳ của tháng trước')
    sales_same_year = fields.Float('Doanh số cùng kỳ của năm trước')
    growth_month = fields.Float('Tăng trưởng cùng kỳ của tháng trước')
    growth_year = fields.Float('Tăng trưởng cùng kỳ của năm trước')
    stock_qty = fields.Float('SL tồn kho')
    avg_day = fields.Float('Số lượng bán TB')
    avg_stock_days = fields.Float(string="Ngày tồn kho TB")
    num_covered = fields.Integer(string="Số SP đạt phủ")
    num_not_covered = fields.Integer(string="Số SP không đạt phủ")
    coverage_percent = fields.Float(string="% Đạt phủ")
    total_value = fields.Float(string="Tổng giá trị hàng")
    coverage_line_ids = fields.One2many(comodel_name='report.coverage.month.line', inverse_name='coverage_id', string="Chi tiết sản phẩm")
