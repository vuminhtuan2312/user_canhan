# Part of Odoo. See LICENSE file for full copyright and licensing details.
from werkzeug.urls import url_encode
import json
from odoo import api, fields, models


class TTBKpiReport(models.Model):
    _name = "ttb.kpi.report"
    _description = "Báo cáo Thống kê theo năng suất của NV CSKH"
    _auto = True
    _rec_name = 'user_id'
    _order = 'user_id desc'

    report_id = fields.Many2one('helpdesk.crm.report')
    user_id = fields.Many2one('res.users', string='Người xử lý')
    hpc_success = fields.Integer(string='HPC thành công')
    customer_error = fields.Integer(string='Sai số khách hàng báo')
    refused_interview = fields.Integer(string='Từ chối phỏng vấn')
    count_uncontact = fields.Integer(string='Không liên lạc được')
    count_nocall = fields.Integer(string='Không nghe máy')
    count_follow = fields.Integer(string='Theo dõi')
    total = fields.Integer(string='Tổng')

    def action_open_hpc_success(self):
        self.ensure_one()
        action = self.env.ref('ttb_helpdesk.ttb_happy_call_history_action').sudo().read()[0]
        # lọc đúng theo dòng hiện tại
        action['domain'] = [
            ('user_id', '=', self.user_id.id),
            # ví dụ tiêu chí bạn dùng để đếm:
            ('state', '=', 'success'),
            # nếu cần theo NV/đối tượng:
            # ('assignee_id', '=', self.staff_id.id),
        ]
        action['views'] = [(False, 'list'), (False, 'form')]
        return action

    def action_open_customer_error(self):
        self.ensure_one()
        action = self.env.ref('ttb_helpdesk.ttb_happy_call_history_action').sudo().read()[0]
        # lọc đúng theo dòng hiện tại
        action['domain'] = [
            ('user_id', '=', self.user_id.id),
            # ví dụ tiêu chí bạn dùng để đếm:
            ('state', '=', 'wrong_number'),
        ]
        action['views'] = [(False, 'list'), (False, 'form')]
        return action

    def action_open_refused_interview(self):
        self.ensure_one()
        action = self.env.ref('ttb_helpdesk.ttb_happy_call_history_action').sudo().read()[0]
        # lọc đúng theo dòng hiện tại
        action['domain'] = [
            ('user_id', '=', self.user_id.id),
            # ví dụ tiêu chí bạn dùng để đếm:
            ('state', '=', 'refuse'),
            # nếu cần theo NV/đối tượng:
            # ('assignee_id', '=', self.staff_id.id),
        ]
        action['views'] = [(False, 'list'), (False, 'form')]
        return action

    def get_data(self, report_id):
        data = self.calculate_data()
        report_id.kpi_report_ids = [(5, 0, 0)] + [(0, 0, vals) for vals in data]

    def calculate_data(self, config=False, user_id=False):
        config = config or self.env['ttb.popup.filtered.cskh'].get_last_config()
        branch_ids = config.get_selected_brands()
        
        domain = [('ttb_branch_id', 'in', branch_ids.ids)]
        
        if config.user_id:
            domain.append(('user_id', '=', config.user_id.id))
        if config.survey_state:
            domain.append(('state', '=', config.survey_state))
        if config.date_from:
            domain += [('execution_date', '>=', config.date_from)]
        if config.date_to:
            domain += [('execution_date', '<=', config.date_to)]

        if self.env.user.has_group('ttb_kpi.group_ttb_kpi_nv_cskh'):
            domain.append(('user_id', '=', self.env.user.id))
        elif user_id:  # nếu bạn truyền user_id cụ thể từ popup
            domain.append(('user_id', '=', user_id.id))
        
        records = self.env['ttb.happy.call'].search(domain)
        per_user = {}
        for rec in records:
            user_id = rec.user_id.id if rec.user_id else False
            state = rec.state

            if not user_id:
                continue

            if user_id not in per_user:
                per_user[user_id] = {
                    'user_id': user_id,
                    'hpc_success': 0,
                    'customer_error': 0,
                    'refused_interview': 0,
                    # 'count_uncontact': 0,
                    # 'count_nocall': 0,
                    # 'count_follow': 0,
                    'total': 0,
                }
            if state == 'success':
                per_user[user_id]['hpc_success'] += 1
                per_user[user_id]['total'] += 1
            elif state == 'wrong_number':
                per_user[user_id]['customer_error'] += 1
                per_user[user_id]['total'] += 1
            elif state == 'refuse':
                per_user[user_id]['refused_interview'] += 1
                per_user[user_id]['total'] += 1
            # elif state == 'no_contact':
            #     per_user[user_id]['count_uncontact'] += 1
            # elif state == 'no_answer':
            #     per_user[user_id]['count_nocall'] += 1
            # elif state == 'follow_up':
            #     per_user[user_id]['count_follow'] += 1
            # per_user[user_id]['total'] += 1

        return list(per_user.values())
