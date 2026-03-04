from odoo import models, fields

class ReportCoverageMonthLine(models.TransientModel):
    _name = 'report.coverage.month.line'
    _description = 'Chi tiết sản phẩm độ phủ'

    coverage_id = fields.Many2one(comodel_name='report.coverage.month', string="Báo cáo cơ sở", ondelete='cascade')

    mch1 = fields.Char(string="MCH1")
    mch2 = fields.Char(string="MCH2")
    mch3 = fields.Char(string="MCH3")
    mch4 = fields.Char(string="MCH4")
    mch5 = fields.Char(string="MCH5")

    product_id = fields.Many2one(comodel_name='product.product', string="Sản phẩm")

    sales_month = fields.Float(string="Doanh số theo tháng")
    sales_same_month = fields.Float(string="Doanh số cùng kỳ của tháng trước")
    sales_same_year = fields.Float(string="Doanh số cùng kỳ của năm trước")

    growth_month = fields.Float(string="Tăng trưởng cùng kỳ của tháng trước")
    growth_year = fields.Float(string="Tăng trưởng cùng kỳ của năm trước")

    stock_qty = fields.Float(string="SL tồn")
    stock_value = fields.Float(string="Giá trị tồn")

    avg_day = fields.Float(string="Số lượng bán TB")
    avg_stock_days = fields.Float(string="Ngày tồn kho")

    min_qty = fields.Float(string="Tồn kho tối thiểu")
    covered = fields.Selection([('yes', 'Có'), ('no', 'Không')], string="Đạt phủ")
