from odoo import *


class StockMove(models.Model):
    _inherit = 'stock.move'

    ttb_product_string = fields.Char(string='Mã sản phẩm',compute='_compute_ttb_product_string')

    @api.depends('product_id')
    def _compute_ttb_product_string(self):
        fs = ['ttb_product_code','ttb_barcode_k','ttb_barcode_vendor','ttb_default_code']
        for rec in self:
            str_arr = [rec[f] for f in fs if rec[f]]
            rec.ttb_product_string = ' | '.join(str_arr) if str_arr else ''

    ttb_product_code = fields.Char(string='Mã vạch', related='product_id.barcode')
    ttb_barcode_k = fields.Char(string='Mã vạch khác', related='product_id.barcode_k')
    ttb_barcode_vendor = fields.Char(string='Mã hàng NCC', related='product_id.barcode_vendor')
    ttb_default_code = fields.Char(string='Mã nội bộ', related='product_id.default_code')
    ttb_price_unit = fields.Float(string='Đơn giá')