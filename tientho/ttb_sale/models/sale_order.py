from odoo import *


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    ttb_branch_id = fields.Many2one(string='Cơ sở', comodel_name='ttb.branch', required=True)
