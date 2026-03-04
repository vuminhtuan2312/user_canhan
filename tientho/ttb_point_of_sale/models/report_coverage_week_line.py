from odoo import models, fields

class ReportCoverageWeekLine(models.TransientModel):
    _name = 'report.coverage.week.line'
    _description = 'Chi tiết sản phẩm độ phủ theo tuần'

    coverage_id = fields.Many2one(comodel_name='report.coverage.week', string="Báo cáo cơ sở", ondelete='cascade')

    mch1 = fields.Char(string="MCH1")
    mch2 = fields.Char(string="MCH2")
    mch3 = fields.Char(string="MCH3")
    mch4 = fields.Char(string="MCH4")
    mch5 = fields.Char(string="MCH5")

    product_id = fields.Many2one(comodel_name='product.product', string="Sản phẩm")

    sales_week= fields.Float('Doanh số theo tuần')
    sales_same_week_month = fields.Float('Doanh số cùng kỳ của tuần trước')
    sales_same_week_year = fields.Float('Doanh số cùng kỳ của năm trước')

    growth_week_month = fields.Float('Tăng trưởng cùng kỳ của tuần trước')
    growth_week_year = fields.Float('Tăng trưởng cùng kỳ của năm trước')

    stock_qty = fields.Float(string="SL tồn")
    stock_value = fields.Float(string="Giá trị tồn")

    avg_day = fields.Float(string="Số lượng bán TB")
    avg_stock_days = fields.Float(string="Ngày tồn kho")

    min_qty = fields.Float(string="Tồn kho tối thiểu")
    covered = fields.Selection([('yes', 'Có'), ('no', 'Không')], string="Đạt phủ")
