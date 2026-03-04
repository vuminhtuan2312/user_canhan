# -*- coding: utf-8 -*-
from odoo import models, fields, api

class TtbTaskDelayWizard(models.TransientModel):
    _name = 'ttb.task.delay.wizard'
    _description = 'Wizard báo cáo tạm hoãn'

    task_id = fields.Many2one('ttb.operational.task', string='Công việc', required=True)
    reason_id = fields.Many2one('ttb.pause.reason', string='Lý do', required=True)
    note = fields.Text(string='Ghi chú chi tiết', required=True)

    def action_confirm_delay(self):
        """
        Xử lý khi nhân viên bấm 'Xác nhận' trên popup
        """
        self.ensure_one()
        task = self.task_id
        
        # 1. Update thông tin vào task
        task.write({
            'state': 'delayed',
            'delay_reason_id': self.reason_id.id,
            'delay_note': self.note
        })
        
        # 2. Gửi thông báo (Activity) cho Quản lý trực tiếp của nhân viên
        if task.employee_id.parent_id:
            task.activity_schedule(
                'mail.mail_activity_data_warning',
                user_id=task.employee_id.parent_id.user_id.id,
                note=f"Nhân viên {task.employee_id.name} báo cáo tạm hoãn việc: {task.name}. Lý do: {self.reason_id.name} - {self.note}",
                summary='Báo cáo sự cố vận hành'
            )
            
        return {'type': 'ir.actions.act_window_close'}
