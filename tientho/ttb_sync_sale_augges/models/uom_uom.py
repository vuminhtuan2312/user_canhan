from odoo import models, fields, api, _


class UoM(models.Model):
    _inherit = 'uom.uom'
    _description = 'Product Unit of Measure'

    id_augges = fields.Integer(string='ID Augges')
    code_augges = fields.Char(string='Mã đơn vị tính')
