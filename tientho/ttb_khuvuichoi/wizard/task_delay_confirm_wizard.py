# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta


class TtbTaskDelayConfirmWizard(models.TransientModel):
    _name = 'ttb.task.delay.confirm.wizard'
    _description = 'Wizard Quản lý xác nhận tạm hoãn'

    task_id = fields.Many2one('ttb.operational.task', string='Công việc', required=True)
    
    # Các trường hiển thị lại (Readonly)
    reason_id = fields.Many2one('ttb.pause.reason', string='Lý do nhân viên báo', readonly=True)
    note = fields.Text(string='Ghi chú của nhân viên', readonly=True)
    
    # Trường Quản lý nhập
    delay_until = fields.Datetime(string='Hoãn đến khi', required=True)

    def action_confirm_manager(self):
        self.ensure_one()
        if self.delay_until < fields.Datetime.now():
            raise UserError(_("Thời gian hoãn không hợp lệ. Vui lòng chọn thời gian hoãn lớn hơn thời gian hiện tại."))

        task = self.task_id
        duration = (task.template_id and task.template_id.duration_minutes) or 15
        duration_use = max(duration, 15)
        end_by_delay_calc = self.delay_until + timedelta(minutes=duration_use)
        old_planned_end = task.planned_date_end

        if old_planned_end and end_by_delay_calc < old_planned_end:
            planned_date_end_by_delay = False
        else:
            planned_date_end_by_delay = end_by_delay_calc

        task.write({
            'state': 'delayed',
            'delay_until': self.delay_until,
            'planned_date_end_by_delay': planned_date_end_by_delay,
        })

        task._unlink_subsequent_same_type_in_area()

        if task.employee_id.user_id:
            delay_until_str = fields.Datetime.to_string(self.delay_until) if self.delay_until else ''
            task.activity_schedule(
                act_type_xmlid='mail.mail_activity_data_todo',
                user_id=task.employee_id.user_id.id,
                summary=_('Yêu cầu tạm hoãn của bạn đã được hoãn đến %s', delay_until_str),
                note=_('Công việc: %s', task.name),
            )

        return {'type': 'ir.actions.act_window_close'}
