from odoo import models, fields, api

class ParamMappingLine(models.Model):
    _name = 'param.mapping.line'
    _description = 'Parameter mapping Line'
    _order = 'id'

    key = fields.Char()
    value = fields.Char()
    mapping_value = fields.Char(string='Giá trị tương ứng', help='giá trị tương ứng')
    param_id = fields.Many2one('param.mapping')
