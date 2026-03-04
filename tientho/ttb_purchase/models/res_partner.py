from odoo import *


class ResPartner(models.Model):
    _inherit = 'res.partner'

    ttb_consign = fields.Boolean(string='Ký gửi', default=False)
    ttb_stock_limit = fields.Float(string='Hạn mức nhập kho vượt nhu cầu', default=0)

    phone = fields.Char(string='Điện thoại', required=True)
    street = fields.Char(string='Đường', required=True)
    street2 = fields.Char(string='Đường 2', required=True)
    city = fields.Char(string='Thành phố', required=True)
    state_id = fields.Many2one(string='Trạng thái', comodel_name='res.country.state', required=True)
    country_id = fields.Many2one(string='Quốc gia', comodel_name='res.country', required=True)


