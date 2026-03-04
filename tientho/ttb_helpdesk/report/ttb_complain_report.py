# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class TTBComplainReport(models.Model):
    _name = "ttb.complain.report"
    _description = "Báo cáo Thống kê than phiền"
    _rec_name = 'branch_id'
    _order = 'branch_id desc'

    report_id = fields.Many2one('helpdesk.crm.report')
    branch_id = fields.Many2one('ttb.branch', string='Cơ sở')
    total_partner = fields.Integer(string='SLKH tham gia khảo sát')
    in_control = fields.Integer(string='SL Trong tầm')
    out_control = fields.Integer(string='SL ngoài tầm')
    out_control_error = fields.Integer(string='SL ngoài tầm tính lỗi')
    out_control_no_error = fields.Integer(string='SL ngoài tầm ko tính lỗi')
    out_control_heavy_error = fields.Integer(string='SL ngoài tầm lỗi nặng')
    out_control_light_error = fields.Integer(string='SL ngoài tầm lỗi nhẹ')
    in_control_score = fields.Float(string='Điểm trong tầm')
    out_control_score = fields.Float(string='Điểm ngoài tầm')
    complain_score = fields.Float(string='Điểm than phiền (final)')

    # def _query(self):
    #     return f"""
    #     select id,
    #     id as branch_id,
    #     0 as total_partner,
    #     0 as in_control,
    #     0 as out_control,
    #     0 as out_control_error,
    #     0 as out_control_no_error,
    #     0 as out_control_heavy_error,
    #     0 as out_control_light_error,
    #     0 as in_control_score,
    #     0 as out_control_score,
    #     0 as complain_score
    #     from ttb_branch
    #     --where has_report = true
    #     """
    # 
    # @property
    # def _table_query(self):
    #     return self._query()

    def tinh_so_luong_trong_va_ngoai_tam(self, sl_ticket, sl_tham_gia_khao_sat):
        sluong_in = 0
        sluong_out = 0

        chu_de = self.env.ref('ttb_helpdesk.ttb_description_under_control_data').id
        for rec in sl_ticket:
            if chu_de in rec.ttb_description_ids.ids:
                sluong_in += len(rec.under_control_content_ids) if rec.under_control_content_ids else 0
        for rec in sl_tham_gia_khao_sat:
            sluong_out += len(rec.out_control_content_ids) if rec.out_control_content_ids else 0
        return sluong_in, sluong_out

    def tinh_so_luong_ngoai_tam_tinh_loi(self, sl_hthanh_khao_sat, transactions):
        sl_call = 0
        for rec in sl_hthanh_khao_sat:
            for line in rec.out_control_content_ids:
                sl_call += 1 if line.level in ('Nặng', 'Nhẹ') else 0
        sl_transaction = 0
        for rec in transactions:
            for line in rec.out_control_content_ids:
                sl_transaction += 1 if line.level in ('Nặng', 'Nhẹ') else 0
        return (sl_call + sl_transaction)

    def tinh_so_luong_ngoai_tam_khong_tinh_loi(self, sl_hthanh_khao_sat, transactions):
        sl_call = 0
        for rec in sl_hthanh_khao_sat:
            for line in rec.out_control_content_ids:
                sl_call += 1 if line.level == 'Không tính lỗi' else 0
        sl_transaction = 0
        for rec in transactions:
            for line in rec.out_control_content_ids:
                sl_transaction += 1 if line.level == 'Không tính lỗi' else 0
        return (sl_call + sl_transaction)

    def tinh_so_luong_ngoai_tam_loi_nang_nhe(self, sl_hthanh_khao_sat, sl_transaction):
        sl_call_nang = 0
        sl_call_nhe = 0
        sl_transaction_nang = 0
        sl_transaction_nhe = 0
        if sl_hthanh_khao_sat:
            for rec in sl_hthanh_khao_sat:
                if rec.out_control_content_ids:
                    for line in rec.out_control_content_ids:
                        sl_call_nang += 1 if line.level == 'Nặng' else 0
                        sl_call_nhe += 1 if line.level == 'Nhẹ' else 0
        for rec in sl_transaction:
            for line in rec.out_control_content_ids:
                sl_transaction_nang += 1 if line.level == 'Nặng' else 0
                sl_transaction_nhe += 1 if line.level == 'Nhẹ' else 0
        return (sl_call_nang + sl_transaction_nang), (sl_call_nhe+ sl_transaction_nhe)

    def calculate_data(self, config=False):
        config = config or self.env['ttb.popup.filtered.thanphien'].get_last_config()
        return self._calculate_data(config.report_in_control_complaint_coefficient,
                                    config.report_heavy_complaint_coefficient,
                                    config.report_light_complaint_coefficient,
                                    config.report_out_of_control_complaint_multiplier,
                                    config.report_in_control_complaint_multiplier,
                                    config.date_from,
                                    config.date_to,
                                    config.get_selected_brands()
                                    )


    def _calculate_data(self, ts_than_phien_trong_tam, hs_nang, hs_nhe, hs_ngoai_tam, hs_trong_tam, start_date, end_date, branch_ids):
        data = []
        
        domain_happy_call = []
        domain_ticket = []
        domain_transaction = []
        if start_date:
            domain_happy_call += [('execution_date', '>=', start_date)]
            domain_ticket += [('report_date', '>=', start_date)]
            domain_transaction += [('report_date', '>=', start_date)]
        if end_date:
            domain_happy_call += [('execution_date', '<=', end_date)]
            domain_ticket += [('report_date', '<=', end_date)]
            domain_transaction += [('report_date', '<=', end_date)]
        
        for item in branch_ids:
            domain_common = [('ttb_branch_id', '=', item.id)]
            sl_tham_gia_khao_sat = self.env['ttb.happy.call'].search(domain_common + domain_happy_call)
            sl_ticket = self.env['helpdesk.ticket'].search(domain_common + domain_ticket)
            sl_transaction = self.env['ttb.transaction'].search(domain_common + domain_transaction)

            sl_hthanh_khao_sat = sl_tham_gia_khao_sat.filtered(lambda x: x.state == 'success')
            sl_trong_tam, sl_ngoai_tam_call = self.tinh_so_luong_trong_va_ngoai_tam(sl_ticket, sl_hthanh_khao_sat)

            if sl_transaction:
                sl_ngoai_tam_transaction = sum(len(rec.out_control_content_ids) for rec in sl_transaction)
            else:
                sl_ngoai_tam_transaction = 0
            sl_ngoai_tam = sl_ngoai_tam_call + sl_ngoai_tam_transaction
            sl_ngoai_tam_tinh_loi = self.tinh_so_luong_ngoai_tam_tinh_loi(sl_hthanh_khao_sat, sl_transaction)
            sl_ngoai_tam_khong_tinh_loi = self.tinh_so_luong_ngoai_tam_khong_tinh_loi(sl_hthanh_khao_sat,
                                                                                      sl_transaction)
            sl_ngoai_tam_loi_nang, sl_ngoai_tam_loi_nhe = self.tinh_so_luong_ngoai_tam_loi_nang_nhe(sl_hthanh_khao_sat,
                                                                                                    sl_transaction)
            if len(sl_hthanh_khao_sat) > 0:
                diem_trong_tam = (1 - (sl_trong_tam * ts_than_phien_trong_tam / len(sl_hthanh_khao_sat))) * hs_trong_tam
                diem_ngoai_tam = (1 - ((sl_ngoai_tam_loi_nang * hs_nang + sl_ngoai_tam_loi_nhe * hs_nhe) / len(sl_hthanh_khao_sat))) * hs_ngoai_tam
            else:
                diem_trong_tam = 0
                diem_ngoai_tam = 0
            diem_than_phien = 0.8 * diem_trong_tam + 0.2 * diem_ngoai_tam

            data.append({
                'branch_id': item.id,
                'total_partner': len(sl_hthanh_khao_sat),
                'in_control': sl_trong_tam,
                'out_control': sl_ngoai_tam,
                'out_control_error': sl_ngoai_tam_tinh_loi,
                'out_control_no_error': sl_ngoai_tam_khong_tinh_loi,
                'out_control_heavy_error': sl_ngoai_tam_loi_nang,
                'out_control_light_error': sl_ngoai_tam_loi_nhe,
                'in_control_score': diem_trong_tam,
                'out_control_score': diem_ngoai_tam,
                'complain_score': diem_than_phien
            })
        return data

    def get_data(self, report_id):
        data = self.calculate_data()
        report_id.complain_report_ids = [(5, 0, 0)] + [(0, 0, vals) for vals in data]
