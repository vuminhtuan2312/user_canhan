from odoo import api, fields, models, _


class ScanBarcodeLog(models.Model):
    _name = "scan.barcode.log"
    _description = "Log quét mã vạch sản phẩm"

    barcode = fields.Char('Barcode đã quét')
    # is_found = fields.Boolean('Tìm thấy sản phẩm')
    message = fields.Text("Thông tin")

    product_id = fields.Many2one('product.product', string='Sản phẩm', index=True, compute="compute_product_id", store=True)
    res_id = fields.Integer(string='Record ID', index=True)
    model = fields.Char(string='Model', index=True, default='stock.picking')

    log_type = fields.Selection([
        ('scan', 'Quét mã'), 
        ('add', 'Tăng giảm số lượng'), 
        ('set', 'Nhập số lượng'),
        ('open', 'Quét mã mở formview'),
    ], 'Loại log')

    @api.depends('barcode')
    def compute_product_id(self):
        for rec in self:
            if rec.barcode and not rec.product_id:
                product = self.env['product.product'].search([('barcode_search', '=', rec.barcode)], limit=1)
                rec.product_id = product
