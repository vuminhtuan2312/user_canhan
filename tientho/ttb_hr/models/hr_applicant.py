from odoo import api, fields, models
from odoo.exceptions import UserError
from .const import education_dict, list_criteria, graduation_results_dict
import base64
import io
import re

try:
    import pdfplumber
except ImportError:
    pdfplumber = None


class HrApplicant(models.Model):
    _inherit = "hr.applicant"

    recruitment_requirements_id = fields.Many2one('recruitment.requirements', 'Yêu cầu tuyển dụng',
                                                  domain="[('job_id', '=', job_id)]")
    platform_ids = fields.Many2many(related='recruitment_requirements_id.platform_ids')
    review_infor_ids = fields.One2many('review.information', 'hr_applicant_id', 'Thông tin xét tuyển',
                                       compute='compute_reviews_infor', store=True)
    review_infor_display_ids = fields.One2many('review.information','hr_applicant_id',
                                                string="Đánh giá cho vòng hiện tại",
                                                compute='_compute_review_infor_display_ids', readonly=False)
    test_result_ids = fields.One2many('test.result', 'hr_applicant_id', 'Kết quả đánh giá',
                                  compute='compute_reviews_infor', store=True)
    test_result_display_ids = fields.One2many('test.result', 'hr_applicant_id', 'Kết quả đánh giá',
                                  compute='_compute_test_result_display_ids', readonly=False)
    platform = fields.Many2one('platform.and.media', 'Nền tảng tuyển dụng')

    temp_email_from = fields.Char('Email tạm thời', store=False)
    temp_partner_phone = fields.Char('Số điện thoại tạm thời', store=False)

    cv_pdf_file = fields.Binary('CV PDF')

    @api.onchange('email_from', 'partner_phone')
    def _onchange_save_contact_info(self):
        """Lưu tạm thời thông tin liên hệ trước khi có candidate_id"""
        if not self.candidate_id:
            # Lưu vào trường tạm thời
            if self.email_from:
                self.temp_email_from = self.email_from
            if self.partner_phone:
                self.temp_partner_phone = self.partner_phone

    @api.onchange('candidate_id')
    def _onchange_candidate_id(self):
        """Tự động điền thông tin email và phone cho candidate mới tạo"""
        if self.candidate_id and not self.candidate_id.email_from and not self.candidate_id.partner_phone:
            # Lấy giá trị từ trường tạm thời
            temp_email = self.temp_email_from or ''
            temp_phone = self.temp_partner_phone or ''

            # Cập nhật thông tin cho candidate mới
            if temp_email or temp_phone:
                self.candidate_id.write({
                    'email_from': temp_email,
                    'partner_phone': temp_phone,
                })
                # Xóa giá trị tạm thời sau khi đã cập nhật
                self.temp_email_from = False
                self.temp_partner_phone = False

    @api.onchange('cv_pdf_file')
    def onchange_import_cv_pdf(self):
        if not self.cv_pdf_file:
            return
        if not pdfplumber:
            raise UserError("Chưa cài đặt thư viện pdfplumber. Vui lòng cài đặt bằng pip install pdfplumber.")

        # Đọc nội dung PDF
        pdf_content = base64.b64decode(self.cv_pdf_file)
        with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() or ""

        # Regex tìm tên, email, số điện thoại
        email_match = re.search(r'[\w\.-]+@[\w\.-]+', text)
        phone_match = re.search(r'(\+?\d[\d\-\.\s]{8,}\d)', text)

        email = email_match.group(0) if email_match else ""
        phone = phone_match.group(0) if phone_match else ""

        # Kiểm tra candidate theo email
        candidate = self.env['hr.candidate'].search([('email_from', '=', email), ('partner_phone', '=', phone)],
                                                    limit=1) if email and phone else False
        if candidate:
            self.candidate_id = candidate.id
        else:
            self.email_from = email
            self.partner_phone = phone


    def gen_content_value(self, job_id):
        content_dict = {}
        default_text = 'không yêu cầu'

        prioritize = job_id.prioritize if job_id.prioritize else default_text
        graduation_results = graduation_results_dict[job_id.graduation_results] if job_id.graduation_results else default_text
        if job_id.education == 'high_school':
            content_dict[list_criteria[0]] = f'Trình độ: Trung học phổ thông, ưu tiên trường: {prioritize}, loại tốt nghiệp: {graduation_results}.'
        else:
            education = education_dict[job_id.education] if job_id.education else default_text
            major = job_id.major if job_id.major else default_text
            content_dict[list_criteria[0]] = f'Trình độ: {education}, chuyên ngành: {major}, ưu tiên trường {job_id.prioritize}, loại tốt nghiệp: {graduation_results}.'
        if job_id.experience:
            content_exp = ""
            for rec in job_id.experience_for_job_ids:
                content_exp += f'Vị trí: {rec.job_position}'
                if rec.no_of_years:
                    content_exp += f', số năm kinh nghiệm: {rec.no_of_years}'
                if rec.company_size:
                    content_exp += f', quy mô công ty/ngành nghề: {rec.company_size}'
                content_exp += ".\n"
            content_dict[list_criteria[1]] = content_exp
        if job_id.experience_for_category:
            content_exp_category = ""
            for rec in job_id.experience_for_category_ids:
                content_exp_category += f'Hạng mục công việc: {rec.job_category}'
                if rec.no_of_years_for_category:
                    content_exp_category += f', số năm hạng mục: {rec.no_of_years_for_category}'
                if rec.notice:
                    content_exp_category += f', ghi chú: {rec.notice}'
                content_exp_category += ".\n"
            content_dict[list_criteria[2]] = content_exp_category
        content_dict[list_criteria[3]] = job_id.knowledge if job_id.knowledge else default_text
        content_dict[list_criteria[4]] = job_id.professional_skills if job_id.professional_skills else default_text
        content_dict[list_criteria[5]] = job_id.soft_skills if job_id.soft_skills else default_text
        core_list = job_id.fit_core_value.mapped('name') if job_id.fit_core_value else []
        content_dict[list_criteria[6]] =', '.join(core_list) if core_list else default_text
        content_dict[list_criteria[7]] = job_id.style if job_id.style else default_text
        return content_dict

    @api.depends('review_infor_ids', 'stage_id')
    def _compute_review_infor_display_ids(self):
        for rec in self:
            if not rec.stage_id:
                # Nếu không có stage, không hiển thị gì cả
                rec.review_infor_display_ids = self.env['review.information']
                continue

            # Lọc từ tất cả các bản ghi đã có
            filtered_reviews = rec.review_infor_ids.filtered(
                lambda r: r.stage_name.id == rec.stage_id.id
            )
            rec.review_infor_display_ids = filtered_reviews

    @api.depends('test_result_ids', 'stage_id')
    def _compute_test_result_display_ids(self):
        for rec in self:
            if not rec.stage_id:
                # Nếu không có stage, không hiển thị gì cả
                rec.test_result_display_ids = self.env['test.result']
                continue

            # Lọc từ tất cả các bản ghi đã có
            filtered_reviews = rec.test_result_ids.filtered(
                lambda r: r.stage_id.id == rec.stage_id.id
            )
            rec.test_result_display_ids = filtered_reviews

    @api.depends('job_id')
    def compute_reviews_infor(self):
        for rec in self:
            #Tạo thông tin tiêu chí đánh giá chi tiết
            if not rec.review_infor_ids:
                content_dict = self.gen_content_value(rec.job_id)

                recruitment_stage_ids = self.env['recruitment.stage.customize'].search([('hr_job_id', '=', rec.job_id.id)])
                lines_to_create = []
                for line in recruitment_stage_ids:
                    for stage in line.hr_recruitment_stage_id:
                        line_values = {
                            'name': line.criteria,
                            'content': content_dict[line.criteria] if line.criteria in content_dict else '',
                            'stage_name': stage.id
                        }
                        lines_to_create.append((0, 0, line_values))
                rec.review_infor_ids = lines_to_create

            #Tạo thông tin kêt quả đánh giá từng vòng
            if not rec.test_result_ids:
                line_result_to_create = []
                for line in rec.job_id.stage_ids:
                    line_values = {
                        'stage_id': line.id
                    }
                    line_result_to_create.append((0, 0, line_values))
                rec.test_result_ids = line_result_to_create

    reviewed_ids = fields.Many2many(comodel_name='res.users', string='Người đánh giá', compute='_compute_reviewed_ids')

    @api.depends('stage_id', 'job_id')
    def _compute_reviewed_ids(self):
        for rec in self:
            if rec.stage_id and rec.job_id:
                reviewed = self.env['hr.job.reviewed'].search(
                    [('hr_job_id', '=', rec.job_id.id), ('stage_id', '=', rec.stage_id.id)], limit=1)
                rec.reviewed_ids = reviewed.employee_ids.ids
            else:
                rec.reviewed_ids = False

    def open_change_stage_wizard(self, new_stage_id):
        self.ensure_one()
        template_id = self.env['hr.recruitment.stage'].browse(new_stage_id).mapped('template_id')
        if template_id:
            wizard = self.env['applicant.change.stage.wizard'].create({
                'applicant_ids': [(6, 0, self.ids)],
                'stage_id': new_stage_id,
            })

            return {
                'name': 'Change Stage Options',
                'type': 'ir.actions.act_window',
                'res_model': 'applicant.change.stage.wizard',
                'res_id': wizard.id,
                'view_mode': 'form',
                'target': 'new',
                'views': [[self.env.ref('ttb_hr.view_applicant_change_stage_wizard_form').id, 'form']],
            }
    def send_notify(self, message, users, subject=''):
        if not users:
            return
        mail_template_id = 'ttb_approval.notify_record_message_template'
        for record in self:
            if not record.exists():
                continue
            self.message_subscribe(partner_ids=users.mapped('partner_id').ids)
            model_description = self.env['ir.model']._get(record._name).with_context(lang=self.env.user.lang or 'vi_VN').display_name
            values = {
                'object': record,
                'model_description': model_description,
                'message': message,
                'access_link': self.env[self._name]._notify_get_action_link('view', model=record._name, res_id=record.id),
            }
            rendered_body = self.env['ir.qweb']._render(mail_template_id, values)
            if not subject:
                subject = record.display_name
            record.message_notify(
                subject=subject,
                body=rendered_body,
                partner_ids=users.mapped('partner_id').ids,
                record_name=subject,
                subtype_xmlid='mail.mt_comment',
                email_layout_xmlid='mail.mail_notification_light',
                model_description=model_description,
                mail_auto_delete=False,
            )

    def write(self, vals):
        res = super(HrApplicant, self).write(vals)
        if 'stage_id' in vals:
            for rec in self:
                if rec.reviewed_ids:
                    rec.send_notify(message=f'Bạn có yêu cầu đánh giá {rec.stage_id.name} cho vị trí {rec.job_id.name}',
                                    users=rec.reviewed_ids,
                                    subject='Yêu cầu đánh giá tuyển dụng')
        return res

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        for rec in res:
            if rec.reviewed_ids:
                rec.send_notify(message=f'Bạn có yêu cầu đánh giá {rec.stage_id.name} cho vị trí {rec.job_id.name}',
                                 users=rec.reviewed_ids,
                                 subject='Yêu cầu đánh giá tuyển dụng')
        return res

