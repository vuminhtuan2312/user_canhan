from odoo.exceptions import UserError
from odoo import api, fields, models
import datetime


class RecruitmentRequirements(models.Model):
    _name = 'recruitment.requirements'
    _description = 'Yêu cầu tuyển dụng'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'ttb.approval.mixin']
    _rec_name = "job_id"

    # trường gốc odoo
    job_id = fields.Many2one('hr.job', 'Tên vị trí', tracking=True, required=True)
    department_id = fields.Many2one('hr.department', 'Phòng ban',
                                    compute='_compute_information_job', store=True)

    # Trường thêm mới theo thiết kế
    # Thông tin cơ bản
    manager_id = fields.Many2one('res.users', 'Quản lý trực tiếp',tracking=True)
    no_of_recruitment = fields.Integer(string='Số lượng cần tuyển', copy=False,
                                       help='Number of new employees you expect to recruit.', default=1)
    type_of_recruitment = fields.Selection([('new', 'Tuyển mới'), ('replace', 'Tuyển thay thế')], 'Loại tuyển dụng',
                                        default='replace', required=True)
    on_the_payroll = fields.Selection([('yes', 'Trong định biên'), ('no', 'Ngoài định biên')], 'Định biên',
                                        default='yes')
    attached_documents = fields.Many2many('ir.attachment', string="Tài liệu phê duyệt định biên", tracking=True)
    check_attached_documents = fields.Boolean('Xác nhận tài liệu định biên', tracking=True)
    time_recruitment = fields.Selection([('normal', 'Theo quy định'), ('urgent', 'Gấp')], 'Thời gian tuyển dụng',
                                        default='normal', required=True)

    person_in_charge = fields.Many2one('res.users', 'HR phụ trách', tracking=True)
    desired_time = fields.Date('Ngày mong muốn', tracking=True, compute='compute_desired_time', store=True, readonly=False)
    reason = fields.Char('Lý do')
    expected_number_of_days = fields.Integer('Thời gian tuyển dụng (ngày)', related='job_id.time_recruitment')


    # Chân dung ứng viên
    job_responsibility_ids = fields.One2many('job.responsibility', 'recruitment_requirements_id', 'Nhiệm vụ công việc',
                                             compute='_compute_information_job', store=True, readonly=False)
    total_proportion = fields.Float('Tổng tỷ trọng(%)', readonly=True, store=False)

    # trình độ
    education = fields.Selection([('none', 'Không'), ('university', 'Đại học'), ('college', 'Cao đẳng'),
                                  ('intermediate', 'Trung cấp'), ('high_school', 'Trung học phổ thông')],
                                 string='Trình độ', compute='_compute_information_job', store=True, readonly=False)
    major = fields.Char('Chuyên ngành', compute='_compute_information_job', store=True, readonly=False)
    prioritize = fields.Char('Ưu tiên trường', compute='_compute_information_job', store=True, readonly=False)
    graduation_results = fields.Selection([('excellent', 'Xuất sắc'), ('good', 'Giỏi'), ('fair', 'Khá'),
                                           ('average-good', 'Trung bình - khá'), ('average', 'Trung bình')],
                                          'Kết quả tốt nghiệp', compute='_compute_information_job', store=True, readonly=False)
    # kinh nghiệm công việc
    experience = fields.Boolean('Kinh nghiệm cho vị trí công việc', default=False, compute='_compute_information_job', store=True, readonly=False)
    experience_for_job_ids = fields.One2many('experience.for.job', 'recruitment_requirements_id')
    # kinh nghiệm hạng mục công việc
    experience_for_category = fields.Boolean('Kinh nghiệm theo công việc', default=False, compute='_compute_information_job', store=True, readonly=False)
    experience_for_category_ids = fields.One2many('experience.for.category', 'recruitment_requirements_id')
    # không tin khác
    knowledge = fields.Text('Kiến thức', compute='_compute_information_job', store=True, readonly=False)
    professional_skills = fields.Text('Kỹ năng chuyên môn', compute='_compute_information_job', store=True, readonly=False)
    soft_skills = fields.Text('Kỹ năng mềm', compute='_compute_information_job', store=True, readonly=False)
    fit_core_value = fields.Many2many(comodel_name='core.value', string='Phù hợp giá trị cốt lõi', compute='_compute_information_job', store=True, readonly=False)
    other_qualities = fields.Text('Phẩm chất khác', compute='_compute_information_job', store=True, readonly=False)
    style = fields.Text('Tác phong', compute='_compute_information_job', store=True, readonly=False)
    min_old = fields.Integer('Tuổi tối thiểu', compute='_compute_information_job', store=True, readonly=False)
    max_old = fields.Integer('Tuổi tối đa', compute='_compute_information_job', store=True, readonly=False)
    gender_preference = fields.Selection([('male', 'Nam'), ('female', 'Nữ'), ('none', 'Không')],
                                         string='Giới tính ưu tiên', default='none', compute='_compute_information_job', store=True, readonly=False)
    other_require = fields.Text('Yêu cầu khác', compute='_compute_information_job', store=True, readonly=False)
    time_job_recruitment = fields.Integer('Thời gian tuyển dụng', compute='_compute_information_job', store=True, readonly=False)

    # Thông tin HR bổ sung
    platform_infinfor_and_key_ids = fields.One2many('platform.infor.and.key', 'recruitment_requirements_id','Kênh và từ khoá ',
                                                    compute='_compute_information_job', store=True, readonly=False)
    platform_ids = fields.Many2many('platform.and.media', string='Nền tảng', compute='compute_platform_ids')
    salary_range_min = fields.Integer('Lương tối thiểu', tracking=True, compute='_compute_information_job', store=True, readonly=False)
    salary_range_max = fields.Integer('Lương tối đa', tracking=True, compute='_compute_information_job', store=True, readonly=False)
    key_word = fields.Text('Từ khóa',compute='_compute_information_job', store=True, readonly=False)

    #Kế hoạch tuyển dụng
    start_date = fields.Date('Ngày nhận việc', default=fields.Datetime.now)
    plan_detail_ids = fields.One2many('plan.of.recruitment', 'recruitment_requirements_id')

    #Tổng hợp hồ sơ ứng viên
    hr_applicant_ids = fields.One2many('hr.applicant', 'recruitment_requirements_id')

    state = fields.Selection([("draft", "Nháp"),
                              ("confirm", 'Đã gửi yêu cầu'),
                              ("rejected", "Không duyệt"),
                              ("approved", "Đã duyệt"),
                              ("done", "Hoàn thành"),
                              ("cancel", "Hủy")], string='Trạng thái', tracking=True, default="draft",
                             compute='_compute_state', store=True)
    date_send_requiment = fields.Date('Ngày gửi yêu cầu')
    date_check_attached_documents = fields.Date('Ngày duyệt tài liệu định biên')

    @api.depends('platform_infinfor_and_key_ids')
    def compute_platform_ids(self):
        for rec in self:
            rec.platform_ids = rec.platform_infinfor_and_key_ids.mapped('name')

    @api.depends('hr_applicant_ids', 'hr_applicant_ids.stage_id')
    def _compute_state(self):
        for rec in self:
            if len(rec.hr_applicant_ids.filtered(lambda r: r.stage_id and r.stage_id.hired_stage==True)) >= rec.no_of_recruitment if rec.no_of_recruitment else 0:
                rec.state = 'done'


    @api.onchange('job_responsibility_ids')
    def compute_total_proportion(self):
        for rec in self:
            total = 0
            for detail in rec.job_responsibility_ids:
                if detail.proportion:
                    total += detail.proportion
            rec.total_proportion = total

    @api.depends('job_id')
    def _compute_information_job(self):
        for rec in self:
            if rec.job_id:
                rec.department_id = rec.job_id.department_id.id
                rec.education = rec.job_id.education
                rec.major = rec.job_id.major
                rec.prioritize = rec.job_id.prioritize
                rec.graduation_results = rec.job_id.graduation_results
                rec.experience = rec.job_id.experience
                rec.experience_for_category = rec.job_id.experience_for_category
                rec.knowledge = rec.job_id.knowledge
                rec.professional_skills = rec.job_id.professional_skills
                rec.soft_skills = rec.job_id.soft_skills
                rec.fit_core_value = rec.job_id.fit_core_value.ids
                rec.other_qualities = rec.job_id.other_qualities
                rec.style = rec.job_id.style
                rec.min_old = rec.job_id.min_old
                rec.max_old = rec.job_id.max_old
                rec.gender_preference = rec.job_id.gender_preference
                rec.other_require = rec.job_id.other_require
                rec.time_job_recruitment = rec.job_id.time_recruitment

                rec.job_responsibility_ids = rec.job_id.job_responsibility_ids.copy({
                    'hr_job_id': None,
                })
                rec.experience_for_job_ids = rec.job_id.experience_for_job_ids.copy({
                    'hr_job_id': None,
                })
                rec.experience_for_category_ids = rec.job_id.experience_for_category_ids.copy({
                    'hr_job_id': None,
                })
                rec.platform_infinfor_and_key_ids = rec.job_id.platform_infinfor_and_key_ids.copy({
                    'hr_job_id': None,
                })
                rec.plan_detail_ids = rec.job_id.plan_detail_ids.copy({
                    'hr_job_id': None,
                })
                rec.salary_range_min = rec.job_id.salary_range_min
                rec.salary_range_max = rec.job_id.salary_range_max
                rec.key_word = rec.job_id.key_word

    @api.depends('create_uid')
    def _compute_sent_ok(self):
        for rec in self:
            rec.sent_ok = rec.create_uid and self.env.user == rec.create_uid

    def button_ready(self):
        if self.on_the_payroll == 'no' and not self.attached_documents:
            raise UserError('Chưa có tài liệu xác nhận định biên. Vui lòng kiểm tra lại.')
        elif self.on_the_payroll == 'no' and self.attached_documents and not self.check_attached_documents:
            raise UserError('Tài liệu định biên chưa được xác nhận. Vui lòng kiểm tra lại.')
        self.date_send_requiment = fields.Datetime.now()
        
        if self.state != 'draft': return
        if not self.sent_ok: return
        process_id, approval_line_ids = self.get_approval_line_ids()
        self.write({'process_id': process_id.id,
                    'date_sent': fields.Datetime.now(),
                    'state': 'confirm',
                    'approval_line_ids': [(5, 0, 0)] + approval_line_ids})
        if self.env.user.id not in self.current_approve_user_ids.ids:
            self.send_notify(message='Bạn cần duyệt yêu cầu tuyển dụng', users=self.current_approve_user_ids, subject='Yêu cầu tuyển dụng cần duyệt')
        self.button_approve_request()
        return True

    def button_approve_request(self):
        if self.state != 'confirm': return
        if not self.approve_ok and self.rule_line_ids: return
        if self.state_change('approved'):
            self.sudo().write({'state': 'approved', 'date_approved': fields.Datetime.now()})
            if self.rule_line_ids:
                self.send_notify(message='Yêu cầu tuyển dụng của bạn đã được duyệt', users=self.create_uid, subject='Yêu cầu tuyển dụng đã duyệt')
                self.send_notify(message='Bạn được phân công thực hiện yêu cầu tuyển dụng', users=self.notif_user_ids, subject='Yêu cầu tuyển dụng cần thực hiện')
        else:
            self.send_notify(message='Bạn cần duyệt yêu cầu tuyển dụng', users=self.current_approve_user_ids, subject='Yêu cầu tuyển dụng cần duyệt')
        return True

    def action_reject(self):
        if self.state != 'confirm': return
        if not self.approve_ok: return
        self.state_change('rejected')
        if self.rule_line_ids.search([('notif_only', '=', False), ('res_id', 'in', self.ids), ('res_model', '=', self._name)], order='sequence asc', limit=1).state == 'rejected':
            self.sudo().write({'state': 'draft'})
            self.send_notify(message='Yêu cầu tuyển dụng của bạn đã bị từ chối', users=self.create_uid, subject='Yêu cầu tuyển dụng bị từ chối')
        else:
            self.send_notify(message='Bạn cần duyệt yêu cầu tuyển dụng', users=self.current_approve_user_ids, subject='Yêu cầu tuyển dụng cần duyệt')
        return True

    def button_done_request(self):
        self.state = 'done'

    def button_cancel_request(self):
        self.state= 'cancel'

    def button_check_attached_documents(self):
        if not self.attached_documents:
            raise UserError('Chưa có tài liệu xác nhận định biên. Vui lòng kiểm tra lại.')
        self.date_check_attached_documents = fields.Datetime.now()
        self.check_attached_documents = True

    @api.depends('date_send_requiment', 'date_check_attached_documents', 'expected_number_of_days', 'time_recruitment',
                 'type_of_recruitment', 'on_the_payroll')
    def compute_desired_time(self):
        for rec in self:
            if rec.time_recruitment == 'normal':
                if rec.type_of_recruitment == 'replace' or (
                        rec.type_of_recruitment == 'new' and rec.on_the_payroll == 'yes'):
                    if rec.date_send_requiment:
                        rec.desired_time = rec.date_send_requiment + datetime.timedelta(
                            days=rec.expected_number_of_days)
                elif rec.type_of_recruitment == 'new' and rec.on_the_payroll == 'no':
                    if rec.date_check_attached_documents:
                        rec.desired_time = rec.date_check_attached_documents + datetime.timedelta(
                            days=rec.expected_number_of_days)

    can_edit_hr = fields.Boolean('HR phụ trách', compute='_compute_can_edit_hr')
    last_approve_user_ids = fields.Many2many(string='Người duyệt cuối cùng', comodel_name='res.users', compute='_compute_last_approve_user_ids')

    @api.depends('rule_line_ids')
    def _compute_last_approve_user_ids(self):
        for rec in self:
            last_lines = rec.rule_line_ids.sorted(lambda r: r.sequence, reverse=True)
            if last_lines:
                max_sequence = last_lines[0].sequence
                rec.last_approve_user_ids = last_lines.filtered(lambda r: r.sequence == max_sequence).mapped('approve_user_ids')
            else:
                rec.last_approve_user_ids = False

    @api.depends_context('uid')
    @api.depends('rule_line_ids')
    def _compute_can_edit_hr(self):
        for rec in self:
            rec.can_edit_hr = rec.last_approve_user_ids and self.env.user in rec.last_approve_user_ids

