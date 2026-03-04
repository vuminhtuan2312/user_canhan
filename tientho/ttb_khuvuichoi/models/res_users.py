# -*- coding: utf-8 -*-
from odoo import models, fields, api


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
        Assignment = self.env['ttb.shift.assignment']
        Employee = self.env['hr.employee']
        for user in self:
            branch_ids = self.env['ttb.branch']
            if not user.id:
                user.ttb_visible_branch_ids = branch_ids
                continue
            managed = Branch.search([('manager_id', '=', user.id)])
            assignments = Assignment.search([('manager_id.user_id', '=', user.id)])
            assignment_branches = assignments.mapped('branch_id')
            emp = Employee.search([('user_id', '=', user.id)], limit=1)
            emp_branches = (emp.ttb_branch_ids if hasattr(emp, 'ttb_branch_ids') else Branch) if emp else Branch.browse()
            user.ttb_visible_branch_ids = managed | assignment_branches | emp_branches

    @api.model
    def set_ttb_notification_enabled(self, enabled):
        self.browse(self.env.uid).sudo().write({'ttb_notification_enabled': bool(enabled)})
