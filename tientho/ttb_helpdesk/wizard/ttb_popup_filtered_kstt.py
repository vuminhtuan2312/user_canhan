import ast
from odoo import api, fields, models, _

class TtbPopupFilteredKSTT(models.Model):
    _name = 'ttb.popup.filtered.kstt'
    _inherit = 'ttb.popup.filtered.base'
    _description = 'Lọc báo cáo CRM kstt'

    def btn_apply_filters(self):
        self.env['ttb.survey.report'].get_data(self.get_report())
