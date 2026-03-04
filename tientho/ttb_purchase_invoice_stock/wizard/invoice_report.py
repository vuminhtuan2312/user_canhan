# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import api, fields, models


class InvoiceReportView(models.TransientModel):
    _name = 'invoice.report.view'
    _rec_name = "name"

    name = fields.Char(string='Tên báo cáo', default='Báo cáo công nợ')
    partner_id = fields.Many2one('res.partner', string='Nhà cung cấp')
    start_date = fields.Date(string='Ngày bắt đầu')
    end_date = fields.Date(string='Ngày kết thúc')

    def generate_report(self):
        generate_report = self.env['cong.no.co.hoa.don']
        adjusted_end_date = None
        if self.end_date:
            adjusted_end_date = (self.end_date + timedelta(days=1)).strftime('%Y%m%d')

        generate_report.refresh_materialized_view_with_conditions(
            partner_id=self.partner_id.id if self.partner_id else None,
            start_date=self.start_date.strftime('%Y%m%d') if self.start_date else None,
            end_date=adjusted_end_date
        )
        view_id = self.env.ref('ttb_purchase_invoice_stock.gen_bao_cao_cong_no_co_hoa_don_view').id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Báo cáo công nợ có hóa đơn',
            'res_model': 'cong.no.co.hoa.don',
            'view_mode': 'list',
            'target': 'current',
            'view_id': view_id,
            'domain': [],
            'context': {},
        }

    def generate_report_no_invoice(self):
        generate_report = self.env['cong.no.khong.hoa.don']
        adjusted_end_date = None
        if self.end_date:
            adjusted_end_date = (self.end_date + timedelta(days=1)).strftime('%Y%m%d')

        generate_report.refresh_materialized_view_with_conditions(
            partner_id=self.partner_id.id if self.partner_id else None,
            start_date=self.start_date.strftime('%Y%m%d') if self.start_date else None,
            end_date=adjusted_end_date
        )
        view_id = self.env.ref('ttb_purchase_invoice_stock.gen_bao_cao_cong_no_khong_co_hoa_don_view').id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Báo cáo công nợ không có hóa đơn',
            'res_model': 'cong.no.khong.hoa.don',
            'view_mode': 'list',
            'target': 'current',
            'view_id': view_id,
            'domain': [],
            'context': {},
        }

