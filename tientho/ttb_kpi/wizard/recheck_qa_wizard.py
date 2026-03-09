from odoo import fields, models, api

class RecheckQAWizard(models.TransientModel):
    _name = 'recheck.qa.wizard'
    _description = 'Wizard chấm lại QA'

    report_id = fields.Many2one('ttb.task.report', string='Phiếu', required=True, readonly=True)
    reason_qa = fields.Text(string='Lý do chấm lại QA', required=True)

    def action_confirm(self):
        self.ensure_one()
        report = self.report_id

        now = fields.Datetime.now()

        vals = {
            'qa_retry_count': report.qa_retry_count + 1,
            'qa_retry_time': now,
        }

        if report.state == 'waiting':
            vals['state'] = 'done_qc'
        elif report.state == 'done_qa':
            vals['state'] = 'reviewing'

        report.write(vals)

        # Ghi dữ liệu vào bảng QA cũ
        report._snapshot_qa_lines()

        # Ghi dữ liệu vào bảng lệch cũ
        report.create_mismatch_old()

        # Xóa dữ liệu trong tab chấm chéo
        report.line_id_cross_dot.write({
            'x_pass': False,
            'fail': False,
            'image_ids': [(5, 0, 0)],
            'note': ''
        })
