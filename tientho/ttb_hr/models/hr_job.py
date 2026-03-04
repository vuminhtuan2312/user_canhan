from odoo import *
from .const import list_criteria

class HrJob(models.Model):
    _inherit ='hr.job'

    ttb_user_template_id = fields.Many2one(string='Mẫu người dùng', domain=lambda self: ['|', ('active', '=', False), ('active', '=', True)], comodel_name='res.users')
    recruitment_requirements_ids = fields.One2many('recruitment.requirements', 'job_id', 'Các yêu cầu tuyển dụng',)

    job_responsibility_ids = fields.One2many('job.responsibility', 'hr_job_id', 'Nhiệm vụ công việc')
    total_proportion = fields.Float('Tổng tỷ trọng(%)', )
    #trình độ học vấn
    education = fields.Selection([('none', 'Không'), ('university', 'Đại học'), ('college', 'Cao đẳng'),
                                  ('intermediate', 'Trung cấp'), ('high_school', 'Trung học phổ thông')], string='Trình độ', required=True)
    major = fields.Char('Chuyên ngành')
    prioritize = fields.Char('Ưu tiên trường')
    graduation_results = fields.Selection([('excellent', 'Xuất sắc'), ('good', 'Giỏi'), ('fair', 'Khá'),
                                           ('average-good', 'Trung bình - khá'), ('average', 'Trung bình')], 'Kết quả tốt nghiệp')
    #Kinh nghiệm công việc
    experience = fields.Boolean('Kinh nghiệm cho vị trí công việc', default=False)
    experience_for_job_ids = fields.One2many('experience.for.job', 'hr_job_id')
    #Kinh nghiệm hạng mục công việc
    experience_for_category = fields.Boolean('Kinh nghiệm theo công việc', default=False)
    experience_for_category_ids = fields.One2many('experience.for.category', 'hr_job_id')
    #Thông tin khác
    knowledge = fields.Text('Kiến thức')
    professional_skills = fields.Text('Kỹ năng chuyên môn')
    soft_skills = fields.Text('Kỹ năng mềm')
    fit_core_value = fields.Many2many(comodel_name='core.value', string='Phù hợp giá trị cốt lõi',)
    other_qualities = fields.Text('Phẩm chất khác')
    style = fields.Text('Tác phong')
    min_old = fields.Integer('Tuổi tối thiểu')
    max_old = fields.Integer('Tuổi tối đa')
    gender_preference = fields.Selection([('male', 'Nam'), ('female', 'Nữ'), ('none', 'Không')],
                                         string='Giới tính ưu tiên', default='none')
    other_require = fields.Text('Yêu cầu khác')
    time_recruitment = fields.Integer('Thời gian tuyển dụng')

    # Thông tin HR bổ sung
    platform_infinfor_and_key_ids = fields.One2many('platform.infor.and.key', 'hr_job_id',
                                                    'Kênh và từ khoá ', )
    salary_range_min = fields.Integer('Lương tối thiểu', tracking=True, )
    salary_range_max = fields.Integer('Lương tối đa', tracking=True, )
    key_word = fields.Text('Từ khóa', )

    # Các giai đoạn
    stage_ids = fields.Many2many(comodel_name='hr.recruitment.stage', string='Vòng tuyển dụng')
    recruitment_stage_ids = fields.One2many('recruitment.stage.customize', 'hr_job_id', 'Các vòng tuyển dụng', )

    # Kế hoạch tuyển dụng
    plan_template_id = fields.Many2one('plan.of.recruitment.template', 'Kế hoạch mẫu')
    plan_detail_ids = fields.One2many('plan.of.recruitment', 'hr_job_id')

    @api.onchange('job_responsibility_ids', 'job_responsibility_ids.proportion')
    def compute_total_proportion(self):
        for rec in self:
            total = 0
            for detail in rec.job_responsibility_ids:
                if detail.proportion:
                    total += detail.proportion
            rec.total_proportion = total

    @api.onchange('stage_ids')
    def onchange_recruitment_stage(self):
        if not self.recruitment_stage_ids:
            lines_to_create = []
            for criteria in list_criteria:
                line_values = {
                    'criteria': criteria,
                }
                lines_to_create.append((0, 0, line_values))
            self.recruitment_stage_ids = [(5, 0, 0)] + lines_to_create

    @api.onchange('plan_template_id')
    def onchange_plan_of_recruitment(self):
        if self.plan_template_id:
            step_of_plan_list = self.env['step.of.plan'].search(
                [('id', 'in', self.plan_template_id.step_of_plan_ids.ids)])
            lines_to_create = []
            for step in step_of_plan_list:
                line_values = {
                    'name': step.name,
                    'detail': step.detail,
                    'no_of_start_days': step.no_of_start_days,
                    'no_of_end_days': step.no_of_end_days,
                    'result': step.result,
                }
                lines_to_create.append((0, 0, line_values))
            if lines_to_create:
                self.plan_detail_ids = [(5, 0, 0)] + lines_to_create
        else:
            self.plan_detail_ids = [(5, 0, 0)]

    reviewed_ids = fields.One2many('hr.job.reviewed', 'hr_job_id', 'Người đánh giá',)

