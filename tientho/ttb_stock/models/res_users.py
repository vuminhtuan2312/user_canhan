from odoo import api, fields, models, _

class ResUsers(models.Model):
    _inherit = 'res.users'

    ttb_branch_ids = fields.Many2many(string='Cơ sở', comodel_name='ttb.branch', required=False)
    ttb_branch_id = fields.Many2one(string='Cơ sở', comodel_name='ttb.branch', required=False)

    @api.model
    def _cron_migrate_branch(self):
        users = self.search([])
        for user in users:
            if user.ttb_branch_id and not user.ttb_branch_ids:
                user.ttb_branch_ids = [(4, user.ttb_branch_id.id)]