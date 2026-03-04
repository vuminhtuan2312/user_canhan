from odoo import models, fields, api

class TtbReportCoverage(models.TransientModel):
    _name = 'report.coverage.week'
    _description = 'Báo cáo độ phủ theo tuần'

    branch = fields.Char('Cơ sở')
    sales_week= fields.Float('Doanh số theo tuần')
    sales_same_week_month = fields.Float('Doanh số cùng kỳ của tuần trước')
    sales_same_week_year = fields.Float('Doanh số cùng kỳ của năm trước')
    growth_week_month = fields.Float('Tăng trưởng cùng kỳ của tuần trước')
    growth_week_year = fields.Float('Tăng trưởng cùng kỳ của năm trước')
    stock_qty = fields.Float('SL tồn kho')
    avg_day = fields.Float('Số lượng bán TB')
    avg_stock_days = fields.Float(string="Ngày tồn kho TB")
    num_covered = fields.Integer(string="Số SP đạt phủ")
    num_not_covered = fields.Integer(string="Số SP không đạt phủ")
    coverage_percent = fields.Float(string="% Đạt phủ")
    total_value = fields.Float(string="Tổng giá trị hàng")
    coverage_line_ids = fields.One2many(comodel_name='report.coverage.week.line', inverse_name='coverage_id', string="Chi tiết sản phẩm")
