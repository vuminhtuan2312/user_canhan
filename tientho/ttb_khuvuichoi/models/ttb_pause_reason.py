# -*- coding: utf-8 -*-
from odoo import models, fields

class TtbPauseReason(models.Model):
    _name = 'ttb.pause.reason'
    _description = 'Lý do tạm hoãn'

    name = fields.Char(string='Tên lý do', required=True)
    code = fields.Char(string='Mã lý do')