from odoo import models, fields, api, _


class PosConfig(models.Model):
    _inherit = 'pos.config'

    ttb_branch_id = fields.Many2one(string='Cơ sở', comodel_name='ttb.branch', related='picking_type_id.warehouse_id.ttb_branch_id')
