from odoo import models, fields, api


class TtbAuggesDmnx(models.Model):
    _name = 'ttb.augges.dmnx'
    _description = 'Augges DMNX Configuration'

    id_augges = fields.Char(string="Id Augges", required=True)
    ma_ct = fields.Char(string='Ma CT')
    ma_nx = fields.Char(string='Ma NX')
    ten_nx = fields.Char(string='Ten NX')

    no_tk = fields.Char(string='No TK')
    co_tk = fields.Char(string='Co TK')

    active = fields.Boolean(default=True)

