from odoo import fields, models

class TtbTaskReportMismatchOld(models.Model):
    _name = 'ttb.task.report.mismatch.old'
    _description = 'Danh sách tiêu chí lệch cũ'

    report_id = fields.Many2one(comodel_name='ttb.task.report')
    score_type = fields.Selection([
        ('qc', 'QC'),
        ('qa', 'QA')
    ])
    template_line_id = fields.Many2one(string='Nhiệm vụ', comodel_name='ttb.task.template.line', required=True)
    note = fields.Text(string="Ghi chú")
    x_pass = fields.Boolean(string='Đạt', default=False)
    fail = fields.Boolean(string='Không đạt', default=False)
    image_ids = fields.Many2many(string='Hình ảnh', comodel_name='ir.attachment')