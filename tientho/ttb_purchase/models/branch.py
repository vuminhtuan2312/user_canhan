from odoo import *


class Branch(models.Model):
    _inherit = 'ttb.branch'

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        if self._context.get('show_branch'):
            domain = [('id', 'in', self._context.get('show_branch'))]
        return super().search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    def _compute_display_name(self):
        if self._context.get('show_branch'):
            for rec in self:
                rec.display_name = rec.code or rec.name
        else:
            super()._compute_display_name()
