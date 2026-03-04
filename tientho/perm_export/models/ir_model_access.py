# models/ir_model_access.py
from odoo import models, tools, fields, api

class IrModelAccess(models.Model):
    _inherit = 'ir.model.access'

    perm_export = fields.Boolean('Quyền Xuất')

    @tools.ormcache('self.env.uid')
    def _get_allowed_models_export(self):
        self.flush_model()
        self.env.cr.execute("""
            SELECT m.model
              FROM ir_model_access a
              JOIN ir_model m ON m.id = a.model_id
             WHERE a.perm_export AND a.active
               AND (a.group_id IS NULL OR a.group_id IN (
                        SELECT gu.gid FROM res_groups_users_rel gu WHERE gu.uid = %s
                   ))
            GROUP BY m.model
        """, (self.env.uid,))
        return frozenset(row[0] for row in self.env.cr.fetchall())

    def _clear_export_cache(self):
        try:
            self._get_allowed_models_export.clear_cache(self)
        except Exception:
            pass

    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        self.env.invalidate_all()
        self._clear_export_cache()
        return recs

    def write(self, vals):
        res = super().write(vals)
        if any(k in vals for k in ('perm_export', 'active', 'group_id', 'model_id')):
            self.env.invalidate_all()
            self._clear_export_cache()
        return res

    def unlink(self):
        res = super().unlink()
        self.env.invalidate_all()
        self._clear_export_cache()
        return res
