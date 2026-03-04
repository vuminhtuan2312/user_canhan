import ast
from odoo import api, fields, models, _

class TtbPopupFilteredNPS(models.Model):
    _name = 'ttb.popup.filtered.nps'
    _inherit = 'ttb.popup.filtered.base'
    _description = 'Lọc báo cáo CRM nps'

    def btn_apply_filters(self):
        self.env['ttb.nps.report'].get_data(self.get_report())
