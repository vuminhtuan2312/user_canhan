from odoo import *


class PurchasePriceLine(models.Model):
    _name = 'ttb.purchase.price.line'
    _description = 'Chi tiết đề nghị duyệt giá'

    price_id = fields.Many2one(string='Đề nghị duyệt giá', comodel_name='ttb.purchase.price', required=True, ondelete='cascade')
    default_code = fields.Char(string='Mã nội bộ', related='product_id.default_code')
    barcode = fields.Char(string='Mã barcode', related='product_id.barcode')
    product_id = fields.Many2one(string='Sản phẩm', comodel_name='product.product', required=True)
    packaging_id = fields.Many2one(string='Đơn vị tính', comodel_name='product.packaging', domain="[('product_id','=',product_id)]")

    @api.onchange('product_id')
    def _onchange_product_id(self):
        self.packaging_id = False

    old_price = fields.Monetary(string='Giá cũ', compute='_compute_old_price', store=True)
    old_discount = fields.Float(string='Chiết khấu cũ (%)', compute='_compute_old_price', store=True)

    @api.depends('price_id.partner_id', 'product_id', 'currency_id', 'packaging_id')
    def _compute_old_price(self):
        for rec in self:
            if not rec.price_id.partner_id or not rec.product_id:
                rec.old_price = 0
                rec.old_discount = 0
                continue
            currency_id = rec.currency_id or self.env.company.currency_id
            sellers = rec.product_id._get_filtered_sellers_no_date(rec.price_id.partner_id, None)
            chosen_seller = self.env['product.supplierinfo']
            if sellers and sellers.filtered(lambda x: x.date_start):
                chosen_seller = sellers.filtered(lambda x: x.date_start).sorted(lambda s: s.date_start, reverse=True)[0]
            elif sellers:
                chosen_seller = sellers.filtered(lambda x: not x.date_start).sorted(lambda s: s.create_date, reverse=True)[0]
            old_discount = chosen_seller.discount
            old_price = chosen_seller.currency_id._convert(from_amount=chosen_seller.price,
                                                           to_currency=currency_id,
                                                           company=rec.price_id.company_id,
                                                           date=fields.Date.today()) if sellers else 0
            if rec.packaging_id:
                old_price = old_price * rec.packaging_id.qty
            rec.old_price = old_price
            rec.old_discount = old_discount

    price = fields.Monetary(string='Giá mới', store=True)
    discount = fields.Float(string='Chiết khấu mới (%)', default=0)
    change_rate = fields.Float(string='% thay đổi', compute='_compute_change_rate', store=True)

    @api.depends('old_price', 'price', 'discount', 'old_discount')
    def _compute_change_rate(self):
        for rec in self:
            rec.change_rate = (rec.price * (1 - rec.discount / 100)) / (rec.old_price * (1 - rec.old_discount / 100)) - 1 if rec.old_price * (1 - rec.old_discount / 100) else False

    currency_id = fields.Many2one(string='Tiền tệ', comodel_name='res.currency', default=lambda self: self.env.company.currency_id, required=True)

    old_tax = fields.Many2many(string='Thuế cũ', comodel_name='account.tax', readonly=True, store=False)
    new_tax = fields.Many2many(string='Thuế mới', comodel_name='account.tax')

    @api.model
    def create(self, vals):
        line = super().create(vals)
        if not line.old_tax and line.product_id:
            product_template = line.product_id.product_tmpl_id
            line.old_tax = [(6, 0, product_template.supplier_taxes_id.ids)]
        return line

class SupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    taxes = fields.Many2many(comodel_name='account.tax', string='Thuế', domain="[('type_tax_use', '=', 'purchase')]")

    def _sync_taxes_to_product(self):
        self.ensure_one()
        today = fields.Date.today()
        if (not self.date_start or self.date_start <= today) and (not self.date_end or self.date_end >= today):
            if self.product_tmpl_id:
                self.product_tmpl_id.sudo().supplier_taxes_id = [(6, 0, self.taxes.ids)]
            elif self.product_id:
                self.product_id.sudo().supplier_taxes_id = [(6, 0, self.taxes.ids)]

    @api.model_create_multi
    def create(self, vals_list):
        records = super(SupplierInfo, self).create(vals_list)
        for record in records:
            if 'taxes' in record._fields and record.taxes:
                record._sync_taxes_to_product()
        return records

    def write(self, vals):
        res = super(SupplierInfo, self).write(vals)
        if 'taxes' in vals or 'date_start' in vals or 'date_end' in vals:
            for record in self:
                record._sync_taxes_to_product()
        return res

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    supplier_taxes_id = fields.Many2many(
        'account.tax',
        string="Supplier Taxes",
        help="Taxes used when buying the product.",
        tracking=True,
    )