from odoo import api, fields, models, _
from odoo.exceptions import UserError


class TTBDescription(models.Model):
    _name = 'ttb.description'
    _description = 'Chủ đề'

    name = fields.Char(string='Vùng')
    type = fields.Char(string='Loại')
