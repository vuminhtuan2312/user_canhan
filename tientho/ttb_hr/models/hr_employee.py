from odoo import api, fields, models, _


class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    ttb_code = fields.Char(string='Mã nhân viên')


class HrEmployeePrivate(models.Model):
    _inherit = "hr.employee"
    _parent_name = "parent_id"
    _parent_store = True

    def toggle_active(self):
        res = super().toggle_active()
        for rec in self:
            if rec.user_id.active != rec.active:
                rec.user_id.sudo().toggle_active()
        return res

    parent_path = fields.Char(index=True)
    ttb_code = fields.Char(string='Mã nhân viên', required=True)

    def ttb_prepare_user(self):
        return {
            'name': self.name,
            'login': self.ttb_code,
            'ttb_user_template_id': self.job_id.ttb_user_template_id.id,
            'password': 'hochoilientuc'
        }

    def ttb_create_user(self):
        if self.user_id: return
        vals = self.ttb_prepare_user()
        user = self.env['res.users'].sudo().create(vals)
        self.user_id = user

    @api.depends('name', 'ttb_code')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"[{rec.ttb_code}] {rec.name}" if rec.ttb_code else rec.name


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'
    _parent_name = "parent_id"
    _parent_store = True

    parent_path = fields.Char(index=True)
