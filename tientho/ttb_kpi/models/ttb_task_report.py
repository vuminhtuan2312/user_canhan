from datetime import datetime, time, date, timedelta
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)
class TtbTaskReport(models.Model):
    _name = 'ttb.task.report'
    _description = 'Đánh giá nhiệm vụ'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _mail_post_access = 'read'

    @api.model
    def default_get(self, fields):
        result = super(TtbTaskReport, self).default_get(fields)
        if self._context.get('kpi_type_id', False) == 'VM':
            result['kpi_type_id'] = self.env.ref('ttb_kpi.ttb_kpi_type_vm')
        if self._context.get('kpi_type_id', False) == 'VS':
            result['kpi_type_id'] = self.env.ref('ttb_kpi.ttb_kpi_type_vs')
        if self._context.get('kpi_type_id', False) == 'CSKH':
            result['kpi_type_id'] = self.env.ref('ttb_kpi.ttb_kpi_type_cskh')
        if self._context.get('kpi_type_id', False) == 'ANAT':
            result['kpi_type_id'] = self.env.ref('ttb_kpi.ttb_kpi_type_anat')
        if self._context.get('kpi_type_id', False) == 'PCCC':
            result['kpi_type_id'] = self.env.ref('ttb_kpi.ttb_kpi_type_pccc')
        if self._context.get('kpi_type_id', False) == 'KVC':
            result['kpi_type_id'] = self.env.ref('ttb_kpi.ttb_kpi_type_kvc')
        if self._context.get('kpi_type_id', False) == 'VSKVC':
            result['kpi_type_id'] = self.env.ref('ttb_kpi.ttb_kpi_type_vs_kvc')
        return result

    name = fields.Char(string='Mã đánh giá', required=True, readonly=True, default='Mới', copy=False)
    date = fields.Datetime(string='Ngày đánh giá', required=False, readonly=False, copy=False)
    reviewer_id = fields.Many2one(string='Người đánh giá', comodel_name='res.users', required=False, readonly=True, copy=False)
    reviewer_job_id = fields.Many2one(string='Chức vụ người đánh giá', comodel_name='hr.job', compute='_compute_reviewer_job_id', store=True, tracking=True)
    group = fields.Selection(string='Nhóm đánh giá', selection=[('region_manager', 'Quản lý vùng'), ('cross_dot_area_manager', 'Giám đốc vùng chấm chéo'),('branch_mannager', 'Quản lý cơ sở'), ('cs', 'Trải nghiệm khách hàng'), ('manager', 'Quản lý trực tiếp')], default='manager', required=True, tracking=True)
    kpi_type_id = fields.Many2one(string='Loại KPI', comodel_name='ttb.kpi.type', required=True)
    code = fields.Char(string='Mã Loại KPI', related='kpi_type_id.code', readonly=True)
    area_id = fields.Many2one(string='Khu vực', comodel_name='ttb.area', tracking=True)
    categ_id = fields.Many2one(string='Quầy', comodel_name='product.category', domain="[('category_level', '=', 1)]", tracking=True)
    user_ids = fields.Many2many(string='Nhóm được đánh giá', comodel_name='res.users', tracking=True)

    user_job_id = fields.Many2one(string='Chức vụ người được đánh giá', comodel_name='hr.job', required=False, tracking=True)
    user_warehouse_id = fields.Many2one(string='Cơ sở người được đánh giá', comodel_name='stock.warehouse', required=False)
    user_branch_id = fields.Many2one(string='Cơ sở được đánh giá', comodel_name='ttb.branch', required=True, tracking=True)
    user_id = fields.Many2one(string='Người được đánh giá', comodel_name='res.users', required=False, tracking=True)
    domain_user = fields.Many2many(string='Domain Người được đánh giá', comodel_name='res.users', compute='_compute_domain_user_id')
    report_status = fields.Selection([
        ('on_time', 'Đúng hạn'),
        ('overdue', 'Quá hạn'),
    ], string='Trạng thái đánh giá', tracking=True)
    average_rate_report = fields.Float(string='Điểm trung bình', related='kpi_ids.average_rate', store=True)
    period = fields.Integer(string='Kỳ sinh phiếu', readonly=True)
    creation_month = fields.Integer(string='Tháng sinh phiếu', readonly=True)
    show_check_list_fields = fields.Boolean(compute="_compute_show_check_list_fields")
    has_failed_lines = fields.Boolean(compute="_compute_has_failed_lines")
    show_tb_fail_mission = fields.Boolean(compute="_compute_show_tab_mission")
    result_task = fields.Selection([
        ('pass', 'Đạt'),
        ('fail', 'Không đạt'),
    ], string='Kết quả phiếu', compute='_compute_result', store=True)
    final_score = fields.Float(
        string="Điểm cuối",
        readonly=True
    )
    origin_report_id = fields.Many2one(
        string="Phiếu đánh giá gốc",
        comodel_name='ttb.task.report',
        tracking=True
    )
    note = fields.Text(string="Ghi chú", tracking=True)
    state = fields.Selection(string='Trạng thái', selection=[('new', 'Mới'), ('reviewing', 'Đang đánh giá'), ('done', 'Hoàn thành'), ('cancel', 'Hủy'), ('waiting', 'Chờ duyệt'), ('overdue','Trễ hạn'),('awaiting_approval','Gửi duyệt mở phiếu')], default='new', tracking=True)
    line_ids = fields.One2many(string='Danh sách công việc', comodel_name='ttb.task.report.line', inverse_name='report_id')
    line_id_cross_dot = fields.One2many('ttb.task.report.line', inverse_name='report_cross_id', string='Danh sách nhiệm vụ chấm chéo')
    mismatch_ids = fields.One2many('ttb.task.report.mismatch.line', inverse_name='report_id', string='Tiêu chí lệch')
    kpi_ids = fields.One2many(string='KPI', comodel_name='ttb.task.report.kpi', inverse_name='report_id')
    hide_button_cancel = fields.Boolean(string='Hiện button hủy phiếu', compute='_compute_hide_button_cancel')
    cei_id = fields.Many2one(string='Phiếu điểm CEI', comodel_name='ttb.cei.score')
    manager_score = fields.Float(string='Điểm quản lý', related="cei_id.manager_score", store=True)
    branch_manager_score = fields.Float(string='Điểm giám đốc', related="cei_id.branch_manager_score", store=True)
    show_agree_button = fields.Boolean(compute="_compute_show_agree_button", string="Hiển thị nút Đồng thuận")
    readonly_area = fields.Boolean(compute="_compute_readonly_area")
    domain_origin = fields.Binary(string='Domain Phiếu đánh giá gốc', compute='_compute_domain_origin')
    date_origin = fields.Date(string='Ngày đánh giá phiếu gốc')
    image_vote = fields.Many2many(string='Ảnh', comodel_name='ir.attachment', tracking=True)
    approver_ids = fields.One2many('ttb.task.report.approver', inverse_name='report_id', string='Người phê duyệt')
    show_button_approval_reject = fields.Boolean(string='Được xem phiếu duyệt lại hay không', compute='_def_show_button_approval_reject')
    previous_state = fields.Char(string="Trạng thái cũ",store=True)
    show_button_request_approval = fields.Boolean(string='Được xem nút đề xuất mở phiếu',compute='_def_show_button_reopen_approval_reject')
    number_votes = fields.Char(string='Số phiếu')
    total_rate = fields.Float(string='Điểm theo tỉ trọng tính', related='kpi_ids.total_rate', store=True)
    total_rate_cluster = fields.Float(string='Điểm tỷ trọng theo cụm', related='kpi_ids.total_rate_cluster', store=True)
    active = fields.Boolean(default=True)
    deadline = fields.Date(string='Hạn đánh giá')
    image_identification = fields.Many2many(
        comodel_name='ir.attachment',
        relation='ttb_task_report_image_identification_rel',
        column1='report_id',
        column2='attachment_id',
        string='Ảnh nhận dạng nhân viên',
        tracking=True
    )
    check_permission_image = fields.Boolean(compute="_compute_check_permission_image")
    manager_id = fields.Many2one('hr.employee', string='Quản lý trực tiếp')
    gsc_evaluated_at = fields.Datetime(string='Thời điểm GSC đánh giá xong', tracking=True)
    sla_status = fields.Selection([('on_time', 'Đúng hạn'), ('overdue_24h', 'Quá hạn CS (24h)'), ('overdue_48h', 'Quá hạn GSC (48h)')], string='Trạng thái SLA', default='on_time', tracking=True)
    has_fail = fields.Boolean(string='Phiếu không đạt', compute='_compute_has_fail', store=True)
    image_uploaded_by = fields.Many2one(string='Người upload ảnh', comodel_name='res.users', tracking=True, readonly=True)
    additional_image = fields.Boolean(string='Trạng thái bổ sung ảnh', default=False)
    user_group = fields.Integer(string='Nhóm', help='Nhóm từ 1-4 cho việc xoay vòng tạo task')
    rotation_period = fields.Integer(string='Kỳ xoay vòng', help='Kỳ 1-4 trong tháng')
    is_weekend_task = fields.Boolean(string='Phiếu cuối tuần', help='Đánh dấu phiếu được tạo vào cuối tuần')
    day_type = fields.Selection([
        ('weekday', 'Ngày thường'),
        ('weekend', 'Cuối tuần')
    ], string='Loại ngày', help='Phân loại phiếu được tạo vào ngày thường hay cuối tuần', index=True)

    cancel_reason_id = fields.Many2one('ttb.cancel.reason', string='Lý do hủy phiếu', readonly=True, tracking=True)
    cs_agreement = fields.Selection([('agree', 'Đồng thuận'), ('disagree', 'Không đồng thuận')], string='Ý kiến cơ sở', tracking=True)
    can_edit_cs_agreement = fields.Boolean(compute='_compute_can_edit_cs_agreement')
    show_btn_base_confirm = fields.Boolean(compute='_compute_show_btn_base_confirm')
    base_confirmed = fields.Boolean(default=False)
    sla_start_datetime = fields.Datetime(string="Thời điểm bắt đầu SLA", tracking=True)
    upper_level_process = fields.Boolean(string='Cấp trên xử lý', default=False, tracking=True)
    upper_response_note = fields.Text(string="Kết quả chốt", tracking=True)
    upper_response_done = fields.Boolean(string="Cấp trên phản hồi kết quả", default=False, tracking=True)

    def _compute_can_edit_cs_agreement(self):
        now = fields.Datetime.now()
        for rec in self:
            if not rec.gsc_evaluated_at:
                rec.can_edit_cs_agreement = True
                continue

            delta_hours = (now - rec.gsc_evaluated_at).total_seconds() / 3600
            rec.can_edit_cs_agreement = delta_hours < 24

    def _compute_show_btn_base_confirm(self):
        now = fields.Datetime.now()
        for rec in self:
            rec.show_btn_base_confirm = False
            if (
                    rec.state == 'waiting'
                    and rec.has_fail
                    and rec.gsc_evaluated_at
            ):
                delta_hours = (now - rec.gsc_evaluated_at).total_seconds() / 3600
                if delta_hours < 24:
                    rec.show_btn_base_confirm = True

    def button_base_confirm(self):
        for rec in self:
            if not rec.can_edit_cs_agreement:
                raise UserError('Phiếu đã quá hạn 24h, không thể xác nhận.')

            if not rec.cs_agreement:
                raise UserError('Vui lòng chọn Đồng thuận hoặc Không đồng thuận.')

            employee = rec.user_id.employee_id
            ma_phieu = rec.name or ''
            code_employee = employee.ttb_code or ''
            name_employee = employee.name
            employee_display = f"{code_employee} - {name_employee}" if code_employee else name_employee
            if rec.cs_agreement == 'agree':
                rec.write({
                    'state': 'done'
                })

                if rec.user_id.partner_id:
                    rec.message_notify(
                        subject="Phiếu TNKH không đạt",
                        body=f"Phiếu TNKH không đạt {ma_phieu} của nhân viên {employee_display} đã hoàn thành với sự đồng thuận kết quả từ cơ sở",
                        partner_ids=[rec.user_id.partner_id.id],
                        subtype_xmlid="mail.mt_comment",
                        email_layout_xmlid=False,
                        email_add_signature=False
                    )

                # Gửi thông báo cho quản lý của nhân viên đó
                manager_emp = employee.parent_id
                if manager_emp and manager_emp.user_id and manager_emp.user_id.partner_id:
                    rec.message_notify(
                        subject="Phiếu TNKH không đạt",
                        body=f"Phiếu TNKH không đạt {ma_phieu} của nhân viên {employee_display} đã hoàn thành với sự đồng thuận kết quả từ cơ sở",
                        partner_ids=[manager_emp.user_id.partner_id.id],
                        subtype_xmlid="mail.mt_comment",
                        email_layout_xmlid=False,
                        email_add_signature=False
                    )

                # Gửi thông báo cho giám đốc nhà sách
                director_emp = manager_emp.parent_id if manager_emp else False
                if director_emp and director_emp.user_id and director_emp.user_id.partner_id:
                    rec.message_notify(
                        subject="Phiếu TNKH không đạt",
                        body=f"Phiếu TNKH không đạt {ma_phieu} của nhân viên {employee_display} đã hoàn thành với sự đồng thuận kết quả từ cơ sở",
                        partner_ids=[director_emp.user_id.partner_id.id],
                        subtype_xmlid="mail.mt_comment",
                        email_layout_xmlid=False,
                        email_add_signature=False
                    )
                partner = rec.reviewer_id.partner_id
                if partner:
                    rec.message_notify(
                        subject="Phiếu TNKH đã được đồng thuận",
                        body=f"Cơ sở đã phản hồi đồng thuận phiếu TNKH {ma_phieu} của nhân viên {employee_display} bạn thực hiện chấm",
                        partner_ids=[partner.id],
                        subtype_xmlid="mail.mt_comment",
                        email_layout_xmlid=False,
                        email_add_signature=False
                    )
            elif rec.cs_agreement == 'disagree':
                now = fields.Datetime.now()
                rec.sudo().write({
                    'sla_start_datetime': now,
                    'sla_status': 'on_time',
                    'base_confirmed': True
                })
                partner = rec.reviewer_id.partner_id
                if partner:
                    rec.message_notify(
                        subject="Phiếu lỗi không đồng thuận",
                        body=f"Cơ sở đã phản hồi không đồng thuận phiếu TNKH {ma_phieu} của nhân viên {employee_display} bạn thực hiện chấm",
                        partner_ids=[partner.id],
                        subtype_xmlid="mail.mt_comment",
                        email_layout_xmlid=False,
                        email_add_signature=False
                    )
    def action_transfer_upper_level(self):
        for rec in self:
            if rec.cs_agreement != 'disagree':
                raise UserError("Chỉ chuyển cấp trên khi cơ sở không đồng thuận.")
            rec.upper_level_process = True
            rec.notify_tnkh_manager()

    def notify_tnkh_manager(self):
        group_tn_cskh = self.env.ref('ttb_kpi.group_ttb_kpi_tn_cskh', raise_if_not_found=False)
        if not group_tn_cskh:
            return

        partners = group_tn_cskh.users.mapped('partner_id').filtered(lambda p: p)

        for rec in self:
            if not rec.user_id or not rec.user_id.employee_id:
                continue

            if not partners:
                continue

            employee = rec.user_id.employee_id
            ma_phieu = rec.name or ''
            code_employee = employee.ttb_code or ''
            name_employee = employee.name
            employee_display = f"{code_employee} - {name_employee}" if code_employee else name_employee

            # Gửi thông báo đến trưởng nhóm GSC
            rec.message_notify(
                subject="Phiếu TNKH không đạt",
                body=f"Phiếu TNKH {ma_phieu} không đạt đã được chuyển lên trưởng nhóm giám sát camera xử lý.",
                partner_ids=partners.ids,
                subtype_xmlid="mail.mt_comment",
                email_layout_xmlid=False,
                email_add_signature=False
            )
            # Gửi thông báo cho nhân viên được chấm
            if rec.user_id.partner_id:
                rec.message_notify(
                    subject="Phiếu TNKH không đạt",
                    body=f"Bạn có phiếu TNKH {ma_phieu} không đạt đã được chuyển lên trưởng nhóm giám sát camera xử lý",
                    partner_ids=[rec.user_id.partner_id.id],
                    subtype_xmlid="mail.mt_comment",
                    email_layout_xmlid=False,
                    email_add_signature=False
                )

            # Gửi thông báo cho quản lý của nhân viên đó
            manager_emp = employee.parent_id
            if manager_emp and manager_emp.user_id and manager_emp.user_id.partner_id:
                rec.message_notify(
                    subject="Phiếu TNKH không đạt",
                    body=(
                        f"Bộ phận bạn có phiếu TNKH {ma_phieu} của nhân viên {employee_display} không đạt đã được chuyển lên trưởng nhóm giám sát camera xử lý "
                    ),
                    partner_ids=[manager_emp.user_id.partner_id.id],
                    subtype_xmlid="mail.mt_comment",
                    email_layout_xmlid=False,
                    email_add_signature=False
                )

            # Gửi thông báo cho giám đốc nhà sách
            director_emp = manager_emp.parent_id if manager_emp else False
            if director_emp and director_emp.user_id and director_emp.user_id.partner_id:
                rec.message_notify(
                    subject="Phiếu TNKH không đạt",
                    body=(
                        f"Cơ sở bạn có phiếu TNKH {ma_phieu} của nhân viên {employee_display} không đạt đã được chuyển lên trưởng nhóm giám sát camera xử lý"
                    ),
                    partner_ids=[director_emp.user_id.partner_id.id],
                    subtype_xmlid="mail.mt_comment",
                    email_layout_xmlid=False,
                    email_add_signature=False
                )
    def action_upper_finalize(self):
        for rec in self:
            if not rec.upper_response_note:
                raise UserError("Vui lòng nhập kết quả chốt trước khi hoàn thành.")

            employee = rec.user_id.employee_id
            ma_phieu = rec.name or ''
            code_employee = employee.ttb_code or ''
            name_employee = employee.name
            employee_display = f"{code_employee} - {name_employee}" if code_employee else name_employee

            rec.upper_response_done = True
            rec.state = 'done'

            if rec.user_id.partner_id:
                rec.message_notify(
                    subject="Phiếu TNKH không đạt",
                    body=f"Phiếu TNKH không đạt {ma_phieu} của nhân viên {employee_display} đã hoàn thành theo kết quả trao đổi cuối cùng.",
                    partner_ids=[rec.user_id.partner_id.id],
                    subtype_xmlid="mail.mt_comment",
                    email_layout_xmlid=False,
                    email_add_signature=False
                )

            # Gửi thông báo cho quản lý của nhân viên đó
            manager_emp = employee.parent_id
            if manager_emp and manager_emp.user_id and manager_emp.user_id.partner_id:
                rec.message_notify(
                    subject="Phiếu TNKH không đạt",
                    body=f"Phiếu TNKH không đạt {ma_phieu} của nhân viên {employee_display} đã hoàn thành theo kết quả trao đổi cuối cùng.",
                    partner_ids=[manager_emp.user_id.partner_id.id],
                    subtype_xmlid="mail.mt_comment",
                    email_layout_xmlid=False,
                    email_add_signature=False
                )

            # Gửi thông báo cho giám đốc nhà sách
            director_emp = manager_emp.parent_id if manager_emp else False
            if director_emp and director_emp.user_id and director_emp.user_id.partner_id:
                rec.message_notify(
                    subject="Phiếu TNKH không đạt",
                    body=f"Phiếu TNKH không đạt {ma_phieu} của nhân viên {employee_display} đã hoàn thành theo kết quả trao đổi cuối cùng.",
                    partner_ids=[director_emp.user_id.partner_id.id],
                    subtype_xmlid="mail.mt_comment",
                    email_layout_xmlid=False,
                    email_add_signature=False
                )

            # Gửi thông báo đến người chấm
            partner = rec.reviewer_id.partner_id
            if partner:
                rec.message_notify(
                    subject="Chốt kết quả phiếu",
                    body=f"Cấp trên đã chốt kết quả phiếu TNKH {ma_phieu} của nhân viên {employee_display} bạn thực hiện chấm",
                    partner_ids=[partner.id],
                    subtype_xmlid="mail.mt_comment",
                    email_layout_xmlid=False,
                    email_add_signature=False
                )
    def action_open_cancel_wizard(self):
        self.ensure_one()
        return {
            'name': _('Xác nhận hủy phiếu'),
            'type': 'ir.actions.act_window',
            'res_model': 'ttb.task.report.cancel.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_report_id': self.id},
        }

    def write(self, vals):
        res = super().write(vals)

        # Ghi nhận người upload ảnh
        if 'image_identification' in vals:
            for rec in self:
                if rec.image_identification:
                    last_attach = rec.image_identification.sorted(
                        key=lambda a: a.create_date or fields.Datetime.now()
                    )[-1]
                    rec.image_uploaded_by = last_attach.create_uid
                    rec.additional_image = True
        return res

    @api.depends('line_ids.fail')
    def _compute_has_fail(self):
        for rec in self:
            rec.has_fail = bool(rec.line_ids.filtered(lambda l: l.fail))

    def _compute_check_permission_image(self):
        user = self.env.user
        for rec in self:
            rec.check_permission_image = False
            if rec.kpi_type_id and rec.kpi_type_id.code == 'CSKH' and rec.group == 'cs':
                if not any(user.has_group(group) for group in [
                    'ttb_kpi.group_ttb_kpi_tnkh_manager',
                    'ttb_kpi.group_ttb_kpi_nv_cskh',
                    'ttb_kpi.group_ttb_kpi_tn_cskh',
                    'base.group_system'
                ]):
                    rec.check_permission_image = True

    @api.depends("kpi_ids.total_rate")
    def _compute_result(self):
        for rec in self:
            if rec.group == 'cs' and rec.kpi_type_id.code == 'CSKH' and rec.number_votes == 'T2':
                rates = rec.kpi_ids.mapped('total_rate')
                if rates and all(rate == 1 for rate in rates):
                    rec.result_task = 'pass'
                else:
                    rec.result_task = 'fail'

    @api.depends('kpi_type_id.code')
    def _compute_show_tab_mission(self):
        for rec in self:
            rec.show_tb_fail_mission = False
            if rec.kpi_type_id.code in ['KVC', 'VM', 'VS'] or rec.kpi_type_id.is_checklist or rec.kpi_type_id.is_checklist_restaurant:
                rec.show_tb_fail_mission = True

    def _compute_has_failed_lines(self):
        for rec in self:
            rec.has_failed_lines = any(line.fail for line in rec.line_ids)
    @api.depends('kpi_type_id.code')
    def _compute_show_check_list_fields(self):
        for rec in self:
            rec.show_check_list_fields = False
            if rec.kpi_type_id.is_checklist:
                rec.show_check_list_fields = True

    @api.depends('user_branch_id', 'user_job_id')
    def _compute_domain_user_id(self):
        for rec in self:
            domain = []
            if rec.user_job_id:
                domain.append(('employee_id.job_id', '=', rec.user_job_id.id))
            if rec.user_branch_id:
                domain.append(('ttb_branch_ids', 'in', [rec.user_branch_id.id]))
            rec.domain_user = self.env['res.users'].with_company(rec.env.company).sudo().search(domain).ids

    @api.onchange('user_job_id', 'user_branch_id')
    def _onchange_job_branch(self):
        if self.user_job_id and self.user_job_id.name == 'Giám đốc Nhà sách' and self.user_branch_id:
            user = self.env['res.users'].search([
                ('employee_id.job_id.name', '=', 'Giám đốc Nhà sách'),
                ('ttb_branch_ids', 'in', [self.user_branch_id.id])
            ], limit=1)
            self.user_id = user or False

    # Nút duyệt mở lại
    @api.depends('group', 'state')
    def _def_show_button_approval_reject(self):
        current_user = self.env.user
        for rec in self:
            show_button = False
            if rec.state == 'awaiting_approval':
                # Xét cho admin nhìn được
                if self.env.user.has_group('base.group_system'):
                    show_button = True
                else:
                    is_approver = rec.approver_ids.filtered(lambda approver: approver.user_id.id == current_user.id and approver.state == 'waiting')
                    if is_approver:
                        show_button = True
            rec.show_button_approval_reject = show_button
    # Nút đề xuất mở lại
    @api.depends('state', 'group')
    def _def_show_button_reopen_approval_reject(self):
        for rec in self:
            rec.show_button_request_approval = False  # đặt mặc định

            if rec.state == 'overdue':
                # Xét cho admin nhìn được
                if self.env.user.has_group('base.group_system'):
                    rec.show_button_request_approval = True
                elif self.env.user.has_group('ttb_kpi.group_ttb_kpi_warehouse_manager'):
                    rec.show_button_request_approval = True
                elif self.env.user.has_group('ttb_kpi.group_ttb_kpi_warehouse_director'):
                    rec.show_button_request_approval = True
                elif self.env.user.has_group('ttb_kpi.group_ttb_kpi_asm'):
                    rec.show_button_request_approval = True
                elif rec.group == 'cs' and rec.kpi_type_id.code == 'CSKH':
                    rec.show_button_request_approval = False

    @api.depends('user_id', 'kpi_type_id')
    def _compute_domain_origin(self):
        for record in self:
            domain = [
                ('kpi_type_id', '=', record.kpi_type_id.id),
                ('state', '=', 'done')
            ]
            if record.user_id:
                domain.append(('user_id', '=', record.user_id.id))
            record.domain_origin= domain

    @api.onchange('origin_report_id')
    def _onchange_origin_date(self):
        if self.origin_report_id and self.origin_report_id.date:
            self.date_origin = self.origin_report_id.date
        else:
            self.date_origin = False

    def _compute_readonly_area(self):
        for rec in self:
            rec.readonly_area = rec.kpi_type_id.code in ['CSKH']
    @api.depends('reviewer_id', 'state')
    @api.depends_context('uid')
    def _compute_hide_button_cancel(self):
        for rec in self:
            hide_button_cancel = False
            if rec.state == 'done' and (rec.reviewer_id == self.env.user or self.env.user.has_group('ttb_kpi.group_ttb_kpi_nv_cskh') or self.env.user.has_group('ttb_kpi.group_ttb_kpi_tnkh_manager')):
                hide_button_cancel = True
            rec.hide_button_cancel = hide_button_cancel

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name', False) == 'Mới':
                vals['name'] = self.env['ir.sequence'].next_by_code('seg.ttb.task.report')
        return super(TtbTaskReport, self).create(vals_list)

    @api.depends('reviewer_id')
    def _compute_reviewer_job_id(self):
        for rec in self:
            rec.reviewer_job_id = rec.reviewer_id.employee_id.job_id.id

    def button_filter_date(self):
        popup_id = self.env['ttb.popup.filtered'].search(
            [('create_uid', '=', self.env.uid), ('res_model', '=', self._name)], limit=1)
        if not popup_id:
            popup_id = self.env['ttb.popup.filtered'].create({'res_model': self._name})
        action = self.env['ir.actions.actions']._for_xml_id('ttb_kpi.ttb_popup_filtered_action')
        action['context'] = {'active_model': self._name}
        action['target'] = 'new'
        action['res_id'] = popup_id.id
        return action

    # Action reset phiếu chấm CSKH
    kpi_is_cskh = fields.Boolean(compute='_compute_is_cskh')

    @api.depends('kpi_type_id.code')
    def _compute_is_cskh(self):
        for rec in self:
            rec.kpi_is_cskh = rec.kpi_type_id.code == 'CSKH'

    def action_reset_review(self):
        for rec in self:
            rec.sudo().line_ids.unlink()
            rec.sudo().kpi_ids.unlink()
        self.sudo().write({
            'state': 'new',
            'deadline': (datetime.now() + timedelta(days=2)).date(),
        })

    def _check_duplicate_evaluation(self):
        today = fields.Date.context_today(self)
        start_dt = datetime.combine(today, time.min)
        end_dt = datetime.combine(today, time.max)
        for rec in self:
            domain = [
                ('id', '!=', rec.id),
                ('kpi_type_id', '=', rec.kpi_type_id.id),
                ('group', '=', rec.group),
                ('date', '>=', start_dt),
                ('date', '<=', end_dt),
                ('state', '=', 'done'),
                ('reviewer_id', '=', self.env.uid),
                ('user_branch_id', '=', rec.user_branch_id.id)
            ]
            kpi_type = rec.kpi_type_id.code

            if kpi_type == 'CSKH' and rec.group == 'cs':
                continue

            if rec.kpi_type_id.is_checklist or rec.kpi_type_id.is_checklist_restaurant:
                continue

            # Điều kiện riêng theo loại KPI
            if kpi_type == 'CSKH':
                domain += [('user_id', '=', rec.user_id.id)]
            elif kpi_type in ['VS','KVC','VSKVC']:
                domain += [('area_id', '=', rec.area_id.id)]
            elif kpi_type == 'VM':
                domain += [('categ_id', '=', rec.categ_id.id)]

            duplicated = self.env['ttb.task.report'].sudo().search(domain, limit=1)
            if duplicated:
                raise UserError("Không được phép đánh giá 2 phiếu trong cùng 1 ngày cho cùng 1 đối tượng")

    def button_start(self):
        # self._check_duplicate_evaluation()
        if self.kpi_type_id.code == 'CSKH' and self.env.user.employee_id.job_id.name == 'Quản lý Nhà sách' and self.group == 'cs':
            raise UserError('Quản lý nhà sách không được chấm phiếu đánh giá của trải nghiệm khách hàng. ')
        if (
                self.kpi_type_id.code == 'KVC'
                and  not any(
                    self.env.user.has_group(group)
                    for group in [
                        'ttb_kpi.group_ttb_kpi_warehouse_manager',
                        'ttb_kpi.group_ttb_kpi_warehouse_director',
                        'ttb_kpi.group_ttb_kpi_asm',
                        'ttb_kpi.group_ttb_kpi_vhkd_director'
                    ]
                )
        ):
            raise UserError('Bạn không có quyền chấm KPI của khu vui chơi')
        for rec in self:
            today = date.today()
            if rec.state == 'reviewing':
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'type': 'danger',
                        'sticky': True,
                        'message': "Phiếu đang được đánh giá. Vui lòng tải lại trang! ",
                    }
                }
            kpi_code = rec.kpi_type_id.code if rec.kpi_type_id and rec.kpi_type_id.code else ""
            if not (rec.kpi_type_id.is_checklist or rec.kpi_type_id.code == 'KVC'):
                if not rec.user_id and not rec.user_ids:
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'type': 'danger',
                            'sticky': True,
                            'message': "Bạn chưa chọn người được đánh giá hoặc nhóm được đánh giá. Vui lòng chọn lại trước khi hoàn thành.",
                        }
                    }
            domain = [
                ('date_from', '<=', today),
                ('date_to', '>=', today),
                ('kpi_type_id', '=', rec.kpi_type_id.id),
            ]

            if rec.kpi_type_id.is_checklist:
                domain += [
                    '|', ('job_ids', '=', False),
                    ('job_ids', 'in', [rec.reviewer_job_id.id]),
                ]
            else:
                domain += [
                    '&',
                    '|', ('job_ids', '=', False), ('job_ids', '=', rec.user_job_id.id),
                    '&',
                    '|', ('area_ids', '=', False), ('area_ids', '=', rec.area_id.id),
                    '|', ('categ_ids', '=', False), ('categ_ids', '=', rec.categ_id.id),
                ]
            task_template = self.env['ttb.task.template'].sudo().search(domain, order='id desc', limit=1)
            if task_template:
                task_template_line = task_template.sudo().line_ids.filtered_domain(['|',('applied_job_ids', '=', False), ('applied_job_ids', '=', rec.user_job_id.id)])
                if not task_template_line and not rec.kpi_type_id.is_checklist and not rec.kpi_type_id.code == 'KVC':
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'type': 'danger',
                            'sticky': True,
                            'message': "Thông báo: Không tìm thấy Danh sách công việc. Vui lòng kiểm tra lại các tiêu chí đã chọn! (Đặc biệt là 2 tiêu chí Chức vụ và Khu vực)",
                        }
                    }
                for line in task_template_line:
                    vals = {
                        'template_line_id': line.id,
                        'category_id': line.category_id.id,
                        'sequence': line.sequence,
                        'requirement': line.requirement,
                        'kpi_type': line.kpi_type.id,
                        'rate': line.rate,
                        'cluster': line.cluster,
                        'standard': line.standard.ids,
                        'rate_cluster': line.rate_cluster,
                        'criteria': line.criteria
                    }

                    vals_main = vals.copy()
                    vals_main['report_id'] = rec.id
                    self.env['ttb.task.report.line'].sudo().create(vals_main)

                    if rec.group == 'region_manager':
                        vals_cross = vals.copy()
                        vals_cross['report_cross_id'] = rec.id
                        self.env['ttb.task.report.line'].sudo().create(vals_cross)
            elif not rec.kpi_type_id.is_checklist or not rec.kpi_type_id.code == 'KVC':
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'type': 'danger',
                        'sticky': True,
                        'message': "Thông báo: Không tìm thấy Danh sách công việc. Vui lòng kiểm tra lại các tiêu chí đã chọn! (Đặc biệt là 2 tiêu chí Chức vụ và Khu vực)",
                    }
                }
            if kpi_code == 'CSKH' and rec.group == 'cs':
                line_ids = rec.line_ids.filtered(lambda l: l.kpi_type)

                kpi_groups = {}
                for line in line_ids:
                    kpi_groups.setdefault(line.kpi_type.id, []).append(line)

                for kpi_id, lines in kpi_groups.items():
                    self.env['ttb.task.report.kpi'].sudo().create({
                        'report_id': rec.id,
                        'kpi_type': kpi_id,
                        'number_of_item': len(lines),
                        'total_rate': 0,
                        'average_rate': 0,
                    })
            rec.state = 'reviewing'

    def button_done(self):
        # self._check_duplicate_evaluation()
        if self.kpi_type_id.code == 'CSKH' and self.env.user.employee_id.job_id.name == 'Quản lý Nhà sách' and self.group == 'cs':
            raise UserError('Quản lý nhà sách không được chấm phiếu đánh giá của trải nghiệm khách hàng. ')
        if (
                self.kpi_type_id.code == 'KVC'
                and  not any(
                    self.env.user.has_group(group)
                    for group in [
                        'ttb_kpi.group_ttb_kpi_warehouse_manager',
                        'ttb_kpi.group_ttb_kpi_warehouse_director',
                        'ttb_kpi.group_ttb_kpi_asm',
                        'ttb_kpi.group_ttb_kpi_vhkd_director'
                    ]
                )
        ):
            raise UserError('Bạn không có quyền chấm KPI của khu vui chơi')
        for rec in self:
            check_line_ids = rec.line_ids.filtered_domain([('fail', '=', False), ('x_pass', '=', False)])
            check_line_id_cross_dot = rec.line_id_cross_dot.filtered_domain([('fail', '=', False), ('x_pass', '=', False)])
            check_mismatch_ids = rec.mismatch_ids.filtered_domain([('fail', '=', False), ('x_pass', '=', False)])
            if check_line_ids:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'type': 'danger',
                        'sticky': True,
                        'message': "Cần đánh giá tất cả các tiêu chí trước khi hoàn thành",
                    }
                }
            if rec.group == 'region_manager' and (check_line_id_cross_dot or check_mismatch_ids):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'type': 'danger',
                        'sticky': True,
                        'message': "Cần đánh giá tất cả các tiêu chí trước khi hoàn thành",
                    }
                }
            if rec.kpi_type_id.code == 'CSKH' and rec.line_ids.filtered_domain([('fail', '=', True)]) and not rec.note:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'type': 'danger',
                        'sticky': True,
                        'message': "Bạn cần ghi chú lý do chấm không đạt",
                    }
                }
            line_ids = rec.line_ids.filtered_domain([('kpi_type', '!=', False), '|', ('fail', '=', True), ('x_pass', '=', True)])
            if line_ids:
                kpi_types = line_ids.mapped('kpi_type')
                for kpi in kpi_types:
                    TtbTaskReportKpi = self.env['ttb.task.report.kpi']
                    kpi_lines = line_ids.filtered_domain([('kpi_type', '=', kpi.id)])
                    number_of_item = len(kpi_lines)
                    total_rate = sum(kpi_lines.filtered(lambda l: l.x_pass).mapped('rate'))
                    total_x_pass = len(kpi_lines.filtered(lambda l: l.x_pass))
                    average_rate = total_x_pass / number_of_item if number_of_item else 0.0

                    # Tính tỉ trọng cụm
                    total_rate_cluster = sum(
                        (line.rate_cluster or 0.0) * (line.rate or 0.0)
                        for line in kpi_lines
                        if line.x_pass
                    )

                    old_kpi = rec.kpi_ids.filtered(lambda r: r.kpi_type.id == kpi.id)

                    vals = {
                        'number_of_item': number_of_item,
                        'total_rate': total_rate,
                        'average_rate': average_rate,
                        'total_rate_cluster': total_rate_cluster,
                    }

                    if old_kpi:
                        old_kpi.write(vals)
                    else:
                        TtbTaskReportKpi.sudo().create({
                            'report_id': rec.id,
                            'kpi_type': kpi.id,
                            **vals
                        })
            if not rec.user_id and not rec.user_ids:
                if rec.kpi_type_id.is_checklist or rec.kpi_type_id.is_checklist_restaurant or rec.kpi_type_id.code == 'KVC':
                    rec.user_ids = [(5, 0, 0)]
                else:
                    rec.user_ids = [(6, 0, rec.domain_user.ids)]

            # Kiểm tra phiếu không đạt
            has_fail = bool(rec.line_ids.filtered_domain([('fail', '=', True)]))

            vals = {
                'reviewer_id': self.env.user.id,
                'date': fields.Datetime.now()
            }
            if has_fail and rec.kpi_type_id.code == 'CSKH' and rec.group == 'cs':
                vals.update({
                    'state': 'waiting',
                    'sla_status': 'on_time',
                    'sla_start_datetime': fields.Datetime.now(),
                    'gsc_evaluated_at': fields.Datetime.now(),
                })
                rec.notify_tnkh_fail()
            else:
                vals['state'] = 'done'

            if rec.date and rec.deadline:
                vals['report_status'] = 'overdue' if rec.date.date() > rec.deadline else 'on_time'
            rec.write(vals)

            # Chỉ áp dụng với KPI KVC: cập nhật người xử lý cho dòng không đạt

            if not rec.kpi_type_id.need_approved_plan:
                for fail_line in rec.failed_line_ids:
                    fail_line.sudo().processor_id = rec.reviewer_id
                    fail_line.process_status = 'approved_plan'
                    fail_line.env['my.task'].create({'task_report_line_id': fail_line.id})

            if rec.kpi_type_id.code in ['VM', 'VS']:
                for fail_line in rec.failed_line_ids:
                    if rec.group == 'manager':
                        fail_line.sudo().processor_id = rec.reviewer_id
                        fail_line.process_status = 'approved_plan'
                        self.env['my.task'].sudo().create({'task_report_line_id': fail_line.id})
                    elif rec.group in ['branch_mannager', 'region_manager']:
                        domain = [
                            ('ttb_branch_ids', '=', fail_line.user_branch_id.id),
                            ('employee_id.job_id.name', '=', 'Quản lý Nhà sách')
                        ]

                        if rec.kpi_type_id.code == 'VM' and fail_line.categ_id:
                            domain.append(('ttb_categ_ids', 'in', fail_line.categ_id.id))
                        elif rec.kpi_type_id.code == 'VS' and fail_line.area_id:
                            domain.append(('ttb_area_ids', 'in', fail_line.area_id.id))

                        manager = self.env['res.users'].sudo().search(domain, limit=1)

                        if manager:
                            fail_line.sudo().processor_id = manager.id
                            fail_line.process_status = 'approved_plan'
                            self.env['my.task'].sudo().create({'task_report_line_id': fail_line.id})

    def notify_tnkh_fail(self):
        for rec in self:
            if not rec.user_id or not rec.user_id.employee_id:
                continue

            employee = rec.user_id.employee_id
            ma_phieu = rec.name or ''
            code_employee = employee.ttb_code or ''
            name_employee = employee.name
            employee_display = f"{code_employee} - {name_employee}" if code_employee else name_employee

            # Gửi thông báo cho nhân viên được chấm
            if rec.user_id.partner_id:
                rec.message_notify(
                    subject="Phiếu TNKH không đạt",
                    body=f"Bạn có phiếu TNKH {ma_phieu} không đạt",
                    partner_ids=[rec.user_id.partner_id.id],
                    subtype_xmlid="mail.mt_comment",
                    email_layout_xmlid=False,
                    email_add_signature=False
                )

            # Gửi thông báo cho quản lý của nhân viên đó
            manager_emp = employee.parent_id
            if manager_emp and manager_emp.user_id and manager_emp.user_id.partner_id:
                rec.message_notify(
                    subject="Phiếu TNKH không đạt",
                    body=(
                        f"Bộ phận bạn có phiếu TNKH {ma_phieu} của nhân viên {employee_display} không đạt. "
                    ),
                    partner_ids=[manager_emp.user_id.partner_id.id],
                    subtype_xmlid="mail.mt_comment",
                    email_layout_xmlid=False,
                    email_add_signature=False
                )

            # Gửi thông báo cho giám đốc nhà sách
            director_emp = manager_emp.parent_id if manager_emp else False
            if director_emp and director_emp.user_id and director_emp.user_id.partner_id:
                rec.message_notify(
                    subject="Phiếu TNKH không đạt",
                    body=(
                        f"Cơ sở bạn có phiếu TNKH {ma_phieu} của nhân viên {employee_display} không đạt."
                    ),
                    partner_ids=[director_emp.user_id.partner_id.id],
                    subtype_xmlid="mail.mt_comment",
                    email_layout_xmlid=False,
                    email_add_signature=False
                )
    def _recompute_kpi_values(self):
        for rec in self:
            kpi_records = rec.kpi_ids
            lines = rec.line_ids.filtered(lambda l: l.kpi_type)

            for kpi in kpi_records:
                related_lines = lines.filtered(lambda l: l.kpi_type.id == kpi.kpi_type.id)

                number_of_item = len(related_lines)
                total_x_pass = len(related_lines.filtered(lambda l: l.x_pass))
                total_rate = sum(related_lines.filtered(lambda l: l.x_pass).mapped('rate'))
                average_rate = total_x_pass / number_of_item if number_of_item else 0

                kpi.write({
                    'number_of_item': number_of_item,
                    'total_rate': total_rate,
                    'average_rate': average_rate
                })

    def action_agree(self):
        for rec in self.sudo():
            rec.state = 'done'
            if rec.group == 'cs' and rec.kpi_type_id.code == 'CSKH':
                rec.kpi_ids.sudo().unlink()

                line_ids = rec.line_ids.filtered_domain([
                    ('kpi_type', '!=', False),
                    '|', ('fail', '=', True), ('x_pass', '=', True)
                ])
                if line_ids:
                    kpi_types = line_ids.mapped('kpi_type')
                    for kpi in kpi_types:
                        number_of_item = len(line_ids.filtered_domain([('kpi_type', '=', kpi.id)]))
                        total_rate = sum(line_ids.filtered_domain([('kpi_type', '=', kpi.id), ('x_pass', '=', True)]).mapped('rate'))
                        total_x_pass = len(line_ids.filtered_domain([('kpi_type', '=', kpi.id), ('x_pass', '=', True)]))
                        average_rate = total_x_pass / number_of_item if number_of_item else 0.0

                        self.env['ttb.task.report.kpi'].sudo().create({
                            'report_id': rec.id,
                            'kpi_type': kpi.id,
                            'number_of_item': number_of_item,
                            'date': fields.Datetime.now(),
                            'total_rate': total_rate,
                            'average_rate': average_rate
                        })

    def button_cancel(self):
        for rec in self.sudo():
            rec.state = 'cancel'

    def _compute_show_agree_button(self):
        for rec in self:
            rec.show_agree_button = rec._get_button_visibility()

    def _get_button_visibility(self):
        self.ensure_one()
        return (
                self.state == "waiting"
                and self.env.user.has_group("ttb_kpi.group_ttb_kpi_admin_it")
                or self.env.user.has_group("ttb_kpi.group_ttb_kpi_nv_cskh")
                or self.env.user.has_group("ttb_kpi.group_ttb_kpi_tnkh_manager")
        )
    def reopen_approval(self):
        return {
            'name': 'Chọn người duyệt đề xuất',
            'type': 'ir.actions.act_window',
            'res_model': 'reopen.approval.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_model': self._name,
                'default_message': '',
                'default_model_id': self.id,
            }
        }

    def button_reject(self):
        for rec in self.sudo():
            rec.state = 'cancel'

    def button_approved(self):
        current_user = self.env.user
        today = fields.Date.context_today(self)

        for rec in self.sudo():
            approver_line = rec.approver_ids.filtered(lambda a: a.user_id.id == current_user.id and a.state == 'waiting')
            approver_line.write({
                'state': 'approved',
                'approved_date': fields.Datetime.now(),
            })

            all_approved = all(line.state == 'approved' for line in rec.approver_ids)

            if all_approved:
                rec.write({
                    'state': rec.previous_state,
                    'deadline': today + timedelta(days=2)
                })

    def unlink(self):
        for rec in self:
            if rec.state != 'new':
                raise UserError('Không thể xóa bản ghi đã bắt đầu đánh giá')
        return super().unlink()

    def count_existed(self, values, not_include_keys=[]):
        domain = []
        for key in values:
            if key not in not_include_keys:
                domain.append((key, '=', values[key]))
        records = self.sudo().search(domain)
        return len(records)

    def cron_check_gsc_sla(self):
        now = fields.Datetime.now()

        reports = self.search([
            ('has_fail', '=', True),
            ('gsc_evaluated_at', '!=', False),
            ('state', '=', 'waiting'),
        ])

        for rec in reports:
            # Cơ sở không phản hồi
            delta_hours_gsc_evaluated = (now - rec.gsc_evaluated_at).total_seconds() / 3600
            if not rec.cs_agreement:
                if delta_hours_gsc_evaluated >= 24:
                    if rec.state != 'done':
                        rec.write({
                            'state': 'done',
                            'sla_status': 'overdue_24h',
                        })
                        rec._notify_auto_done_cs_overdue()
                else:
                    if rec.sla_status != 'on_time':
                        rec.sla_status = 'on_time'
                continue
            if delta_hours_gsc_evaluated >= 48:
                if rec.sla_status != 'overdue_48h':
                    rec.sla_status = 'overdue_48h'
                continue

            if not rec.sla_start_datetime:
                continue

            delta_hours = (now - rec.sla_start_datetime).total_seconds() / 3600

            if delta_hours >= 24:
                new_status = 'overdue_24h'
            else:
                new_status = 'on_time'

            if rec.sla_status != new_status:
                rec.sla_status = new_status

    def _notify_auto_done_cs_overdue(self):
        for rec in self:

            employee = rec.user_id.employee_id
            emp_code = employee.ttb_code or ''
            emp_name = employee.name or ''
            emp_display = f"{emp_code} - {emp_name}" if emp_code else emp_name
            ma_phieu = rec.name or ''

            body = (f"Phiếu TNKH không đạt {ma_phieu} của nhân viên {emp_display} đã tự động hoàn thành do quá 24h cơ sở không phản hồi.")

            partner_ids = set()

            # Nhân viên được chấm
            if rec.user_id.partner_id:
                partner_ids.add(rec.user_id.partner_id.id)

            # Quản lý trực tiếp
            manager = employee.parent_id
            if manager and manager.user_id and manager.user_id.partner_id:
                partner_ids.add(manager.user_id.partner_id.id)

            # Giám đốc nhà sách
            director = manager.parent_id if manager else False
            if director and director.user_id and director.user_id.partner_id:
                partner_ids.add(director.user_id.partner_id.id)

            if partner_ids:
                rec.message_notify(
                    subject="Phiếu TNKH không đạt",
                    body=body,
                    partner_ids=list(partner_ids),
                    subtype_xmlid="mail.mt_comment",
                    email_layout_xmlid=False,
                    email_add_signature=False,
                )

    # Sinh phiếu tự động theo kỳ
    def cron_create_task_report_vs(self, branch_ids = [], target_date=None):
        if target_date:
            today = fields.Date.from_string(target_date)
        else:
            today = (datetime.now() + relativedelta(hours=7)).date()

        creation_month = today.month

        if today.day not in [1, 8, 15, 22]:
            return

        period = (today.day - 1) // 7 + 1

        # Tính deadline
        if today.day == 1:
            deadline = today.replace(day=7)
        elif today.day == 8:
            deadline = today.replace(day=14)
        elif today.day == 15:
            deadline = today.replace(day=21)
        else:
            next_month = today.replace(day=28) + timedelta(days=4)
            last_day = next_month - timedelta(days=next_month.day)
            deadline = last_day
        kpi_type_id = self.env.ref('ttb_kpi.ttb_kpi_type_vs').id
        task_template = self.env['ttb.task.template'].sudo().search([('date_from', '<=', today), ('date_to', '>=', today),
                                                                     ('kpi_type_id', '=', kpi_type_id),
                                                                     ('area_ids', '!=', False),
                                                                     ])
        if not task_template:
            return
        task_template_area_ids = task_template.mapped('area_ids')
        branches = self.env['ttb.branch'].search([('id', 'not in', branch_ids)])
        for branch in branches:
            for area in task_template_area_ids:
                users = self.env['res.users'].with_company(self.env.company).sudo().search([
                    ('ttb_branch_ids', '=', branch.id),
                    ('ttb_area_ids', '=', area.id)
                ])
                filtered_user_ids = []
                for user in users:
                    employee = user.employee_id
                    official_date = employee.official_working_date
                    if official_date and official_date.month == today.month and official_date.day >= 15:
                        if today.day in [15, 22]:
                            continue
                    filtered_user_ids.append(user.id)

                values = {
                        'kpi_type_id': kpi_type_id,
                        'area_id': area.id,
                        'user_branch_id': branch.id,
                        'deadline': deadline,
                        'user_ids':filtered_user_ids,
                        'group': 'manager',
                        'period': period,
                        'creation_month': creation_month
                }
                existed_count = self.count_existed(values, ['user_ids'])
                for i in range(max(0, 3-existed_count)):
                    manager_values = values.copy()
                    # manager_values['group'] = 'manager'
                    self.create(manager_values)

                branch_mannager_values = values.copy()
                branch_mannager_values['group'] = 'branch_mannager'
                existed_count = self.count_existed(branch_mannager_values, ['user_ids'])
                if not existed_count:
                    self.create(branch_mannager_values)

    def cron_create_task_report_vm(self, branch_ids=[], target_date=None):
        if target_date:
            today = fields.Date.from_string(target_date)
        else:
            today = (datetime.now() + relativedelta(hours=7)).date()

        creation_month = today.month

        if today.day not in [1, 8, 15, 22]:
            return

        period = (today.day - 1) // 7 + 1

        # Tính deadline
        if today.day == 1:
            deadline = today.replace(day=7)
        elif today.day == 8:
            deadline = today.replace(day=14)
        elif today.day == 15:
            deadline = today.replace(day=21)
        else:
            next_month = today.replace(day=28) + timedelta(days=4)
            last_day = next_month - timedelta(days=next_month.day)
            deadline = last_day

        kpi_type_id = self.env.ref('ttb_kpi.ttb_kpi_type_vm').id
        task_template = self.env['ttb.task.template'].sudo().search([('date_from', '<=', today), ('date_to', '>=', today),
                                                                     ('kpi_type_id', '=', kpi_type_id),
                                                                     ('categ_ids', '!=', False)])
        if not task_template:
            return
        task_template_categ_ids = task_template.mapped('categ_ids')
        branches = self.env['ttb.branch'].search([('id', 'not in', branch_ids)])
        for branch in branches:
            for categ in task_template_categ_ids:
                users = self.env['res.users'].with_company(self.env.company).sudo().search([
                    ('ttb_branch_ids', '=', branch.id),
                    ('ttb_categ_ids', '=', categ.id)
                ])
                filtered_user_ids = []
                for user in users:
                    employee = user.employee_id
                    official_date = employee.official_working_date
                    if official_date and official_date.month == today.month and official_date.day >= 15:
                        if today.day in [15, 22]:
                            continue
                    filtered_user_ids.append(user.id)

                values = {'kpi_type_id': kpi_type_id,
                          'categ_id': categ.id,
                          'user_branch_id': branch.id,
                          'deadline': deadline,
                          'user_ids': filtered_user_ids,
                          'group': 'manager',
                          'period': period,
                          'creation_month': creation_month
                          }
                existed_count = self.count_existed(values, ['user_ids'])
                for i in range(max(0, 3-existed_count)):
                    manager_values = values.copy()
                    # manager_values['group'] = 'manager'
                    self.create(manager_values)
                branch_mannager_values = values.copy()
                branch_mannager_values['group'] = 'branch_mannager'
                existed_count = self.count_existed(branch_mannager_values, ['user_ids'])
                if not existed_count:
                    self.create(branch_mannager_values)

    def cron_create_task_report_cskh(self, exclude_branch_ids=[], target_date=None):
        if target_date:
            today = fields.Date.from_string(target_date)
        else:
            today = (datetime.now() + relativedelta(hours=7)).date()

        creation_month = today.month

        if today.day not in [1, 8, 15, 22]:
            return

        period = (today.day - 1) // 7 + 1

        # Tính deadline
        if today.day == 1:
            deadline = today.replace(day=7)
        elif today.day == 8:
            deadline = today.replace(day=14)
        elif today.day == 15:
            deadline = today.replace(day=21)
        else:
            next_month = today.replace(day=28) + timedelta(days=4)
            last_day = next_month - timedelta(days=next_month.day)
            deadline = last_day

        kpi_type_id = self.env.ref('ttb_kpi.ttb_kpi_type_cskh').id
        task_templates = self.env['ttb.task.template'].sudo().search([
            ('date_from', '<=', today),
            ('date_to', '>=', today),
            ('kpi_type_id', '=', kpi_type_id),
            ('area_ids', '!=', False),
        ])
        if not task_templates:
            return

        already_processed_users = set()

        for template in task_templates:
            template_area_ids = template.area_ids.ids

            domain = [
                ('ttb_area_ids', 'in', template_area_ids),
                ('ttb_branch_ids', '!=', False),
            ]
            if exclude_branch_ids:
                domain.append(('ttb_branch_ids', 'not in', exclude_branch_ids))

            users = self.env['res.users'].sudo().search(domain)

            users = list({u.id: u for u in users}.values())

            for user in users:
                if user.id in already_processed_users:
                    continue

                employee = user.employee_id
                job_name = employee.job_id.name if employee and employee.job_id else ''
                official_date = employee.official_working_date

                if job_name == "Quản lý Nhà sách":
                    continue

                if official_date and official_date.month == today.month and official_date.day >= 15:
                    continue

                user_area_ids = user.ttb_area_ids.filtered(lambda a: a.id in template_area_ids)
                if not user_area_ids:
                    continue

                area = user_area_ids[0]

                for branch in user.ttb_branch_ids:
                    existing = self.search([
                        ('user_id', '=', user.id),
                        ('user_branch_id', '=', branch.id),
                        ('area_id', '=', area.id),
                        ('kpi_type_id', '=', kpi_type_id),
                        ('deadline', '=', deadline),
                        ('group', '=', 'manager')
                    ])
                    if existing:
                        continue

                    values = {
                        'kpi_type_id': kpi_type_id,
                        'deadline': deadline,
                        'group': 'manager',
                        'user_id': user.id,
                        'user_job_id': employee.job_id.id if employee else False,
                        'user_branch_id': branch.id,
                        'area_id': area.id,
                        'categ_id': user.ttb_categ_id.id if user.ttb_categ_id else False,
                        'period': period,
                        'creation_month': creation_month
                    }
                    self.create(values)

                already_processed_users.add(user.id)
    # Sinh phiếu bổ sung chạy lúc 23h cho CSKH
    def cron_create_task_report_cskh_additional(self, target_date=None):
        if target_date:
            today = fields.Date.from_string(target_date)
        else:
            today = (datetime.now() + relativedelta(hours=7)).date()

        creation_month = today.month

        employees = self.env['hr.employee'].sudo().search([
            ('official_working_date', '=', today),
            ('user_id', '!=', False)
        ])
        users = employees.mapped('user_id')

        kpi_type_id = self.env.ref('ttb_kpi.ttb_kpi_type_cskh').id
        task_templates = self.env['ttb.task.template'].sudo().search([
            ('date_from', '<=', today),
            ('date_to', '>=', today),
            ('kpi_type_id', '=', kpi_type_id),
            ('area_ids', '!=', False),
        ])
        if not task_templates:
            return
        for user in users:
            employee = user.employee_id
            job_name = employee.job_id.name if employee and employee.job_id else ''
            official_date = employee.official_working_date

            if job_name == "Quản lý Nhà sách":
                continue

            user_area_ids = user.ttb_area_ids
            user_branch_ids = user.ttb_branch_ids.ids

            for template in task_templates:
                common_area_ids = user_area_ids.filtered(lambda a: a.id in template.area_ids.ids)

                if not common_area_ids:
                    continue

                area = common_area_ids[0]

                for branch_id in user_branch_ids:
                    if official_date.day <= 7:
                        period = 1
                        deadline = official_date.replace(day=14)
                    elif 8 <= official_date.day < 15:
                        period = 2
                        deadline = official_date.replace(day=21)
                    else:
                        continue

                    existed = self.search_count([
                        ('user_id', '=', user.id),
                        ('user_branch_id', '=', branch_id),
                        ('area_id', '=', area.id),
                        ('kpi_type_id', '=', kpi_type_id),
                        ('period', '=', period),
                        ('creation_month', '=', creation_month),
                    ])
                    if not existed:
                        values = {
                            'kpi_type_id': kpi_type_id,
                            'deadline': deadline,
                            'group': 'manager',
                            'user_id': user.id,
                            'user_job_id': employee.job_id.id if employee else False,
                            'user_branch_id': branch_id,
                            'area_id': area.id,
                            'categ_id': user.ttb_categ_id.id if user.ttb_categ_id else False,
                            'period': period,
                            'creation_month': creation_month
                        }
                        self.create(values)

    def _is_weekday(self, date):
        """Kiểm tra ngày có phải là ngày trong tuần (T2-T6)"""
        return date.weekday() < 5

    def _get_next_weekday(self, date):
        """Lấy ngày đầu tuần tiếp theo (Thứ 2)"""
        weekday = date.weekday()

        if weekday == 6:
            return date + timedelta(days=1)
        elif weekday == 5:
            return date + timedelta(days=2)
        else:
            days_to_monday = (7 - weekday) % 7
            if days_to_monday == 0:
                days_to_monday = 7
            return date + timedelta(days=days_to_monday)

    def _get_next_weekend(self, date):
        """Lấy ngày cuối tuần tiếp theo (Thứ 7 hoặc CN)"""
        weekday = date.weekday()
        if weekday == 5:  # Thứ 7
            return date + timedelta(days=1)  # Chủ Nhật
        elif weekday == 6:  # Chủ Nhật
            return date + timedelta(days=6)  # Thứ 7 tuần sau
        else:
            days_ahead = 5 - weekday
            return date + timedelta(days=days_ahead)

    def _assign_user_to_group(self, user_id):
        """Phân nhóm cho nhân viên mới - chọn nhóm ít người nhất"""
        group_counts = {}
        for group in range(1, 5):
            count = self.env['res.users'].sudo().search_count([
                ('ttb_user_group', '=', group)
            ])
            group_counts[group] = count

        min_count = min(group_counts.values())
        available_groups = [g for g, c in group_counts.items() if c == min_count]
        return available_groups[0]

    def _get_rotation_groups(self, period, is_weekday_start, today):
        """
        Xác định nhóm nào được tạo task dựa trên kỳ và ngày bắt đầu
        """
        rotation_map = {
            1: {'weekday_groups': [1, 2], 'weekend_groups': [3, 4]},
            2: {'weekday_groups': [2, 3], 'weekend_groups': [4, 1]},
            3: {'weekday_groups': [3, 4], 'weekend_groups': [1, 2]},
            4: {'weekday_groups': [4, 1], 'weekend_groups': [2, 3]},
        }

        weekday_groups = rotation_map[period]['weekday_groups']
        weekend_groups = rotation_map[period]['weekend_groups']

        # Xác định ngày bắt đầu kỳ
        if period == 1:
            period_start_date = today.replace(day=1)
        elif period == 2:
            period_start_date = today.replace(day=8)
        elif period == 3:
            period_start_date = today.replace(day=15)
        else:
            period_start_date = today.replace(day=22)

        if is_weekday_start:
            weekday_date = period_start_date
            weekend_date = self._get_next_weekend(period_start_date)
        else:
            weekend_date = period_start_date
            weekday_date = self._get_next_weekday(period_start_date)

        return {
            'weekday_groups': weekday_groups,
            'weekend_groups': weekend_groups,
            'weekday_date': weekday_date,
            'weekend_date': weekend_date
        }

    def _assign_groups_at_month_start(self):
        """Chia nhóm cho tất cả nhân viên vào đầu tháng"""
        all_users = self.env['res.users'].sudo().search([
            ('ttb_branch_ids', '!=', False)
        ])

        user_list = list(all_users)
        import random
        random.shuffle(user_list)

        group_size = len(user_list) // 4
        remainder = len(user_list) % 4

        current_index = 0
        for group in range(1, 5):
            size = group_size + (1 if group <= remainder else 0)
            for i in range(size):
                if current_index < len(user_list):
                    user_list[current_index].sudo().write({'ttb_user_group': group})
                    current_index += 1

    @api.model
    def cron_assign_groups_monthly(self):
        """Chạy vào ngày 1 hàng tháng để phân nhóm lại"""
        today = (datetime.now() + relativedelta(hours=7)).date()
        if today.day == 1:
            self._assign_groups_at_month_start()
    def cron_create_task_report_gsc(self, exclude_branch_ids=[], target_date=None):
        if target_date:
            today = fields.Date.from_string(target_date)
        else:
            today = (datetime.now() + relativedelta(hours=7)).date()

        creation_month = today.month
        creation_year = today.year

        # Luôn kiểm tra delayed tasks trước
        self._check_and_create_delayed_tasks(today, exclude_branch_ids)

        # Chỉ tạo phiếu mới vào ngày đầu kỳ
        if today.day not in [1, 8, 15, 22]:
            return

        period = (today.day - 1) // 7 + 1

        # Tính deadline
        if today.day == 1:
            deadline = today.replace(day=10)
        elif today.day == 8:
            deadline = today.replace(day=17)
        elif today.day == 15:
            deadline = today.replace(day=24)
        else:
            next_month = today.replace(day=28) + timedelta(days=4)
            last_day = next_month - timedelta(days=next_month.day)
            deadline = last_day + timedelta(days=3)

        # Nếu là đầu tháng, phân nhóm lại
        if today.day == 1:
            self._assign_groups_at_month_start()

        kpi_type_id = self.env.ref('ttb_kpi.ttb_kpi_type_cskh').id
        task_templates = self.env['ttb.task.template'].sudo().search([
            ('date_from', '<=', today),
            ('date_to', '>=', today),
            ('kpi_type_id', '=', kpi_type_id),
            ('area_ids', '!=', False),
        ])

        if not task_templates:
            return

        # Xác định nhóm nào được tạo task
        is_weekday = self._is_weekday(today)
        rotation_info = self._get_rotation_groups(period, is_weekday, today)

        # Xác định immediate và delayed groups
        if is_weekday:
            immediate_groups = rotation_info['weekday_groups']
            delayed_groups = rotation_info['weekend_groups']
            delay_date = rotation_info['weekend_date']
            is_weekend_task = False
            delayed_is_weekend = True
        else:
            immediate_groups = rotation_info['weekend_groups']
            delayed_groups = rotation_info['weekday_groups']
            delay_date = rotation_info['weekday_date']
            is_weekend_task = True
            delayed_is_weekend = False

        # Lưu thông tin delayed task vào model
        delayed_obj = self.env['ttb.task.report.delayed']

        # Xóa delayed cũ của kỳ này (nếu có)
        old_delayed = delayed_obj.search([
            ('period', '=', period),
            ('creation_month', '=', creation_month),
            ('creation_year', '=', creation_year),
        ])
        old_delayed.unlink()

        # Tạo mới delayed task
        delayed_obj.create({
            'period': period,
            'creation_month': creation_month,
            'creation_year': creation_year,
            'execution_date': delay_date,
            'group_ids': ','.join(map(str, delayed_groups)),
            'is_weekend_task': delayed_is_weekend,
            'state': 'pending',
        })

        # Tạo task cho các nhóm immediate
        self._create_tasks_for_groups(
            immediate_groups,
            task_templates,
            exclude_branch_ids,
            today,
            deadline,
            kpi_type_id,
            creation_month,
            period,
            is_weekend_task
        )

    def _check_and_create_delayed_tasks(self, today, exclude_branch_ids):
        """Kiểm tra và tạo task cho nhóm delayed"""
        delayed_obj = self.env['ttb.task.report.delayed']

        # Tìm các delayed tasks cần thực thi hôm nay
        pending_tasks = delayed_obj.search([
            ('execution_date', '=', today),
            ('state', '=', 'pending'),
        ])

        for delayed_task in pending_tasks:
            delayed_groups = [int(g) for g in delayed_task.group_ids.split(',')]

            # Tính deadline cho kỳ này
            period = delayed_task.period
            month = delayed_task.creation_month
            year = delayed_task.creation_year

            period_start = today.replace(year=year, month=month, day=1)
            if period == 1:
                deadline = period_start.replace(day=10)
            elif period == 2:
                deadline = period_start.replace(day=17)
            elif period == 3:
                deadline = period_start.replace(day=24)
            else:
                next_month = period_start.replace(day=28) + timedelta(days=4)
                last_day = next_month - timedelta(days=next_month.day)
                deadline = last_day + timedelta(days=3)

            kpi_type_id = self.env.ref('ttb_kpi.ttb_kpi_type_cskh').id
            task_templates = self.env['ttb.task.template'].sudo().search([
                ('kpi_type_id', '=', kpi_type_id),
                ('area_ids', '!=', False),
            ])

            # Tạo task cho nhóm delayed
            self._create_tasks_for_groups(
                delayed_groups,
                task_templates,
                exclude_branch_ids,
                today,
                deadline,
                kpi_type_id,
                month,
                period,
                delayed_task.is_weekend_task
            )

            # Đánh dấu đã xử lý
            delayed_task.write({'state': 'done'})

    def _create_tasks_for_groups(self, groups, task_templates, exclude_branch_ids,
                                 today, deadline, kpi_type_id, creation_month, period,
                                 is_weekend_task=False):
        """Tạo task cho các nhóm được chỉ định"""
        created_count = 0

        for template in task_templates:
            template_area_ids = template.area_ids.ids
            domain = [
                ('ttb_area_ids', 'in', template_area_ids),
                ('ttb_branch_ids', '!=', False),
                ('ttb_user_group', 'in', groups),
            ]
            if exclude_branch_ids:
                domain.append(('ttb_branch_ids', 'not in', exclude_branch_ids))

            users = self.env['res.users'].sudo().search(domain)
            users = list({u.id: u for u in users}.values())

            for user in users:
                employee = user.employee_id
                manager = employee.parent_id if employee else False
                job_name = employee.job_id.name if employee and employee.job_id else ''

                if job_name in ["Quản lý Nhà sách", 'Giám đốc Nhà sách']:
                    continue

                user_area_ids = user.ttb_area_ids.filtered(lambda a: a.id in template_area_ids)
                if not user_area_ids:
                    continue

                area = user_area_ids[0]

                for branch in user.ttb_branch_ids:
                    existing = self.search([
                        ('user_id', '=', user.id),
                        ('user_branch_id', '=', branch.id),
                        ('area_id', '=', area.id),
                        ('kpi_type_id', '=', kpi_type_id),
                        ('group', '=', 'cs'),
                        ('rotation_period', '=', period),
                        ('creation_month', '=', creation_month),
                    ])

                    if existing:
                        continue

                    values = {
                        'kpi_type_id': kpi_type_id,
                        'deadline': deadline,
                        'group': 'cs',
                        'user_id': user.id,
                        'user_job_id': employee.job_id.id if employee else False,
                        'user_branch_id': branch.id,
                        'area_id': area.id,
                        'categ_id': user.ttb_categ_id.id if user.ttb_categ_id else False,
                        'creation_month': creation_month,
                        'manager_id': manager.id if manager else False,
                        'period': period,
                        'user_group': user.ttb_user_group,
                        'rotation_period': period,
                        'is_weekend_task': is_weekend_task,
                        'day_type': 'weekend' if is_weekend_task else 'weekday',
                    }
                    self.create(values)
                    created_count += 1

    # Theo tháng
    def cron_create_task_report_month_vs(self, branch_ids=[], count=1):
        if count < 1:
            return
        today = (datetime.now() + relativedelta(hours=7)).date()
        end_month = today.replace(day=1) + relativedelta(months=1, days=-1)
        kpi_type_id = self.env.ref('ttb_kpi.ttb_kpi_type_vs').id
        task_template = self.env['ttb.task.template'].sudo().search([('date_from', '<=', today), ('date_to', '>=', today),
                                                                     ('kpi_type_id', '=', kpi_type_id),
                                                                     ('area_ids', '!=', False),
                                                                     ])
        if not task_template:
            return
        task_template_area_ids = task_template.mapped('area_ids')
        branches = self.env['ttb.branch'].search([('id', 'in', branch_ids)])
        for branch in branches:
            for area in task_template_area_ids:
                user_ids = self.env['res.users'].with_company(self.env.company).sudo().search([('ttb_branch_ids', '=', branch.id), ('ttb_area_ids', '=', area.id)]).ids
                values = {'kpi_type_id': kpi_type_id,
                          'area_id': area.id,
                          'user_branch_id': branch.id,
                          'deadline': end_month,
                          'group': 'region_manager',
                          'user_ids':user_ids,
                          }
                existed_count = self.count_existed(values, ['user_ids'])
                for i in range(max(0, count-existed_count)):
                    create_values = values.copy()
                    self.create(create_values)
    def cron_create_task_report_month_vm(self, branch_ids=[], count=1):
        if count < 1:
            return
        today = (datetime.now() + relativedelta(hours=7)).date()
        end_month = today.replace(day=1) + relativedelta(months=1, days=-1)
        kpi_type_id = self.env.ref('ttb_kpi.ttb_kpi_type_vm').id
        task_template = self.env['ttb.task.template'].sudo().search([('date_from', '<=', today), ('date_to', '>=', today),
                                                                     ('kpi_type_id', '=', kpi_type_id),
                                                                     ('categ_ids', '!=', False)])
        if not task_template:
            return
        task_template_categ_ids = task_template.mapped('categ_ids')
        branches = self.env['ttb.branch'].search([('id', 'in', branch_ids)])
        for branch in branches:
            for categ in task_template_categ_ids:
                user_ids = self.env['res.users'].with_company(self.env.company).sudo().search([('ttb_branch_ids', '=', branch.id), ('ttb_categ_ids', '=', categ.id)]).ids
                values = {'kpi_type_id': kpi_type_id,
                          'categ_id': categ.id,
                          'user_branch_id': branch.id,
                          'deadline': end_month,
                          'group': 'region_manager',
                          'user_ids': user_ids
                          }
                existed_count = self.count_existed(values, ['user_ids'])
                for i in range(max(0, count-existed_count)):
                    create_values = values.copy()
                    self.create(create_values)

    def cron_create_task_report_month_kvc(self,branch_ids=[], count=1):
        if count < 1:
            return
        today = (datetime.now() + relativedelta(hours=7)).date()
        end_month = today.replace(day=1) + relativedelta(months=1, days=-1)
        kpi_type_id = self.env.ref('ttb_kpi.ttb_kpi_type_kvc').id

        task_templates = self.env['ttb.task.template'].sudo().search([
            ('date_from', '<=', today),
            ('date_to', '>=', today),
            ('kpi_type_id', '=', kpi_type_id),
            ('area_ids', '!=', False),
            ('branch_ids', '!=', False),
        ])
        if not task_templates:
            return

        for template in task_templates:
            for branch in template.branch_ids:
                if branch_ids and branch.id not in branch_ids:
                    continue
                for area in template.area_ids:
                    user_ids = self.env['res.users'].sudo().search([
                        ('ttb_branch_ids', '=', branch.id),
                        ('ttb_area_ids', '=', area.id),
                    ]).ids
                    values = {
                        'kpi_type_id': kpi_type_id,
                        'area_id': area.id,
                        'user_branch_id': branch.id,
                        'deadline': end_month,
                        'group': 'region_manager',
                    }
                    existed_count = self.count_existed(values)
                    for i in range(max(0, count - existed_count)):
                        create_values = values.copy()
                        create_values['user_ids'] = [(6, 0, user_ids)]
                        self.create(create_values)
    # Sinh phiếu tự động checklist
    def cron_create_task_report_anat(self, branch_ids=[], target_date=None, run_type=None):
        if target_date:
            today = fields.Date.from_string(target_date)
        else:
            today = (datetime.now() + relativedelta(hours=7)).date()

        if today.weekday() not in [4, 6]:
            return

        deadline = datetime.combine(today, time(23, 59, 59))
        kpi_type_id = self.env.ref('ttb_kpi.ttb_kpi_type_anat').id

        task_templates = self.env['ttb.task.template'].sudo().search([
            ('date_from', '<=', today),
            ('date_to', '>=', today),
            ('kpi_type_id', '=', kpi_type_id),
        ])

        if not task_templates:
            return

        branches = self.env['ttb.branch'].search([('id', 'in', branch_ids)])
        for branch in branches:
            branch_directors = self.env['res.users'].sudo().search([
                ('ttb_branch_ids', '=', branch.id),
                ('employee_id.job_id.name', '=', 'Nhân viên Kỹ thuật'),
            ])

            for user in branch_directors:
                values = {
                    'kpi_type_id': kpi_type_id,
                    'user_branch_id': branch.id,
                    'reviewer_id': user.id,
                    'reviewer_job_id': user.employee_id.job_id.id if user.employee_id else False,
                    'deadline': deadline,
                }

                existed = self.search([
                    ('kpi_type_id', '=', kpi_type_id),
                    ('deadline', '=', deadline),
                    ('user_branch_id', '=', branch.id),
                    ('reviewer_id', '=', user.id),
                    ('reviewer_job_id', '=', user.employee_id.job_id.id if user.employee_id else False,)
                ])
                if not existed:
                    if (run_type == 'fri_afternoon' and today.weekday() == 4) or (run_type == 'sun_morning' and today.weekday() == 6):
                        report = self.create(values)

                        ky_thuat_users = self.env['res.users'].sudo().search([
                            ('employee_id.job_id.name', '=', 'Nhân viên Kỹ thuật'),
                            ('ttb_branch_ids', '=', branch.id)
                        ])

                        partner_ids = set(ky_thuat_users.mapped('partner_id.id'))

                        for user in ky_thuat_users:
                            employee = user.employee_id
                            if employee and employee.parent_id and employee.parent_id.user_id:
                                manager_partner = employee.parent_id.user_id.partner_id
                                if manager_partner:
                                    partner_ids.add(manager_partner.id)

                        if partner_ids:
                            report.message_notify(
                                subject="Thông báo: Phiếu ATAN mới",
                                body="Hệ thống vừa tạo phiếu kiểm tra ANAT định kỳ. Vui lòng truy cập để xem chi tiết.",
                                partner_ids=list(partner_ids),
                            )

    def cron_create_task_report_gdns_anat(self, branch_ids=[], target_date=None, run_type=None):
        if target_date:
            today = fields.Date.from_string(target_date)
        else:
            today = (datetime.now() + relativedelta(hours=7)).date()

        if today.weekday() not in [0, 5]:
            return

        deadline = datetime.combine(today, time(23, 59, 59))
        kpi_type_id = self.env.ref('ttb_kpi.ttb_kpi_type_anat').id

        branches = self.env['ttb.branch'].search([('id', 'in', branch_ids)])
        for branch in branches:
            branch_directors = self.env['res.users'].sudo().search([
                ('ttb_branch_ids', '=', branch.id),
                ('employee_id.job_id.name', '=', 'Giám đốc Nhà sách'),
            ])

            for user in branch_directors:
                task_templates = self.env['ttb.task.template'].sudo().search([
                    ('date_from', '<=', today),
                    ('date_to', '>=', today),
                    ('kpi_type_id', '=', kpi_type_id),
                ])

                if not task_templates:
                    continue

                values = {
                    'group': 'branch_mannager',
                    'kpi_type_id': kpi_type_id,
                    'user_branch_id': branch.id,
                    'reviewer_id': user.id,
                    'reviewer_job_id': user.employee_id.job_id.id if user.employee_id else False,
                    'deadline': deadline,
                }

                existed = self.search([
                    ('group', '=', 'branch_mannager'),
                    ('kpi_type_id', '=', kpi_type_id),
                    ('deadline', '=', deadline),
                    ('user_branch_id', '=', branch.id),
                    ('reviewer_id', '=', user.id),
                    ('reviewer_job_id', '=', user.employee_id.job_id.id if user.employee_id else False),
                ])

                if not existed:
                    if (run_type == 'sta_afternoon' and today.weekday() == 5) or (
                            run_type == 'mon_morning' and today.weekday() == 0):
                        report = self.create(values)

                        branch_directors_users = self.env['res.users'].sudo().search([
                            ('employee_id.job_id.name', '=', 'Giám đốc Nhà sách'),
                            ('ttb_branch_ids', '=', branch.id)
                        ])

                        partner_ids = set(branch_directors_users.mapped('partner_id.id'))

                        for user in branch_directors_users:
                            employee = user.employee_id
                            if employee and employee.parent_id and employee.parent_id.user_id:
                                manager_partner = employee.parent_id.user_id.partner_id
                                if manager_partner:
                                    partner_ids.add(manager_partner.id)

                        if partner_ids:
                            report.message_notify(
                                subject="Thông báo: Phiếu ANAT mới",
                                body="Hệ thống vừa tạo phiếu kiểm tra ANAT định kỳ. Vui lòng truy cập để xem chi tiết.",
                                partner_ids=list(partner_ids),
                            )

    def cron_create_task_report_pccc(self, branch_ids=[], target_date=None):
        if target_date:
            today = fields.Date.from_string(target_date)
        else:
            today = (datetime.now() + relativedelta(hours=7)).date()

        if today.weekday() != 1:
            return

        week_number = today.isocalendar()[1]
        if week_number % 2 == 0:
            return

        deadline = datetime.combine(today, time(23, 59, 59))
        kpi_type_id = self.env.ref('ttb_kpi.ttb_kpi_type_pccc').id

        task_templates = self.env['ttb.task.template'].sudo().search([
            ('date_from', '<=', today),
            ('date_to', '>=', today),
            ('kpi_type_id', '=', kpi_type_id),
        ])

        if not task_templates:
            return

        branches = self.env['ttb.branch'].search([('id', 'in', branch_ids)])
        for branch in branches:
            branch_directors = self.env['res.users'].sudo().search([
                ('ttb_branch_ids', '=', branch.id),
                ('employee_id.job_id.name', '=', 'Nhân viên Kỹ thuật'),
            ])

            for user in branch_directors:
                values = {
                    'kpi_type_id': kpi_type_id,
                    'user_branch_id': branch.id,
                    'reviewer_id': user.id,
                    'reviewer_job_id': user.employee_id.job_id.id if user.employee_id else False,
                    'deadline': deadline,
                }

                existed = self.search([
                    ('kpi_type_id', '=', kpi_type_id),
                    ('deadline', '=', deadline),
                    ('user_branch_id', '=', branch.id),
                    ('reviewer_id', '=', user.id),
                    ('reviewer_job_id', '=', user.employee_id.job_id.id if user.employee_id else False,)
                ])
                if not existed:
                    report = self.create(values)

                    ky_thuat_users = self.env['res.users'].sudo().search([
                        ('employee_id.job_id.name', '=', 'Nhân viên Kỹ thuật'),
                        ('ttb_branch_ids', '=', branch.id)
                    ])

                    partner_ids = set(ky_thuat_users.mapped('partner_id.id'))

                    for user in ky_thuat_users:
                        employee = user.employee_id
                        if employee and employee.parent_id and employee.parent_id.user_id:
                            manager_partner = employee.parent_id.user_id.partner_id
                            if manager_partner:
                                partner_ids.add(manager_partner.id)

                    if partner_ids:
                        report.message_notify(
                            subject="Thông báo: Phiếu PCCC mới",
                            body="Hệ thống vừa tạo phiếu kiểm tra PCCC định kỳ. Vui lòng truy cập để xem chi tiết.",
                            partner_ids=list(partner_ids),
                        )

    def cron_create_task_report_gdns_pccc(self, branch_ids=[], target_date=None):
        if target_date:
            today = fields.Date.from_string(target_date)
        else:
            today = (datetime.now() + relativedelta(hours=7)).date()

        if today.weekday() != 2:
            return

        week_number = today.isocalendar()[1]
        if week_number % 2 == 0:
            return

        deadline = datetime.combine(today, time(23, 59, 59))
        kpi_type_id = self.env.ref('ttb_kpi.ttb_kpi_type_pccc').id

        branches = self.env['ttb.branch'].search([('id', 'in', branch_ids)])
        for branch in branches:
            branch_directors = self.env['res.users'].sudo().search([
                ('ttb_branch_ids', '=', branch.id),
                ('employee_id.job_id.name', '=', 'Giám đốc Nhà sách'),
            ])

            for user in branch_directors:
                task_templates = self.env['ttb.task.template'].sudo().search([
                    ('date_from', '<=', today),
                    ('date_to', '>=', today),
                    ('kpi_type_id', '=', kpi_type_id),
                    ('job_ids', 'in', [user.employee_id.job_id.id]),
                ])

                if not task_templates:
                    continue

                values = {
                    'group': 'branch_mannager',
                    'kpi_type_id': kpi_type_id,
                    'user_branch_id': branch.id,
                    'reviewer_id': user.id,
                    'reviewer_job_id': user.employee_id.job_id.id if user.employee_id else False,
                    'deadline': deadline,
                }

                existed = self.search([
                    ('group', '=', 'branch_mannager'),
                    ('kpi_type_id', '=', kpi_type_id),
                    ('deadline', '=', deadline),
                    ('user_branch_id', '=', branch.id),
                    ('reviewer_id', '=', user.id),
                    ('reviewer_job_id', '=', user.employee_id.job_id.id if user.employee_id else False),
                ])

                if not existed:
                    report = self.create(values)

                    branch_directors_users = self.env['res.users'].sudo().search([
                        ('employee_id.job_id.name', '=', 'Giám đốc Nhà sách'),
                        ('ttb_branch_ids', '=', branch.id)
                    ])

                    partner_ids = set(branch_directors_users.mapped('partner_id.id'))

                    for user in branch_directors_users:
                        employee = user.employee_id
                        if employee and employee.parent_id and employee.parent_id.user_id:
                            manager_partner = employee.parent_id.user_id.partner_id
                            if manager_partner:
                                partner_ids.add(manager_partner.id)

                    if partner_ids:
                        report.message_notify(
                            subject="Thông báo: Phiếu PCCC mới",
                            body="Hệ thống vừa tạo phiếu kiểm tra PCCC định kỳ. Vui lòng truy cập để xem chi tiết.",
                            partner_ids=list(partner_ids),
                        )

    def cron_create_task_report_kvc(self, branch_ids=[], target_date=None):
        if target_date:
            today = fields.Date.from_string(target_date)
        else:
            today = (datetime.now() + relativedelta(hours=7)).date()

        weekday = today.weekday()
        deadline = today

        kpi_type_id = None
        if weekday in (2,4,6):
            kpi_type_id = self.env.ref('ttb_kpi.ttb_kpi_type_kvc').id
        # elif weekday in (2,4):
        #     kpi_type_id = self.env.ref('ttb_kpi.ttb_kpi_type_vs_kvc').id

        task_templates = self.env['ttb.task.template'].sudo().search([
            ('date_from', '<=', today),
            ('date_to', '>=', today),
            ('kpi_type_id', '=', kpi_type_id),
            ('area_ids', '!=', False),
            ('branch_ids', '!=', False),
        ])

        for template in task_templates:
            for branch in template.branch_ids:
                if branch_ids and branch.id not in branch_ids:
                    continue
                for area in template.area_ids:
                    user_ids = self.env['res.users'].sudo().search([
                        ('ttb_branch_ids', '=', branch.id),
                        ('ttb_area_ids', '=', area.id),
                    ]).ids

                    values = {
                        'kpi_type_id': kpi_type_id,
                        'area_id': area.id,
                        'user_branch_id': branch.id,
                        'deadline': deadline,
                        'group': 'manager',
                        'user_ids': [(6, 0, user_ids)],
                    }
                    existed = self.search([
                        ('kpi_type_id', '=', kpi_type_id),
                        ('area_id', '=', area.id),
                        ('deadline', '=', deadline),
                        ('user_branch_id', '=', branch.id),
                        ('group', '=', 'manager')
                    ])
                    if not existed:
                        self.create(values)

    def cron_create_task_report_kvc_new(self, branch_ids=[]):

        today = (datetime.now() + relativedelta(hours=7)).date()

        weekday = today.weekday()
        deadline = today

        kpi_type_id = self.env.ref('ttb_kpi.ttb_kpi_type_kvc').id

        if weekday <= 4:
            required_count = 6
        else:
            required_count = 9
        for branch in branch_ids:
            task_templates = self.env['ttb.task.template'].sudo().search([
                ('date_from', '<=', today),
                ('date_to', '>=', today),
                ('kpi_type_id', '=', kpi_type_id)
            ])

            if not task_templates:
                continue

            domain = [
                ('kpi_type_id', '=', kpi_type_id),
                ('deadline', '=', deadline),
                ('user_branch_id', '=', branch),
                ('group', '=', 'manager'),
            ]

            existed_reports = self.search(domain)
            existed_count = len(existed_reports)

            if existed_count >= required_count:
                continue

            missing = required_count - existed_count

            vals_list = []
            for i in range(missing):
                vals_list.append({
                    'kpi_type_id': kpi_type_id,
                    'user_branch_id': branch,
                    'deadline': deadline,
                    'group': 'manager',
                    'area_id': 10
                })

            if vals_list:
                self.create(vals_list)

    def cron_create_task_report_branch_manager_kvc(self, branch_ids=[], target_date=None):
        if target_date:
            today = fields.Date.from_string(target_date)
        else:
            today = (datetime.now() + relativedelta(hours=7)).date()

        weekday = today.weekday()

        kpi_type_id = None
        deadline = None

        if weekday == 3:
            kpi_type_id = self.env.ref('ttb_kpi.ttb_kpi_type_kvc').id
            deadline = today
        elif weekday == 5:
            kpi_type_id = self.env.ref('ttb_kpi.ttb_kpi_type_kvc').id
            deadline = today + timedelta(days=1)
        # elif weekday == 5:
        #     kpi_type_id = self.env.ref('ttb_kpi.ttb_kpi_type_vs_kvc').id
        #     deadline = today + timedelta(days=1)

        task_templates = self.env['ttb.task.template'].sudo().search([
            ('date_from', '<=', today),
            ('date_to', '>=', today),
            ('kpi_type_id', '=', kpi_type_id),
            ('area_ids', '!=', False),
            ('branch_ids', '!=', False),
        ])

        for template in task_templates:
            for branch in template.branch_ids:
                if branch_ids and branch.id not in branch_ids:
                    continue
                for area in template.area_ids:
                    user_ids = self.env['res.users'].sudo().search([
                        ('ttb_branch_ids', '=', branch.id),
                        ('ttb_area_ids', '=', area.id),
                    ]).ids
                    values = {
                        'kpi_type_id': kpi_type_id,
                        'area_id': area.id,
                        'user_branch_id': branch.id,
                        'deadline': deadline,
                        'group': 'branch_mannager',
                        'user_ids': [(6, 0, user_ids)],
                    }
                    existed = self.search([
                        ('kpi_type_id', '=', kpi_type_id),
                        ('area_id', '=', area.id),
                        ('deadline', '=', deadline),
                        ('user_branch_id', '=', branch.id),
                        ('group', '=', 'branch_mannager')
                    ])
                    if not existed:
                        self.create(values)

    def cron_task_cancel(self):
        today = (datetime.now() + relativedelta(hours=7)).date()
        task_report = self.search([('state', 'in', ['new', 'reviewing']), ('deadline', '<', today)])
        for task in task_report:
            task.previous_state = task.state
            task.write({'state': 'overdue', 'report_status': 'overdue',})

    def cron_task_information(self):
        today = (datetime.now() + relativedelta(hours=7)).date()
        days_until_sunday = 6 - today.weekday()
        sunday = today + timedelta(days=days_until_sunday)
        director_group = self.env.ref('ttb_kpi.group_ttb_kpi_warehouse_director')
        users = director_group.mapped('users')
        for user in users:
            task_report = self.search([('state', 'not in', ['done', 'cancel']), ('deadline', '=', sunday), ('user_branch_id', 'in', user.ttb_branch_ids.ids)])
            if task_report:
                self.message_notify(subject='Đánh giá nhiệm vụ', body=f"Tuần này, cơ sở của bạn còn {len(task_report)} phiếu chưa hoàn thành là: {', '.join(task_report.mapped('name'))}", partner_ids=user.partner_id.ids)

    failed_line_ids = fields.One2many(string='Không đạt và phương án xử lý', comodel_name='ttb.task.report.line', inverse_name='report_id', domain=[('fail', '=', True)])
    confirmed_by_primary_evaluator_id = fields.Many2one(string='Người xác nhận danh sách nhiệm vụ', comodel_name='res.users', tracking=True)
    confirmed_by_cross_evaluator_id = fields.Many2one(string='Người xác nhận kết quả chéo', comodel_name='res.users', tracking=True)
    confirmed_by_final_evaluator_id = fields.Many2one(string='Người xác nhận tiêu chí lệch', comodel_name='res.users', tracking=True)

    def action_confirm_comparison(self):
        if self.line_ids:
            self.confirmed_by_primary_evaluator_id = self.env.user.id
        if self.line_id_cross_dot:
            self.confirmed_by_cross_evaluator_id = self.env.user.id
        for report in self:
            mismatch_vals = []

            for line in report.line_ids:
                cross_line = report.line_id_cross_dot.filtered(
                    lambda x: x.template_line_id.id == line.template_line_id.id)
                if cross_line:
                    line_result = 'dat' if line.x_pass else 'khong_dat'
                    cross_result = 'dat' if cross_line[0].x_pass else 'khong_dat'

                    if line_result != cross_result:
                        mismatch_vals.append((0, 0, {
                            'template_line_id': line.template_line_id.id,
                            'origin_line_id': line.id,
                            'result_1': line_result,
                            'result_2': cross_result,
                        }))

            report.mismatch_ids = [(5, 0, 0)] + mismatch_vals

    def action_confirm_mismatch(self):
        self.ensure_one()
        self.confirmed_by_final_evaluator_id = self.env.user.id
        for rec in self:
            for mismatch_line in rec.mismatch_ids:
                origin_line = mismatch_line.origin_line_id

                if origin_line and mismatch_line.fail:
                    origin_line.write({
                        'x_pass': False,
                        'fail': True,
                    })
                elif origin_line and mismatch_line.x_pass:
                    origin_line.write({
                        'x_pass': True,
                        'fail': False,
                    })
