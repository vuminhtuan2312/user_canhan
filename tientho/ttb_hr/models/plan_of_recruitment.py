from odoo.exceptions import UserError
from odoo import api, fields, models
import datetime

class PlanOfRecruitment(models.Model):
    _name = 'plan.of.recruitment'
    _description = 'Kế hoạch tuyển dụng'
    _rec_name = 'name'
    _order = 'id'

    hr_job_id = fields.Many2one('hr.job', 'Vị trí/chức vụ')
    recruitment_requirements_id = fields.Many2one('recruitment.requirements', ' Yêu cầu tuyển dụng')
    name = fields.Char('Tên bước', required=True)
    detail = fields.Text('Chi tiết')
    no_of_start_days = fields.Integer('Ngày bắt đầu', required=True)
    no_of_end_days = fields.Integer('Ngày kết thúc', required=True)
    start_date = fields.Date('Ngày bắt đầu',compute="_compute_dealine", store=True)
    end_date = fields.Date('Ngày kết thúc', compute="_compute_dealine", store=True)
    result = fields.Text('Kết quả đầu ra')
    date_done = fields.Date('Ngày hoàn thành thực tế', compute="_compute_date_done", store=True)
    status = fields.Selection([('new', 'Mới'), ('doing', 'Đang làm'), ('done', ' Hoàn thành'), ('cancel', 'Hủy')],
                              string='Trạng thái', default='new', readonly=True)

    @api.depends('recruitment_requirements_id.start_date', 'no_of_start_days', 'no_of_end_days')
    def _compute_dealine(self):
        for rec in self:
            if rec.recruitment_requirements_id.start_date and rec.no_of_start_days:
                rec.start_date = rec.recruitment_requirements_id.start_date - datetime.timedelta(days=rec.no_of_start_days)
            if rec.recruitment_requirements_id.start_date and (rec.no_of_end_days or rec.no_of_end_days == 0):
                rec.end_date = rec.recruitment_requirements_id.start_date - datetime.timedelta(days=rec.no_of_end_days)

    @api.depends('status')
    def _compute_date_done(self):
        for rec in self:
            if rec.status == 'done':
                rec.date_done = fields.Datetime.now()
            else:
                rec.date_done = None

    def button_swap_status(self):
        status = self.env['form.swap.status'].create({
            'plan_recruitment_id': self.id
        })
        return {
            'name': 'Thay đổi trạng thái',
            'type': 'ir.actions.act_window',
            'res_model': 'form.swap.status',
            'view_mode': 'form',
            'view_id': self.env.ref('ttb_hr.form_swap_status').id,
            'res_id': status.id,
            'target': 'new',
        }
