# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime, date, timedelta

class ApplicantChangeStageWizard(models.TransientModel):
    _name = 'applicant.change.stage.wizard'
    _description = 'Wizard to Change Applicant Stage with Options'

    def _get_default_applicant_ids(self):
        return self.env.context.get('active_ids')

    applicant_ids = fields.Many2many(
        'hr.applicant',
        string='Applicants',
        required=True,
        default=_get_default_applicant_ids
    )
    stage_id = fields.Many2one(
        'hr.recruitment.stage',
        string='New Stage',
        required=True
    )
    send_option = fields.Selection([
        ('now', 'Mặc định'),
        ('schedule', 'Gửi theo kế hoạch')
    ], string='Tùy chon thời điểm gửi mail', default='now', required=True)
    time_option = fields.Selection([
        ('specific_time', 'Thời điểm chính xác'),
        ('period', 'Sau khoảng thời gian')
    ], string='Tùy chon thời gian gửi mail', default='specific_time',)
    schedule_date = fields.Datetime(string='Thời điểm gửi')
    schedule_time = fields.Integer(string='Gửi sau(giờ)')

    @api.onchange('send_option')
    def onchange_time_option(self):
        if self.send_option == 'schedule':
            self.time_option = 'specific_time'

    @api.onchange('schedule_time')
    def onchange_time_option(self):
        if self.schedule_time:
            self.schedule_date = fields.Datetime.now() + timedelta(hours=self.schedule_time)

    @api.constrains('schedule_date', 'time_option')
    def _check_schedule_date(self):
        for wizard in self:
            if self.send_option == 'schedule':
                if wizard.schedule_date <= fields.Datetime.now():
                    raise UserError(f'Thời gian gửi mail thông báo là {wizard.schedule_date}, '
                                f'thời gian gửi phải sau thời điểm hiện tại. Vui lòng kiểm tra lại.')

    def action_confirm(self):
        self.ensure_one()
        if not self.applicant_ids:
            return {'type': 'ir.actions.act_window_close'}

        if self.send_option == 'schedule':
            self.applicant_ids.with_context(
                use_schedule = True,
                schedule_date = self.schedule_date
            ).write({'stage_id': self.stage_id.id})
        else:
            self.applicant_ids.write({'stage_id': self.stage_id.id})

        return {'type': 'ir.actions.act_window_close'}
