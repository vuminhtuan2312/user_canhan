from odoo import api, fields, models, _
from odoo.exceptions import UserError

class TtbReportConfig(models.Model):
    _name = 'ttb.report.config'
    _description = 'Cấu hình báo cáo Helpdesk'

    name = fields.Char(default='Cấu hình báo cáo Helpdesk', readonly=True, required=True)

    # Báo cáo CEI
    report_camera_weight = fields.Float(string='Tỷ trọng điểm camera')
    report_csat_weight = fields.Float(string='Tỷ trọng điểm KH hài lòng')
    report_nps_weight = fields.Float(string='Tỷ trọng điểm KH sẵn lòng giới thiệu')
    report_complain_weight = fields.Float(string='Tỷ trọng điểm KH than phiền')

    # Báo cáo than phiền
    report_camera_deduction_coefficient = fields.Float(string='Hệ số điểm trừ camera')
    report_in_control_complaint_coefficient = fields.Float(string='Hệ số điểm than phiền trong tầm')
    report_out_of_control_complaint_multiplier = fields.Float(string='Hệ số nhân than phiền lỗi ngoài tầm')
    report_in_control_complaint_multiplier = fields.Float(string='Hệ số nhân điểm than phiền trong tầm')
    report_heavy_complaint_coefficient = fields.Float(string='Hệ số than phiền lỗi nặng')
    report_light_complaint_coefficient = fields.Float(string='Hệ số than phiền lỗi nhẹ')
    report_in_control_weight = fields.Float(string='Tỷ trọng điểm trong tầm')
    report_out_of_control_weight = fields.Float(string='Tỷ trọng điểm ngoài tầm')

    # Ngày áp dụng
    report_date_from = fields.Date(string='Áp dụng: Từ ngày')
    report_date_to = fields.Date(string='Đến ngày')

    @api.model
    def create(self, vals):
        if self.search_count([]) > 0:
            raise UserError(_('Chỉ có thể có một bản ghi cấu hình.'))
        return super(TtbReportConfig, self).create(vals)

    def get_config(self):
        return self.search([], limit=1)
