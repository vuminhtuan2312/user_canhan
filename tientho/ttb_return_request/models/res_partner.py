from odoo import models, fields, api
from odoo.exceptions import UserError

class ResPartner(models.Model):
    _inherit = 'res.partner'

    ttb_categ_ids = fields.Many2many(string='Quầy', comodel_name='product.category', domain="[('category_level', '=', 1)]", tracking=True)
