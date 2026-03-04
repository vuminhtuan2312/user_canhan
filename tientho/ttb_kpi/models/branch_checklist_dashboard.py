from odoo import models, fields, api
import json

class TtbBranchChecklistDashboard(models.Model):
    _inherit = 'ttb.branch'

    checklist_count_need_approve = fields.Integer(string='Phiếu cần duyệt', compute='_compute_checklist_dashboard')
    checklist_count_acceptance = fields.Integer(string='Phiếu nghiệm thu', compute='_compute_checklist_dashboard')
    checklist_count_overdue = fields.Integer(string='Trễ hạn', compute='_compute_checklist_dashboard')
    graph_dashboard_checklist = fields.Text(string='Biểu đồ checklist', compute='_compute_graph_dashboard_checklist')

    @api.depends()
    def _compute_checklist_dashboard(self):
        TaskReport = self.env['ttb.task.report']
        AccountRecord = self.env['ttb.acceptance.record']
        for branch in self:
            # Phiếu cần duyệt
            need_approve = TaskReport.search_count([
                ('user_branch_id', '=', branch.id),
                ('kpi_type_id.code', 'in', ['ANAT', 'PCCC']),
                ('state', '=', 'done'),
                ('line_ids.fail', '=', True),
            ])
            # Phiếu nghiệm thu ANAT
            acceptance_ANAT = AccountRecord.search_count([
                ('user_branch_id', '=', branch.id),
                ('kpi_type_id.code', '=', 'ANAT'),
                ('state', '=', 'new'),
            ])
            # Phiếu nghiệm thu PCCC
            acceptance_PCCC = AccountRecord.search_count([
                ('user_branch_id', '=', branch.id),
                ('kpi_type_id.code', '=', 'PCCC'),
                ('state', '=', 'new'),
            ])
            # Trễ hạn
            overdue = AccountRecord.search_count([
                ('user_branch_id', '=', branch.id),
                ('kpi_type_id.code', 'in', ['ANAT', 'PCCC']),
                ('state', '=', 'overdue'),
            ])
            branch.checklist_count_need_approve = need_approve
            branch.checklist_count_acceptance = acceptance_ANAT + acceptance_PCCC
            branch.checklist_count_overdue = overdue

    @api.depends('checklist_count_need_approve', 'checklist_count_acceptance', 'checklist_count_overdue')
    def _compute_graph_dashboard_checklist(self):
        for rec in self:
            graph_data = [{
                'key': 'Checklist',
                'values': [
                    {'label': 'Cần duyệt', 'value': rec.checklist_count_need_approve},
                    {'label': 'Nghiệm thu', 'value': rec.checklist_count_acceptance},
                    {'label': 'Trễ hạn', 'value': rec.checklist_count_overdue},
                ],
            }]
            rec.graph_dashboard_checklist = json.dumps(graph_data)

    def action_checklist_need_approve(self):
        # Lấy action đã được định nghĩa sẵn trong file XML
        action = self.env['ir.actions.act_window']._for_xml_id('ttb_kpi.ttb_task_report_action')

        # Tạo domain riêng cho trường hợp này
        action['domain'] = [
            ('user_branch_id', '=', self.id),
            ('kpi_type_id.code', 'in', ['ANAT', 'PCCC']),
            ('state', '=', 'done'),
            ('line_ids.fail', '=', True),
        ]
        # Thay đổi tên của cửa sổ để người dùng dễ hiểu
        action['display_name'] = f'Phiếu cần duyệt ({self.name})'
        return action

    def action_checklist_acceptance(self):

        action = self.env['ir.actions.act_window']._for_xml_id('ttb_kpi.ttb_task_report_acceptance_anat_action')

        action['domain'] = [
            ('user_branch_id', '=', self.id),
            ('kpi_type_id.code', 'in', ['ANAT', 'PCCC']),
            ('state', '=', 'new'),
        ]
        action['display_name'] = f'Phiếu nghiệm thu ({self.name})'
        return action

    def action_checklist_overdue(self):

        action = self.env['ir.actions.act_window']._for_xml_id('ttb_kpi.ttb_task_report_acceptance_anat_action')

        action['domain'] = [
            ('user_branch_id', '=', self.id),
            ('kpi_type_id.code', 'in', ['ANAT', 'PCCC']),
            ('state', '=', 'overdue'),
        ]
        action['display_name'] = f'Phiếu trễ hạn ({self.name})'
        return action