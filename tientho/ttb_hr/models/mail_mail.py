# Trong mail_mail.py
from odoo import api, fields, models


class MailMail(models.Model):
    _inherit = 'mail.mail'

    def create(self, vals):
        # Lấy context
        schedule_date = self.env.context.get('schedule_date')
        use_schedule = self.env.context.get('use_schedule')

        if use_schedule and schedule_date:
            # Gán scheduled_date nếu không được thiết lập
            if not vals.get('scheduled_date'):
                vals['scheduled_date'] = schedule_date

        return super().create(vals)
