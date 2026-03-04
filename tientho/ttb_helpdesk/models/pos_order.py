from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError

from email.policy import default
import re

class POSOrder(models.Model):
    _inherit = "pos.order"

    total_accumulated_points = fields.Float(string='Tổng điểm tích lũy')
    redeemed_accumulated_points = fields.Float(string='Điểm tích lũy SD')
    remaining_accumulated_points = fields.Float(string='Điểm tích lũy còn')

    mobile_masked = fields.Char(compute="_compute_mobile_masked", store=False)

    @api.depends('mobile')
    def _compute_mobile_masked(self):
        is_cskh = self.env.user.has_group('ttb_kpi.group_ttb_kpi_nv_cskh')
        is_cv_vhkd = self.env.user.has_group('ttb_kpi.group_cv_vhkd')
        is_warehouse_director = self.env.user.has_group('ttb_kpi.group_ttb_kpi_warehouse_director')
        is_asm = self.env.user.has_group('ttb_kpi.group_ttb_kpi_asm')
        for rec in self:
            if rec.mobile:
                if not rec.id:
                    rec.mobile_masked = rec.mobile
                    continue

                if is_cskh or is_cv_vhkd or is_warehouse_director or is_asm:
                    clean_mobile = re.sub(r'\D', '', rec.mobile)
                    if len(clean_mobile) > 3:
                        rec.mobile_masked = '*' * (len(clean_mobile) - 3) + clean_mobile[-3:]
                    else:
                        rec.mobile_masked = '*' * len(clean_mobile)
                else:
                    rec.mobile_masked = rec.mobile
            else:
                rec.mobile_masked = ""
