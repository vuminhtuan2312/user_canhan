from odoo import api, fields, models, _

class TtbPopupFilteredComplain(models.Model):
    _name = 'ttb.popup.filtered.thanphien'
    _inherit = 'ttb.popup.filtered.base'
    _description = 'Lọc báo cáo CRM than phiền'

    report_in_control_complaint_coefficient = fields.Float(string='Hệ số điểm than phiền trong tầm', default=lambda
        self: self._get_default_config().report_in_control_complaint_coefficient)
    report_out_of_control_complaint_multiplier = fields.Float(string='Hệ số nhân than phiền lỗi ngoài tầm',
                                                              default=lambda
                                                                  self: self._get_default_config().report_out_of_control_complaint_multiplier)
    report_in_control_complaint_multiplier = fields.Float(string='Hệ số nhân điểm than phiền trong tầm', default=lambda
        self: self._get_default_config().report_in_control_complaint_multiplier)
    report_heavy_complaint_coefficient = fields.Float(string='Hệ số than phiền lỗi nặng', default=lambda
        self: self._get_default_config().report_heavy_complaint_coefficient)
    report_light_complaint_coefficient = fields.Float(string='Hệ số than phiền lỗi nhẹ', default=lambda
        self: self._get_default_config().report_light_complaint_coefficient)

    def btn_apply_filters(self):
        self.env['ttb.complain.report'].get_data(self.get_report())
