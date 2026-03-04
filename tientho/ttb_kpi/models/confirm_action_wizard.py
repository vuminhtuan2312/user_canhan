from datetime import date, timedelta
from odoo import models, fields, api
from odoo.exceptions import UserError

class ConfirmActionWizard(models.TransientModel):
    _name = 'reopen.approval.wizard'
    _description = 'Confirm Action Wizard'

    approver_id = fields.Many2many('res.users', string='Người dùng', required=True)

    def action_confirm(self):
        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get('active_ids')
        if not active_model or not active_ids:
            raise UserError("Không tìm thấy dữ liệu nguồn để cập nhật.")
        model = self.env[active_model]
        records = model.browse(active_ids).sudo()
        for rec in records:
            rec.write({
                'state': 'awaiting_approval',
                'approver_ids': self.approver_id.ids,
            })
            rec.approver_ids.unlink()
            for user in self.approver_id:
                self.env['ttb.task.report.approver'].create({
                    'report_id': rec.id,
                    'user_id': user.id,
                    'state': 'waiting',
                })
            if not rec.approver_ids:
                raise UserError("Trường người được đánh giá đang không được điền")
            rec.message_notify(
                subject="Phiếu KPI cần duyệt lại",
                body="Bạn vừa được giao duyệt lại phiếu KPI.",
                partner_ids=self.approver_id.mapped('partner_id.id'),
                email_layout_xmlid='mail.mail_notification_layout',
                model_description='Đánh giá nhiệm vụ',
            )

        return {'type': 'ir.actions.act_window_close'}

    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}

class ChangeCategoryWizard(models.Model):
    _name = 'change.category.wizard'
    _description = 'Change Category Wizard'

    ttb_categ_ids=fields.Many2many(string='Quầy', comodel_name='product.category', required=True, default=lambda self: self.env.context.get('default_ttb_categ_ids',[]))

    def action_confirm(self):
        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get('active_ids')
        if not active_model or not active_ids:
            raise UserError("Không tìm thấy dữ liệu nguồn để cập nhật.")
        model = self.env[active_model]
        records = model.browse(active_ids).sudo()
        for rec in records:
            rec.write({
                'ttb_categ_ids': [(6, 0, self.ttb_categ_ids.ids)],
            })
        return {'type': 'ir.actions.act_window_close'}

    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}

class ChangeAreaWizard(models.Model):
    _name = 'change.area.wizard'
    _description = 'Change Area Wizard'

    ttb_area_ids=fields.Many2many(string='Khu vực', comodel_name='ttb.area', required=True, default=lambda self: self.env.context.get('default_ttb_area_ids',[]))

    def action_confirm(self):
        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get('active_ids')
        if not active_model or not active_ids:
            raise UserError("Không tìm thấy dữ liệu nguồn để cập nhật.")
        model = self.env[active_model]
        records = model.browse(active_ids).sudo()
        for rec in records:
            rec.write({
                'ttb_area_ids': [(6, 0, self.ttb_area_ids.ids)],
            })
        return {'type': 'ir.actions.act_window_close'}

    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}

class PauseWorkWizard(models.Model):
    _name = 'pause.work.wizard'
    _description = 'Pause Work Wizard'

    date_start = fields.Date(string="Thời gian nghỉ việc", required=True, default=lambda self: date.today())
    date_end = fields.Date(string="Ngày Kết thúc", required=True)

    @api.constrains('date_start', 'date_end')
    def _check_date_range(self):
        for record in self:
            if record.date_end < record.date_start:
                raise ValidationError("End Date must be after Start Date.")

    def action_confirm(self):
        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get('active_ids')
        if not active_model or not active_ids:
            raise UserError("Không tìm thấy dữ liệu nguồn để cập nhật.")
        model = self.env[active_model]
        records = model.browse(active_ids).sudo()
        for rec in records:
            rec.write({
                'date_start': self.date_start,
                'date_end': self.date_end,
            })
        return {'type': 'ir.actions.act_window_close'}

    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}

class QuitJobWizard(models.Model):
    _name = 'quit.job.wizard'
    _description = 'Quit Job Wizard'

    quit_type = fields.Selection(string="Loại nghỉ", selection=[('sudden_leave','Nghỉ đột xuất'),('planned_leave', 'Nghỉ có báo trước')], required=True)
    reason = fields.Text(string="Lý do")

    def action_confirm(self):
        today = date.today()
        first_day_of_month = today.replace(day=1)
        next_month = (first_day_of_month.replace(day=28) + timedelta(days=4)).replace(day=1)
        last_day_of_month = next_month - timedelta(days=1)
        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get('active_ids')
        user_id = self.env.context.get('user_id')
        if not active_model or not active_ids:
            raise UserError(_("Không tìm thấy dữ liệu nguồn để cập nhật."))
        employees = self.env[active_model].browse(active_ids).sudo()
        task_model = self.env['ttb.task.report']
        task_kpi_model = self.env['ttb.task.report.kpi']
        result_kpi = self.env['ttb.kpi.result']
        result_line_kpi = self.env['ttb.kpi.result.line']
        for emp in employees:
            if self.quit_type == 'sudden_leave':
                if not self.reason:
                    raise UserError("Vui lòng nhập lý do khi nghỉ đột xuất.")
                lines = task_model.search([('user_id', '=', user_id),('state','=','done')])
                # Xóa phiếu mới
                task_report = task_model.sudo().search([('user_id', '=', user_id), ('state', '=', 'new')])
                task_report.unlink()

                for line in lines:
                    line.write({'average_rate_report': 0})
                kpi = task_kpi_model.search([('user_id','=',user_id),('state','=','done')])
                for detail in kpi:
                    detail.write({'average_rate':0})
                result = result_kpi.search([('user_id','=',user_id),('date_from','>=',first_day_of_month),('date_to','<=',last_day_of_month)])
                for res in result:
                    res.write({'score':0})
                result_line = result_line_kpi.search([('user_id', '=', user_id), ('date_from', '>=', first_day_of_month),
                                            ('date_from', '<=', last_day_of_month)])
                for res in result_line:
                    res.write({'score': 0})
            elif self.quit_type == 'planned_leave':
                lines = task_model.sudo().search([('user_id', '=', user_id), ('state', '=', 'new')])
                lines.unlink()
            emp.sudo().write({
                'active': False,
                'quit_type': self.quit_type,
                'reason': self.reason if self.reason else '',
            })
            if emp.user_id:
                emp.user_id.sudo().write({
                    'active': False,
                })
        return {'type': 'ir.actions.act_window_close'}
    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}
