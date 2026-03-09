from odoo import fields, models, api

class TaskReportMismatchLine(models.Model):
    _name = 'ttb.task.report.mismatch.line'
    _description = 'Tiêu chí lệch'

    report_id = fields.Many2one('ttb.task.report', string='Phiếu đánh giá')
    template_line_id = fields.Many2one('ttb.task.template.line', string='Tiêu chí')
    selected = fields.Boolean(string='Lựa chọn')
    score_type = fields.Selection([('qc', 'QC'), ('qa', 'QA')], string='Loại chấm')
    source_line_id = fields.Many2one('ttb.task.report.line')
    source_line_cross_id = fields.Many2one('ttb.task.report.line')
    image_ids = fields.Many2many('ir.attachment', relation='ttb_mismatch_attachment_rel', column1='mismatch_id', column2='attachment_id', string="Hình ảnh")
    note = fields.Text(string='Ghi chú')
    pair_key = fields.Char(string='Pair Key', help="Dùng để xác định cặp lệch")
    x_pass = fields.Boolean(string='Đạt', default=False)
    fail = fields.Boolean(string='Không đạt', default=False)
    state = fields.Selection(string='Trạng thái', related='report_id.state', store=True)

    @api.model
    def write(self,vals):
        res = super().write(vals)

        if 'selected' in vals  and vals['selected']:
            for rec in self:
                others = rec.report_id.mismatch_ids.filtered(
                    lambda l: l.pair_key == rec.pair_key and l.id != rec.id
                )
                others.write({
                    'selected': False
                })
        return res

