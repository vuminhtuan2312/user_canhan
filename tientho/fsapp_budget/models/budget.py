import requests
from odoo import api, fields, models

# Model copy từ odoo 14
class AccountAnalyticTag(models.Model):
    _name = 'account.analytic.tag'
    _description = 'Analytic Tags'
    name = fields.Char(string='Analytic Tag', index=True, required=True)
    color = fields.Integer('Color Index')
    active = fields.Boolean(default=True, help="Set active to false to hide the Analytic Tag without removing it.")
    active_analytic_distribution = fields.Boolean('Analytic Distribution')
    # analytic_distribution_ids = fields.One2many('account.analytic.distribution', 'tag_id', string="Analytic Accounts")
    company_id = fields.Many2one('res.company', string='Company')

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # default_budget_approver_id = fields.Many2one(
    #     'res.users', string='Người duyệt ngân sách',
    #     config_parameter='fsapp_budget.default_budget_approver_id'
    # )
    budget_approver_id = fields.Many2one(
        'res.users',
        string='Người duyệt ngân sách',
        config_parameter='fsapp_budget.budget_approver_id',
    )

class Budget(models.Model):
    _name = 'fsapp.budget'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Ngân sách dự toán'
    name = fields.Char('Tên ngân sách', required=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Mới'),
        ('waiting', 'Đang duyệt'),
        ('approved', 'Đã duyệt'),
        ('rejected', 'Không duyệt'),
        ('cancelled', 'Hủy')
    ], string='Trạng thái', default='draft', tracking=True, required=True)

    department_id = fields.Many2one('hr.department', string='Phòng/Ban', required=True, tracking=True)
    manager_id = fields.Many2one('hr.employee', related='department_id.manager_id', string='Chủ dự toán', readonly=True)
    project_budget_id = fields.Many2one('account.analytic.tag', string='Dự án', required=True, tracking=True)
    budget_type = fields.Selection([
        ('month', 'Tháng'),
        ('quarter', 'Quý'),
        ('half-year', 'Nửa năm'),
        ('year', 'Năm')
    ], string='Loại dự toán', required=True, tracking=True)
    date_from = fields.Date('Từ ngày', required=True, tracking=True)
    date_to = fields.Date('Đến ngày', required=True, tracking=True)
    # approve_user_id = fields.Many2one('res.users', string='Người duyệt', required=True, tracking=True)
    approve_user_id = fields.Many2one(
        'res.users', string='Người duyệt', tracking=True,
        default=lambda self: self.env['ir.config_parameter'].sudo().get_param('fsapp_budget.default_budget_approver_id') and int(self.env['ir.config_parameter'].sudo().get_param('fsapp_budget.default_budget_approver_id'))
    )
    total_budget = fields.Float('Tổng ngân sách', compute='_compute_total_budget', store=True, tracking=True)

    budget_line_ids = fields.One2many('fsapp.budget.line', 'budget_id', string='Các dòng ngân sách', required=True)

    can_submit = fields.Boolean(string='Có thể gửi duyệt', compute='_compute_can_submit')
    can_approve = fields.Boolean(string='Có thể duyệt', compute='_compute_can_approve')
    can_cancel = fields.Boolean(string='Có thể hủy', compute='_compute_can_cancel')
    can_reset = fields.Boolean(string='Có thể về mới', compute='_compute_can_reset')

    @api.depends('create_uid', 'manager_id.user_id', 'state')
    def _compute_can_submit(self):
        current_user = self.env.user
        for budget in self:
            valid_state = budget.state in ('draft', 'rejected')
            budget.can_submit = valid_state and (
                budget.create_uid == current_user or
                (budget.manager_id and budget.manager_id.user_id == current_user)
            )

    @api.depends('approve_user_id', 'state')
    def _compute_can_approve(self):
        current_user = self.env.user
        for budget in self:
            budget.can_approve = budget.state == 'waiting' and budget.approve_user_id == current_user

    @api.depends('create_uid', 'manager_id.user_id', 'approve_user_id', 'state')
    def _compute_can_cancel(self):
        current_user = self.env.user
        for budget in self:
            if budget.state in ('waiting', 'rejected'):
                budget.can_cancel = budget.create_uid == current_user or \
                    (budget.manager_id and budget.manager_id.user_id == current_user)
            elif budget.state == 'approved':
                budget.can_cancel = budget.approve_user_id == current_user
            else:
                budget.can_cancel = False

    @api.depends('create_uid', 'manager_id.user_id', 'state')
    def _compute_can_reset(self):
        current_user = self.env.user
        for budget in self:
            budget.can_reset = budget.state == 'cancelled' and (
                budget.create_uid == current_user or
                (budget.manager_id and budget.manager_id.user_id == current_user)
            )

    @api.depends('budget_line_ids.planned_cost')
    def _compute_total_budget(self):
        for budget in self:
            budget.total_budget = sum(line.planned_cost for line in budget.budget_line_ids)

    def action_submit(self):
        for record in self:
            approver_id = int(self.env['ir.config_parameter'].sudo().get_param('fsapp_budget.budget_approver_id') or 0)
            record.approve_user_id = approver_id
            record.state = 'waiting'

    def action_cancel(self):
        for record in self:
            record.state = 'cancelled'

    def action_approve(self):
        for record in self:
            record.state = 'approved'

    def action_reject(self):
        for record in self:
            record.state = 'rejected'

    def action_reset_to_draft(self):
        for record in self:
            record.state = 'draft'

    active = fields.Boolean(default=True)


# class BudgetLine(models.Model):
#     _name = 'fsapp.budget.line'
#     _description = 'Dòng ngân sách'

#     analytic_account_id = fields.Many2one('account.analytic.account', string='Chi phí', required=True)
#     cost_group = fields.Many2one('account.analytic.group', string='Nhóm chi phí', related='analytic_account_id.group_id', store=True, readonly=True)
#     planned_cost = fields.Float('Chi phí kế hoạch')
#     description = fields.Char('Mô tả')

class BudgetLine(models.Model):
    _name = 'fsapp.budget.line'
    _description = 'Dòng ngân sách'

    budget_id = fields.Many2one('fsapp.budget', string='Ngân sách cha', required=True, ondelete='cascade')
    
    budget_type = fields.Selection(related='budget_id.budget_type', store=True)
    date_from = fields.Date(related='budget_id.date_from', store=True)
    date_to = fields.Date(related='budget_id.date_to', store=True)
    department_id = fields.Many2one('hr.department', related='budget_id.department_id', store=True)
    manager_id = fields.Many2one('hr.employee', related='budget_id.manager_id', store=True)
    project_budget_id = fields.Many2one('account.analytic.tag', related='budget_id.project_budget_id', store=True)
    
    analytic_account_id = fields.Many2one('account.analytic.account', string='Chi phí', required=True)
    cost_group = fields.Many2one('account.analytic.plan', string='Nhóm chi phí', related='analytic_account_id.plan_id', store=True, readonly=True)
    planned_cost = fields.Float('Chi phí kế hoạch')
    description = fields.Char('Mô tả')

    adjustment_cost = fields.Float(string='Chi phí điều chỉnh', readonly=True)
    adjustment_count = fields.Integer(string='Số lần điều chỉnh', readonly=True)
    final_cost = fields.Float('Chi phí sau điều chỉnh', compute='compute_final_cost')
    @api.depends('planned_cost', 'adjustment_cost')
    def compute_final_cost(self):
        for rec in self:
            rec.final_cost = rec.planned_cost + rec.adjustment_cost
