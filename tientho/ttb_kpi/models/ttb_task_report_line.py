from datetime import timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class TtbTaskReportLine(models.Model):
    _name = 'ttb.task.report.line'
    _description = 'Chi tiết đánh giá nhiệm vụ'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'report_id'


    report_id = fields.Many2one(string='Đánh giá nhiệm vụ', comodel_name='ttb.task.report')
    report_cross_id = fields.Many2one('ttb.task.report', string='Phiếu chéo')
    category_id = fields.Many2one(string='Danh mục', comodel_name='ttb.task.category', store=True, related=False)
    sequence = fields.Integer(string='STT', store=True, related=False)
    template_line_id = fields.Many2one(string='Nhiệm vụ', comodel_name='ttb.task.template.line', required=True)
    requirement = fields.Text(string='Yêu cầu cần đạt', related=False, store=True)
    kpi_type = fields.Many2one(string='Loại KPI', comodel_name='ttb.kpi.type', related=False, store=True)
    x_pass = fields.Boolean(string='Đạt', default=False)
    fail = fields.Boolean(string='Không đạt', default=False)
    rate = fields.Float(string='Tỉ trọng', related=False, store=True)
    image = fields.Binary(attachment=True, string="Hình ảnh old")
    image_ids = fields.Many2many(string="Hình ảnh", comodel_name='ir.attachment')
    company_id = fields.Many2one(comodel_name='res.company', string='Công ty', index=True, default=lambda self: self.env.company)
    state = fields.Selection(string='Trạng thái', related='report_id.state', store=True)
    group = fields.Selection(string='Nhóm đánh giá', related='report_id.group', store=True)
    date = fields.Datetime(string='Ngày đánh giá', related='report_id.date', store=True)
    reviewer_id = fields.Many2one(string='Người đánh giá', related='report_id.reviewer_id', store=True)
    kpi_type_id = fields.Many2one(string='Loại KPI', related='report_id.kpi_type_id', store=True)
    user_job_id = fields.Many2one(string='Chức vụ người được đánh giá', related='report_id.user_job_id', store=True)
    user_branch_id = fields.Many2one(string='Cơ sở được đánh giá', related='report_id.user_branch_id', store=True)
    area_id = fields.Many2one(string='Khu vực', related='report_id.area_id', store=True)
    categ_id = fields.Many2one(string='Quầy', related='report_id.categ_id', store=True)
    user_id = fields.Many2one(string='Người được đánh giá', related='report_id.user_id', store=True)
    user_ids = fields.Many2many(string='Nhóm được đánh giá', related='report_id.user_ids')
    solution_plan = fields.Char(string='Phương án xử lý', tracking=True, required=True)
    urgency_level = fields.Selection(string='Mức độ gấp', selection=[('urgent', 'Xử lý gấp'), ('3_days', 'Xử lý 3 ngày'), ('7_days', 'Xử lý trong 7 ngày')], tracking=True, required=True)
    show_solution_fields = fields.Boolean(compute="_compute_show_solution_fields")
    process_status = fields.Selection([
        ('waiting', 'Chờ xử lý'),
        ('approved_plan', 'Đã duyệt phương án'),
        ('waiting_for_approval', 'Chờ duyệt'),
        ('done', 'Hoàn thành'),
    ], string='Trạng thái xử lý', default='waiting', tracking=True, readonly=1)
    processor_id = fields.Many2one('res.users', string='Người xử lý', tracking=True)
    processing_deadline = fields.Date(string='Hạn xử lý', compute='_compute_processing_deadline', store=True)
    approver_id = fields.Many2one('res.users', string='Người duyệt')
    result_image_ids = fields.Many2many('ir.attachment', 'ttb_task_report_line_result_image_rel', 'line_id', 'attachment_id', string='Hình ảnh kết quả')
    show_approve_button = fields.Boolean(compute='_compute_show_approve_button')
    show_approve_solution = fields.Boolean(compute='_compute_show_approve_solution')
    number_votes = fields.Char(string='Số phiếu', related='report_id.number_votes', store=True)
    check_permission_image = fields.Boolean(related='report_id.check_permission_image')
    cluster = fields.Char(string='Cụm')
    standard = fields.Many2many(string='Tiêu chuẩn', comodel_name='ttb.task.template.line.standard')
    rate_cluster = fields.Float(string='Tỉ trọng của cụm')
    criteria = fields.Char(string='Tiêu chí')
    @api.depends('kpi_type_id.code')
    def _compute_show_approve_solution(self):
        for rec in self:
            rec.show_approve_solution = rec.kpi_type_id.code != 'KVC'

    @api.depends('kpi_type_id.code')
    def _compute_show_solution_fields(self):
        for rec in self:
            rec.show_solution_fields = False
            if rec.kpi_type_id.code in ['VM', 'VS', 'KVC'] or rec.kpi_type_id.is_checklist or rec.kpi_type_id.is_checklist_restaurant:
                rec.show_solution_fields = True


    def _compute_show_approve_button(self):
        for line in self:
            user = self.env.user
            is_manager = user.has_group('ttb_kpi.group_ttb_kpi_warehouse_manager') or user.has_group('ttb_kpi.group_ttb_kpi_warehouse_director')
            is_correct_branch = line.report_id.user_branch_id in user.ttb_branch_ids
            line.show_approve_button = is_manager and is_correct_branch

    @api.depends('urgency_level', 'process_status')
    def _compute_processing_deadline(self):
        for line in self:
            if line.urgency_level and line.report_id.date:
                approval_date = line.report_id.date.date()
                if line.urgency_level == 'urgent':
                    line.processing_deadline = approval_date + timedelta(days=1)
                elif line.urgency_level == '3_days':
                    line.processing_deadline = approval_date + timedelta(days=3)
                elif line.urgency_level == '7_days':
                    line.processing_deadline = approval_date + timedelta(days=7)
                else:
                    line.processing_deadline = False
            else:
                line.processing_deadline = False

    def button_approve_solution(self):
        for rec in self:
            if not rec.processor_id:
                raise UserError("Bạn cần điền người xử lý.")

            rec.process_status = 'approved_plan'
            rec.approver_id = self.env.user.id
            self.env['my.task'].create({'task_report_line_id': rec.id})
            rec.message_post(
                body=f"Bạn đã được giao một nhiệm vụ cần xử lý: '{rec.template_line_id.name}'. Vui lòng hoàn thành trước ngày {rec.processing_deadline.strftime('%d-%m-%Y')}.",
                message_type='notification',
                subtype_xmlid='mail.mt_comment',  # Kiểu thông báo bình luận thông thường
                author_id=self.env.user.partner_id.id,  # Người gửi là người dùng hiện tại
                partner_ids=[rec.processor_id.partner_id.id]  # Gửi đến partner của Người xử lý
            )

    def action_create_pr(self):
        self.ensure_one()
        return {
            'name': _('Tạo Yêu cầu mua hàng'),
            'type': 'ir.actions.act_window',
            'res_model': 'ttb.purchase.request',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_origin': self.report_id.name,
            }
        }

    def action_complete_task(self):
        for rec in self:
            rec.process_status = 'waiting_for_approval'

    def action_approve_task(self):
        for rec in self:
            rec.process_status = 'done'

    def action_approve_task_kvc(self):
        for rec in self:
            if self.env.user.employee_id.job_id.name != 'Giám đốc Nhà sách':
                raise UserError("Chỉ người có chức vụ Giám đốc nhà sách mới được duyệt.")
            rec.process_status = 'done'

    def action_reject_task(self):
        for rec in self:
            rec.process_status = 'waiting'
            if rec.report_id.kpi_type_id.code in ['KVC','VSKVC']:
                rec.process_status = 'approved_plan'
            rec.message_post(
                body=f"Bạn đã được giao một nhiệm vụ cần xử lý: '{rec.template_line_id.name}'. Vui lòng hoàn thành trước ngày {rec.processing_deadline.strftime('%d-%m-%Y')}.",
                message_type='notification',
                subtype_xmlid='mail.mt_comment',  # Kiểu thông báo bình luận thông thường
                author_id=self.env.user.partner_id.id,  # Người gửi là người dùng hiện tại
                partner_ids=[rec.processor_id.partner_id.id]  # Gửi đến partner của Người xử lý
            )

    @api.model
    def _cron_send_deadline_reminder(self):
        tomorrow = fields.Date.today() + timedelta(days=1)
        lines = self.search([('processing_deadline', '=', tomorrow), ('process_status', '!=', 'done')])
        for line in lines:
            if line.processor_id:
                line.message_post(
                    body=f"Bạn có nhiệm vụ bị trễ hạn: '{line.template_line_id.name}'. Vui lòng hoàn thành trước ngày {line.processing_deadline.strftime('%d-%m-%Y')}.",
                    message_type='notification',
                    subtype_xmlid='mail.mt_comment',  # Kiểu thông báo bình luận thông thường
                    author_id=self.env.user.partner_id.id,  # Người gửi là người dùng hiện tại
                    partner_ids=[line.processor_id.partner_id.id]  # Gửi đến partner của Người xử lý
                )

    @api.model
    def create(self, vals):
        if not vals.get('fail'):
            vals['process_status'] = False
        record = super().create(vals)
        if (
                record.kpi_type_id
                and record.kpi_type_id.code == 'CSKH'
                and record.group == 'cs'
                and record.report_id
        ):
            record.report_id._recompute_kpi_values()
        return record

    def write(self, vals):
        if 'fail' in vals and not vals['fail']:
            vals['process_status'] = False

        old_data = {}

        if vals.get('x_pass'):
            vals['fail'] = False
        if vals.get('fail'):
            vals['x_pass'] = False

        for line in self:
            old_data[line.id] = {
                'x_pass': line.x_pass,
                'fail': line.fail,
                'image_ids': set(line.image_ids.ids)
            }
        res = super().write(vals)
        for line in self:
            report = line.report_id

            if not report:
                continue

            messages = []

            if 'x_pass' in vals or 'fail' in vals:
                old_pass = old_data[line.id]['x_pass']
                old_fail = old_data[line.id]['fail']
                new_pass = line.x_pass
                new_fail = line.fail

                if (old_pass, old_fail) != (new_pass, new_fail):
                    if new_pass:
                        messages.append("- Kết quả: Đạt")
                    elif new_fail:
                        messages.append("- Kết quả: Không đạt")

            if 'image_ids' in vals:
                old_imgs = old_data[line.id]['image_ids']
                new_imgs = set(line.image_ids.ids)

                added = new_imgs - old_imgs
                removed = old_imgs - new_imgs

                if added:
                    messages.append(f"- Đã thêm ảnh")
                if removed:
                    messages.append(f"- Đã xóa ảnh")

            if messages:
                body = (f"{line.template_line_id.name}" + "".join(messages))
                report.message_post(body=body)

            if line.kpi_type_id.code == 'CSKH' and line.group == 'cs':
                if any(field in vals for field in ['x_pass', 'fail']):
                    if line.report_id:
                        line.report_id._recompute_kpi_values()
        return res

    @api.onchange('x_pass')
    def _onchange_x_pass(self):
        if self.x_pass:
            self.fail = False

    @api.onchange('fail')
    def _onchange_fail(self):
        if self.fail:
            self.x_pass = False

    def button_x_pass(self):
        if self.state == 'done':
            return
        self.x_pass = not self.x_pass
        self._onchange_x_pass()
        if self.kpi_type.code != 'CSKH':
            return {
                    'type': 'ir.actions.act_window',
                    'name': 'Hình ảnh',
                    'res_model': 'ttb.task.report.line',
                    'view_mode': 'form',
                    'view_id': self.env.ref('ttb_kpi.image_pass_ttb_task_report_line_view_form').id,
                    'res_id': self.id,
                    'target': 'new',
                    }
    def button_fail(self):
        if self.state == 'done':
            return
        if self.kpi_type.code == 'CSKH':
            self.fail = not self.fail
            self._onchange_fail()
        if self.kpi_type.code != 'CSKH':
            return {
                    'type': 'ir.actions.act_window',
                    'name': 'Hình ảnh',
                    'res_model': 'ttb.task.report.line',
                    'view_mode': 'form',
                    'view_id': self.env.ref('ttb_kpi.image_ttb_task_report_line_view_form').id,
                    'res_id': self.id,
                    'target': 'new',
                    }

    def button_fail_form(self):
        """
        Hành động này được gọi từ nút "Xác nhận" trên form popup.
        Nó sẽ thay đổi trạng thái và đóng popup.
        """
        self.ensure_one()
        # Thiện copy điều kiện hiển thị trường phương án xử lý vào lệnh if require trường này
        # if not self.report_cross_id:
        if self.kpi_type_id.code in ['KVC', 'VM', 'VS'] or self.kpi_type_id.is_checklist or self.kpi_type_id.is_checklist_restaurant:
            # Thêm kiểm tra bắt buộc ở đây để chắc chắn
            if not self.solution_plan:
                raise UserError("Bạn phải cung cấp phương án.")
            if not self.urgency_level:
                raise UserError("Bạn phải cung cấp thời gian xử lý ")

        # Thay đổi trạng thái
        self.fail = not self.fail  # Giả định là luôn set thành True, không phải đảo ngược
        self._onchange_fail()
        # <<< THAY ĐỔI QUAN TRỌNG: Trả về action để đóng popup
        return {'type': 'ir.actions.act_window_close'}

    def action_open_form(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Chi tiết đánh giá nhiệm vụ',
            'res_model': 'ttb.task.report.line',
            'view_mode': 'form',
            'view_id': self.env.ref('ttb_kpi.ttb_task_report_line_view_form').id,
            'res_id': self.id,
            'target': 'current',
        }

    def action_open_image(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Chụp ảnh',
            'res_model': 'ttb.task.report.line',
            'view_mode': 'form',
            'view_id': self.env.ref('ttb_kpi.image_ttb_task_report_line_view_form').id,
            'res_id': self.id,
            'target': 'current',
        }

    def button_filterd_date(self):
        popup_id = self.env['ttb.popup.filtered'].search([('create_uid', '=', self.env.uid), ('res_model', '=', self._name)], limit=1)
        if not popup_id:
            popup_id = self.env['ttb.popup.filtered'].create({'res_model': self._name})
        action = self.env["ir.actions.actions"]._for_xml_id("ttb_kpi.ttb_popup_filtered_action")
        action["context"] = {'active_model': self._name}
        action['target'] = 'new'
        action['res_id'] = popup_id.id
        return action
