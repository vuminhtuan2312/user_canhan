# -*- coding: utf-8 -*-
from odoo import models, fields, api

ALLOWED_JOB_NAMES_LOWER = ('giám đốc nhà sách', 'quản lý nhà sách')

class ResUsers(models.Model):
    _inherit = 'res.users'

    ttb_notification_enabled = fields.Boolean(
        string='Bật thông báo công việc (tổng quan)',
        default=True,
        help='Khi bật, hệ thống gửi thông báo khi có công việc đến giờ thực hiện.'
    )

    ttb_visible_branch_ids = fields.Many2many(
        comodel_name='ttb.branch',
        string='Cơ sở được xem',
        compute='_compute_ttb_visible_branch_ids',
    )

    @api.depends_context('uid')
    def _compute_ttb_visible_branch_ids(self):
        Branch = self.env['ttb.branch']
        Employee = self.env['hr.employee']
        for user in self:
            if not user.id:
                user.ttb_visible_branch_ids = Branch.browse()
                continue
            emp = Employee.search([('user_id', '=', user.id)], limit=1)
            if not emp:
                user.ttb_visible_branch_ids = Branch.browse()
                continue
            job_name_lower = (emp.job_id.name or '').strip().lower()
            if job_name_lower not in ALLOWED_JOB_NAMES_LOWER:
                user.ttb_visible_branch_ids = Branch.browse()
                continue
            emp_branches = emp.ttb_branch_ids if hasattr(emp, 'ttb_branch_ids') else Branch.browse()
            user.ttb_visible_branch_ids = emp_branches

    @api.model
    def set_ttb_notification_enabled(self, enabled):
        self.browse(self.env.uid).sudo().write({'ttb_notification_enabled': bool(enabled)})
