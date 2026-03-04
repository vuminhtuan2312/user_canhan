from odoo import fields, models, api

class StockTransferRequestLine(models.Model):
    _name = 'stock.transfer.request.line'
    _description = 'Chi tiết điều chuyển hàng'

    request_id = fields.Many2one('stock.transfer.request',string='Đề nghị điều chuyển hàng',ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Tên sản phẩm')
    default_code = fields.Char(string='Mã sản phẩm', compute='_compute_default_code')
    uom_id = fields.Many2one(string="Đơn vị tính", comodel_name='uom.uom', related='product_id.uom_id')
    quantity = fields.Float(string='Số lượng')

    @api.depends('product_id')
    def _compute_default_code(self):
        for rec in self:
            rec.default_code = rec.product_id.barcode or rec.product_id.default_code


