from odoo import fields, models, api

class RecheckQCWizard(models.TransientModel):
    _name = 'recheck.qc.wizard'
    _description = 'Wizard chấm lại QC'

    report_id = fields.Many2one('ttb.task.report', string='Phiếu', required=True, readonly=True)
    reason_qc = fields.Text(string='Lý do chấm lại QC', required=True)

    def action_confirm(self):
        self.ensure_one()
        report = self.report_id

        now = fields.Datetime.now()

        vals = {
            'qc_retry_count': report.qc_retry_count + 1,
            'qc_retry_time': now,
        }

        if report.state == 'waiting':
            vals['state'] = 'done_qa'
        elif report.state == 'done_qc':
            vals['state'] = 'reviewing'

        report.write(vals)

        # Ghi dữ liệu vào bảng QA cũ
        report._snapshot_qc_lines()

        # Ghi dữ liệu vào bảng lệch cũ
        report.create_mismatch_old()

        # Xóa dữ liệu trong tab chấm chéo
        report.line_ids.write({
            'x_pass': False,
            'fail': False,
            'image_ids': [(5, 0, 0)],
            'note': ''
        })
