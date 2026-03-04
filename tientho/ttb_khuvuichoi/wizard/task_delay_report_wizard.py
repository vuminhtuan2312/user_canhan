# -*- coding: utf-8 -*-
from odoo import models, fields, api

class TtbTaskDelayReportWizard(models.TransientModel):
    _name = 'ttb.task.delay.report.wizard'
    _description = 'Wizard Nhân viên báo cáo tạm hoãn'

    task_id = fields.Many2one('ttb.operational.task', string='Công việc', required=True)
    reason_id = fields.Many2one('ttb.pause.reason', string='Lý do', required=True)
    note = fields.Text(string='Ghi chú chi tiết', required=True)

    def action_submit_delay(self):
        """
        Xử lý khi nhân viên bấm 'Xác nhận'
        """
        self.ensure_one()
        task = self.task_id
        
        # 1. Update trạng thái task
        task.write({
            'state': 'suspended',
            'delay_reason_id': self.reason_id.id,
            'delay_note': self.note
        })
        
        # 2. Gửi Activity cho Quản lý trực tiếp (parent_id) và Quản lý ca (assignment.manager_id)
        activity_type = self.env.ref('mail.mail_activity_data_warning', raise_if_not_found=False)
        activity_type_xmlid = 'mail.mail_activity_data_warning' if activity_type else 'mail.mail_activity_data_todo'
        summary = f'SỰ CỐ: {self.reason_id.name}'
        note = f"Nhân viên {task.employee_id.name} báo cáo: {self.note}. Vui lòng kiểm tra và xác nhận thời gian hoãn."

        # Quản lý trực tiếp
        direct_manager = task.employee_id.parent_id.user_id
        if direct_manager:
            task.activity_schedule(
                activity_type_xmlid,
                user_id=direct_manager.id,
                summary=summary,
                note=note,
            )

        # Quản lý ca (tránh trùng nếu cùng người với quản lý trực tiếp)
        shift_manager = task.assignment_id.manager_id.user_id if task.assignment_id and task.assignment_id.manager_id else None
        if shift_manager and shift_manager.id != (direct_manager.id if direct_manager else None):
            task.activity_schedule(
                activity_type_xmlid,
                user_id=shift_manager.id,
                summary=summary,
                note=note,
            )

        return {'type': 'ir.actions.act_window_close'}
