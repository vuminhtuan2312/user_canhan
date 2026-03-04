# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class TtbAuditFailWizard(models.TransientModel):
    _name = 'ttb.audit.fail.wizard'
    _description = 'Wizard Nhập lý do Hậu kiểm không đạt'

    task_id = fields.Many2one('ttb.operational.task', string='Công việc', required=True)
    note = fields.Text(string='Ghi chú lỗi', required=True, help="Mô tả chi tiết lỗi sai của nhân viên")

    def action_confirm_fail(self):
        """
        Xác nhận Không đạt. Tạo công việc bổ sung (làm lại) và gán vào rework_task_id.
        Chỉ quản lý ca hoặc quản lý nhà sách được phép.
        """
        self.ensure_one()
        if not self.task_id.can_audit:
            raise UserError(_("Chỉ Quản lý ca hoặc Quản lý nhà sách mới được đánh giá hậu kiểm (Đạt/Không đạt)."))
        task = self.task_id
        rework_name = "[Làm lại] " + (task.name or "")
        rework_vals = {
            'name': rework_name,
            'assignment_id': task.assignment_id.id,
            'template_id': task.template_id.id,
            'area_id': task.area_id.id,
            'employee_id': task.employee_id.id,
            'planned_date_start': task.planned_date_start,
            'planned_date_end': task.planned_date_end,
            'is_rework': True,
            'state': 'waiting',
        }
        rework = self.env['ttb.operational.task'].create(rework_vals)
        task.write({
            'audit_state': 'fail',
            'audit_note': self.note,
            'audit_user_id': self.env.uid,
            'audit_date': fields.Datetime.now(),
            'rework_task_id': rework.id,
        })
        return {'type': 'ir.actions.act_window_close'}
