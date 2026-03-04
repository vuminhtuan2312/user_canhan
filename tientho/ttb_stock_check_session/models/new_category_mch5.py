from odoo import fields, models, api

class NewCategoryMch5(models.Model):
    _name = 'new.category.mch5'
    _description = 'MCH5 mới'

    name = fields.Char(string='MCH5 mới')