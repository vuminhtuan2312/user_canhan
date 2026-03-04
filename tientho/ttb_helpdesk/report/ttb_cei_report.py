# Part of Odoo. See LICENSE file for full copyright and licensing details.
import math
from odoo import api, fields, models


class TTBCEIReport(models.Model):
    _name = "ttb.cei.report"
    _description = "Báo cáo điểm trải nghiệm khách hàng (CEI)"
    _rec_name = 'branch_id'
    _order = 'cei desc'

    report_id = fields.Many2one('helpdesk.crm.report')
    branch_id = fields.Many2one('ttb.branch', string='Cơ sở')
    top = fields.Char(string='Top')
    cei = fields.Float(string='CEI')
    camera = fields.Float(string='Camera')
    complain = fields.Float(string='Than phiền')
    csat = fields.Float(string='CSAT')
    nps = fields.Float(string='NPS')

    def get_data(self, report_id):
        data = self.calculate_data()
        report_id.cei_report_ids = [(5, 0, 0)] + [(0, 0, vals) for vals in data]

    def calculate_data(self, config=False):
        config = config or self.env['ttb.popup.filtered.cei'].get_last_config()
        branches = config.get_selected_brands(full=True)

        camera_popup_model = self.env['ttb.popup.filtered.camera']
        camera_config = camera_popup_model.get_last_config()
        camera_config.write({
            'branch_ids': [(6, 0, branches.ids)],
            'date_filter': config.date_filter,
            'date_from': config.date_from,
            'date_to': config.date_to,
        })
        camera_data = self.env['ttb.camera.report'].calculate_data(camera_config)
        all_camera_data = {d['branch_id']: d['total'] for d in camera_data}


        complain_popup_model = self.env['ttb.popup.filtered.thanphien']
        complain_config = complain_popup_model.get_last_config()
        complain_config.write({
            'branch_ids': [(6, 0, branches.ids)],
            'date_filter': config.date_filter,
            'date_from': config.date_from,
            'date_to': config.date_to,
        })
        complain_data = self.env['ttb.complain.report'].calculate_data(complain_config)
        all_complain_data = {d['branch_id']: d['complain_score'] for d in complain_data}

        domain_common = []
        if config.date_from:
            domain_common += [('execution_date', '>=', config.date_from)]
        if config.date_to:
            domain_common += [('execution_date', '<=', config.date_to)]
        results = []
        for branch in branches:

            domain = [('ttb_branch_id', '=', branch.id), ('state', '=', 'success')] + domain_common
            happy_calls_success = self.env['ttb.happy.call'].search(domain)
            total_happy_calls_success = len(happy_calls_success)

            camera_score = all_camera_data.get(branch.id, 0)
            complain_score = all_complain_data.get(branch.id, 0)

            csat_score = 0
            if total_happy_calls_success > 0:
                satisfied_count = len(
                    happy_calls_success.filtered(lambda r: r.shopping_experience in ['Rất hài lòng', 'Hài lòng']))
                csat_score = (satisfied_count / total_happy_calls_success) * 10

            nps_score = 0
            if total_happy_calls_success > 0:
                promoters = len(happy_calls_success.filtered(
                    lambda r: r.introduce_to_others in ['Rất sẵn lòng', 'Sẵn lòng']))
                detractors = len(
                    happy_calls_success.filtered(lambda r: r.introduce_to_others == 'Không sẵn lòng'))

                promoter_ratio = promoters / total_happy_calls_success
                detractor_ratio = detractors / total_happy_calls_success
                nps_score = (promoter_ratio - detractor_ratio) * 10

            report_camera_weight = config.report_camera_weight
            report_csat_weight = config.report_csat_weight
            report_nps_weight = config.report_nps_weight
            report_complain_weight = config.report_complain_weight

            cei = (camera_score * report_camera_weight) + \
                  (csat_score * report_csat_weight) + \
                  (nps_score * report_nps_weight) + \
                  (complain_score * report_complain_weight)

            results.append({
                'branch_id': branch.id,
                'cei': cei,
                'camera': camera_score,
                'complain': complain_score,
                'csat': csat_score,
                'nps': nps_score,
            })

        if not results:
            return []

        # Sort results by CEI score and determine top 20%
        sorted_results = sorted(results, key=lambda r: r.get('cei', 0.0), reverse=True)
        n = len(sorted_results)

        top_n = min(2, n)  # 2 cơ sở đứng đầu
        bottom_n = min(2, n - top_n) if n > 2 else 0  # 2 cơ sở cuối

        for i, res in enumerate(sorted_results):
            if i < top_n:
                res['top'] = '20%'  # theo yêu cầu hiển thị text '20%'
            elif i >= n - bottom_n:
                res['top'] = 'Bottom'
            else:
                res['top'] = 'Middle'
        return sorted_results
