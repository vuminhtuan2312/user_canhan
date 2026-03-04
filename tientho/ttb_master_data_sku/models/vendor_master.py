from odoo import models, api, fields

class VendorMaster(models.Model):
    _name = 'vendor.master'
    _description = 'Vendor Master Data'

    vendor_code = fields.Char(string='Mã NCC', related='supplier_id.ref', store=True)
    supplier_id = fields.Many2one(string='Tên NCC', comodel_name='res.partner')
    street = fields.Char(string='Địa chỉ', related='supplier_id.street', store=True)
    phone = fields.Char(string='Điện thoại', related='supplier_id.phone', store=True)
    email = fields.Char(string='Email', related='supplier_id.email', store=True)
    return_condition = fields.Selection([
        ('pass', 'Đạt'),
        ('fail', 'Không đạt'),
    ], string='Điều kiện trả hàng')

    payment_term = fields.Selection([
        ('cash_now', 'Thanh toán ngay'),
        ('monthly_credit', 'Công nợ tháng'),
        ('consignment', 'Hàng ký gửi'),
    ], string='Điều kiện thanh toán')
    discount_condition = fields.Char(string='Điều kiện chiết khấu')

    contract_file = fields.Many2many(string='File hợp đồng', comodel_name='ir.attachment')
