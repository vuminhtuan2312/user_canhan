# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.osv import expression


class ApplicantGetRefuseReason(models.TransientModel):
    _inherit = 'applicant.get.refuse.reason'

    send_date = fields.Datetime(string='Ngày gửi', default=lambda r: datetime.now() + timedelta(days=1))

    def action_refuse_reason_apply(self):
        self = self.with_context(
                use_schedule = True,
                schedule_date = self.send_date)
        res = super().action_refuse_reason_apply()
        return res
