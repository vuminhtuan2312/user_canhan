from odoo import models, fields, api
from odoo.exceptions import UserError

class StockMove(models.Model):
    _inherit = 'stock.move'

    ttb_return_request_line_id = fields.Many2one('ttb.return.request.line', string='Dòng yêu cầu trả lại', copy=False)
    qty_picked = fields.Float(string='SL nhặt', related='ttb_return_request_line_id.qty_picked')

    return_price_unit = fields.Float(string='Đơn giá trả')
    return_price_subtotal = fields.Float(string='Thành tiền', compute='_compute_return_price_subtotal')
    confirm_vendor_price  = fields.Float(string='Giá NCC xác nhận')

    ttb_discount = fields.Float(string='Chiết khấu %', compute='_compute_discount_and_tax', compute_sudo=True)
    ttb_taxes_id = fields.Many2many(comodel_name='account.tax', string='Thuế', compute='_compute_discount_and_tax', compute_sudo=True)
    price_tax = fields.Float(string='Tiền thuế', compute='_compute_discount_and_tax', compute_sudo=True)
    ttb_discount_amount = fields.Float(string='CK tiền', compute='_compute_discount_and_tax', compute_sudo=True)
    vendor_product_name = fields.Char(string='Tên sản phẩm nhà cung cấp')

    @api.depends('quantity', 'confirm_vendor_price', 'ttb_discount_amount', 'price_tax')
    def _compute_return_price_subtotal(self):
        for rec in self:
            rec.return_price_subtotal = rec.quantity * (rec.confirm_vendor_price - rec.ttb_discount_amount) + rec.price_tax

    @api.depends('ttb_return_request_line_id', 'purchase_line_id')
    def _compute_discount_and_tax(self):
        for rec in self:
            if rec.ttb_return_request_line_id:
                rec.ttb_discount = rec.ttb_return_request_line_id.discount
                rec.ttb_taxes_id = rec.ttb_return_request_line_id.ttb_taxes_id.ids
                rec.price_tax = rec.ttb_return_request_line_id.price_tax
                rec.ttb_discount_amount = rec.ttb_return_request_line_id.ttb_discount_amount
            elif rec.purchase_line_id:
                rec.ttb_discount = rec.purchase_line_id.discount
                rec.ttb_taxes_id = rec.purchase_line_id.taxes_id.ids
                rec.price_tax = 0.0
                rec.ttb_discount_amount = 0.0
            else:
                rec.ttb_discount = 0.0
                rec.ttb_taxes_id = False
                rec.price_tax = 0.0
                rec.ttb_discount_amount = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        for lines in res:
            if lines.picking_id.pickup_status:
                vendor_product_name = self.env['product.supplierinfo'].search([('partner_id', '=', lines.ttb_return_request_line_id.request_id.supplier_id.id),
                                                                              ('product_tmpl_id', '=', lines.product_id.product_tmpl_id.id)], limit=1).product_name
                for line in lines:
                    if line.ttb_return_request_line_id.vendor_product_name:
                        line.vendor_product_name = line.ttb_return_request_line_id.vendor_product_name
                    elif vendor_product_name:
                        line.vendor_product_name = vendor_product_name
                    else:
                        line.vendor_product_name = line.product_id.name
        return res