# Copyright 2018-2022 Sodexis
# License OPL-1 (See LICENSE file for full copyright and licensing details).

from odoo import models, api

class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _notify_thread(self, message, msg_vals=False, **kwargs):
        rdata = super()._notify_thread(message, msg_vals=msg_vals, **kwargs)
        inbox_rdata = []
        email_rdata = []
        for partner_data in rdata:
            if partner_data['notif'] == 'both':
                inbox_partner = partner_data.copy()
                email_partner = partner_data.copy()
                inbox_partner['notif'] = 'inbox'
                email_partner['notif'] = 'email'
                inbox_rdata.append(inbox_partner)
                email_rdata.append(email_partner)
        if inbox_rdata:
            self._notify_thread_by_inbox(message, inbox_rdata, msg_vals=msg_vals, **kwargs)
        if email_rdata:
            email_message = message.copy()
            self._notify_thread_by_email(email_message, email_rdata, msg_vals=msg_vals, **kwargs)
        return rdata
