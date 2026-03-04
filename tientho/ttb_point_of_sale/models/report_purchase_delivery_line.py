from odoo import models, fields, api
class ReportPurchaseDeliveryLine(models.TransientModel):
    _name = 'report.purchase.delivery.line'
    _description = 'Chi tiết sản phẩm giao hàng'

    delivery_id = fields.Many2one('report.purchase.delivery', string='Báo cáo')
    product_id = fields.Many2one('product.product', string='Sản phẩm')
    qty_order = fields.Float('SL đặt')
    qty_received = fields.Float('SL giao')
    price_unit = fields.Float('Giá mua')
    value_received = fields.Float('Giá trị giao')
