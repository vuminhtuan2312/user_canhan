from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
from typing import Optional


class VoipCall(models.Model):
    _inherit = "voip.call"

    recording_link = fields.Char(string="File ghi âm", readonly=True)
    ttb_happy_call_id = fields.Many2one('ttb.happy.call', string='Happy Call', readonly=True)
    extension = fields.Char(string="Extension", readonly=True)

    @api.model
    def create_and_format(self, res_id: Optional[int] = None, res_model: Optional[str] = None, **kwargs) -> list:
        if res_id and res_model == 'ttb.happy.call':
            kwargs["ttb_happy_call_id"] = res_id
        kwargs["extension"] = self.env.user.res_users_settings_id.voip_username
        return super().create_and_format(res_id=res_id, res_model=res_model, **kwargs)

    def get_recording_link(self):
        raise UserError('Tính năng đang phát triển')
        for rec in self:
            phone = rec.phone_number
            extension = rec.extension
            date_from = rec.create_date


            rec.recording_link = 'https://vietdialerapi.vietpbx.com/2022/09/27/10/uncompress/8008-20220927104146-+84123123123-1664250106.284.WAV'
