import ast
from odoo import api, fields, models, _
from datetime import datetime, timedelta
import pytz

class TtbPopupFilteredCamera(models.Model):
    _name = 'ttb.popup.filtered.camera'
    _inherit = 'ttb.popup.filtered.base'
    _description = 'Lọc báo cáo CRM camera'

    report_camera_deduction_coefficient = fields.Float(string='Hệ số điểm trừ Camera', default=lambda self: self._get_default_config().report_camera_deduction_coefficient)

    def btn_apply_filters(self):
        self.env['ttb.camera.report'].get_data(self.get_report())
