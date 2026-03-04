from odoo import models, fields, api

class CancelRequestLine(models.Model):
    _name = 'cancel.request.line'
    _description = 'Chi tiết đề xuất hủy'

    request_id = fields.Many2one('cancel.request', string='Đề xuất')
    product_id = fields.Many2one('product.product', string='Sản phẩm', required=True)
    barcode = fields.Char(related='product_id.barcode', string='Mã vạch', readonly=True)

    qty_picked = fields.Float(string='SL nhặt', default=0)
    qty_office_received = fields.Float(string='SL VP nhận', default=0)
    qty_cancelled = fields.Float(string='SL hủy', default=0)

    uom_id = fields.Many2one('uom.uom', string='Đơn vị', compute='_compute_uom', store=True, readonly=False)
    price_unit = fields.Float(string='Đơn giá nhập', compute='_compute_price_unit', store=True)
    subtotal = fields.Float(string='Thành tiền', compute='_compute_subtotal', store=True)

    @api.depends('product_id')
    def _compute_uom(self):
        for rec in self:
            if rec.product_id:
                # Đơn vị mua hàng
                rec.uom_id = rec.product_id.uom_po_id

    @api.depends('product_id')
    def _compute_price_unit(self):
        for rec in self:
            if not rec.product_id:
                rec.price_unit = 0
                continue

            # Lấy PO xác nhận gần nhất
            domain = [
                ('product_id', '=', rec.product_id.id),
                ('state', 'in', ['purchase', 'done'])
            ]
            last_pol = self.env['purchase.order.line'].search(domain, order='date_approve desc', limit=1)

            if last_pol and last_pol.product_qty:
                # Công thức: Tổng tiền sau thuế / Số lượng
                # Lưu ý: price_total trong PO Line là tax included
                rec.price_unit = last_pol.price_total / last_pol.product_qty
            else:
                rec.price_unit = 0

    @api.depends('price_unit', 'qty_cancelled')
    def _compute_subtotal(self):
        for rec in self:
            rec.subtotal = rec.price_unit * rec.qty_cancelled

    @api.onchange('product_id')
    def _onchange_product(self):
        if self.product_id:
            self.barcode = self.product_id.barcode
            self.uom_id = self.product_id.uom_po_id
