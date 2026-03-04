from odoo import *
from pytz import timezone
from datetime import datetime, time


class PurchasePrice(models.Model):
    _name = 'ttb.purchase.price'
    _description = 'Đề nghị duyệt giá'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'ttb.approval.mixin']
    _order = 'date desc, id desc'

    def action_update_pol_price_unit(self):
        self.ensure_one()
        self = self.sudo()
        date_order = timezone(self.env.user.tz).localize(datetime.combine(self.date_applied, time.min)).astimezone(timezone('UTC')).replace(tzinfo=None)
        orders = self.env['purchase.order'].search([('partner_id', '=', self.partner_id.id), ('date_order', '>=', date_order), ('product_id', 'in', self.mapped('line_ids.product_id').ids)])
        for product in self.mapped('line_ids.product_id'):
            if not product:
                continue
            lines = self.env['purchase.order.line'].search([('order_id', 'in', orders.ids), ('product_id', '=', product.id)])
            lines._compute_price_unit_and_date_planned_and_name()
        return {
            'effect': {
                'fadeout': 'slow',
                'message': 'Đã cập nhật giá PO!',
                'img_url': '/web/image/%s/%s/image_1024' % (self.env.user._name, self.env.user.id) if self.env.user.image_1024 else '/web/static/img/smile.svg',
                'type': 'rainbow_man',
            }
        }

    name = fields.Char(string='Mã đề nghị', default='Mới', readonly=True, copy=False, required=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == 'Mới':
                vals['name'] = self.env['ir.sequence'].next_by_code('purchase.price') or 'Mới'
        return super().create(vals_list)

    date = fields.Datetime(string='Ngày đề nghị', required=True, default=lambda self: fields.Datetime.now())
    user_id = fields.Many2one(string='Người đề nghị', required=True, comodel_name='res.users', default=lambda self: self.env.user)
    company_id = fields.Many2one(string='Công ty', required=True, comodel_name='res.company', default=lambda self: self.env.company)
    partner_id = fields.Many2one(string='Nhà cung cấp', comodel_name='res.partner', required=True)
    date_applied = fields.Date(string='Ngày áp dụng', required=True)

    state = fields.Selection(string='Trạng thái', selection=[('new', 'Mới'),
                                                             ('sent', 'Đang phê duyệt'),
                                                             ('approved', 'Đã duyệt'),
                                                             ('cancel', 'Hủy')]
                             , readonly=True, copy=False, default='new', tracking=True)
    line_ids = fields.One2many(string='Danh sách sản phẩm', comodel_name='ttb.purchase.price.line', inverse_name='price_id', copy=True)
    product_id = fields.Many2one(related='line_ids.product_id', string='Sản phẩm')

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
            user_ids = self.line_ids.mapped('product_id.categ_id.ttb_user_id')
        return user_ids

    @api.depends('user_id')
    def _compute_sent_ok(self):
        for rec in self:
            rec.sent_ok = rec.user_id and self.env.user == rec.user_id

    def _update_taxes(self):
        for rec in self:
            for line in rec.line_ids:
                if not line.new_tax or not line.product_id:
                    continue

                partner = line.price_id.partner_id
                product_template = line.product_id.product_tmpl_id

                supplier_infos = self.env['product.supplierinfo'].search([
                    ('product_tmpl_id', '=', product_template.id),
                    ('partner_id', '=', partner.id),
                ])
                for info in supplier_infos:
                    info.taxes = [(6, 0, line.new_tax.ids)]

                product_template.supplier_taxes_id = [(6, 0, line.new_tax.ids)]

    def action_sent(self):
        if self.state != 'new': return
        if not self.sent_ok: return
        process_id, approval_line_ids = self.get_approval_line_ids()
        self.write({'process_id': process_id.id,
                    'date_sent': fields.Datetime.now(),
                    'state': 'sent',
                    'approval_line_ids': [(5, 0, 0)] + approval_line_ids})
        if self.env.user.id not in self.current_approve_user_ids.ids:
            self.send_notify(message='Bạn cần duyệt đề nghị duyệt giá', users=self.current_approve_user_ids, subject='Đề nghị duyệt giá cần duyệt')
        self.action_approve()
        return True

    def action_approve(self):
        if self.state != 'sent': return
        if not self.approve_ok and self.rule_line_ids: return
        if self.state_change('approved'):
            self = self.sudo()
            self.write({'state': 'approved', 'date_approved': fields.Datetime.now()})
            if self.rule_line_ids:
                self.send_notify(message='Đề nghị duyệt giá của bạn đã được duyệt', users=self.user_id, subject='Đề nghị duyệt giá đã duyệt')
                self.send_notify(message='Bạn được phân công thực hiện đề nghị duyệt giá', users=self.notif_user_ids, subject='Đề nghị duyệt giá cần thực hiện')
            vals_lst = []
            for line in self.line_ids:
                vals_lst += [{
                    'partner_id': line.price_id.partner_id.id,
                    'product_id': line.product_id.id,
                    'discount': line.discount,
                    'price': line.packaging_id._compute_qty(line.price) if line.packaging_id else line.price,
                    'currency_id': line.currency_id.id,
                    'date_start': line.price_id.date_applied
                }]
                sellers = line.product_id._get_filtered_sellers_no_date(line.price_id.partner_id, None)
                sellers.filtered(lambda x: not x.date_end or x.date_end >= line.price_id.date_applied).write({'date_end': fields.Date.add(line.price_id.date_applied, days=-1)})
            if vals_lst:
                self.env['product.supplierinfo'].create(vals_lst)
                self._update_taxes()
        else:
            self.send_notify(message='Bạn cần duyệt đề nghị duyệt giá', users=self.current_approve_user_ids, subject='Đề nghị duyệt giá cần duyệt')
        return True

    def action_reject(self):
        if self.state != 'sent': return
        if not self.approve_ok: return
        self.state_change('rejected')
        if self.rule_line_ids.search([('notif_only', '=', False), ('res_id', 'in', self.ids), ('res_model', '=', self._name)], order='sequence asc', limit=1).state == 'rejected':
            self.sudo().write({'state': 'new'})
            self.send_notify(message='Đề nghị duyệt giá của bạn đã bị từ chối', users=self.user_id, subject='Đề nghị duyệt giá bị từ chối')
        else:
            self.send_notify(message='Bạn cần duyệt đề nghị duyệt giá', users=self.current_approve_user_ids, subject='Đề nghị duyệt giá cần duyệt')
        return True

    def action_cancel(self):
        if self.state != 'new': return
        self.sudo().write({'state': 'cancel'})
        return True

    def action_import_product(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'import',
            'target': 'new',
            'name': 'Nhập sản phẩm',
            'params': {
                'context': {'default_price_id': self.id},
                'active_model': 'ttb.purchase.price.line',
            }
        }
