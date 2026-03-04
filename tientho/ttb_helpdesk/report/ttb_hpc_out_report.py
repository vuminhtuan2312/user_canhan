# Part of Odoo. See LICENSE file for full copyright and licensing details.
from networkx import config
from odoo import api, fields, models


class TTBHpcOutReport(models.Model):
    _name = "ttb.hpc.out.report"
    _description = "[HPC] Khách hàng góp ý ngoài tầm kiểm soát"
    _auto = True
    _rec_name = 'branch_id'
    _order = 'branch_id desc'

    report_id = fields.Many2one('helpdesk.crm.report')
    branch_id = fields.Many2one('ttb.branch', string='Cơ sở')
    ttb_related_content_id = fields.Many2one('ttb.related.content', string='Nội dung liên quan')
    total = fields.Integer(string='Tổng')

    def get_data(self, report_id):
        data = self.calculate_data()
        report_id.hpc_out_report_ids = [(5, 0, 0)] + [(0, 0, vals) for vals in data]

    def calculate_data(self, config=False):
        config = config or self.env['ttb.popup.filtered.hpc'].get_last_config()
        counter = {}
        branch_ids = config.get_selected_brands()
        related_content_ids = config.related_content_ids
        domain = [('ttb_branch_id', 'in', branch_ids.ids)]
        if config.date_from:
            domain.append(('execution_date', '>=', config.date_from))
        if config.date_to:
            domain.append(('execution_date', '<=', config.date_to))
        if related_content_ids:
            domain.append(('out_control_content_ids', '>=', related_content_ids.ids))
        records = self.env['ttb.happy.call'].search(domain)
        for rec in records:
            branch_id = rec.ttb_branch_id.id if rec.ttb_branch_id else False
            if not branch_id:
                continue

            for content in rec.out_control_content_ids:
                key = (branch_id, content.id)
                if key not in counter:
                    counter[key] = {
                        'branch_id': branch_id,
                        'ttb_related_content_id': content.id,
                        'content_name': content.name,  # thêm tên để sắp xếp
                        'total': 0,
                    }
                counter[key]['total'] += 1

        result = list(counter.values())
        result.sort(key=lambda x: x['content_name'])
        # loại bỏ content_name khỏi kết quả
        for r in result:
            r.pop('content_name', None)
        return result
