from odoo import models, fields, api
from odoo.exceptions import UserError

class MyTask(models.Model):
    _name = 'my.task'
    _description = 'Công việc của tôi'

    kpi_type_id = fields.Many2one(string='Loại KPI', comodel_name='ttb.kpi.type', related='task_report_line_id.kpi_type_id', store=True)
    task_report_id = fields.Many2one(string='Mã phiếu đánh giá', comodel_name='ttb.task.report', related='task_report_line_id.report_id', store=True)
    name = fields.Text(string='Nhiệm vụ', related='task_report_line_id.template_line_id.name', store=True)
    requirement = fields.Text(string='Yêu cầu', related='task_report_line_id.requirement', store=True)
    image_ids = fields.Many2many(string='Hình ảnh', related='task_report_line_id.image_ids')
    solution_plan = fields.Char(string='Phương án xử lý', related='task_report_line_id.solution_plan', store=True)
    urgency_level = fields.Selection(string='Mức độ gấp', related='task_report_line_id.urgency_level', store=True)
    processor_id = fields.Many2one('res.users', string='Người xử lý', related='task_report_line_id.processor_id', store=True)
    process_status = fields.Selection(string='Trạng thái xử lý', related='task_report_line_id.process_status', store=True)
    processing_deadline = fields.Date(string='Hạn xử lý', related='task_report_line_id.processing_deadline', store=True)
    result_image_ids = fields.Many2many('ir.attachment', string='Hình ảnh kết quả', related='task_report_line_id.result_image_ids', readonly=False)
    task_report_line_id = fields.Many2one('ttb.task.report.line', string='Task Report Line', ondelete='cascade')
    approver_id = fields.Many2one('res.users', string='Người duyệt', related='task_report_line_id.approver_id', store=True)
    branch_id = fields.Many2one(string='Cơ sở', related='task_report_line_id.report_id.user_branch_id', store=True)
    def action_complete_task(self):
        for rec in self:
            if not rec.result_image_ids:
                raise UserError("Bạn cần tải lên hình ảnh kết quả trước khi hoàn thành.")
            rec.process_status = 'waiting_for_approval'
            rec.approver_id = rec.env.user.id
            rec.task_report_line_id.action_complete_task()

    def action_approve_task(self):
        self.task_report_line_id.action_approve_task()

    def action_approve_task_kvc(self):
        self.task_report_line_id.action_approve_task_kvc()

    def action_reject_task(self):
        self.result_image_ids.unlink()
        self.task_report_line_id.action_reject_task()

