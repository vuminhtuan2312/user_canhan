from odoo import models, fields, api

class ReportPurchaseDelivery(models.TransientModel):
    _name = 'report.purchase.delivery'
    _description = 'Báo cáo giao hàng thời vụ'

    branch = fields.Char(string='Cơ sở')
    supplier_code = fields.Char(string='Mã nhà cung cấp')
    supplier_name = fields.Char(string='Tên nhà cung cấp')
    qty_order = fields.Integer(string='Số lượng đặt')
    amount_order = fields.Float(string='Giá trị đặt')
    qty_received = fields.Integer(string='Số lượng đã giao')
    amount_received = fields.Float(string='Gía trị giao hàng')
    rate_delivery = fields.Float(string='Tỷ lệ giao')
    avg_delivery_days = fields.Float(string='Số ngày giao TB')
    line_ids = fields.One2many('report.purchase.delivery.line', inverse_name='delivery_id', string='Chi tiết sản phẩm')