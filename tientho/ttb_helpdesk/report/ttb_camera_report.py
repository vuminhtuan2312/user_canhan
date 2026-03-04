# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class TTBCameraReport(models.Model):
    _name = "ttb.camera.report"
    _description = "Thống kê camera"
    _rec_name = 'branch_id'
    _order = 'branch_id desc'

    report_id = fields.Many2one('helpdesk.crm.report')
    branch_id = fields.Many2one('ttb.branch', string='Cơ sở')
    deducted_point = fields.Float(string='Số điểm bị trừ')
    total = fields.Float(string='Điểm total')

    def calculate_data(self, config=False):
        config = config or self.env['ttb.popup.filtered.camera'].get_last_config()
        data = []
        branches = config.get_selected_brands()

        domain_common = []
        if config.date_from:
            domain_common += [('deadline', '>=', config.date_from)]
        if config.date_to:
            domain_common += [('deadline', '<=', config.date_to)]

        for branch in branches:
            tickets = self.env['error.ticket'].search([('branch_id', '=', branch.id)] + domain_common)
            diem_tru = sum(tickets.mapped('deducted_points'))

            report_camera_deduction_coefficient = config.report_camera_deduction_coefficient
            total = (100 - (diem_tru * report_camera_deduction_coefficient)) / 10
            deducted_point = diem_tru
            data.append({
                'branch_id': branch.id,
                'total': total if total > 0 else 0,
                'deducted_point': deducted_point
            })
        return data

    def get_data(self, report_id):
        data = self.calculate_data()
        report_id.camera_report_ids = [(5, 0, 0)] + [(0, 0, vals) for vals in data]
