from odoo import *
from odoo import api, Command, fields, models, SUPERUSER_ID, _

class PurchaseRequestLine(models.Model):
    _name = 'ttb.purchase.request.line'
    _description = 'Chi tiết yêu cầu mua hàng'
    _check_company_auto = True

    product_image = fields.Binary('Hình ảnh sản phẩm')
    product_link = fields.Char('Link sản phẩm')
    cbm = fields.Float('CBM(Khối/kiện)')
    number_of_cases = fields.Integer('Số kiện')
    product_per_case = fields.Integer('Số sản phẩm/kiện')
    weight = fields.Float('Kg')
    item = fields.Char('Mã hàng của NCC')
    price_cn = fields.Float('Đơn giá(tệ)')
    separate_prd = fields.Boolean('Sản phẩm tách riêng', default=False)
    price_total_line = fields.Float('Thành tiền(tệ)', compute='_compute_price_total')

    @api.depends('price_cn', 'demand_qty')
    def _compute_price_total(self):
        for rec in self:
            rec.price_total_line = rec.price_cn * rec.demand_qty

    def action_mapping_product(self):
        count = 0
        for rec in self:
            if rec.item:
                product = self.env['product.product'].search([('default_code', '=', rec.item)], limit=1)
                if product:
                    rec.product_id = product.id
                    count += 1
        message = _("Bạn đã khớp thành công %s trên %s sản phẩm.") % (count, len(self))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Thông báo'),
                'message': message,
                'type': 'success',
                'next': {
                    'type': 'ir.actions.act_window_close'
                },
            }
        }
    def button_open_link_prd(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": self.product_link,
            "target": "new",
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('request_id') and self._context.get('default_request_id'):
                vals['request_id'] = self._context.get('default_request_id')
        records = super().create(vals_list)
        for rec in records:
            if rec.product_id:
                rec.request_id.update_stock_system()
        return records

    def action_add_to_purchase_approval(self):
        approval = self.env['ttb.purchase.approval'].browse(self.env.context.get('active_approval_id'))
        line_ids = []
        for line in self:
            line_ids += [(0,0,{
                'product_id': line.product_id.id,
                'product_name': line.description,
                'quantity': line.demand_qty,
                'uom_id': line.uom_id.id,
                'prline_id': line.id,
            })]
        if line_ids:
            approval.write({'line_ids': [(5, 0, 0)] + line_ids})
        return

    approval_line_ids = fields.One2many(string='Chi tiết tờ trình duyệt giá', comodel_name='ttb.purchase.approval.line', readonly=True, copy=False, inverse_name='prline_id')

    stock_qty = fields.Float(string='Tồn kho', compute='_compute_sale_stock_qty', store=True)
    sale_30_qty = fields.Float(string='SL bán 30 ngày', compute='_compute_sale_stock_qty', store=True)
    sale_90_qty = fields.Float(string='SL bán 90 ngày', compute='_compute_sale_stock_qty', store=True)

    @api.depends('product_id', 'request_id.branch_id', 'request_id.type')
    def _compute_sale_stock_qty(self):
        if not self.mapped("product_id") or not self.request_id.mapped("type") or not self.request_id.mapped("branch_id"):
            self.stock_qty = 0
            self.sale_30_qty = 0
            self.sale_90_qty = 0
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
                AND {"sw.ttb_type in " + str(tuple(self.request_id.mapped("type") + ['00'])) if self.request_id.mapped("type") else "0 = 1"}
                AND {"sw.ttb_branch_id in " + str(tuple(self.request_id.mapped("branch_id").ids + [0])) if self.request_id.mapped("branch_id") else "0 = 1"}
            group by sw.ttb_branch_id,sq.product_id,sw.ttb_type
        '''
        self._cr.execute(stock_query)
        stock_results = self._cr.dictfetchall()
        calculated = self.env[self._name]
        for result in stock_results:
            records = self.filtered(lambda x: x.product_id.id == result.get('product_id')
                                              and x.request_id.type == result.get('ttb_type')
                                              and x.request_id.branch_id.id == result.get('ttb_branch_id')
                                    )
            records.stock_qty = result.get('quantity')
            calculated |= records
        (self - calculated).stock_qty = 0
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
                AND {"sw.ttb_type in " + str(tuple(self.request_id.mapped("type") + ['00'])) if self.request_id.mapped("type") else "0 = 1"}
                AND {"sw.ttb_branch_id in " + str(tuple(self.request_id.mapped("branch_id").ids + [0])) if self.request_id.mapped("branch_id") else "0 = 1"}
            group by sw.ttb_branch_id,pol.product_id,sw.ttb_type
        '''
        self._cr.execute(sale_query)
        sale_results = self._cr.dictfetchall()
        calculated = self.env[self._name]
        for result in sale_results:
            records = self.filtered(lambda x: x.product_id.id == result.get('product_id')
                                              and x.request_id.type == result.get('ttb_type')
                                              and x.request_id.branch_id.id == result.get('ttb_branch_id')
                                    )
            records.sale_30_qty = result.get('sale_30_qty')
            records.sale_90_qty = result.get('sale_90_qty')
            calculated |= records
        (self - calculated).sale_30_qty = 0
        (self - calculated).sale_90_qty = 0

    sale_days = fields.Float(string='Số ngày bán dự kiến', compute='_compute_sale_days', store=True)

    @api.depends('sale_30_qty', 'quantity', 'stock_qty')
    def _compute_sale_days(self):
        self.filtered(lambda x: not x.sale_30_qty).sale_days = 0
        for rec in self.filtered(lambda x: x.sale_30_qty):
            rec.sale_days = (rec.stock_qty + rec.quantity) / rec.sale_30_qty * 30

    def action_view_product(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "product.product",
            "views": [[False, "form"]],
            "res_id": self.product_id.id,
            "name": "Sản phẩm",
            "target": "new",
            'flags': {'mode': 'readonly'},
        }

    request_id = fields.Many2one(string='Yêu cầu mua hàng', comodel_name='ttb.purchase.request', required=True, ondelete='cascade')
    default_code = fields.Char(string='Mã sản phẩm', compute='_compute_default_code')

    @api.depends('product_id')
    def _compute_default_code(self):
        for rec in self:
            rec.default_code = rec.product_id.barcode or rec.product_id.default_code

    product_id = fields.Many2one(string='Sản phẩm', comodel_name='product.product', required=False)

    @api.depends('request_id.name', 'default_code')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f'{rec.request_id.name} {rec.default_code}'

    description = fields.Char(string='Mô tả')
    demand_qty = fields.Float(string='Số lượng', default=0, digits='Product Unit of Measure')
    uom_qty = fields.Float(string='Số lượng theo đơn vị mua', compute='_compute_uom_qty', store=True, readonly=False, digits='Product Unit of Measure')

    @api.depends('demand_qty', 'packaging_id')
    def _compute_uom_qty(self):
        for rec in self:
            rec.uom_qty = rec.packaging_id._compute_qty(rec.demand_qty) if rec.packaging_id else 0

    quantity = fields.Float(string='Số lượng duyệt', digits='Product Unit of Measure', compute='_compute_quantity', store=True, readonly=False)

    @api.depends('demand_qty')
    def _compute_quantity(self):
        for rec in self:
            rec.quantity = rec.demand_qty

    purchase_qty = fields.Float(string='Số lượng mua', compute='_compute_purchase_qty', store=True)

    @api.depends('po_line_ids.product_qty')
    def _compute_purchase_qty(self):
        for rec in self:
            rec.purchase_qty = sum(rec.po_line_ids.mapped('product_qty'))

    received_qty = fields.Float(string='Số lượng đã giao', compute='_compute_received_qty', store=True)

    @api.depends('po_line_ids.qty_received')
    def _compute_received_qty(self):
        for rec in self:
            rec.received_qty = sum(rec.po_line_ids.mapped('qty_received'))

    uom_id = fields.Many2one(string='Đơn vị tính', comodel_name='uom.uom', compute='_compute_uom_id', store=True, readonly=False)

    @api.depends('product_id')
    def _compute_uom_id(self):
        for rec in self:
            rec.uom_id = rec.product_id.uom_id

    packaging_id = fields.Many2one(string='Đơn vị tính mua hàng', comodel_name='product.packaging', domain="[('product_id','=',product_id)]")

    @api.onchange('product_id')
    def _onchange_product_id(self):
        self.packaging_id = False

    reject = fields.Boolean(string='Không duyệt', default=False, copy=False)
    partner_id = fields.Many2one(string='Nhà cung cấp', comodel_name='res.partner', compute='_compute_partner_id', store=True, readonly=False)
    user_id = fields.Many2one(string='Người phụ trách', related='product_id.categ_id.ttb_user_id')
    batch_line_id = fields.Many2one(string='Đơn tổng hợp', comodel_name='ttb.purchase.batch.line', copy=False)
    po_line_ids = fields.One2many(string='Chi tiết đơn mua hàng', comodel_name='purchase.order.line', inverse_name='ttb_request_line_id')
    company_id = fields.Many2one(related='request_id.company_id', store=True, index=True, precompute=True)
    currency_id = fields.Many2one(related='request_id.currency_id', depends=['request_id.currency_id'], store=True, precompute=True)

    @api.depends('request_id.partner_id')
    def _compute_partner_id(self):
        for rec in self:
            if rec.request_id.partner_id:
                rec.partner_id = rec.request_id.partner_id.id

    def _auto_fill_item_code(self):
        for rec in self:
            if not rec.item:
                rec.item = self.env['ir.sequence'].next_by_code('purchase.request.line.item') or 'Mới'