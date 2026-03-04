# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class HelpdeskCRMreport(models.Model):
    _name = 'helpdesk.crm.report'
    _description = 'Helpdesk CRM Report'
    _order = 'priority, id'

    name = fields.Char(string='Name', default='Báo cáo')

    cei_report_ids = fields.One2many('ttb.cei.report', 'report_id', string='Báo cáo điểm trải nghiệm khách hàng (CEI)', readonly=True)
    camera_report_ids = fields.One2many('ttb.camera.report', 'report_id', string='Thống kê camera', readonly=True)
    complain_report_ids = fields.One2many('ttb.complain.report', 'report_id', string='Báo cáo Thống kê than phiền', readonly=True)
    csat_report_ids = fields.One2many('ttb.csat.report', 'report_id', string='Báo cáo theo câu trả lời của KH - CSAT', readonly=True)
    nps_report_ids = fields.One2many('ttb.nps.report', 'report_id', string='Báo cáo theo câu trả lời của KH - NPS', readonly=True)
    survey_report_ids = fields.One2many('ttb.survey.report', 'report_id', string='Thống kê kết quả theo khảo sát trung tâm', readonly=True)
    kpi_report_ids = fields.One2many('ttb.kpi.report', 'report_id', string='Báo cáo Thống kê theo năng suất của NV CSKH', readonly=True)
    hpc_out_report_ids = fields.One2many('ttb.hpc.out.report', 'report_id', string='[HPC] Khách hàng góp ý ngoài tầm kiểm soát', readonly=True)
    transaction_out_report_ids = fields.One2many('ttb.transaction.out.report', 'report_id', string='[Tương tác] Khách hàng góp ý ngoài tầm kiểm soát', readonly=True)

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)

        defaults['camera_report_ids'] = [(0, 0, vals) for vals in self.env['ttb.camera.report'].calculate_data()]
        defaults['complain_report_ids'] = [(0, 0, vals) for vals in self.env['ttb.complain.report'].calculate_data()]
        defaults['csat_report_ids'] = [(0, 0, vals) for vals in self.env['ttb.csat.report'].calculate_data()]
        defaults['hpc_out_report_ids'] = [(0, 0, vals) for vals in self.env['ttb.hpc.out.report'].calculate_data()]
        defaults['kpi_report_ids'] = [(0, 0, vals) for vals in self.env['ttb.kpi.report'].calculate_data()]
        defaults['nps_report_ids'] = [(0, 0, vals) for vals in self.env['ttb.nps.report'].calculate_data()]
        defaults['survey_report_ids'] = [(0, 0, vals) for vals in self.env['ttb.survey.report'].calculate_data()]
        defaults['transaction_out_report_ids'] = [(0, 0, vals) for vals in self.env['ttb.transaction.out.report'].calculate_data()]
        # báo cáo này để cuối
        defaults['cei_report_ids'] = [(0, 0, vals) for vals in self.env['ttb.cei.report'].calculate_data()]

        return defaults

    def btn_open_filtter_camera(self):
        return self.env['ttb.popup.filtered.camera'].action_popup()

    def btn_open_filtter_thanphien(self):
        return self.env['ttb.popup.filtered.thanphien'].action_popup()

    def btn_open_filtter_cei(self):
        return self.env['ttb.popup.filtered.cei'].action_popup()

    def btn_open_filtter_csat(self):
        return self.env['ttb.popup.filtered.csat'].action_popup()

    def btn_open_filtter_nps(self):
        return self.env['ttb.popup.filtered.nps'].action_popup()

    def btn_open_filtter_kstt(self):
        return self.env['ttb.popup.filtered.kstt'].action_popup()

    def btn_open_filtter_hpc(self):
        return self.env['ttb.popup.filtered.hpc'].action_popup()

    def btn_open_filtter_dltt(self):
        return self.env['ttb.popup.filtered.dltt'].action_popup()

    def btn_open_filtter_cskh(self):
        return self.env['ttb.popup.filtered.cskh'].action_popup()
