from odoo import models, api, fields

class ProductMasterSupplierLine(models.Model):
    _name = 'product.master.supplier.line'
    _description = 'Nhà cung cấp của SKU'

    master_id = fields.Many2one('product.master', string='Master')
    partner_id = fields.Many2one('res.partner', string='Nhà cung cấp')
    price = fields.Float(string='Giá nhập')
    time_end_import_price = fields.Date(string='Thời gian kết thúc giá nhập')
    time_start_import_price = fields.Date(string='Thời gian bắt đầu giá nhập')
