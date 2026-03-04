from odoo import *


class PurchaseApprovalLine(models.Model):
    _name = 'ttb.purchase.approval.line'
    _description = 'Chi tiết tờ trình duyệt giá'

    approval_id = fields.Many2one(string='Tờ trình duyệt giá', comodel_name='ttb.purchase.approval', required=True, ondelete='cascade')
    product_code = fields.Char(string='Mã sản phẩm', compute='_compute_product_code', store=True, readonly=False)

    @api.depends('product_id')
    def _compute_product_code(self):
        for rec in self:
            rec.product_code = rec.product_id.barcode or rec.product_id.default_code

    product_id = fields.Many2one(string='Sản phẩm', comodel_name='product.product')
    product_name = fields.Char(string='Tên sản phẩm')
    categ_id = fields.Many2one(string='MCH 5', comodel_name='product.category', compute='_compute_based_on_product', store=True, readonly=False)
    uom_id = fields.Many2one(string='Đơn vị tính', comodel_name='uom.uom', compute='_compute_based_on_product', store=True, readonly=False)

    @api.depends('product_id')
    def _compute_based_on_product(self):
        for rec in self:
            rec.categ_id = rec.product_id.categ_id
            rec.uom_id = rec.product_id.uom_id

    quantity = fields.Float(string='Số lượng', default=0, readonly=True)
    price_unit = fields.Monetary(string='Đơn giá', default=0)
    discount = fields.Float(string='Chiết khấu', default=0)
    tax_ids = fields.Many2many(string='Thuế', comodel_name='account.tax')
    price_tax = fields.Monetary(string='Tiền thuế', compute='_compute_amount', aggregator=None, store=True)
    price_subtotal = fields.Monetary(string='Thành tiền không thuế', compute='_compute_amount', store=True)
    price_total = fields.Monetary(string='Thành tiền', compute='_compute_amount', store=True)
    currency_id = fields.Many2one(string='Tiền tệ', related='approval_id.currency_id')
    company_id = fields.Many2one(string='Công ty', related='approval_id.company_id')
    prline_id = fields.Many2one(string='Chi tiết yêu cầu mua hàng', comodel_name='ttb.purchase.request.line')

    def _prepare_base_line_for_taxes_computation(self):
        self.ensure_one()
        return self.env['account.tax']._prepare_base_line_for_taxes_computation(
            self,
            tax_ids=self.tax_ids,
            quantity=self.quantity,
            partner_id=self.approval_id.partner_id,
            currency_id=self.approval_id.currency_id or self.approval_id.company_id.currency_id,
            rate=self.approval_id.currency_rate,
        )

    @api.depends('quantity', 'price_unit', 'tax_ids', 'discount')
    def _compute_amount(self):
        for line in self:
            base_line = line._prepare_base_line_for_taxes_computation()
            self.env['account.tax']._add_tax_details_in_base_line(base_line, line.company_id)
            line.price_subtotal = base_line.get('tax_details', {}).get('total_excluded_currency', 0)
            line.price_total = base_line.get('tax_details', {}).get('total_included_currency', 0)
            line.price_tax = line.price_total - line.price_subtotal
