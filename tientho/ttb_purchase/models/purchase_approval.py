from odoo import *
import json


class PurchaseApproval(models.Model):
    _name = 'ttb.purchase.approval'
    _description = 'Tờ trình duyệt giá'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'ttb.approval.mixin']
    _order = 'date desc, id desc'

    pr_domain = fields.Binary(compute='_compute_pr_domain')

    @api.depends_context('uid')
    @api.depends('user_id')
    def _compute_pr_domain(self):
        self.pr_domain = json.dumps([('notif_user_ids', '=', self.env.user.id)] if not self.env.user.has_group('purchase.group_purchase_manager') else [('id', '!=', False)])

    product_id = fields.Many2one(related='line_ids.product_id')
    po_ids = fields.One2many(string='Đơn mua hàng', comodel_name='purchase.order', inverse_name='ttb_approval_id')
    po_count = fields.Integer(string='Số đơn mua hàng', compute='_compute_po_count')

    def action_to_po(self):
        action = self.env["ir.actions.actions"]._for_xml_id("purchase.act_res_partner_2_purchase_order")
        action['context'] = {'create': 0}
        action['domain'] = [('id', 'in', self.po_ids.ids)]
        return action

    @api.depends('po_count')
    def _compute_po_count(self):
        for rec in self:
            rec.po_count = len(rec.po_ids)

    def action_created_po(self):
        self = self.sudo()
        partner_id = self.partner_id
        if self.vendor_type == 'new':
            partner_id = self.env['res.partner'].create({'name': self.vendor_name})
        line_ids = []
        order_line = []
        for line in self.line_ids:
            product = line.product_id
            if not product and not line.product_name:
                continue
            if not product:
                product = self.env['product.product'].create({
                    'default_code': line.product_code,
                    'name': line.product_name,
                    'categ_id': (line.categ_id or self.env.ref('product.product_category_all')).id,
                    'uom_id': (line.uom_id or self.env.ref('uom.product_uom_unit')).id,
                    'uom_po_id': (line.uom_id or self.env.ref('uom.product_uom_unit')).id,
                    'ttb_product_status': 'z1',
                })
                line_ids += [(1, line.id, {'product_id': product.id})]
            order_line += [(0, 0, {
                'product_id': product.id,
                'product_qty': line.quantity,
                'ttb_approval_line_id': line.id,
                'product_uom': line.uom_id.id,
                'price_unit': line.price_unit,
                'discount': line.discount,
                'taxes_id': [(6, 0, line.tax_ids.ids)],
            })]
        picking_type_id = self.env['stock.warehouse'].search([('ttb_type', '=', self.pr_id.type), ('ttb_branch_id', '=', self.branch_id.id)], limit=1).in_type_id.id
        if not picking_type_id:
            picking_type_id = self.env['stock.warehouse'].search([('ttb_branch_id', '=', self.branch_id.id)], limit=1).in_type_id.id
        if not picking_type_id:
            picking_type_id = self.env.user.property_warehouse_id.in_type_id.id
        if not picking_type_id:
            picking_type_id = self.env['stock.warehouse'].search([], limit=1).in_type_id.id

        self.write({
            'line_ids': line_ids,
            'po_ids': [(0, 0, {
                'partner_id': partner_id.id,
                'ttb_type': 'not_sale',
                'user_id': self.user_id.id,
                'company_id': self.company_id.id,
                'currency_id': self.currency_id.id,
                'date_order': fields.Date.today(),
                'ttb_branch_id': self.branch_id.id,
                'picking_type_id': picking_type_id,
                'ttb_approval_id': self.id,
                'order_line': order_line
            })],
            'partner_id': partner_id.id,
            # 'state': 'created_po',
        })

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == 'Mới':
                vals['name'] = self.env['ir.sequence'].next_by_code('purchase.approval') or 'Mới'
        return super().create(vals_list)

    def action_product_select(self):
        if not self.pr_id:
            raise exceptions.ValidationError('Cần chọn Yêu cầu mua hàng trước khi chọn sản phẩm')
        action = self.env["ir.actions.actions"]._for_xml_id("ttb_purchase.purchase_request_line_action")
        action['domain'] = [('approval_line_ids', '=', False), ('request_id', '=', self.pr_id.id)]
        action['context'] = {'active_approval_id': self.id}
        return action

    tax_country_id = fields.Many2one(comodel_name='res.country', related='company_id.account_fiscal_country_id')
    name = fields.Char(string='Mã tờ trình', default='Mới', readonly=True, copy=False, required=True)
    date = fields.Datetime(string='Ngày đề nghị', required=True, default=lambda self: fields.Datetime.now())
    user_id = fields.Many2one(string='Người đề nghị', required=True, comodel_name='res.users', default=lambda self: self.env.user)
    pr_id = fields.Many2one(string='Yêu cầu mua hàng', comodel_name='ttb.purchase.request')
    branch_id = fields.Many2one(string='Cơ sở', related='pr_id.branch_id', store=True)
    company_id = fields.Many2one(string='Công ty', related='pr_id.company_id', store=True)
    vendor_type = fields.Selection(string='Loại nhà cung cấp', selection=[('new', 'Nhà cung cấp mới'), ('old', 'Nhà cung cấp đã có')], default='new', required=True)
    vendor_name = fields.Char(string='Tên nhà cung cấp')
    partner_id = fields.Many2one(string='Nhà cung cấp', comodel_name='res.partner')
    currency_id = fields.Many2one(string='Tiền tệ', related='pr_id.currency_id')
    amount_total = fields.Monetary(string='Tổng', store=True, readonly=True, compute='_amount_all')
    amount_subtotal = fields.Monetary(string='Tổng trước thuế', store=True, readonly=True, compute='_amount_all')
    amount_tax = fields.Monetary(string='Tổng thuế', store=True, readonly=True, compute='_amount_all')

    @api.depends('line_ids.price_subtotal', 'company_id')
    def _amount_all(self):
        AccountTax = self.env['account.tax']
        for order in self:
            order_lines = order.line_ids
            base_lines = [line._prepare_base_line_for_taxes_computation() for line in order_lines]
            AccountTax._add_tax_details_in_base_lines(base_lines, order.company_id)
            AccountTax._round_base_lines_tax_details(base_lines, order.company_id)
            tax_totals = AccountTax._get_tax_totals_summary(
                base_lines=base_lines,
                currency=order.currency_id or order.company_id.currency_id,
                company=order.company_id,
            )
            order.amount_subtotal = tax_totals['base_amount_currency']
            order.amount_tax = tax_totals['tax_amount_currency']
            order.amount_total = tax_totals['total_amount_currency']

    tax_totals = fields.Binary(string='Diễn giải thuế', compute='_compute_tax_totals', exportable=False)

    @api.depends_context('lang')
    @api.depends('line_ids.price_subtotal', 'currency_id', 'company_id')
    def _compute_tax_totals(self):
        AccountTax = self.env['account.tax']
        for order in self:
            company_id = order.company_id or self.env.company
            order_lines = order.line_ids
            base_lines = [line._prepare_base_line_for_taxes_computation() for line in order_lines]
            AccountTax._add_tax_details_in_base_lines(base_lines, company_id)
            AccountTax._round_base_lines_tax_details(base_lines, company_id)
            tax_totals = AccountTax._get_tax_totals_summary(
                base_lines=base_lines,
                currency=order.currency_id or company_id.currency_id,
                company=company_id,
            )
            order.tax_totals = tax_totals

    state = fields.Selection(string='Trạng thái', selection=[('new', 'Mới'), ('sent', 'Đang phê duyệt'), ('approved', 'Đã duyệt')], default='new', required=True, readonly=True, copy=False)
    line_ids = fields.One2many(string='Chi tiết', comodel_name='ttb.purchase.approval.line', inverse_name='approval_id')
    currency_rate = fields.Float(string="Tỷ giá", compute='_compute_currency_rate', digits=0, store=True)

    @api.depends('currency_id', 'date', 'company_id')
    def _compute_currency_rate(self):
        for order in self:
            order.currency_rate = self.env['res.currency']._get_conversion_rate(
                from_currency=order.company_id.currency_id,
                to_currency=order.currency_id,
                company=order.company_id,
                date=(order.date or fields.Datetime.now()).date(),
            )

    def get_approve_user_ids(self, rule):
        if rule.method not in ['manager', 'title_manager', 'mch_manager']:
            return super().get_approve_user_ids(rule)
        user_ids = self.env['res.users']
        company_domain = []
        if self.fields_get(['company_id']).get('company_id') and self.company_id:
            self = self.with_company(self.company_id)
            company_domain = ['|', ('company_id', '=', self.company_id.id), ('company_id', '=', False)]
        if rule.method == 'manager':
            user_ids = self.user_id.employee_id.parent_id.user_id
        elif rule.method == 'title_manager':
            parent = self.user_id.employee_id.parent_id
            while parent:
                if parent.job_id.id == rule.job_id.id:
                    user_ids |= parent.user_id
                parent = parent.parent_id
        elif rule.method == 'mch_manager':
            user_ids = self.line_ids.categ_id.mapped('ttb_user_id')
        return user_ids

    @api.depends('user_id')
    def _compute_sent_ok(self):
        for rec in self:
            rec.sent_ok = rec.user_id and self.env.user == rec.user_id

    def action_sent(self):
        if self.state != 'new': return
        if not self.sent_ok: return
        process_id, approval_line_ids = self.get_approval_line_ids()
        self.write({'process_id': process_id.id,
                    'date_sent': fields.Datetime.now(),
                    'state': 'sent',
                    'approval_line_ids': [(5, 0, 0)] + approval_line_ids})
        if self.env.user.id not in self.current_approve_user_ids.ids:
            self.send_notify(message='Bạn cần duyệt tờ trình duyệt giá', users=self.current_approve_user_ids, subject='Yêu cầu mua hàng cần duyệt')
        self.action_approve()
        return True

    def action_approve(self):
        if self.state != 'sent': return
        if not self.approve_ok and self.rule_line_ids: return
        if self.state_change('approved'):
            self.sudo().write({'state': 'approved', 'date_approved': fields.Datetime.now()})
            self.action_created_po()
            if self.rule_line_ids:
                self.send_notify(message='Tờ trình duyệt giá của bạn đã được duyệt', users=self.user_id, subject='Tờ trình duyệt giá đã duyệt')
                self.send_notify(message='Bạn được phân công thực hiện tờ trình duyệt giá', users=self.notif_user_ids, subject='Tờ trình duyệt giá cần thực hiện')
        else:
            self.send_notify(message='Bạn cần duyệt tờ trình duyệt giá', users=self.current_approve_user_ids, subject='Tờ trình duyệt giá cần duyệt')
        return True

    def action_reject(self):
        if self.state != 'sent': return
        if not self.approve_ok: return
        self.state_change('rejected')
        if self.rule_line_ids.search([('notif_only', '=', False), ('res_id', 'in', self.ids), ('res_model', '=', self._name)], order='sequence asc', limit=1).state == 'rejected':
            self.sudo().write({'state': 'new'})
            self.send_notify(message='Tờ trình duyệt giá của bạn đã bị từ chối', users=self.user_id, subject='Tờ trình duyệt giá bị từ chối')
        else:
            self.send_notify(message='Bạn cần điều chỉnh duyệt tờ trình duyệt giá', users=self.current_approve_user_ids, subject='Tờ trình duyệt giá cần duyệt')
        return True
