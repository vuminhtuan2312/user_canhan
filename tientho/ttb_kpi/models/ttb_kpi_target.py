import datetime, calendar
from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval


class TtbKpiTarget(models.Model):
    _name = 'ttb.kpi.target'
    _description = 'Chỉ tiêu'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Tên chỉ tiêu', required=True)
    type = fields.Selection(string='Loại chỉ tiêu', selection=[('revenue', 'Doanh thu'), ('expend', 'Chi phí')], required=True)
    so_domain = fields.Char(string='Điều kiện đơn hàng')
    pos_domain = fields.Char(string='Điệu kiện đơn POS')
    date_from = fields.Date(string='Từ ngày', required=True)
    date_to = fields.Date(string='Đến ngày', required=True)
    amount_total = fields.Monetary(string='Tổng chỉ tiêu', compute='_compute_amount_total', store=True)

    @api.depends('warehouse_ids')
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = sum(rec.warehouse_ids.mapped('target'))

    currency_id = fields.Many2one('res.currency', string='Tiền tệ', default=lambda self: self.env.company.currency_id)
    warehouse_ids = fields.One2many(comodel_name='ttb.kpi.target.line', inverse_name='target_id', string='Cơ sở', domain=[('type', '=', 'shop')])
    shelf_ids = fields.One2many(comodel_name='ttb.kpi.target.line', inverse_name='target_id', string='Quầy', domain=[('type', '=', 'shelf')])
    company_id = fields.Many2one(comodel_name='res.company', string='Công ty', index=True, default=lambda self: self.env.company)


class TtbKpiTargetLine(models.Model):
    _name = 'ttb.kpi.target.line'
    _description = 'Phân bổ chỉ tiêu'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    target_id = fields.Many2one(comodel_name='ttb.kpi.target', string='Chỉ tiêu', required=True)
    type = fields.Selection(string='Loại chỉ tiêu', selection=[('shop', 'Cơ sở'), ('shelf', 'Quầy')], required=True)
    target_type = fields.Selection(string='Loại', related='target_id.type')
    ttb_branch_id = fields.Many2one(string='Cơ sở', comodel_name='ttb.branch', required=True)
    warehouse_id = fields.Many2one(string='Cơ sở cũ', comodel_name='stock.warehouse', required=False)
    categ_id = fields.Many2one(string='Quầy', comodel_name='product.category', domain="[('category_level', '=', 1)]")
    shelf = fields.Char(string='Quầy cũ')
    target = fields.Monetary(string='Chỉ tiêu')
    achieve = fields.Monetary(string='Mức đạt được', compute='_compute_achieve', store=True, readonly=False, precompute=True)

    @api.depends('target_id', 'target_type', 'ttb_branch_id', 'target_id.date_from', 'target_id.date_to')
    def _compute_achieve(self):
        for rec in self.sudo():
            if rec.target_type == 'revenue':
                achieve = 0
                domain_sale_order = expression.AND([[('date_order', '>=', rec.target_id.date_from), ('date_order', '<=', rec.target_id.date_to), ('ttb_branch_id', '=', rec.ttb_branch_id.id)], safe_eval(rec.target_id.so_domain or '[]')])
                sale_order = self.env['sale.order'].sudo().search(domain_sale_order)
                if sale_order:
                    achieve += sum(sale_order.mapped('amount_total'))
                domain_post_order = expression.AND([[('date_order', '>=', rec.target_id.date_from), ('date_order', '<=', rec.target_id.date_to), ('ttb_branch_id', '=', rec.ttb_branch_id.id)], safe_eval(rec.target_id.pos_domain or '[]')])
                pos_order = self.env['pos.order'].sudo().search(domain_post_order)
                if pos_order:
                    achieve += sum(pos_order.mapped('amount_total'))
                rec.achieve = achieve
            else:
                rec.achieve = rec.achieve

    def _cron_compute_achieve(self):
        # today = fields.Date.context_today(self)
        # record = self.search([('target_type', '=', 'revenue'), ('target_id.date_from', '<=', today), ('target_id.date_to', '>=', today)])
        # tạm thời search hết tuy nhiên cũng cần tính thêm logic như trên hay không
        record = self.sudo().search([])
        if record:
            record._compute_achieve()

    currency_id = fields.Many2one('res.currency', string='Tiền tệ', default=lambda self: self.env.company.currency_id)
    current_rate = fields.Float(string='Tỷ lệ đạt', compute='_compute_current_rate', store=True)

    @api.depends('achieve', 'target')
    def _compute_current_rate(self):
        for rec in self:
            rec.current_rate = rec.achieve/rec.target if rec.target else 0

    expected_rate = fields.Float(string='Dự kiến tỷ lệ đạt cuối kỳ', compute='_compute_expected_rate', store=True)

    @api.depends('achieve', 'target')
    def _compute_expected_rate(self):
        for rec in self:
            if rec.target:
                today = datetime.date.today()
                day = today.day - 1
                _, last_day = calendar.monthrange(today.year, today.month)
                if day:
                    rec.expected_rate = (rec.achieve * last_day)/(rec.target * day)
                else:
                    rec.expected_rate = 0
            else:
                rec.expected_rate = 0

    bonus = fields.Monetary(string='Số tiền vượt chỉ tiêu', compute='_compute_bonus', store=True)

    @api.depends('achieve', 'target')
    def _compute_bonus(self):
        for rec in self:
            rec.bonus = max((rec.achieve - rec.target), 0)
