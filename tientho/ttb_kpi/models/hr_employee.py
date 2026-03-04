from odoo import api, fields, models, _
from datetime import date


class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    ttb_branch_id = fields.Many2one(string='Cở sở (bỏ)', comodel_name='ttb.branch')
    ttb_branch_ids = fields.Many2many(string='Cở sở', comodel_name='ttb.branch')
    ttb_area_id = fields.Many2one(string='Khu vực (bỏ)', comodel_name='ttb.area')
    ttb_area_ids = fields.Many2many(string='Khu vực', comodel_name='ttb.area', tracking=True)
    ttb_categ_id = fields.Many2one(string='Quầy (bỏ)', comodel_name='product.category')
    ttb_categ_ids = fields.Many2many(string='Quầy', comodel_name='product.category', domain="[('category_level', '=', 1)]", tracking=True)


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    official_working_date = fields.Date(string="Ngày làm việc chính thức")

    def ttb_prepare_user(self):
        res = super().ttb_prepare_user()
        res['ttb_area_ids'] = self.ttb_area_ids.ids
        res['ttb_categ_ids'] = self.ttb_categ_ids.ids
        res['ttb_branch_ids'] = self.ttb_branch_ids.ids
        return res

    def write(self, vals):
        res = super().write(vals)
        for emp in self:
            if emp.user_id:
                user_vals = {
                    'ttb_area_ids': [(6, 0, emp.ttb_area_ids.ids)],
                    'ttb_categ_ids': [(6, 0, emp.ttb_categ_ids.ids)],
                    'ttb_branch_ids': [(6, 0, emp.ttb_branch_ids.ids)],
                }
                emp.user_id.sudo().write(user_vals)
        return res
    my_branch_only = fields.Boolean(
        string="Chỉ hiện tại KPI",
        compute='_compute_my_branch_only',
        store=False
    )
    date_start = fields.Date(string="Thời gian nghỉ",tracking=True)
    date_end = fields.Date(string="Ngày Kết thúc",tracking=True)
    quit_type = fields.Selection(string="Loại nghỉ", selection=[('sudden_leave','Nghỉ đột xuất'),('planned_leave', 'Nghỉ có báo trước')], tracking=True)
    reason = fields.Text(string="Lý do",tracking=True)
    show_button_hr = fields.Boolean(string='Xem được nút thao tác HR',compute='_compute_show_button_hr')

    def _compute_show_button_hr(self):
        job = self.env.user.employee_id.job_id.name if self.env.user.employee_id else ''
        hr_jobs = [
            'Chuyên viên Phúc lợi và Tiền Lương',
            'Trưởng nhóm Phúc lợi và Tiền lương',
            'Nhân viên Phúc lợi và Tiền Lương',
        ]
        for rec in self:
            rec.show_button_hr = rec.active and (rec.my_branch_only or job in hr_jobs or self.env.user.has_group('base.group_system'))
    def _compute_my_branch_only(self):
        for rec in self:
            rec.my_branch_only = self.env.context.get('my_branch_only', False)

    def change_category_button (self):
        return {
            'name': 'Chuyển quầy',
            'type': 'ir.actions.act_window',
            'res_model': 'change.category.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_model': self._name,
                'default_message': '',
                'default_model_id': self.id,
                'default_ttb_categ_ids': self.ttb_categ_ids.ids,
            }
        }

    def change_area_button(self):
        return {
            'name': 'Chuyển khu vực',
            'type': 'ir.actions.act_window',
            'res_model': 'change.area.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_model': self._name,
                'default_message': '',
                'default_model_id': self.id,
                'default_ttb_area_ids': self.ttb_area_ids.ids,
            }
        }

    def pause_work_button(self):
        return {
            'name': 'Nghỉ tạm thời',
            'type': 'ir.actions.act_window',
            'res_model': 'pause.work.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_model': self._name,
                'default_message': '',
                'default_model_id': self.id,
            }
        }

    def quit_job_button(self):
        return {
            'name': 'Nghỉ việc',
            'type': 'ir.actions.act_window',
            'res_model': 'quit.job.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_model': self._name,
                'default_message': '',
                'default_model_id': self.id,
                'user_id': self.user_id.id
            }
        }

    @api.model
    def web_search_read(self, domain, specification, offset=0, limit=None, order=None, count_limit=None):
        if self.env.context.get('my_branch_only'):
            domain += [('ttb_branch_ids', 'in', self.env.user.employee_id.ttb_branch_ids.ids)]
        return super().web_search_read(
            domain=domain,
            specification=specification,
            offset=offset,
            limit=limit,
            order=order,
            count_limit=count_limit,
        )

    @api.model
    def _cron_archive_employees(self):
        today = date.today()
        # Lưu trữ nếu hôm nay là ngày bắt đầu
        employees_to_archive = self.search([
            ('date_start', '=', today),
            ('active', '=', True)
        ])
        for emp in employees_to_archive:
            emp.active = False
            if emp.user_id:
                emp.user_id.active = False
        # Bỏ lưu trữ nếu hôm nay là ngày kết thúc
        employees_to_unarchive = self.search([
            ('date_end', '=', today),
            ('active', '=', False)
        ])
        for emp in employees_to_unarchive:
            emp.active = True
            if emp.user_id:
                emp.user_id.active = True

