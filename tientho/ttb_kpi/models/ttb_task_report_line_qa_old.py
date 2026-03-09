from odoo import api, fields, models

class TtbTaskReportLineQaOld(models.Model):
    _name = 'ttb.task.report.line.qa.old'
    _description = 'Bảng chấm QA cũ'

    report_id = fields.Many2one('ttb.task.report', string='Đánh giá nhiệm vụ', ondelete='cascade')
    x_pass = fields.Boolean(string='Đạt', default=False)
    fail = fields.Boolean(string='Không đạt', default=False)
    image_ids = fields.Many2many(string="Hình ảnh", comodel_name='ir.attachment')
    template_line_id = fields.Many2one(string='Nhiệm vụ', comodel_name='ttb.task.template.line', required=True)
    requirement = fields.Text(string='Yêu cầu cần đạt', related=False, store=True)
    note = fields.Text(string="Ghi chú")
