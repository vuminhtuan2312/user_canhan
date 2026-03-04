from odoo import models, fields, api, _


class PosOrder(models.Model):
    _inherit = "pos.order"

    ttb_branch_id = fields.Many2one(string='Cơ sở', comodel_name='ttb.branch', related='config_id.ttb_branch_id', store=True)
