from odoo import api, fields, models, _

class TtbTaskReportCancelWizard(models.TransientModel):
    _name = 'ttb.task.report.cancel.wizard'
    _description = 'Wizard hủy phiếu đánh giá'

    report_id = fields.Many2one('ttb.task.report', string='Phiếu đánh giá', required=True, readonly=True)
    reason_id = fields.Many2one('ttb.cancel.reason', string='Lý do hủy', required=True)

    def action_confirm_cancel(self):
        self.ensure_one()
        self.report_id.write({
            'cancel_reason_id': self.reason_id.id,
            'state': 'cancel'
        })
        return {'type': 'ir.actions.act_window_close'}