from odoo import models, fields

class ChooseResultWizard(models.Model):
    _name = 'choose.result.wizard'
    _description = 'Chọn kết quả QA/QC'

    choice = fields.Selection([
        ('qa', 'QA'),
        ('qc', 'QC')
    ], string="Lựa chọn", required=True)

    def action_confirm(self):
        reports = self.env['ttb.task.report'].browse(
            self.env.context.get('active_ids')
        )

        reports._apply_mismatch_result(self.choice)