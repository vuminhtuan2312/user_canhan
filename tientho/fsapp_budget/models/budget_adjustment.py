# -*- coding: utf-8 -*-

from odoo import models, fields, api

class BudgetAdjustment(models.Model):
    _name = 'fsapp.budget.adjustment'
    _description = 'Điều chỉnh ngân sách'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Tên điều chỉnh', required=True, tracking=True)
    proposer_id = fields.Many2one('res.users', string='Người đề xuất', required=True, default=lambda self: self.env.user, tracking=True)
    budget_id = fields.Many2one('fsapp.budget', string='Ngân sách', required=True, tracking=True, domain="[('state', '=', 'approved')]")
    project_budget_id = fields.Many2one(related='budget_id.project_budget_id', string='Dự án', store=True, readonly=True)
    date_from = fields.Date(related='budget_id.date_from', string='Từ ngày', store=True, readonly=True)
    date_to = fields.Date(related='budget_id.date_to', string='Đến ngày', store=True, readonly=True)

    state = fields.Selection([
        ('draft', 'Mới'),
        ('waiting', 'Đang duyệt'),
        ('approved', 'Đã duyệt'),
        ('rejected', 'Không duyệt'),
        ('cancelled', 'Hủy')
    ], string='Trạng thái', default='draft', tracking=True, required=True)

    adjustment_line_ids = fields.One2many('fsapp.budget.adjustment.line', 'adjustment_id', string='Chi tiết điều chỉnh')

    can_submit = fields.Boolean(string='Có thể gửi duyệt', compute='_compute_can_submit')
    can_approve = fields.Boolean(string='Có thể duyệt', compute='_compute_can_approve')
    can_cancel = fields.Boolean(string='Có thể hủy', compute='_compute_can_cancel')
    can_reset = fields.Boolean(string='Có thể về mới', compute='_compute_can_reset')

    approve_user_id = fields.Many2one('res.users', string='Người duyệt', readonly=True, tracking=True)
    total_adjustment = fields.Float('Tổng điều chỉnh', compute='_compute_total_adjustment', store=True, tracking=True)

    @api.depends('adjustment_line_ids.planned_cost')
    def _compute_total_adjustment(self):
        for rec in self:
            rec.total_adjustment = sum(line.planned_cost for line in rec.adjustment_line_ids)

    @api.depends('proposer_id', 'state')
    def _compute_can_submit(self):
        current_user = self.env.user
        for adj in self:
            adj.can_submit = adj.state in ('draft', 'rejected') and adj.proposer_id == current_user

    @api.depends('approve_user_id', 'state')
    def _compute_can_approve(self):
        current_user = self.env.user
        for adj in self:
            adj.can_approve = adj.state == 'waiting' and adj.approve_user_id == current_user

    @api.depends('proposer_id', 'approve_user_id', 'state')
    def _compute_can_cancel(self):
        current_user = self.env.user
        for adj in self:
            if adj.state in ('waiting', 'rejected'):
                adj.can_cancel = adj.proposer_id == current_user
            elif adj.state == 'approved':
                adj.can_cancel = adj.approve_user_id == current_user
            else:
                adj.can_cancel = False

    @api.depends('proposer_id', 'state')
    def _compute_can_reset(self):
        current_user = self.env.user
        for adj in self:
            adj.can_reset = adj.state == 'cancelled' and adj.proposer_id == current_user

    def action_submit(self):
        for record in self:
            approver_id = int(self.env['ir.config_parameter'].sudo().get_param('fsapp_budget.budget_approver_id') or 0)
            record.approve_user_id = approver_id
            record.state = 'waiting'

    def action_cancel(self):
        for record in self:
            record.state = 'cancelled'

    def action_approve(self):
        for rec in self:
            for line in rec.adjustment_line_ids:
                existing_line = self.env['fsapp.budget.line'].search([
                    ('budget_id', '=', rec.budget_id.id),
                    ('analytic_account_id', '=', line.analytic_account_id.id)
                ], limit=1)

                if existing_line:
                    existing_line.adjustment_cost += line.planned_cost
                    existing_line.adjustment_count += 1
                else:
                    self.env['fsapp.budget.line'].create({
                        'budget_id': rec.budget_id.id,
                        'analytic_account_id': line.analytic_account_id.id,
                        'planned_cost': 0.0,
                        'adjustment_cost': line.planned_cost,
                        'adjustment_count': 1,
                        'description': line.description
                    })
            rec.state = 'approved'

    def action_reject(self):
        for record in self:
            record.state = 'rejected'

    def action_reset_to_draft(self):
        for record in self:
            record.state = 'draft'


class BudgetAdjustmentLine(models.Model):
    _name = 'fsapp.budget.adjustment.line'
    _description = 'Chi tiết điều chỉnh ngân sách'

    adjustment_id = fields.Many2one('fsapp.budget.adjustment', string='Điều chỉnh', required=True, ondelete='cascade')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Chi phí', required=True)
    cost_group = fields.Many2one('account.analytic.plan', string='Nhóm chi phí', related='analytic_account_id.plan_id', store=True, readonly=True)
    planned_cost = fields.Float('Chi phí điều chỉnh')
    description = fields.Char('Mô tả')
