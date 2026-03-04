from odoo import *
import math
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, get_lang
from odoo.tools.float_utils import float_compare, float_round
from odoo.exceptions import UserError, ValidationError

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    ttb_duplicated_ok = fields.Boolean(string='Trùng', compute='_compute_ttb_duplicated_ok')
    ttb_branch_id = fields.Many2one(comodel_name='ttb.branch', related='order_id.ttb_branch_id',store=True, string="Cơ sở")
    @api.depends('order_id.order_line', 'product_id')
    def _compute_ttb_duplicated_ok(self):
        for rec in self:
            ttb_duplicated_ok = False
            if not rec.product_id:
                rec.ttb_duplicated_ok = ttb_duplicated_ok
                continue
            if len(rec.order_id.order_line.filtered(lambda x: x.product_id == rec.product_id)) > 1:
                ttb_duplicated_ok = True
            rec.ttb_duplicated_ok = ttb_duplicated_ok

    ttb_editable = fields.Boolean(compute='_compute_ttb_editable', store=False)

    @api.depends('state', 'product_id.product_tmpl_id.name', 'is_downpayment')
    def _compute_ttb_editable(self):
        for line in self:
            name = line.product_id.product_tmpl_id.name if line.product_id and line.product_id.product_tmpl_id else ''
            if (line.state == 'purchase' and name == 'Chưa rõ sản phẩm' and not line.is_downpayment):
                line.ttb_editable = True
            else:
                line.ttb_editable = False
    ttb_discount_amount = fields.Float(string='CK tiền', compute='_compute_ttb_discount_amount', inverse='_inverse_ttb_discount_amount', store=True, readonly=False)
    discount_type = fields.Selection(selection=[('percent', 'Phần trăm'), ('money', 'Tiền')], string='Loại chiết khấu')

    @api.depends('discount', 'price_unit')
    def _compute_ttb_discount_amount(self):
        for rec in self:
            if rec.discount_type == 'percent':
                rec.ttb_discount_amount = rec.discount * rec.price_unit / 100

    @api.onchange('ttb_discount_amount')
    def _inverse_ttb_discount_amount(self):
        for rec in self:
            rec.discount = rec.ttb_discount_amount / rec.price_unit * 100 if rec.price_unit else 0

    # @api.constrains('product_id', 'order_id')
    # def constrains_duplicated_product(self):
    #     for order in self.mapped('order_id'):
    #         if any(self.search_count([('order_id', '=', order.id), ('product_id', '=', product.id)]) > 1 for product in self.filtered(lambda x: x.product_id and x.order_id.id == order.id).mapped('product_id')):
    #             raise exceptions.ValidationError('Không thể trùng sản phẩm trong 1 đơn mua hàng')

    def _compute_tax_id(self):
        for line in self:
            if line.order_id.ttb_tax_type == 'no_tax':
                line.taxes_id = False
                continue
            super(PurchaseOrderLine, line)._compute_tax_id()

    ttb_sale_price = fields.Float(string='Giá bán', compute='_compute_ttb_sale_price', store=True)

    # @api.depends('product_id', 'order_id.currency_id')
    @api.depends('product_id')
    def _compute_ttb_sale_price(self):
        for rec in self:
            if not rec.product_id:
                rec.ttb_sale_price = 0
                continue
            # rec.ttb_sale_price = rec.company_id.currency_id._convert(rec.product_id.lst_price, rec.order_id.currency_id, date=rec.order_id.date_order)
            rec.ttb_sale_price = rec.product_id.lst_price

    ttb_approval_line_id = fields.Many2one(string='Chi tiết tờ trình duyệt giá', comodel_name='ttb.purchase.approval.line', readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('order_id') and self._context.get('default_order_id'):
                vals['order_id'] = self._context.get('default_order_id')

        # Lưu lại giá trị PO nhập
        manual_vals = []
        for vals in vals_list:
            manual_vals.append({
                'price_unit': vals.get('price_unit'),
                'discount': vals.get('discount')
            })
        
        records = super().create(vals_list)
        for rec, manual in zip(records, manual_vals):
            update = {}
            if manual.get('price_unit') is not None:
                update['price_unit'] = manual['price_unit']
            if manual.get('discount') is not None:
                update['discount'] = manual['discount']
            elif rec.product_id and rec.order_id and rec.order_id.partner_id:
                seller = rec.product_id._select_seller(
                    partner_id=rec.order_id.partner_id,
                    quantity=rec.product_qty,
                    date=rec.order_id.date_order and rec.order_id.date_order.date() or fields.Date.context_today(rec),
                    uom_id=rec.product_uom,
                )
                if seller and seller.discount:
                    update['discount'] = seller.discount
                else:
                    update['discount'] = 0.0

            if update:
                rec.write(update)

        return records

    ttb_stock_qty = fields.Float(string='Tồn kho', compute='_compute_ttb_sale_stock_qty', store=True)
    ttb_sale_30_qty = fields.Float(string='SL bán 30 ngày', compute='_compute_ttb_sale_stock_qty', store=True)
    ttb_sale_90_qty = fields.Float(string='SL bán 90 ngày', compute='_compute_ttb_sale_stock_qty', store=True)

    @api.depends('product_id', 'order_id.ttb_branch_id', 'order_id.ttb_type')
    def _compute_ttb_sale_stock_qty(self):
        if not self.mapped("product_id") or not self.order_id.mapped("ttb_type") or not self.order_id.mapped("ttb_branch_id"):
            self.ttb_stock_qty = 0
            self.ttb_sale_30_qty = 0
            self.ttb_sale_90_qty = 0
            return
        stock_query = f'''
            select sw.ttb_branch_id,
                sq.product_id,
                sw.ttb_type,
                sum(sq.quantity) as quantity 
            from 
            stock_quant sq
                left join stock_location sl on sl.id = sq.location_id
                left join stock_warehouse sw on sw.id = sl.warehouse_id
            where sl.usage = 'internal' 
                AND {"sq.product_id in " + str(tuple(self.mapped("product_id").ids + [0])) if self.mapped("product_id") else "0 = 1"}
                AND {"sw.ttb_type in " + str(tuple(self.order_id.mapped("ttb_type") + ['00'])) if self.order_id.mapped("ttb_type") else "0 = 1"}
                AND {"sw.ttb_branch_id in " + str(tuple(self.order_id.mapped("ttb_branch_id").ids + [0])) if self.order_id.mapped("ttb_branch_id") else "0 = 1"}
            group by sw.ttb_branch_id,sq.product_id,sw.ttb_type
        '''
        self._cr.execute(stock_query)
        stock_results = self._cr.dictfetchall()
        calculated = self.env[self._name]
        for result in stock_results:
            records = self.filtered(lambda x: x.product_id.id == result.get('product_id')
                                              and x.order_id.ttb_type == result.get('ttb_type')
                                              and x.order_id.ttb_branch_id.id == result.get('ttb_branch_id')
                                    )
            records.ttb_stock_qty = result.get('quantity')
            calculated |= records
        (self - calculated).ttb_stock_qty = 0
        sale_query = f'''
            select sw.ttb_branch_id,
                pol.product_id,
                sw.ttb_type,
                SUM(CASE WHEN timezone('{self.env.user.tz or "Asia/Ho_Chi_Minh"}',po.date_order)::date >= timezone('{self.env.user.tz or "Asia/Ho_Chi_Minh"}',now()  - interval '30 day')::date and po.date_order < now() THEN pol.qty ELSE 0 END) as sale_30_qty, 
                SUM(CASE WHEN timezone('{self.env.user.tz or "Asia/Ho_Chi_Minh"}',po.date_order)::date >= timezone('{self.env.user.tz or "Asia/Ho_Chi_Minh"}',now()  - interval '90 day')::date and po.date_order < now() THEN pol.qty ELSE 0 END) as sale_90_qty
            from 
                pos_order_line pol
                left join pos_order po on po.id = pol.order_id
                left join pos_session ps on ps.id = po.session_id
                left join pos_config pc on pc.id = ps.config_id
                left join stock_picking_type spt on spt.id = pc.picking_type_id
                left join stock_warehouse sw on sw.id = spt.warehouse_id
            where po.state not in ('draft','cancel')
                AND {"pol.product_id in " + str(tuple(self.mapped("product_id").ids + [0])) if self.mapped("product_id") else "0 = 1"}
                AND {"sw.ttb_type in " + str(tuple(self.order_id.mapped("ttb_type") + ['00'])) if self.order_id.mapped("ttb_type") else "0 = 1"}
                AND {"sw.ttb_branch_id in " + str(tuple(self.order_id.mapped("ttb_branch_id").ids + [0])) if self.order_id.mapped("ttb_branch_id") else "0 = 1"}
            group by sw.ttb_branch_id,pol.product_id,sw.ttb_type
        '''
        self._cr.execute(sale_query)
        sale_results = self._cr.dictfetchall()
        calculated = self.env[self._name]
        for result in sale_results:
            records = self.filtered(lambda x: x.product_id.id == result.get('product_id')
                                              and x.order_id.ttb_type == result.get('ttb_type')
                                              and x.order_id.ttb_branch_id.id == result.get('ttb_branch_id')
                                    )
            records.ttb_sale_30_qty = result.get('sale_30_qty')
            records.ttb_sale_90_qty = result.get('sale_90_qty')
            calculated |= records
        (self - calculated).ttb_sale_30_qty = 0
        (self - calculated).ttb_sale_90_qty = 0

    ttb_sale_days = fields.Float(string='Số ngày bán dự kiến', compute='_compute_ttb_sale_days', store=True)

    @api.depends('ttb_sale_30_qty', 'product_qty', 'ttb_stock_qty')
    def _compute_ttb_sale_days(self):
        self.filtered(lambda x: not x.ttb_sale_30_qty).ttb_sale_days = 0
        for rec in self.filtered(lambda x: x.ttb_sale_30_qty):
            rec.ttb_sale_days = (rec.ttb_stock_qty + rec.product_qty) / rec.ttb_sale_30_qty * 30

    ttb_product_code = fields.Char(string='Mã sản phẩm', compute='_compute_ttb_product_code')

    @api.depends('product_id')
    def _compute_ttb_product_code(self):
        for rec in self:
            rec.ttb_product_code = rec.product_id.barcode or rec.product_id.default_code

    ttb_request_line_id = fields.Many2one(string='Chi tiết yêu cầu', comodel_name='ttb.purchase.request.line', copy=False, readonly=True)
    ttb_batch_line_id = fields.Many2one(string='Chi tiết tổng hợp', comodel_name='ttb.purchase.batch.line', copy=False, readonly=True)

    def _update_move_date_deadline(self, new_date):
        self = self.sudo()
        return super(PurchaseOrderLine, self)._update_move_date_deadline(new_date)

    def _create_or_update_picking(self):
        self = self.sudo()
        return super(PurchaseOrderLine, self)._create_or_update_picking()

    def _create_stock_moves(self, picking):
        self = self.sudo()
        return super(PurchaseOrderLine, self)._create_stock_moves(picking)

    price_unit_cn = fields.Float(string='Đơn giá(tệ)')
    purchase_price = fields.Float(string='Đơn giá(VNĐ)', compute='_compute_price',
                                 store=True, readonly=False)
    selling_price = fields.Float(string='Giá bán(VNĐ)', compute='_compute_selling_price',
                                 store=True, readonly=False)
    cbm = fields.Float(string='CBM', related='ttb_request_line_id.cbm')
    weight = fields.Float('Kg', related='ttb_request_line_id.weight')
    product_per_case = fields.Integer('Số sản phẩm/kiện', related='ttb_request_line_id.product_per_case')
    profit_margin = fields.Float(string='Tỷ suất lợi nhuận', compute='compute_profit_margin', readonly=False, store=True)
    product_image = fields.Binary('Hình ảnh sản phẩm', related='ttb_request_line_id.product_image')
    product_link = fields.Char('Link sản phẩm', related='ttb_request_line_id.product_link')

    def button_open_link_prd(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": self.product_link,
            "target": "new",
        }

    @api.depends('order_id.profit_margin')
    def compute_profit_margin(self):
        for rec in self:
            rec.profit_margin = rec.order_id.profit_margin if rec.order_id.profit_margin else 2.0

    @api.depends('order_id.exchange_rate', 'price_unit_cn')
    def _compute_price(self):
        for rec in self:
            if rec.order_id.ttb_type == 'imported_goods':
                rec.purchase_price = rec.price_unit_cn * rec.order_id.exchange_rate if rec.price_unit_cn and rec.order_id.exchange_rate else 0

    @api.depends('product_qty', 'product_uom', 'company_id', 'order_id.partner_id', 'cbm', 'order_id.cost_other_total', 'order_id.request_type',
                 'order_id.cbm_total', 'purchase_price', 'product_per_case','order_id.cost_inland_china', 'order_id.cost_international_shipping')
    def _compute_price_unit_and_date_planned_and_name(self):
        for line in self:
            if line.order_id.ttb_type != 'imported_goods':
                if not line.product_id or line.invoice_lines or not line.company_id:
                    continue
                params = line._get_select_sellers_params()
                seller = line.product_id._select_seller(
                    partner_id=line.partner_id,
                    quantity=line.product_qty,
                    date=line.order_id.date_order and line.order_id.date_order.date() or fields.Date.context_today(line),
                    uom_id=line.product_uom,
                    params=params)

                if seller or not line.date_planned:
                    line.date_planned = line._get_date_planned(seller).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

                # If not seller, use the standard price. It needs a proper currency conversion.
                if not seller:
                    line.discount = 0
                    unavailable_seller = line.product_id.seller_ids.filtered(
                        lambda s: s.partner_id == line.order_id.partner_id)
                    if not unavailable_seller and line.price_unit and line.product_uom == line._origin.product_uom:
                        # Avoid to modify the price unit if there is no price list for this partner and
                        # the line has already one to avoid to override unit price set manually.
                        continue
                    po_line_uom = line.product_uom or line.product_id.uom_po_id
                    price_unit = line.env['account.tax']._fix_tax_included_price_company(
                        line.product_id.uom_id._compute_price(line.product_id.standard_price, po_line_uom),
                        line.product_id.supplier_taxes_id,
                        line.taxes_id,
                        line.company_id,
                    )
                    price_unit = line.product_id.cost_currency_id._convert(
                        price_unit,
                        line.currency_id,
                        line.company_id,
                        line.date_order or fields.Date.context_today(line),
                        False
                    )
                    line.price_unit = float_round(price_unit, precision_digits=max(line.currency_id.decimal_places,
                                                                                   self.env[
                                                                                       'decimal.precision'].precision_get(
                                                                                       'Product Price')))

                elif seller:
                    price_unit = line.env['account.tax']._fix_tax_included_price_company(seller.price,
                                                                                         line.product_id.supplier_taxes_id,
                                                                                         line.taxes_id,
                                                                                         line.company_id) if seller else 0.0
                    price_unit = seller.currency_id._convert(price_unit, line.currency_id, line.company_id,
                                                             line.date_order or fields.Date.context_today(line), False)
                    price_unit = float_round(price_unit, precision_digits=max(line.currency_id.decimal_places,
                                                                              self.env['decimal.precision'].precision_get(
                                                                                  'Product Price')))
                    line.price_unit = seller.product_uom._compute_price(price_unit, line.product_uom)
                    line.discount = seller.discount or 0.0

                # record product names to avoid resetting custom descriptions
                default_names = []
                vendors = line.product_id._prepare_sellers(params=params)
                product_ctx = {'seller_id': None, 'partner_id': None, 'lang': get_lang(line.env, line.partner_id.lang).code}
                default_names.append(line._get_product_purchase_description(line.product_id.with_context(product_ctx)))
                for vendor in vendors:
                    product_ctx = {'seller_id': vendor.id, 'lang': get_lang(line.env, line.partner_id.lang).code}
                    default_names.append(line._get_product_purchase_description(line.product_id.with_context(product_ctx)))
                if not line.name or line.name in default_names:
                    product_ctx = {'seller_id': seller.id, 'lang': get_lang(line.env, line.partner_id.lang).code}
                    line.name = line._get_product_purchase_description(line.product_id.with_context(product_ctx))
            else:
                othere_cost = line.order_id.cost_other_total / line.order_id.ttb_quantity_total if line.order_id.ttb_quantity_total else 0
                if line.order_id.request_type == True: #Hàng đồ chơi/văn phòng phẩm
                    if line.order_id.cbm_total > 0 and line.product_per_case > 0:
                        shipping_cost = (line.cbm / line.order_id.cbm_total / line.product_per_case) * (line.order_id.cost_inland_china + line.order_id.cost_international_shipping)
                        price_unit = line.purchase_price + shipping_cost + othere_cost
                        line.price_unit = price_unit
                else:  # Hàng quà tặng
                    price_amount_cn_total = line.order_id.price_amount_cn if line.order_id.price_amount_cn else self._context.get(
                        'amount_cn', 0)
                    if price_amount_cn_total > 0:
                        shipping_cost = (line.price_unit_cn / price_amount_cn_total) * line.order_id.cost_shipping_total
                        price_unit = line.purchase_price + shipping_cost + othere_cost
                        line.price_unit = price_unit
                    else:
                        raise UserError('Tổng giá trị hàng hóa (tệ) phải lớn hơn 0!')

    @api.depends('price_unit','profit_margin')
    def _compute_selling_price(self):
        for rec in self:
            rec.selling_price = math.ceil(rec.price_unit * rec.profit_margin)