class HrJobReviewed(models.Model):
    _name = 'hr.job.reviewed'
    _description = 'Người đánh giá công việc'

    hr_job_id = fields.Many2one('hr.job', 'Chức vụ')
    stage_id = fields.Many2one(comodel_name='hr.recruitment.stage', string='Vòng tuyển dụng',)
    hr_job_ids = fields.Many2many(comodel_name='hr.job', string='Chức vụ')
    employee_ids = fields.Many2many(comodel_name='res.users', string='Người đánh giá', compute='_compute_employee_id', store=True)

    @api.depends('hr_job_ids')
    def _compute_employee_id(self):
        for rec in self:
            if rec.hr_job_ids:
                user_ids = self.env['hr.employee'].search([('job_id', 'in', rec.hr_job_ids.ids)]).mapped('user_id')
                if user_ids:
                    rec.employee_ids = user_ids.ids
                else:
                    rec.employee_ids = False
            else:
                rec.employee_ids = False

class JobResponsibility(models.Model):
    _name = 'job.responsibility'
    _description = 'Nhiệm vụ công việc'
    _rec_name = 'main_responsibility'

    recruitment_requirements_id = fields.Many2one('recruitment.requirements', 'Yêu cầu')
    hr_job_id = fields.Many2one('hr.job', 'Chức vụ')
    main_responsibility = fields.Char('Nhiệm vụ chính')
    detail_responsibility = fields.Text('Nhiệm vụ chi tiết')
    proportion = fields.Float('Tỷ trọng(%)')

class Corevalue(models.Model):
    _name = 'core.value'
    _description = 'Giá trị cốt lõi'
    _rec_name = 'name'

    name = fields.Char('Giá trị')

class ExperienceForJob(models.Model):
    _name = 'experience.for.job'
    _description = 'Thông tin về kinh nghiệm công việc'
    _rec_name = 'job_position'

    hr_job_id = fields.Many2one('hr.job')
    recruitment_requirements_id = fields.Many2one('recruitment.requirements', 'Yêu cầu')
    job_position = fields.Char('Vị trí')
    no_of_years = fields.Float('Số năm')
    company_size = fields.Char('Quy mô công ty/Ngành nghề')

class ExperienceForCategory(models.Model):
    _name = 'experience.for.category'
    _description = 'Thông tin về kinh nghiệm hạng mục'
    _rec_name = 'job_category'

    hr_job_id = fields.Many2one('hr.job')
    recruitment_requirements_id = fields.Many2one('recruitment.requirements', 'Yêu cầu')
    job_category = fields.Char('Hạng mục công việc')
    no_of_years_for_category = fields.Float('Số năm hạng mục')
    notice = fields.Char('Ghi chú')

class HrRecruitmentStage(models.Model):
    _inherit = "hr.recruitment.stage"

    def create(self, values):
        res = super().create(values)
        common_stage = self.env.ref('ttb_hr.stage_common_inactive')
        common_stage_ids = common_stage.ids
        if res.job_ids:
            common_stage_ids = list(set(res.job_ids.ids + common_stage_ids))
        res.sudo().write({
            'job_ids': [(6, 0, common_stage_ids)]
        })
        return res