class ReviewInformation(models.Model):
    _name = "review.information"
    _rec_name = 'name'
    _description = "Thông tin đánh giá ứng viên"

    hr_applicant_id = fields.Many2one('hr.applicant', 'Hồ sơ ứng viên')
    name = fields.Char('Tiêu chí')
    content = fields.Text('Nội dung')
    stage_name = fields.Many2one('hr.recruitment.stage', 'Vòng tuyển dụng')
    sequence = fields.Integer('Trình tự', related='stage_name.sequence', store=True)
    is_pass = fields.Selection([('yes', 'Đạt'), ('no', 'Không đạt')], 'Kết quả')
    can_check = fields.Boolean('Có thể đánh giá', compute='_compute_can_check')
    reviewer_id = fields.Many2one('res.users', 'Người đánh giá')

    @api.depends_context('uid')
    @api.depends('hr_applicant_id.reviewed_ids')
    def _compute_can_check(self):
        for rec in self:
            rec.can_check = rec.hr_applicant_id.reviewed_ids and self.env.user in rec.hr_applicant_id.reviewed_ids

    def button_pass_job(self):
        self.is_pass = 'yes'
        self.reviewer_id = self.env.user

    def button_reject_job(self):
        self.is_pass = 'no'
        self.reviewer_id = self.env.user

class TestResult(models.Model):
    _name = "test.result"
    _description = "Kết quả đánh giá ứng viên"

    hr_applicant_id = fields.Many2one('hr.applicant', 'Hồ sơ ứng viên')
    stage_id = fields.Many2one('hr.recruitment.stage', 'Vòng tuyển dụng')
    result = fields.Selection([('yes', 'Đạt'), ('no', 'Không đạt')], 'Kết quả')
    reviewer_id = fields.Many2one('res.users', 'Người đánh giá')
    can_check = fields.Boolean('Có thể đánh giá', compute='_compute_can_check')

    @api.depends_context('uid')
    @api.depends('hr_applicant_id.reviewed_ids')
    def _compute_can_check(self):
        for rec in self:
            rec.can_check = rec.hr_applicant_id.reviewed_ids and self.env.user in rec.hr_applicant_id.reviewed_ids

    def button_pass_stage(self):
        self.result = 'yes'
        self.reviewer_id = self.env.user

    def button_reject_stage(self):
        self.result = 'no'
        self.reviewer_id = self.env.user

