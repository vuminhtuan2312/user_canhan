# -*- coding: utf-8 -*-

from odoo import models, fields, api

class BudgetReport(models.Model):
    _name = 'fsapp.budget.report'
    _description = 'Báo cáo ngân sách'
    _auto = False

    cost_group = fields.Many2one('account.analytic.plan', string='Nhóm chi phí', readonly=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Chi phí', readonly=True)
    date_from = fields.Date(string='Từ ngày', readonly=True)
    date_to = fields.Date(string='Đến ngày', readonly=True)
    budget_type = fields.Selection([
        ('month', 'Tháng'),
        ('quarter', 'Quý'),
        ('half-year', 'Nửa năm'),
        ('year', 'Năm')
    ], string='Loại dự toán', readonly=True)
    planned_cost = fields.Float(string='Chi phí kế hoạch', readonly=True)
    adjustment_cost = fields.Float(string='Chi phí điều chỉnh', readonly=True)
    adjustment_count = fields.Integer(string='Số lần điều chỉnh', readonly=True)

    def init(self):
        self.env.cr.execute("""
            DROP VIEW IF EXISTS fsapp_budget_report;
            CREATE OR REPLACE VIEW fsapp_budget_report AS (
                SELECT
                    row_number() OVER () AS id,
                    COALESCE(bl.analytic_account_id, al.analytic_account_id) AS analytic_account_id,
                    COALESCE(aa.plan_id, aag.plan_id) AS cost_group,
                    COALESCE(b.date_from, ab.date_from) AS date_from,
                    COALESCE(b.date_to, ab.date_to) AS date_to,
                    COALESCE(b.budget_type, ab.budget_type) AS budget_type,
                    COALESCE(SUM(bl.planned_cost), 0) AS planned_cost,
                    COALESCE(SUM(al.planned_cost), 0) AS adjustment_cost,
                    COUNT(DISTINCT a.id) FILTER (WHERE a.id IS NOT NULL) AS adjustment_count
                FROM fsapp_budget_adjustment a
                JOIN fsapp_budget ab ON a.budget_id = ab.id AND a.state = 'approved'
                JOIN fsapp_budget_adjustment_line al ON al.adjustment_id = a.id
                LEFT JOIN account_analytic_account aag ON al.analytic_account_id = aag.id

                FULL JOIN fsapp_budget_line bl ON bl.analytic_account_id = al.analytic_account_id
                FULL JOIN fsapp_budget b ON bl.budget_id = b.id
                LEFT JOIN account_analytic_account aa ON bl.analytic_account_id = aa.id

                WHERE ab.state = 'approved'

                GROUP BY
                    COALESCE(bl.analytic_account_id, al.analytic_account_id),
                    COALESCE(aa.plan_id, aag.plan_id),
                    COALESCE(b.date_from, ab.date_from),
                    COALESCE(b.date_to, ab.date_to),
                    COALESCE(b.budget_type, ab.budget_type)
            )
        """)
