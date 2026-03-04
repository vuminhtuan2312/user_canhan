from odoo import api, fields, models, _


class ScanBarcodeLog(models.Model):
    _name = "scan.barcode.log"
    _description = "Log quét mã vạch sản phẩm"

    barcode = fields.Char('Barcode đã quét')
    is_found = fields.Boolean('Tìm thấy sản phẩm')
    message = fields.Text("Thông tin")

    product_id = fields.Many2one('product.product', string='Sản phẩm', index=True)
    res_id = fields.Integer(string='Record ID', index=True)
    model = fields.Char(string='Model', index=True)
