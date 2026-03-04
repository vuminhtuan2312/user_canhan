import ast
from odoo import api, fields, models, _

class TtbPopupFilteredCSAT(models.Model):
    _name = 'ttb.popup.filtered.csat'
    _inherit = 'ttb.popup.filtered.base'
    _description = 'Lọc báo cáo CRM csat'


    def btn_apply_filters(self):
        self.env['ttb.csat.report'].get_data(self.get_report())
