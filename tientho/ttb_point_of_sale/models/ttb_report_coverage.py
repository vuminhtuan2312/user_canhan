from odoo import models, fields, api

class TtbReportCoverage(models.TransientModel):
    _name = 'ttb.report.coverage'
    _description = 'Báo cáo độ phủ POS'

    branch = fields.Char('Cơ sở')
    sales_1m = fields.Float('Doanh số 1 tháng')
    sales_period = fields.Float('Doanh số kỳ')
    growth = fields.Float('Tăng trưởng (%)')
    stock_qty = fields.Float('SL tồn kho')
    avg_7d = fields.Float('Doanh thu TB 7 ngày')
    days_stock = fields.Float('Ngày tồn kho')
    avg_stock_days = fields.Float(string="Ngày tồn kho TB")
    num_covered = fields.Integer(string="Số SP đạt phủ")
    num_not_covered = fields.Integer(string="Số SP không đạt phủ")
    coverage_percent = fields.Float(string="% Đạt phủ")
    total_value = fields.Float(string="Tổng giá trị hàng")
    mch1 = fields.Char(string='MCH1')
    mch2 = fields.Char(string='MCH2')
    mch3 = fields.Char(string='MCH3')
    mch4 = fields.Char(string='MCH4')
    mch5 = fields.Char(string='MCH5')