from odoo import models, api

class ResUsers(models.Model):
    _inherit = 'res.users'

    def write(self, vals):
        res = super().write(vals)
        if 'ttb_branch_ids' in vals:
            self.clear_caches()

        return res