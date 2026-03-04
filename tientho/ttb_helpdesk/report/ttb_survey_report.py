# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class TTBSurveyReport(models.Model):
    _name = "ttb.survey.report"
    _description = "Thống kê kết quả theo khảo sát trung tâm"
    _auto = True
    _rec_name = 'branch_id'
    _order = 'branch_id desc'

    report_id = fields.Many2one('helpdesk.crm.report')
    branch_id = fields.Many2one('ttb.branch', string='Cơ sở')
    hpc_success = fields.Integer(string='HPC thành công')
    not_contactable = fields.Integer(string='Không liên lạc được')
    not_answered = fields.Integer(string='Không nghe máy')
    customer_error = fields.Integer(string='Sai số khách hàng báo')
    refused_interview = fields.Integer(string='Từ chối phỏng vấn')
    total = fields.Integer(string='Tổng')

    # def get_data_survey_report(self, config):
    #     return self._get_data_survey_report(config.date_from, config.date_to)
    def action_open_hpc_success(self):
        self.ensure_one()
        action = self.env.ref('ttb_helpdesk.ttb_happy_call_history_action').sudo().read()[0]
        # lọc đúng theo dòng hiện tại
        action['domain'] = [
            ('ttb_branch_id', '=', self.branch_id.id),
            # ví dụ tiêu chí bạn dùng để đếm:
            ('state', '=', 'success'),
        ]
        action['views'] = [(False, 'list'), (False, 'form')]
        return action

    def action_open_customer_error(self):
        self.ensure_one()
        action = self.env.ref('ttb_helpdesk.ttb_happy_call_history_action').sudo().read()[0]
        # lọc đúng theo dòng hiện tại
        action['domain'] = [
            ('ttb_branch_id', '=', self.branch_id.id),
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
            ('ttb_branch_id', '=', self.branch_id.id),
            # ví dụ tiêu chí bạn dùng để đếm:
            ('state', '=', 'refused'),
        ]
        action['views'] = [(False, 'list'), (False, 'form')]
        return action

    def action_open_not_contactable(self):
        self.ensure_one()
        action = self.env.ref('ttb_helpdesk.ttb_happy_call_history_action').sudo().read()[0]
        # lọc đúng theo dòng hiện tại
        action['domain'] = [
            ('ttb_branch_id', '=', self.branch_id.id),
            # ví dụ tiêu chí bạn dùng để đếm:
            ('state', '=', 'no_contact'),
        ]
        action['views'] = [(False, 'list'), (False, 'form')]
        return action

    def action_open_not_answered(self):
        self.ensure_one()
        action = self.env.ref('ttb_helpdesk.ttb_happy_call_history_action').sudo().read()[0]
        # lọc đúng theo dòng hiện tại
        action['domain'] = [
            ('ttb_branch_id', '=', self.branch_id.id),
            # ví dụ tiêu chí bạn dùng để đếm:
            ('state', '=', 'no_answer'),
        ]
        action['views'] = [(False, 'list'), (False, 'form')]
        return action

    def _get_data_survey_report(self, start_date, end_date, branch_ids):
        data = []
        domain_common = []
        if start_date:
            domain_common.append(('execution_date', '>=', start_date))
        if end_date:
            domain_common.append(('execution_date', '<=', end_date))


        for item in branch_ids:
            sl_tham_gia_khao_sat = self.env['ttb.happy.call'].search([('ttb_branch_id', '=', item.id)] + domain_common)

            sl_hthanh_khao_sat = len(sl_tham_gia_khao_sat.filtered(lambda x: x.state == 'success'))
            sl_khong_lien_lac = len(sl_tham_gia_khao_sat.filtered(lambda x: x.state == 'no_contact'))
            sl_khong_nghe_may = len(sl_tham_gia_khao_sat.filtered(lambda x: x.state == 'no_answer'))
            sl_sai_so = len(sl_tham_gia_khao_sat.filtered(lambda x: x.state == 'wrong_number'))
            sl_tu_choi = len(sl_tham_gia_khao_sat.filtered(lambda x: x.state == 'refuse'))
            total = sl_hthanh_khao_sat + sl_khong_lien_lac + sl_khong_nghe_may + sl_sai_so + sl_tu_choi

            data.append({
                'branch_id': item.id,
                'hpc_success': sl_hthanh_khao_sat,
                'not_contactable': sl_khong_lien_lac,
                'not_answered': sl_khong_nghe_may,
                'customer_error': sl_sai_so,
                'refused_interview': sl_tu_choi,
                'total': total,
            })
        return data

    def calculate_data(self, config=False):
        config = config or self.env['ttb.popup.filtered.kstt'].get_last_config()
        return self._get_data_survey_report(config.date_from, config.date_to, config.get_selected_brands())


    def get_data(self, report_id):
        data = self.calculate_data()
        report_id.survey_report_ids = [(5, 0, 0)] + [(0, 0, vals) for vals in data]