class PlatformAndMedia(models.Model):
    _name = 'platform.and.media'
    _description = 'Platform và media'
    _rec_name = "name"

    name = fields.Char('Tên nền tảng')

class PlatformInfinforAndKey(models.Model):
    _name = 'platform.infor.and.key'
    _description = 'Thông tin nền tảng và từ khóa'
    _rec_name = "name"

    hr_job_id = fields.Many2one('hr.job', 'Vị trí/chức vụ')
    recruitment_requirements_id = fields.Many2one('recruitment.requirements', 'Yêu cầu tuyển dụng')
    name = fields.Many2one('platform.and.media', 'Tên nền tảng')
    content = fields.Html('Nội dung đăng tuyển')


class RecruitmentStageCustomize(models.Model):
    _name = 'recruitment.stage.customize'
    _rec_name = "criteria"
    _description = 'Các vòng tuyển dụng theo tiêu chí'

    hr_job_id = fields.Many2one('hr.job', 'Yêu cầu tuyển dụng')
    criteria = fields.Char('Tiêu chí đánh giá')
    criteria_show = fields.Char('Tiêu chí đánh giá', related="criteria")
    hr_recruitment_stage_id = fields.Many2many(comodel_name='hr.recruitment.stage', string='Vòng tuyển dụng',)
