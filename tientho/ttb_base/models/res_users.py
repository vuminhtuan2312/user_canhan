from odoo import api, fields, models, _

class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.depends("login", "name")
    def _compute_display_name(self):
        for rec in self:
            if rec.sudo().job_title:
                rec.display_name = f"[{rec.login}] {rec.name} - {rec.sudo().job_title}"
            else:
                rec.display_name = f"[{rec.login}] {rec.name}"
