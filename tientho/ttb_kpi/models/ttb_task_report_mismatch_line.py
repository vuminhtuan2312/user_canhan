from odoo import fields, models, api

class TaskReportMismatchLine(models.Model):
    _name = 'ttb.task.report.mismatch.line'
    _description = 'Tiêu chí lệch'

    report_id = fields.Many2one('ttb.task.report', string='Phiếu đánh giá')
    template_line_id = fields.Many2one('ttb.task.template.line', string='Tiêu chí')
    result_1 = fields.Selection([('dat', 'Đạt'), ('khong_dat', 'Không đạt')], string='Người đánh giá')
    result_2 = fields.Selection([('dat', 'Đạt'), ('khong_dat', 'Không đạt')], string='Chấm chéo')
    x_pass = fields.Boolean(string='Đạt', default=False)
    fail = fields.Boolean(string='Không đạt', default=False)
    origin_line_id = fields.Many2one('ttb.task.report.line', string="Dòng gốc")
    state = fields.Selection(string='Trạng thái', related='report_id.state', store=True)

    @api.onchange('x_pass')
    def _onchange_x_pass(self):
        if self.x_pass:
            self.fail = False

    @api.onchange('fail')
    def _onchange_fail(self):
        if self.fail:
            self.x_pass = False

    def button_x_pass(self):
        if self.state == 'done':
            return
        self.x_pass = not self.x_pass
        self._onchange_x_pass()

    def button_fail(self):
        if self.state == 'done':
            return
        self.fail = not self.fail
        self._onchange_fail()