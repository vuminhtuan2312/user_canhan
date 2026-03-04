from odoo import *


class ResUsers(models.Model):
    _inherit = 'res.users'

    ttb_user_template_id = fields.Many2one(string='Mẫu người dùng', domain=lambda self: [('id', '!=', self.id), '|', ('active', '=', False), ('active', '=', True)], comodel_name='res.users')

    @api.model_create_multi
    def create(self, vals_lst):
        for vals in vals_lst:
            if vals.get('ttb_user_template_id'):
                template_user = self.env['res.users'].browse(vals.get('ttb_user_template_id'))
                vals['groups_id'] = [(6, 0, template_user.groups_id.ids)]
        res = super().create(vals_lst)
        for user in res:
            if user.ttb_user_template_id:
                for default in self.env['ir.default'].sudo().search([('user_id', '=', user.ttb_user_template_id.id)]):
                    default.sudo().copy({'user_id': user.id})
        return res

    def write(self, vals):
        pre_user_template = {}
        if vals.get('ttb_user_template_id'):
            pre_user_template = {user: user.ttb_user_template_id.id for user in self}
        res = super().write(vals)
        for user in pre_user_template:
            if user.ttb_user_template_id.id != pre_user_template.get(user):
                user.groups_id = [(6, 0, user.ttb_user_template_id.groups_id.ids)]
                self.env['ir.default'].sudo().search([('user_id', '=', user.id)]).unlink()
                for default in self.env['ir.default'].sudo().search([('user_id', '=', user.ttb_user_template_id.id)]):
                    default.sudo().copy({'user_id': user.id})
        return res

    def toggle_active(self):
        res = super().toggle_active()
        archived = self.filtered(lambda x: not x.active)
        if archived:
            to_delete = self.env['ttb.task.report'].sudo().search([('user_id', 'in', archived.ids), ('state', '=', 'new'), ('kpi_type_id.code', '=', 'CSKH')])
            to_delete.sudo().unlink()
        return res
