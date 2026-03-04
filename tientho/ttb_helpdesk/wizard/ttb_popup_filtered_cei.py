import ast
from odoo import api, fields, models, _

class TtbPopupFilteredCEI(models.Model):
    _name = 'ttb.popup.filtered.cei'
    _inherit = 'ttb.popup.filtered.base'
    _description = 'Lọc báo cáo CRM cei'

    report_camera_weight = fields.Float(string='Tỷ trọng Camera',
                                        default=lambda self: self._get_default_config().report_camera_weight)
    report_complain_weight = fields.Float(string='Tỷ trọng điểm KH than phiền',
                                          default=lambda self: self._get_default_config().report_complain_weight)
    report_csat_weight = fields.Float(string='Tỷ trọng điểm KH hài lòng',
                                      default=lambda self: self._get_default_config().report_csat_weight)
    report_nps_weight = fields.Float(string='Tỷ trọng điểm KH sẵn lòng giới thiệu',
                                     default=lambda self: self._get_default_config().report_nps_weight)

    def btn_apply_filters(self):
        self.env['ttb.cei.report'].sudo().get_data(self.get_report())
