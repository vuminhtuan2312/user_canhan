from odoo import *


class PurchaseBatchLine(models.Model):
    _name = 'ttb.purchase.batch.line'
    _description = 'Chi tiết tổng hợp yêu cầu'

    batch_id = fields.Many2one(string='Tổng hợp yêu cầu mua hàng', comodel_name='ttb.purchase.batch', required=True, ondelete='cascade')
    default_code = fields.Char(string='Mã nội bộ', related='product_id.default_code')
    product_id = fields.Many2one(string='Sản phẩm', comodel_name='product.product')
    quantity = fields.Float(string='Số lượng', default=0, digits='Product Unit of Measure')
    uom_id = fields.Many2one(string='Đơn vị tính', comodel_name='uom.uom', compute='_compute_uom_id', store=True, readonly=False)

    @api.depends('product_id')
    def _compute_uom_id(self):
        for rec in self:
            rec.uom_id = rec.product_id.uom_id

    partner_id = fields.Many2one(string='Nhà cung cấp được chọn', comodel_name='res.partner')
    purchase_line_id_1 = fields.Many2one(string='Chi tiết mua hàng 1', comodel_name='purchase.order.line')
    vendor1 = fields.Text(string='Nhà cung cấp 1', compute='_compute_vendor1', store=True)

    @api.depends('purchase_line_id_1')
    def _compute_vendor1(self):
        for rec in self:
            if not rec.purchase_line_id_1:
                rec.vendor1 = False
                continue
            price_unit = rec.purchase_line_id_1.currency_id._convert(from_amount=rec.purchase_line_id_1.price_unit,
                                                                     to_currency=rec.batch_id.currency_id,
                                                                     company=rec.batch_id.company_id,
                                                                     date=fields.Date.today())
            rec.vendor1 = f"{rec.purchase_line_id_1.order_id.partner_id.name}\nGiá: {price_unit}{rec.batch_id.currency_id.symbol}"

    purchase_line_id_2 = fields.Many2one(string='Chi tiết mua hàng 2', comodel_name='purchase.order.line')
    vendor2 = fields.Text(string='Nhà cung cấp 2', compute='_compute_vendor2', store=True)

    @api.depends('purchase_line_id_2')
    def _compute_vendor2(self):
        for rec in self:
            if not rec.purchase_line_id_2:
                rec.vendor2 = False
                continue
            price_unit = rec.purchase_line_id_2.currency_id._convert(from_amount=rec.purchase_line_id_2.price_unit,
                                                                     to_currency=rec.batch_id.currency_id,
                                                                     company=rec.batch_id.company_id,
                                                                     date=fields.Date.today())
            rec.vendor2 = f"{rec.purchase_line_id_2.order_id.partner_id.name}\nGiá: {price_unit}{rec.batch_id.currency_id.symbol}"

    purchase_line_id_3 = fields.Many2one(string='Chi tiết mua hàng 3', comodel_name='purchase.order.line')
    vendor3 = fields.Text(string='Nhà cung cấp 3', compute='_compute_vendor3', store=True)

    @api.depends('purchase_line_id_3')
    def _compute_vendor3(self):
        for rec in self:
            if not rec.purchase_line_id_3:
                rec.vendor3 = False
                continue
            price_unit = rec.purchase_line_id_3.currency_id._convert(from_amount=rec.purchase_line_id_3.price_unit,
                                                                     to_currency=rec.batch_id.currency_id,
                                                                     company=rec.batch_id.company_id,
                                                                     date=fields.Date.today())
            rec.vendor3 = f"{rec.purchase_line_id_1.order_id.partner_id.name}\nGiá: {price_unit}{rec.batch_id.currency_id.symbol}"

    pr_line_ids = fields.One2many(string='Chi tiết đơn mua', comodel_name='ttb.purchase.request.line', inverse_name='batch_line_id')
    po_line_ids = fields.One2many(string='Chi tiết yêu cầu', comodel_name='purchase.order.line', inverse_name='ttb_batch_line_id')
