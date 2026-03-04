from odoo import api, fields, models

class KvcInventoryConfig(models.Model):
    _name = 'kvc.inventory.config'
    _description = 'Cấu hình kiểm kê KVC'

    branch_id = fields.Many2one('ttb.branch', string='Cơ sở')
    product_line_ids = fields.One2many('kvc.inventory.product', inverse_name='config_id', string='Sản phẩm')

class KvcInventoryProduct(models.Model):
    _name = 'kvc.inventory.product'
    _description = 'danh sách sản phẩm kiểm kê'

    config_id = fields.Many2one('kvc.inventory.config', string='Cấu hình')
    product_sector = fields.Char(string='Nhóm hàng')
    product_code = fields.Char(string='Mã hàng')
    product_code_1 = fields.Char(string='Mã hàng 1')
    barcode = fields.Char(string='Mã vạch')
    barcode_k = fields.Char(string='Mã vạch k')
    product_name = fields.Many2one(string='Tên hàng', comodel_name='product.product')
    uom = fields.Char(string='Đơn vị tính')
