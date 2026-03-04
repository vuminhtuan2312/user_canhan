from odoo import api, fields, models, _


class TtbArea(models.Model):
    _name = 'ttb.area'
    _description = 'Khu vực'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Tên khu vực', required=True)
