from odoo import fields, models, api

class StockConsumeRequestLine(models.Model):
    _name = 'stock.consume.request.line'
    _description = 'Chi tiết đề nghị xuất dùng'

    request_id = fields.Many2one('stock.consume.request', string='Đề nghị xuất dùng', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Sản phẩm')
    product_code = fields.Char(string='Mã sản phẩm', related='product_id.default_code', store=True, readonly=True)
    uom_id = fields.Many2one('uom.uom', string='Đơn vị tính', related='product_id.uom_id', store=True)
    quantity = fields.Float(string='Số lượng')