from odoo import models, fields, api

class SeasonType(models.Model):
    _name = 'season.type'
    _description = 'Loại thời vụ'


    name = fields.Char(string='Tên mùa vụ', required=True)