# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class TTBCsatReport(models.Model):
    _name = "ttb.csat.report"
    _description = "Báo cáo theo câu trả lời của KH - CSAT"
    _auto = True
    _rec_name = 'branch_id'
    _order = 'branch_id desc'

    report_id = fields.Many2one('helpdesk.crm.report')
    branch_id = fields.Many2one('ttb.branch', string='Cơ sở')
    count_very = fields.Integer(string='Rất hài lòng', default=0)
    count_good = fields.Integer(string='Hài lòng', default=0)
    count_normal = fields.Integer(string='Bình thường', default=0)
    count_bad = fields.Integer(string='Không hài lòng', default=0)
    count_total = fields.Integer(string='Tổng', default=0)

    def action_open_count_very(self):
        self.ensure_one()
        action = self.env.ref('ttb_helpdesk.ttb_happy_call_history_action').sudo().read()[0]
        # lọc đúng theo dòng hiện tại
        action['domain'] = [
            ('ttb_branch_id', '=', self.branch_id.id),
            # ví dụ tiêu chí bạn dùng để đếm:
            ('shopping_experience', '=', 'Rất hài lòng'),
        ]
        action['views'] = [(False, 'list'), (False, 'form')]
        return action

    def action_open_count_good(self):
        self.ensure_one()
        action = self.env.ref('ttb_helpdesk.ttb_happy_call_history_action').sudo().read()[0]
        # lọc đúng theo dòng hiện tại
        action['domain'] = [
            ('ttb_branch_id', '=', self.branch_id.id),
            # ví dụ tiêu chí bạn dùng để đếm:
            ('shopping_experience', '=', 'Hài lòng'),
        ]
        action['views'] = [(False, 'list'), (False, 'form')]
        return action

    def action_open_count_normal(self):
        self.ensure_one()
        action = self.env.ref('ttb_helpdesk.ttb_happy_call_history_action').sudo().read()[0]
        # lọc đúng theo dòng hiện tại
        action['domain'] = [
            ('ttb_branch_id', '=', self.branch_id.id),
            # ví dụ tiêu chí bạn dùng để đếm:
            ('shopping_experience', '=', 'Bình thường'),
        ]
        action['views'] = [(False, 'list'), (False, 'form')]
        return action

    def action_open_count_bad(self):
        self.ensure_one()
        action = self.env.ref('ttb_helpdesk.ttb_happy_call_history_action').sudo().read()[0]
        # lọc đúng theo dòng hiện tại
        action['domain'] = [
            ('ttb_branch_id', '=', self.branch_id.id),
            # ví dụ tiêu chí bạn dùng để đếm:
            ('shopping_experience', '=', 'Không hài lòng'),
        ]
        action['views'] = [(False, 'list'), (False, 'form')]
        return action

    def get_data(self, report_id):
        data = self.calculate_data()
        report_id.csat_report_ids = [(5, 0, 0)] + [(0, 0, vals) for vals in data]

    def calculate_data(self, config=False):
        config = config or self.env['ttb.popup.filtered.csat'].get_last_config()
        branch_ids = config.get_selected_brands()
        Happy = self.env['ttb.happy.call']

        domain = [
            ('state', '=', 'success'),
            ('ttb_branch_id', 'in', branch_ids.ids),
        ]
        if config.date_from:
            domain.append(('execution_date', '>=', config.date_from))
        if config.date_to:
            domain.append(('execution_date', '<=', config.date_to))
        records = Happy.search(domain)

        per_branch = {}
        for rec in records:
            branch_id = rec.ttb_branch_id.id if rec.ttb_branch_id else False
            exp = rec.shopping_experience

            if not branch_id:
                continue

            if branch_id not in per_branch:
                per_branch[branch_id] = {
                    'branch_id': branch_id,
                    'count_very': 0,
                    'count_good': 0,
                    'count_normal': 0,
                    'count_bad': 0,
                    'count_total': 0,
                }
            if exp == 'Rất hài lòng':
                per_branch[branch_id]['count_very'] += 1
            elif exp == 'Hài lòng':
                per_branch[branch_id]['count_good'] += 1
            elif exp == 'Bình thường':
                per_branch[branch_id]['count_normal'] += 1
            elif exp == 'Không hài lòng':
                per_branch[branch_id]['count_bad'] += 1

            per_branch[branch_id]['count_total'] += 1

        return list(per_branch.values())