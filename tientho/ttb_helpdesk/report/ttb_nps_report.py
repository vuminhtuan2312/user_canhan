# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class TTBNpsReport(models.Model):
    _name = "ttb.nps.report"
    _description = "Báo cáo theo câu trả lời của KH - NPS"
    _auto = True
    _rec_name = 'branch_id'
    _order = 'branch_id desc'

    report_id = fields.Many2one('helpdesk.crm.report')
    branch_id = fields.Many2one('ttb.branch', string='Cơ sở')
    very_willing = fields.Integer(string='Rất sẵn lòng')
    willing = fields.Integer(string='Sẵn lòng')
    consider_passive = fields.Integer(string='Cân nhắc/Thụ động')
    unwilling = fields.Integer(string='Không sẵn lòng')
    total = fields.Integer(string='Tổng')

    def action_open_very_willing(self):
        self.ensure_one()
        action = self.env.ref('ttb_helpdesk.ttb_happy_call_history_action').sudo().read()[0]
        # lọc đúng theo dòng hiện tại
        action['domain'] = [
            ('ttb_branch_id', '=', self.branch_id.id),
            # ví dụ tiêu chí bạn dùng để đếm:
            ('introduce_to_others', '=', 'Rất sẵn lòng'),
        ]
        action['views'] = [(False, 'list'), (False, 'form')]
        return action

    def action_open_willing(self):
        self.ensure_one()
        action = self.env.ref('ttb_helpdesk.ttb_happy_call_history_action').sudo().read()[0]
        # lọc đúng theo dòng hiện tại
        action['domain'] = [
            ('ttb_branch_id', '=', self.branch_id.id),
            # ví dụ tiêu chí bạn dùng để đếm:
            ('introduce_to_others', '=', 'Sẵn lòng'),
        ]
        action['views'] = [(False, 'list'), (False, 'form')]
        return action

    def action_open_consider_passive(self):
        self.ensure_one()
        action = self.env.ref('ttb_helpdesk.ttb_happy_call_history_action').sudo().read()[0]
        # lọc đúng theo dòng hiện tại
        action['domain'] = [
            ('ttb_branch_id', '=', self.branch_id.id),
            # ví dụ tiêu chí bạn dùng để đếm:
            ('introduce_to_others', '=', 'Cân nhắc/Thụ động'),
        ]
        action['views'] = [(False, 'list'), (False, 'form')]
        return action

    def action_open_unwilling(self):
        self.ensure_one()
        action = self.env.ref('ttb_helpdesk.ttb_happy_call_history_action').sudo().read()[0]
        # lọc đúng theo dòng hiện tại
        action['domain'] = [
            ('ttb_branch_id', '=', self.branch_id.id),
            # ví dụ tiêu chí bạn dùng để đếm:
            ('introduce_to_others', '=', 'Không sẵn lòng'),
        ]
        action['views'] = [(False, 'list'), (False, 'form')]
        return action

    def get_data(self, report_id):
        data = self.calculate_data()
        report_id.nps_report_ids = [(5, 0, 0)] + [(0, 0, vals) for vals in data]

    def calculate_data(self, config=False):
        config = config or self.env['ttb.popup.filtered.nps'].get_last_config()
        branch_ids = config.get_selected_brands()
        Happy = self.env['ttb.happy.call']

        domain = [
            ('state', '=', 'success'),
            ('ttb_branch_id', 'in', branch_ids.ids)
        ]
        if config.date_from:
            domain.append(('execution_date', '>=', config.date_from))
        if config.date_to:
            domain.append(('execution_date', '<=', config.date_to))

        records = Happy.search(domain)

        per_branch = {}
        for rec in records:
            branch_id = rec.ttb_branch_id.id if rec.ttb_branch_id else False
            exp = rec.introduce_to_others

            if not branch_id:
                continue

            if branch_id not in per_branch:
                per_branch[branch_id] = {
                    'branch_id': branch_id,
                    'very_willing': 0,
                    'willing': 0,
                    'consider_passive': 0,
                    'unwilling': 0,
                    'total': 0,
                }
            if exp == 'Rất sẵn lòng':
                per_branch[branch_id]['very_willing'] += 1
            elif exp == 'Sẵn lòng':
                per_branch[branch_id]['willing'] += 1
            elif exp == 'Cân nhắc/ Thụ động':
                per_branch[branch_id]['consider_passive'] += 1
            elif exp == 'Không sẵn lòng':
                per_branch[branch_id]['unwilling'] += 1

            per_branch[branch_id]['total'] += 1

        return list(per_branch.values())
