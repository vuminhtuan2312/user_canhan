from odoo import api, fields, models, _


class ResUsers(models.Model):
    _inherit = 'res.users'

    ttb_area_id = fields.Many2one(string='Khu vực', comodel_name='ttb.area')
    ttb_categ_id = fields.Many2one(string='Quầy', comodel_name='product.category', domain="[('category_level', '=', 1)]")

    ttb_area_ids = fields.Many2many(string='Khu vực', comodel_name='ttb.area')
    ttb_categ_ids = fields.Many2many(string='Quầy', comodel_name='product.category', domain="[('category_level', '=', 1)]")

    ttb_user_group = fields.Integer(
        string='Nhóm Task Report',
        help='Nhóm 1-4 cho việc xoay vòng tạo task report',
        default=1
    )
    @api.model
    def _cron_migrate_data(self):
        users = self.search([])
        for user in users:
            if user.ttb_area_id and not user.ttb_area_ids:
                user.ttb_area_ids = [(4, user.ttb_area_id.id)]
            if user.ttb_categ_id and not user.ttb_categ_ids:
                user.ttb_categ_ids = [(4, user.ttb_categ_id.id)]

    @api.model
    def create(self, vals):
        """Tự động phân nhóm cho nhân viên mới"""
        user = super(ResUsers, self).create(vals)

        if user.ttb_branch_ids:
            task_report_obj = self.env['ttb.task.report']
            assigned_group = task_report_obj._assign_user_to_group(user.id)
            user.sudo().write({'ttb_user_group': assigned_group})
        return user