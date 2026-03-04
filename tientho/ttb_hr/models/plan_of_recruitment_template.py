from odoo.exceptions import UserError
from odoo import api, fields, models

class PlanOfRecruitmentTemplate(models.Model):
    _name = 'plan.of.recruitment.template'
    _description = 'Kế hoạch tuyển dụng mẫu'
    _rec_name = 'name'

    name = fields.Char('Tên kế hoạch', required=True)
    step_of_plan_ids = fields.One2many('step.of.plan', 'plan_of_recruitment_template_id', 'Các bước kế hoạch')

class StepOfPlan(models.Model):
    _name = 'step.of.plan'
    _description = 'Các bước kế hoạch'
    _rec_name = 'name'
    _order = 'id'

    plan_of_recruitment_template_id = fields.Many2one('plan.of.recruitment.template', 'Kế hoạch tuyển dụng mẫu')
    name = fields.Char('Tên bước', required=True)
    detail = fields.Text('Chi tiết')
    result = fields.Text('Kết quả đầu ra')
    no_of_start_days = fields.Integer('Ngày bắt đầu')
    no_of_end_days = fields.Integer('Ngày kết thúc')
