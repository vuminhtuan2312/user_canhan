# python
from odoo import models, fields, _, api
from odoo.exceptions import ValidationError, UserError


class ZNSApiCodeError(models.Model):
    _name = 'zns.api.code.error'
    _description = 'ZNS API Code Error'

    code = fields.Char(string='Mã lỗi', required=True)
    message = fields.Char(string='Nội dung lỗi', required=True)

    @api.model
    def _default_zalo_shop_config_id(self):
        config = self.env['zalo.shop.config'].search([('active', '=', True)], limit=1)
        return config.id or False

    zalo_shop_config_id = fields.Many2one(
        'zalo.shop.config',
        string='Cấu hình shop zalo',
        domain=[('active', '=', True)],
        default=_default_zalo_shop_config_id,
    )
