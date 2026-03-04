# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class TTBTransactionOutReport(models.Model):
    _name = "ttb.transaction.out.report"
    _description = "[Tương tác] Khách hàng góp ý ngoài tầm kiểm soát"
    _rec_name = 'branch_id'
    _order = 'branch_id desc'

    report_id = fields.Many2one('helpdesk.crm.report')
    branch_id = fields.Many2one('ttb.branch', string='Cơ sở')
    ttb_related_content_id = fields.Many2one('ttb.related.content', string='Nội dung liên quan')
    total = fields.Integer(string='Tổng')

    def get_data(self, report_id):
        data = self.calculate_data()
        report_id.transaction_out_report_ids = [(5, 0, 0)] + [(0, 0, vals) for vals in data]

    def calculate_data(self, config=False):
        config = config or self.env['ttb.popup.filtered.dltt'].get_last_config()
        return self._get_data_transaction_out_report(config.date_from, config.date_to, config.get_selected_brands(),
                                                     config.related_content_ids, config.level)

    def _get_data_transaction_out_report(self, start_date, end_date, branch_ids, related_content_ids, level):
        domain = [('ttb_branch_id', 'in', branch_ids.ids)]
        if start_date:
            domain.append(('report_date', '>=', start_date))
        if end_date:
            domain.append(('report_date', '<=', end_date))

        sl_tham_gia_khao_sat = self.env['ttb.transaction'].search(domain)

        counter = {}
        for rec in sl_tham_gia_khao_sat:
            branch_id = rec.ttb_branch_id.id if rec.ttb_branch_id else False
            if not branch_id:
                continue

            for content in rec.out_control_content_ids:
                key = (branch_id, content.id)
                if key not in counter:
                    counter[key] = {
                        'branch_id': branch_id,
                        'ttb_related_content_id': content.id,
                        'total': 0,
                    }
                if not related_content_ids and not level:
                    counter[key]['total'] += 1
                elif related_content_ids and level:
                    counter[key]['total'] += 1 if (content.id in related_content_ids.ids and content.level == level) else 0
                elif related_content_ids :
                    counter[key]['total'] += 1 if content.id in related_content_ids.ids else 0
                elif level:
                    counter[key]['total'] += 1 if content.level == level else 0

        result = list(counter.values())
        return result
