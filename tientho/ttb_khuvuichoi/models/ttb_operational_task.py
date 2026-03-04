# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta, time
import json
import random
import urllib.parse


class TtbOperationalTask(models.Model):
    _name = 'ttb.operational.task'
    _description = 'Công việc vận hành'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ---- Trường cơ bản ----
    name = fields.Char(string='Tên công việc', required=True)

    assignment_id = fields.Many2one('ttb.shift.assignment', string='Ca làm việc')
    template_id = fields.Many2one(
        'ttb.work.template',
        string='Mẫu công việc',
        help="Có thể để trống nếu là việc phát sinh thủ công"
    )
    description = fields.Html(related='template_id.description', string='Mô tả công việc', readonly=True)
    expected_result = fields.Text(related='template_id.expected_result', string='Kết quả mong muốn', readonly=True)
    avoid_errors = fields.Text(related='template_id.avoid_errors', string='Lỗi cần tránh', readonly=True)

    area_id = fields.Many2one('ttb.area', string='Khu vực')
    employee_id = fields.Many2one('hr.employee', string='Nhân viên thực hiện')

    planned_date_start = fields.Datetime(string='Thời gian bắt đầu')
    planned_date_end = fields.Datetime(string='Thời gian kết thúc')
    planned_date_end_by_delay = fields.Datetime(string='Thời gian kết thúc do hoãn công việc', readonly=True)
    actual_date_end = fields.Datetime(string='Thực tế kết thúc')

    state = fields.Selection(
        selection=[
            ('waiting', 'Chờ thực hiện'),
            ('ready', 'Sẵn sàng'),
            ('suspended', 'Tạm hoãn'),
            ('delayed', 'Hoãn'),
            ('undone', 'Chưa hoàn thành'),
            ('done', 'Hoàn thành'),
            ('cancel', 'Hủy')
        ],
        string='Trạng thái',
        default='waiting',
        tracking=True,
        group_expand='_expand_state_groups'
    )

    @api.model
    def _expand_state_groups(self, states, domain, orderby=None):
        ordered_states = [
            'ready', 'waiting', 'done',
            'delayed', 'suspended', 'undone', 'cancel'
        ]
        return [state for state in ordered_states if state in states]

    is_late = fields.Boolean(string='Trễ hạn', readonly=True)
    proof_image = fields.Binary(string='Hình ảnh minh chứng')
    proof_image_ids = fields.One2many('ttb.task.proof.image', 'task_id', string='Danh sách ảnh minh chứng')
    proof_image_count = fields.Integer(string='Số ảnh', compute='_compute_proof_image_count', store=False)

    # Thông báo: khi gửi thông báo công việc đến giờ => True; ready -> delayed => False
    notification_sent = fields.Boolean(string='Thông báo đã gửi', default=False)

    # Adhoc
    is_adhoc = fields.Boolean(string='Là việc phát sinh', default=False)
    adhoc_source = fields.Selection(
        selection=[
            ('manual', 'Phát sinh trong ca'),
            ('carry_over', 'Ca trước chuyển sang')
        ],
        string='Nguồn phát sinh'
    )
    is_rework = fields.Boolean(string='Làm lại', default=False)
    rework_task_id = fields.Many2one('ttb.operational.task', string='Công việc bổ sung', readonly=True)

    # Hậu kiểm
    is_audit_required = fields.Boolean(string='Cần hậu kiểm', default=False)
    audit_state = fields.Selection(
        selection=[
            ('pending', 'Đợi kiểm tra'),
            ('pass', 'Đạt'),
            ('fail', 'Không đạt')
        ],
        string='Trạng thái kiểm tra',
        default='pending'
    )
    audit_user_id = fields.Many2one('res.users', string='Người kiểm tra')
    audit_date = fields.Datetime(string='Thời gian kiểm tra')
    audit_note = fields.Text(string='Ghi chú kiểm tra')

    # Related / Tạm hoãn (hiển thị Cơ sở, thông tin hoãn)
    branch_id = fields.Many2one(
        'ttb.branch',
        related='assignment_id.branch_id',
        string='Cơ sở',
        store=True,
        readonly=True
    )
    delay_reason_id = fields.Many2one('ttb.pause.reason', string='Lý do tạm hoãn', readonly=True)
    delay_note = fields.Text(string='Ghi chú hoãn', readonly=True)
    delay_until = fields.Datetime(string='Hoãn đến khi', readonly=True)

    is_branch_manager = fields.Boolean(string='Là quản lý cơ sở', compute='_compute_is_branch_manager')
    is_shift_manager = fields.Boolean(string='Là quản lý ca', compute='_compute_is_shift_manager')
    can_audit = fields.Boolean(string='Được phép đánh giá hậu kiểm', compute='_compute_can_audit')

    @api.constrains('planned_date_start', 'planned_date_end', 'is_adhoc')
    def _check_planned_date(self):
        for task in self:
            if not task.planned_date_start or not task.planned_date_end:
                raise UserError(_("Thời gian bắt đầu và kết thúc không được để trống."))

            if task.planned_date_start > task.planned_date_end:
                raise UserError(_("Thời gian bắt đầu phải nhỏ hơn thời gian kết thúc."))

            if task.is_adhoc and task.planned_date_end < fields.Datetime.now():
                raise UserError(_("Thời gian kết thúc phải lớn hơn thời gian hiện tại."))

    @api.depends('branch_id', 'branch_id.manager_id')
    def _compute_is_branch_manager(self):
        uid = self.env.uid
        for task in self:
            task.is_branch_manager = bool(
                task.branch_id
                and task.branch_id.manager_id
                and task.branch_id.manager_id.id == uid
            )

    @api.depends('assignment_id', 'assignment_id.manager_id', 'assignment_id.manager_id.user_id')
    def _compute_is_shift_manager(self):
        uid = self.env.uid
        for task in self:
            mgr = task.assignment_id and task.assignment_id.manager_id
            task.is_shift_manager = bool(mgr and mgr.user_id and mgr.user_id.id == uid)

    @api.depends('is_branch_manager', 'is_shift_manager')
    def _compute_can_audit(self):
        for task in self:
            task.can_audit = task.is_branch_manager or task.is_shift_manager

    @api.depends('proof_image_ids')
    def _compute_proof_image_count(self):
        for task in self:
            task.proof_image_count = len(task.proof_image_ids)

    def write(self, vals):
        if 'state' in vals and vals.get('state') == 'delayed':
            ready_tasks = self.filtered(lambda t: t.state == 'ready')
        else:
            ready_tasks = self.browse()

        if 'state' in vals and vals.get('state') == 'ready':
            from_suspended = self.filtered(lambda t: t.state == 'suspended')
            if from_suspended:
                vals = dict(vals)
                vals['notification_sent'] = True

        proof_image_data = vals.pop('proof_image', None)
        if proof_image_data and self.env.context.get('proof_image_append', True) and len(self) == 1:
            task = self
            if task.state == 'ready':
                current_count = len(task.proof_image_ids)
                if current_count >= 5:
                    raise UserError(_('Đã đủ tối đa 5 ảnh minh chứng. Không thể thêm ảnh mới.'))
                self.env['ttb.task.proof.image'].create({
                    'task_id': task.id,
                    'image': proof_image_data,
                    'sequence': 10 + current_count,
                })

        res = super(TtbOperationalTask, self).write(vals)
        if ready_tasks:
            ready_tasks.write({'notification_sent': False})
        return res

    # ---------------------------------------------------------
    # CRON
    # ---------------------------------------------------------
    @api.model
    def _cron_activate_tasks(self):
        now = fields.Datetime.now()
        waiting_tasks = self.search([
            ('state', '=', 'waiting'),
            ('planned_date_start', '<=', now)
        ])
        if waiting_tasks:
            waiting_tasks.write({'state': 'ready'})

    @api.model
    def _cron_check_late_tasks(self):
        now = fields.Datetime.now()
        ready_tasks = self.search([('state', '=', 'ready')])
        late_tasks = ready_tasks.filtered(
            lambda t: (t.planned_date_end_by_delay or t.planned_date_end)
            and (t.planned_date_end_by_delay or t.planned_date_end) < now
        )
        if late_tasks:
            late_tasks.write({
                'is_late': True,
                'state': 'undone',
            })

    @api.model
    def _cron_auto_resume_delayed_tasks(self):
        now = fields.Datetime.now()
        to_resume = self.search([
            ('state', '=', 'delayed'),
            ('delay_until', '!=', False),
            ('delay_until', '<=', now),
        ])
        for task in to_resume:
            try:
                task.action_resume()
            except Exception:
                pass

    @api.model
    def _cron_send_ready_task_notifications(self):
        Task = self.env['ttb.operational.task']
        ready_tasks = Task.search([
            ('state', '=', 'ready'),
            ('notification_sent', '=', False),
            ('employee_id.user_id', '!=', False),
        ])
        by_user = {}
        for task in ready_tasks:
            user = task.employee_id.user_id
            if not user:
                continue
            if getattr(user, 'ttb_notification_enabled', True) is False:
                continue
            by_user.setdefault(user.id, []).append(task)

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '').rstrip('/')
        action = self.env.ref('ttb_khuvuichoi.action_my_tasks', raise_if_not_found=False)
        action_id = action.id if action else None

        for user_id, tasks in by_user.items():
            if not tasks:
                continue
            user = self.env['res.users'].browse(user_id)
            n = len(tasks)
            has_rework = any(t.is_rework for t in tasks)
            has_adhoc = any(t.is_adhoc for t in tasks)
            if has_rework and n == 1:
                summary = _('Bạn đang có công việc khắc phục cần thực hiện.')
            elif has_rework:
                summary = _('Bạn có %s công việc khắc phục cần thực hiện.', n)
            elif n == 1:
                summary = _('Bạn đang có công việc cần thực hiện.')
            else:
                summary = _('Bạn có %s công việc cần thực hiện.', n)

            task_ids = [t.id for t in tasks]
            if action_id and base_url:
                domain = [['id', 'in', task_ids]]
                domain_str = urllib.parse.quote(json.dumps(domain))
                url = f"{base_url}/web#action={action_id}&model=ttb.operational.task&view_type=kanban&domain={domain_str}"
                note = _('Nhấn vào link sau để xem danh sách công việc: <br/><a href="%s">Xem %s công việc</a>', url, n)
            else:
                note = _('%s công việc cần thực hiện. Vào menu Công việc của tôi và lọc nhóm Sẵn sàng.', n)

            first_task = tasks[0]
            first_task.activity_schedule(
                act_type_xmlid='mail.mail_activity_data_todo',
                user_id=user_id,
                summary=summary,
                note=note,
            )
            Task.browse(task_ids).write({'notification_sent': True})

    @api.model
    def _get_audit_selection_probability(self):
        """Xác suất chọn công việc để hậu kiểm (0.0–1.0). Mặc định 20%."""
        val = self.env['ir.config_parameter'].sudo().get_param(
            'ttb_khuvuichoi.audit_selection_probability', '0.2'
        )
        try:
            return float(val)
        except (TypeError, ValueError):
            return 0.2

    def _maybe_select_for_audit(self):
        """
        Ngay khi Nhân viên bấm "Hoàn thành": quay số với xác suất cấu hình (vd 20%).
        Nếu trúng thì đánh dấu "Cần kiểm tra lại" và gửi thông báo/activity cho Quản lý cơ sở.
        """
        self.ensure_one()
        if self.is_audit_required:
            return
        prob = self._get_audit_selection_probability()
        if random.random() >= prob:
            return
        self.write({
            'is_audit_required': True,
            'audit_state': 'pending',
        })
        manager = self.branch_id and self.branch_id.manager_id
        if manager:
            self.activity_schedule(
                act_type_xmlid='mail.mail_activity_data_todo',
                user_id=manager.id,
                summary=_('Cần hậu kiểm'),
                note=_('Công việc "%s" đã được chọn kiểm tra. Vui lòng đi kiểm tra.', self.name),
            )

    # ---------------------------------------------------------
    # ACTIONS: Hoàn thành / Tạm hoãn / Tiếp tục
    # ---------------------------------------------------------
    def action_done(self):
        self.ensure_one()
        if self.state != 'ready':
            raise UserError(_("Công việc này chưa sẵn sàng."))

        count = len(self.proof_image_ids)
        if count < 1:
            raise UserError(_("Cần tối thiểu 1 ảnh minh chứng để hoàn thành công việc. Hiện có %s ảnh.") % count)
        if count > 5:
            raise UserError(_("Chỉ được tối đa 5 ảnh minh chứng. Vui lòng xóa bớt ảnh."))

        self.write({
            'state': 'done',
            'actual_date_end': fields.Datetime.now(),
            'proof_image': False,
        })
        self._maybe_select_for_audit()

    def action_open_delay_wizard(self):
        self.ensure_one()
        return {
            'name': 'Báo cáo Tạm hoãn',
            'type': 'ir.actions.act_window',
            'res_model': 'ttb.task.delay.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_task_id': self.id}
        }

    def action_open_delay_report_wizard(self):
        self.ensure_one()
        return {
            'name': _('Báo cáo Sự cố / Tạm hoãn'),
            'type': 'ir.actions.act_window',
            'res_model': 'ttb.task.delay.report.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_task_id': self.id}
        }

    def _unlink_subsequent_same_type_in_area(self):
        self.ensure_one()
        if not self.assignment_id or not self.template_id or not self.area_id:
            return
        Task = self.env['ttb.operational.task']
        to_unlink = Task.search([
            ('assignment_id', '=', self.assignment_id.id),
            ('template_id', '=', self.template_id.id),
            ('area_id', '=', self.area_id.id),
            ('planned_date_start', '>', self.planned_date_start),
            ('state', 'not in', ['done', 'delayed', 'suspended']),
            ('is_late', '=', False),
        ])
        if to_unlink:
            to_unlink.unlink()

    def action_open_delay_confirm_wizard(self):
        self.ensure_one()
        if not self.can_audit:
            raise UserError(_("Chỉ Quản lý ca hoặc Quản lý nhà sách mới được tạm hoãn công việc."))
        return {
            'name': _('Xác nhận Tạm hoãn'),
            'type': 'ir.actions.act_window',
            'res_model': 'ttb.task.delay.confirm.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_task_id': self.id,
                'default_reason_id': self.delay_reason_id.id,
                'default_note': self.delay_note,
                'default_delay_until': self.delay_until,
            }
        }

    def _regenerate_subsequent_same_type_in_area(self):
        self.ensure_one()
        if not self.assignment_id or not self.template_id or not self.area_id:
            return
        assignment = self.assignment_id
        template = self.template_id
        area = self.area_id
        start_dt, end_dt = assignment._get_shift_time_range()
        line = assignment.line_ids.filtered(lambda l: l.area_id == area)
        if not line or not line.employee_ids:
            return
        assigned_employees = line.employee_ids
        freq = template.frequency_minutes or 60
        duration = template.duration_minutes or 15
        duration_use = max(duration, 15)

        ref_time = self.planned_date_end_by_delay or self.planned_date_end

        # Các slot đã tồn tại (tránh tạo trùng)
        Task = self.env['ttb.operational.task']
        existing = Task.search([
            ('assignment_id', '=', assignment.id),
            ('template_id', '=', template.id),
            ('area_id', '=', area.id),
            ('planned_date_start', '!=', False),
        ])
        existing_keys = {
            (t.template_id.id, t.area_id.id, fields.Datetime.to_string(t.planned_date_start))
            for t in existing
        }

        # Slot đầu tiên >= thời gian kết thúc của task vừa tiếp tục
        from_after = self.planned_date_end
        slot_start = start_dt
        while slot_start < from_after:
            slot_start += timedelta(minutes=freq)

        tasks_to_create = []
        # Số thứ tự slot từ đầu ca (để xoay nhân viên giống lúc sinh tự động)
        slot_count_from_start = int((slot_start - start_dt).total_seconds() / 60 / freq) if freq else 0

        while slot_start < end_dt:
            key = (template.id, area.id, fields.Datetime.to_string(slot_start))
            if key in existing_keys:
                slot_start += timedelta(minutes=freq)
                slot_count_from_start += 1
                continue
            planned_end = slot_start + timedelta(minutes=freq)
            if ref_time is not None and ref_time and ref_time >= slot_start:
                slot_start += timedelta(minutes=freq)
                slot_count_from_start += 1
                continue
            employee = assigned_employees[slot_count_from_start % len(assigned_employees)]
            display_time = (slot_start + timedelta(hours=7)).strftime('%H:%M')
            tasks_to_create.append({
                'name': f"{template.name} ({display_time})",
                'assignment_id': assignment.id,
                'template_id': template.id,
                'area_id': area.id,
                'employee_id': employee.id,
                'planned_date_start': slot_start,
                'planned_date_end': planned_end,
                'state': 'waiting',
                'is_adhoc': False,
            })
            existing_keys.add(key)
            slot_start += timedelta(minutes=freq)
            slot_count_from_start += 1

        if tasks_to_create:
            Task.create(tasks_to_create)

    def action_resume(self):
        self.ensure_one()
        now = fields.Datetime.now()
        if self.planned_date_end and now <= self.planned_date_end:
            planned_date_end_by_delay_new = False
        else:
            duration = (self.template_id and self.template_id.duration_minutes) or 15
            duration_use = max(duration, 15)
            planned_date_end_by_delay_new = now + timedelta(minutes=duration_use)

        vals = {
            'state': 'ready',
            'planned_date_end_by_delay': planned_date_end_by_delay_new,
        }
        self.write(vals)
        self._regenerate_subsequent_same_type_in_area()
        activity = self.activity_ids.filtered(lambda a: a.activity_type_id.name == 'Sự cố vận hành')
        if activity:
            activity.action_done()

    def action_cancel_delay(self):
        self.ensure_one()
        if self.state not in ['suspended', 'delayed']:
            raise UserError(_("Công việc này không ở trạng thái tạm hoãn."))

        self.write({
            'state': 'ready',
            'delay_reason_id': False,
            'delay_note': False,
            'delay_until': False,
            'planned_date_end_by_delay': False,
            'notification_sent': True,
        })
        if self.employee_id.user_id:
            self.activity_schedule(
                act_type_xmlid='mail.mail_activity_data_todo',
                user_id=self.employee_id.user_id.id,
                summary=_('Yêu cầu tạm hoãn của bạn đã bị từ chối, vui lòng tiếp tục công việc.'),
                note=_('Công việc: %s', self.name),
            )

    # ---------------------------------------------------------
    # ACTIONS: Hậu kiểm
    # ---------------------------------------------------------
    def action_audit_pass(self):
        """Đánh giá ĐẠT."""
        self.ensure_one()
        if self.state != 'done':
            raise UserError("Công việc này chưa hoàn thành.")
        if not self.can_audit:
            raise UserError(_("Chỉ Quản lý ca hoặc Quản lý nhà sách mới được đánh giá hậu kiểm (Đạt/Không đạt)."))

        self.write({
            'audit_state': 'pass',
            'audit_user_id': self.env.uid,
            'audit_date': fields.Datetime.now()
        })

    def action_audit_fail_wizard(self):
        """Đánh giá KHÔNG ĐẠT -> Mở popup nhập lý do."""
        self.ensure_one()
        if self.state != 'done':
            raise UserError("Công việc này chưa hoàn thành.")
        if not self.can_audit:
            raise UserError(_("Chỉ Quản lý ca hoặc Quản lý nhà sách mới được đánh giá hậu kiểm (Đạt/Không đạt)."))

        return {
            'name': _('Đánh giá Không đạt'),
            'type': 'ir.actions.act_window',
            'res_model': 'ttb.audit.fail.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_task_id': self.id}
        }

    # ---------------------------------------------------------
    # EMPLOYEE DASHBOARD
    # ---------------------------------------------------------
    @api.model
    def _employee_dashboard_range_domain_utc7(self, range_key):
        """
        Lọc task theo khung giờ planned_date_start / planned_date_end theo ngày Việt Nam (UTC+7).
        Mỗi ngày: start = 00:00:00, end = 23:59:59 (giờ VN).
        """
        key = (range_key or 'before').strip().lower()
        if key in ('all', 'toan_bo', 'toanbo'):
            return [], "Toàn bộ"

        # Ngày hôm nay theo giờ Việt Nam
        now_utc = fields.Datetime.now()
        now_vn = now_utc + timedelta(hours=7)
        today_vn = now_vn.date()

        def _vn_day_to_utc_range(day_vn):
            """Chuyển một ngày VN sang khoảng UTC: 00:00:00 - 23:59:59 VN."""
            start_vn = datetime.combine(day_vn, time(0, 0, 0))
            end_vn = datetime.combine(day_vn, time(23, 59, 59))
            start_utc = start_vn - timedelta(hours=7)
            end_utc = end_vn - timedelta(hours=7)
            return start_utc, end_utc

        if key in ('before', 'truoc'):
            # Trước: task có planned_date_end trước 00:00:00 hôm nay (VN)
            start_today_utc, _ = _vn_day_to_utc_range(today_vn)
            domain = [
                ('planned_date_end', '!=', False),
                ('planned_date_end', '<', fields.Datetime.to_string(start_today_utc)),
            ]
            return domain, "Trước"

        if key in ('today', 'hom_nay', 'homnay'):
            day_vn = today_vn
            label = "Hôm nay"
        elif key in ('tomorrow', 'ngay_mai', 'ngaymai'):
            day_vn = today_vn + timedelta(days=1)
            label = "Ngày mai"
        elif key in ('day2', 'ngay_kia', 'ngaykia'):
            day_vn = today_vn + timedelta(days=2)
            label = "Ngày kia"
        else:
            day_vn = today_vn
            label = "Hôm nay"

        start_utc, end_utc = _vn_day_to_utc_range(day_vn)
        start_utc_str = fields.Datetime.to_string(start_utc)
        end_utc_str = fields.Datetime.to_string(end_utc)
        domain = [
            ('planned_date_start', '<=', end_utc_str),
            '|',
            ('planned_date_end', '=', False),
            ('planned_date_end', '>=', start_utc_str),
        ]
        return domain, label

    @api.model
    def get_employee_dashboard_data(self, range_key='before', limit=50):
        Task = self.env['ttb.operational.task']
        uid = self.env.uid

        domain_base = [
            ('employee_id.user_id', '=', uid),
            ('state', '!=', 'cancel'),
        ]
        range_domain, range_label = self._employee_dashboard_range_domain_utc7(range_key)
        domain = domain_base + range_domain

        total_assigned = Task.search_count(domain)
        total_done = Task.search_count(domain + [('state', '=', 'done')])
        total_not_done = Task.search_count(domain + [('state', 'in', ('waiting', 'ready', 'suspended', 'delayed'))])
        total_late = Task.search_count(domain + [('is_late', '=', True)])

        tasks = Task.search(
            domain,
            order='is_late desc, state asc, planned_date_start asc, id desc',
            limit=int(limit or 50),
        )

        User = self.env['res.users'].sudo()
        current_user = User.browse(uid)
        notification_enabled = getattr(current_user, 'ttb_notification_enabled', True)
        is_admin = self.env.user.has_group('base.group_system')

        state_labels = dict(Task._fields['state'].selection)
        result_tasks = []
        for t in tasks:
            result_tasks.append({
                'id': t.id,
                'name': t.name,
                'area_id': t.area_id.id if t.area_id else False,
                'area_name': t.area_id.name if t.area_id else '-',
                'assignment_date': fields.Date.to_string(t.assignment_id.date) if t.assignment_id.date else False,
                'planned_date_start': fields.Datetime.to_string(t.planned_date_start) if t.planned_date_start else False,
                'planned_date_end': fields.Datetime.to_string(t.planned_date_end) if t.planned_date_end else False,
                'actual_date_end': fields.Datetime.to_string(t.actual_date_end) if t.actual_date_end else False,
                'state': t.state,
                'state_label': state_labels.get(t.state, t.state),
                'is_late': bool(t.is_late),
                'note': (t.delay_note or t.audit_note or '').strip(),
                'notification_sent': bool(t.notification_sent),
            })

        meta_extra = {
            'notification_enabled': notification_enabled,
            'is_admin': is_admin,
        }

        # Công việc không đạt (chỉ nhân viên đăng nhập)
        failed_domain = domain_base + range_domain + [('audit_state', '=', 'fail')]
        failed_tasks_rs = Task.search(
            failed_domain,
            order='actual_date_end desc, id desc',
            limit=int(limit or 50),
        )
        audit_state_labels = dict(Task._fields['audit_state'].selection)
        result_failed = []
        for t in failed_tasks_rs:
            result_failed.append({
                'id': t.id,
                'name': t.name,
                'area_id': t.area_id.id if t.area_id else False,
                'area_name': t.area_id.name if t.area_id else '-',
                'assignment_date': fields.Date.to_string(t.assignment_id.date) if t.assignment_id.date else False,
                'employee_id': t.employee_id.id if t.employee_id else False,
                'employee_name': t.employee_id.name if t.employee_id else False,
                'actual_date_end': fields.Datetime.to_string(t.actual_date_end) if t.actual_date_end else False,
                'status': 'fail',
                'status_label': audit_state_labels.get('fail', 'Không đạt'),
                'note': (t.audit_note or '').strip(),
                'rework_task_name': t.rework_task_id.name if t.rework_task_id else False,
                'rework_task_id': t.rework_task_id.id if t.rework_task_id else False,
            })

        PostAudit = self.env['ttb.post.audit']
        failed_audit_lines = PostAudit.get_employee_failed_audit_lines(range_key=range_key or 'today', limit=limit or 50)

        return {
            'meta': {'uid': uid, **meta_extra},
            'range': {'key': (range_key or 'today'), 'label': range_label, 'domain': range_domain},
            'counts': {
                'assigned': total_assigned,
                'done': total_done,
                'not_done': total_not_done,
                'late': total_late,
            },
            'tasks': result_tasks,
            'failed_audit_tasks': result_failed,
            'failed_audit_lines': failed_audit_lines,
        }

    # ---------------------------------------------------------
    # MANAGER DASHBOARD
    # ---------------------------------------------------------
    @api.model
    def _get_current_user_employee(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)

    @api.model
    def get_manager_dashboard_data(self, range_key='before', limit=50):
        """
        Dashboard Quản lý:
        - Quản lý cơ sở (ttb.branch.manager_id): xem toàn bộ task thuộc các cơ sở mình quản lý.
        - Quản lý ca (assignment_id.manager_id): xem task thuộc các phiếu phân công được chỉ định mình làm quản lý ca.
        Trả về: meta (uid, branch_ids), range, counts, employee_tasks, audit_tasks, failed_audit_tasks.
        """
        Task = self.env['ttb.operational.task']
        uid = self.env.uid

        # Quản lý cơ sở: user là manager_id của ttb.branch
        Branch = self.env['ttb.branch']
        managed_branch_ids = Branch.search([('manager_id', '=', uid)]).ids

        # Quản lý ca: user là manager_id của ttb.shift.assignment (các ca được chỉ định phân công)
        Assignment = self.env['ttb.shift.assignment']
        assignments_managed = Assignment.search([('manager_id.user_id', '=', uid)])
        managed_assignment_branch_ids = assignments_managed.mapped('branch_id').ids

        # Gộp branch_ids để dùng cho filter KPI: quản lý cơ sở thấy hết cơ sở; quản lý ca thấy cơ sở của các ca mình quản lý
        visible_branch_ids = list(set(managed_branch_ids) | set(managed_assignment_branch_ids))

        # Chỉ trả về rỗng khi vừa không phải quản lý cơ sở vừa không phải quản lý ca
        if not managed_branch_ids and not assignments_managed:
            return {
                'meta': {'uid': uid, 'branch_ids': []},
                'range': {'key': (range_key or 'today'), 'label': "Toàn bộ", 'domain': []},
                'counts': {'assigned': 0, 'done': 0, 'not_done': 0, 'late': 0},
                'employee_tasks': [],
                'audit_tasks': [],
                'failed_audit_tasks': [],
                'shift_assignments': [],
            }

        # Task thuộc cơ sở mình quản lý HOẶC thuộc phiếu phân công mình làm quản lý ca
        domain_base = [
            ('state', '!=', 'cancel'),
            '|',
            ('branch_id', 'in', managed_branch_ids),
            ('assignment_id.manager_id.user_id', '=', uid),
        ]
        range_domain, range_label = self._employee_dashboard_range_domain_utc7(range_key)
        domain = domain_base + range_domain

        total_assigned = Task.search_count(domain)
        total_done = Task.search_count(domain + [('state', '=', 'done')])
        total_not_done = Task.search_count(domain + [('state', 'in', ('waiting', 'ready', 'suspended', 'delayed'))])
        total_late = Task.search_count(domain + [('is_late', '=', True)])

        def _serialize_task(t, status_key, status_label):
            return {
                'id': t.id,
                'name': t.name,
                'area_id': t.area_id.id if t.area_id else False,
                'area_name': t.area_id.name if t.area_id else '-',
                'assignment_date': fields.Date.to_string(t.assignment_id.date) if t.assignment_id.date else False,
                'employee_id': t.employee_id.id if t.employee_id else False,
                'employee_name': t.employee_id.name if t.employee_id else False,
                'planned_date_start': fields.Datetime.to_string(t.planned_date_start) if t.planned_date_start else False,
                'planned_date_end': fields.Datetime.to_string(t.planned_date_end) if t.planned_date_end else False,
                'actual_date_end': fields.Datetime.to_string(t.actual_date_end) if t.actual_date_end else False,
                'status': status_key,
                'status_label': status_label,
                'is_late': bool(t.is_late),
                'note': (t.delay_note or t.audit_note or '').strip(),
            }

        state_labels = dict(Task._fields['state'].selection)
        audit_state_labels = dict(Task._fields['audit_state'].selection)

        employee_tasks_rs = Task.search(
            domain + [('is_audit_required', '=', False)],
            order='is_late desc, state asc, planned_date_start asc, id desc',
            limit=int(limit or 50),
        )
        result_employee_tasks = [
            _serialize_task(t, t.state, state_labels.get(t.state, t.state))
            for t in employee_tasks_rs
        ]

        audit_tasks_rs = Task.search(
            domain + [('is_audit_required', '=', True)],
            order='audit_state asc, actual_date_end desc, id desc',
            limit=int(limit or 50),
        )
        result_audit_tasks = [
            _serialize_task(t, t.audit_state, audit_state_labels.get(t.audit_state, t.audit_state))
            for t in audit_tasks_rs
        ]

        # Công việc không đạt (tất cả nhân viên của cơ sở)
        failed_audit_rs = Task.search(
            domain + [('is_audit_required', '=', True), ('audit_state', '=', 'fail')],
            order='actual_date_end desc, id desc',
            limit=int(limit or 50),
        )
        result_failed_audit = []
        for t in failed_audit_rs:
            result_failed_audit.append({
                'id': t.id,
                'name': t.name,
                'area_id': t.area_id.id if t.area_id else False,
                'area_name': t.area_id.name if t.area_id else '-',
                'assignment_date': fields.Date.to_string(t.assignment_id.date) if t.assignment_id.date else False,
                'employee_id': t.employee_id.id if t.employee_id else False,
                'employee_name': t.employee_id.name if t.employee_id else False,
                'actual_date_end': fields.Datetime.to_string(t.actual_date_end) if t.actual_date_end else False,
                'status': 'fail',
                'status_label': audit_state_labels.get('fail', 'Không đạt'),
                'note': (t.audit_note or '').strip(),
                'rework_task_name': t.rework_task_id.name if t.rework_task_id else False,
                'rework_task_id': t.rework_task_id.id if t.rework_task_id else False,
            })

        PostAudit = self.env['ttb.post.audit']
        post_audit_data = PostAudit.get_manager_post_audit_dashboard(
            visible_branch_ids, range_key=range_key or 'today', limit=limit or 50
        )

        # Phiếu phân công ca: lọc theo cơ sở và theo ngày (range_key)
        now_utc = fields.Datetime.now()
        now_vn = now_utc + timedelta(hours=7)
        today_vn = now_vn.date()
        key = (range_key or 'today').strip().lower()
        if key in ('all', 'toan_bo', 'toanbo'):
            assignment_date_domain = []
        elif key in ('before', 'truoc'):
            assignment_date_domain = [('date', '<', fields.Date.to_string(today_vn))]
        elif key in ('tomorrow', 'ngay_mai', 'ngaymai'):
            assignment_date_domain = [('date', '=', fields.Date.to_string(today_vn + timedelta(days=1)))]
        else:
            assignment_date_domain = [('date', '=', fields.Date.to_string(today_vn))]
        assignment_domain = [('branch_id', 'in', visible_branch_ids)] + assignment_date_domain
        assignment_rs = Assignment.search(
            assignment_domain,
            order='date desc, id desc',
            limit=int(limit or 50),
        )
        assignment_state_labels = dict(Assignment._fields['state'].selection)
        shift_assignments = [
            {
                'id': a.id,
                'name': a.name,
                'shift_id': a.shift_id.id if a.shift_id else False,
                'shift_name': a.shift_id.name if a.shift_id else '-',
                'state': a.state,
                'state_label': assignment_state_labels.get(a.state, a.state),
            }
            for a in assignment_rs
        ]

        return {
            'meta': {'uid': uid, 'branch_ids': visible_branch_ids},
            'range': {'key': (range_key or 'today'), 'label': range_label, 'domain': range_domain},
            'counts': {
                'assigned': total_assigned,
                'done': total_done,
                'not_done': total_not_done,
                'late': total_late,
            },
            'shift_assignments': shift_assignments,
            'employee_tasks': result_employee_tasks,
            'audit_tasks': result_audit_tasks,
            'failed_audit_tasks': result_failed_audit,
            'post_audits_by_area': post_audit_data.get('post_audits_by_area', []),
            'failed_audit_lines': post_audit_data.get('failed_audit_lines', []),
        }
