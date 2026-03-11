from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta


class TtbPostAudit(models.Model):
    _name = 'ttb.post.audit'
    _description = 'Hậu kiểm công việc vận hành'

    name = fields.Char(string='Tên hậu kiểm', required=True, copy=False, readonly=True, default=lambda self: self.env['ir.sequence'].next_by_code('ttb.post.audit'))

    assignment_id = fields.Many2one('ttb.shift.assignment', string='Phiếu phân công')
    shift_id = fields.Many2one('resource.calendar', string='Ca làm việc', related='assignment_id.shift_id')
    area_id = fields.Many2one('ttb.area', string='Khu vực')
    branch_id = fields.Many2one('ttb.branch', string='Cơ sở', related='assignment_id.branch_id')

    inspector_ids = fields.Many2many('hr.employee', string='Người kiểm tra')
    inspection_time = fields.Datetime(string='Thời gian hậu kiểm')
    line_ids = fields.One2many('ttb.post.audit.line', 'post_audit_id', string='Chi tiết hậu kiểm')

    state = fields.Selection([('draft', 'Nháp'), ('pending', 'Chờ hậu kiểm'), ('done', 'Đã hậu kiểm'), ('cancel', 'Huỷ')], string='Trạng thái', default='draft')

    @api.model
    def _get_audit_hour_for_date(self, calendar, date_vn):
        """Lấy giờ sinh phiếu hậu kiểm (giờ VN) của ca cho ngày date_vn từ attendance tương ứng ngày đó."""
        if not calendar:
            return 0.0
        Attendance = self.env['resource.calendar.attendance']
        dayofweek = str(date_vn.weekday())
        domain = [
            ('calendar_id', '=', calendar.id),
            ('dayofweek', '=', dayofweek),
            ('ttb_audit_hour', '>', 0),
        ]
        if calendar.two_weeks_calendar:
            week_type = str(Attendance.get_week_type(date_vn))
            domain.append(('week_type', '=', week_type))
        att = Attendance.search(domain, order='sequence, hour_from', limit=1)
        return att.ttb_audit_hour if att else 0.0

    @api.model
    def _cron_generate_post_audits(self):
        now_utc = fields.Datetime.now()
        now_vn = now_utc + timedelta(hours=7)
        today_vn = now_vn.date()
        hour_vn = now_vn.hour + now_vn.minute / 60.0 + now_vn.second / 3600.0

        Calendar = self.env['resource.calendar']
        Assignment = self.env['ttb.shift.assignment']

        shifts = Calendar.search([('active', '=', True)])
        for shift in shifts:
            audit_hour = self._get_audit_hour_for_date(shift, today_vn)
            today_assignments = Assignment.browse()
            if audit_hour > 0 and hour_vn >= audit_hour:
                today_assignments = Assignment.search([
                    ('date', '=', today_vn),
                    ('shift_id', '=', shift.id),
                    ('state', '=', 'done'),
                    ('post_audit_generated', '=', False),
                ])
            past_assignments = Assignment.search([
                ('date', '<', today_vn),
                ('shift_id', '=', shift.id),
                ('state', '=', 'done'),
                ('post_audit_generated', '=', False),
            ])
            assignments = today_assignments | past_assignments
            for assignment in assignments:
                inspectors = self.env['hr.employee']
                if assignment.manager_id:
                    inspectors |= assignment.manager_id
                if assignment.branch_id and assignment.branch_id.manager_id:
                    branch_manager_user = assignment.branch_id.manager_id
                    if branch_manager_user._name == 'res.users':
                        emp = self.env['hr.employee'].search([('user_id', '=', branch_manager_user.id)], limit=1)
                        if emp:
                            inspectors |= emp
                    else:
                        inspectors |= branch_manager_user
                inspector_ids = inspectors.ids if inspectors else []

                for line in assignment.line_ids:
                    if not line.area_id or not line.employee_ids:
                        continue
                    existing = self.search([
                        ('assignment_id', '=', assignment.id),
                        ('area_id', '=', line.area_id.id),
                    ], limit=1)
                    if existing:
                        continue
                    post_audit = self.create({
                        'assignment_id': assignment.id,
                        'area_id': line.area_id.id,
                        'inspector_ids': [(6, 0, inspector_ids)],
                        'state': 'pending',
                    })
                    post_audit._fill_audit_lines_from_tasks()

                assigned_areas = assignment.line_ids.filtered(lambda l: l.area_id and l.employee_ids)
                if assigned_areas:
                    existing_audits = self.search([
                        ('assignment_id', '=', assignment.id),
                        ('state', 'in', ['pending', 'done']),
                    ])
                    covered_area_ids = existing_audits.mapped('area_id').ids
                    required_area_ids = assigned_areas.mapped('area_id').ids
                    if set(required_area_ids) <= set(covered_area_ids):
                        assignment.write({'post_audit_generated': True})

    def _fill_audit_lines_from_tasks(self):
        self.ensure_one()
        if not self.area_id or not self.assignment_id:
            return

        line = self.assignment_id.line_ids.filtered(lambda l: l.area_id == self.area_id)
        assigned_employees = line.employee_ids if line else self.env['hr.employee']
        if not assigned_employees:
            return
        Template = self.env['ttb.work.template']
        templates = Template.search([
            ('area_ids', 'in', self.area_id.id),
            ('is_active', '=', True),
        ])
        if not templates:
            return
        Line = self.env['ttb.post.audit.line']
        Task = self.env['ttb.operational.task']
        for template in templates:
            for employee in assigned_employees:
                task = Task.search([
                    ('assignment_id', '=', self.assignment_id.id),
                    ('area_id', '=', self.area_id.id),
                    ('template_id', '=', template.id),
                    ('employee_id', '=', employee.id),
                    ('state', '!=', 'cancel'),
                ], order='planned_date_start', limit=1)
                Line.create({
                    'post_audit_id': self.id,
                    'template_line_id': template.id,
                    'task_id': task.id if task else False,
                    'employee_ids': [(6, 0, [employee.id])],
                })

    def _create_rework_tasks_for_failed_lines(self, inspection_time):
        self.ensure_one()
        Task = self.env['ttb.operational.task']
        failed_lines = self.line_ids.filtered(lambda l: l.is_fail)
        if not failed_lines:
            return
        start_display = (inspection_time + timedelta(hours=7)).strftime('%H:%M')

        for line in failed_lines:
            template = line.template_line_id
            if not template:
                continue
            line_name = template.name or (line.task_id.name if line.task_id else '') or _('Công việc làm lại')
            task_name = f"Khắc phục - {line_name} ({start_display})"
            employee = line.employee_ids[0] if line.employee_ids else self.env['hr.employee']
            freq_minutes = template.frequency_minutes or template.duration_minutes or 15
            planned_end = inspection_time + timedelta(minutes=freq_minutes)
            area = self.area_id
            if not area and template.area_ids:
                area = template.area_ids[0]

            vals = {
                'name': task_name,
                'assignment_id': self.assignment_id.id,
                'template_id': template.id,
                'area_id': area.id if area else False,
                'employee_id': employee.id if employee else False,
                'planned_date_start': inspection_time,
                'planned_date_end': planned_end,
                'state': 'waiting',
                'is_rework': True,
                'is_adhoc': False,
            }
            new_task = Task.create(vals)
            if line.task_id:
                line.task_id.write({'rework_task_id': new_task.id})

    def action_done(self):
        self.ensure_one()
        if self.state != 'pending':
            raise ValidationError(_('Phiếu hậu kiểm này không ở trạng thái chờ hậu kiểm.'))

        now_dt = fields.Datetime.now()
        for line in self.line_ids:
            if not line.is_pass and not line.is_fail:
                label = (line.template_line_id.name if line.template_line_id else None) or (line.task_id.name if line.task_id else '')
                raise ValidationError(_('Công việc "%s": chỉ được chọn Đạt hoặc Không đạt.', label))
            if line.is_fail and not line.proof_image:
                label = (line.template_line_id.name if line.template_line_id else None) or (line.task_id.name if line.task_id else '')
                raise ValidationError(_('Công việc không đạt "%s": cần tối thiểu 1 ảnh minh chứng.') % label)

            # Cập nhật trạng thái hậu kiểm lên công việc vận hành (nếu có task)
            if not line.task_id:
                continue
            vals = {
                'is_audit_required': True,
                'audit_state': 'pass' if line.is_pass else 'fail',
            }
            line.task_id.write(vals)

        self.write({
            'state': 'done',
            'inspection_time': now_dt,
        })

        self._create_rework_tasks_for_failed_lines(now_dt)

    def action_cancel(self):
        self.ensure_one()
        if self.state != 'pending':
            raise ValidationError(_('Phiếu hậu kiểm này không ở trạng thái chờ hậu kiểm.'))

        self.write({
            'state': 'cancel',
        })

    @api.model
    def _post_audit_date_domain(self, range_key):
        """Domain theo ngày phân công (assignment.date) tương ứng range_key (today, before, ...)."""
        from datetime import datetime, timedelta, time
        key = (range_key or 'today').strip().lower()
        now_utc = fields.Datetime.now()
        now_vn = now_utc + timedelta(hours=7)
        today_vn = now_vn.date()
        if key in ('all', 'toan_bo', 'toanbo'):
            return []
        if key in ('before', 'truoc'):
            return [('assignment_id.date', '<', today_vn)]
        if key in ('today', 'hom_nay', 'homnay'):
            return [('assignment_id.date', '=', today_vn)]
        if key in ('tomorrow', 'ngay_mai', 'ngaymai'):
            return [('assignment_id.date', '=', today_vn + timedelta(days=1))]
        if key in ('day2', 'ngay_kia', 'ngaykia'):
            return [('assignment_id.date', '=', today_vn + timedelta(days=2))]
        if key in ('7_days', '7ngay', '7-day', '7day'):
            return [
                ('assignment_id.date', '>=', today_vn - timedelta(days=6)),
                ('assignment_id.date', '<=', today_vn),
            ]
        if key in ('15_days', '15ngay', '15-day', '15day'):
            return [
                ('assignment_id.date', '>=', today_vn - timedelta(days=14)),
                ('assignment_id.date', '<=', today_vn),
            ]
        if key in ('30_days', '30ngay', '30-day', '30day'):
            return [
                ('assignment_id.date', '>=', today_vn - timedelta(days=29)),
                ('assignment_id.date', '<=', today_vn),
            ]
        return [('assignment_id.date', '=', today_vn)]

    @api.model
    def get_manager_post_audit_dashboard(self, branch_ids, range_key='today', limit=None):
        """Dữ liệu dashboard quản lý: phiếu hậu kiểm theo khu vực + công việc không đạt (từ phiếu hậu kiểm)."""
        domain = [('branch_id', 'in', branch_ids)] if branch_ids else []
        domain += self._post_audit_date_domain(range_key)
        search_kw = {'domain': domain, 'order': 'area_id, inspection_time desc, id desc'}
        if limit is not None and limit > 0:
            search_kw['limit'] = int(limit) * 2
        audits = self.search(**search_kw)
        state_labels = dict(self._fields['state'].selection)
        by_area = {}
        for a in audits:
            key = a.area_id.id if a.area_id else 0
            if key not in by_area:
                by_area[key] = {
                    'area_id': a.area_id.id if a.area_id else False,
                    'area_name': a.area_id.name if a.area_id else '-',
                    'post_audits': [],
                }
            by_area[key]['post_audits'].append({
                'id': a.id,
                'name': a.name,
                'shift_id': a.shift_id.id if a.shift_id else False,
                'shift_name': a.shift_id.name if a.shift_id else '-',
                'assignment_date': fields.Date.to_string(a.assignment_id.date) if a.assignment_id and a.assignment_id.date else False,
                'inspection_time': fields.Datetime.to_string(a.inspection_time) if a.inspection_time else False,
                'state': a.state,
                'state_label': state_labels.get(a.state, a.state),
            })
        post_audits_by_area = list(by_area.values())

        Line = self.env['ttb.post.audit.line']
        line_domain = [('post_audit_id.branch_id', 'in', branch_ids), ('is_fail', '=', True)] if branch_ids else [('is_fail', '=', True)]
        for term in self._post_audit_date_domain(range_key):
            if term and len(term) == 3:
                line_domain.append(('post_audit_id.' + term[0], term[1], term[2]))
        line_search_kw = {'domain': line_domain, 'order': 'id desc'}
        if limit is not None and limit > 0:
            line_search_kw['limit'] = int(limit)
        failed_lines = Line.search(**line_search_kw)
        failed_audit_lines = []
        for line in failed_lines:
            audit = line.post_audit_id
            actual_end = line.task_id.actual_date_end if line.task_id else (audit.inspection_time if audit.inspection_time else None)
            rework_task_id = line.task_id.rework_task_id.id if line.task_id and line.task_id.rework_task_id else False
            rework_task_name = line.task_id.rework_task_id.name if line.task_id and line.task_id.rework_task_id else False
            failed_audit_lines.append({
                'id': line.id,
                'post_audit_id': audit.id,
                'area_id': audit.area_id.id if audit.area_id else False,
                'area_name': audit.area_id.name if audit.area_id else '-',
                'template_line_name': line.template_line_id.name if line.template_line_id else '-',
                'template_line_id': line.template_line_id.id if line.template_line_id else False,
                'employee_ids': line.employee_ids.ids,
                'employee_names': ', '.join(line.employee_ids.mapped('name')) if line.employee_ids else '-',
                'actual_date_end': fields.Datetime.to_string(actual_end) if actual_end else False,
                'is_fail': True,
                'note': (line.note or '').strip(),
                'rework_task_id': rework_task_id,
                'rework_task_name': rework_task_name or '-',
            })
        return {'post_audits_by_area': post_audits_by_area, 'failed_audit_lines': failed_audit_lines}

    @api.model
    def get_employee_failed_audit_lines(self, range_key='today', limit=None):
        """Công việc không đạt từ phiếu hậu kiểm mà nhân viên hiện tại phụ trách."""
        emp = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        if not emp:
            return []
        Line = self.env['ttb.post.audit.line']
        domain = [('is_fail', '=', True), ('employee_ids', 'in', [emp.id])]
        for term in self._post_audit_date_domain(range_key):
            if term and len(term) == 3:
                domain.append(('post_audit_id.' + term[0], term[1], term[2]))
        search_kw = {'domain': domain, 'order': 'id desc'}
        if limit is not None and limit > 0:
            search_kw['limit'] = int(limit)
        lines = Line.search(**search_kw)
        result = []
        for line in lines:
            audit = line.post_audit_id
            actual_end = line.task_id.actual_date_end if line.task_id else (audit.inspection_time if audit.inspection_time else None)
            result.append({
                'id': line.id,
                'post_audit_id': audit.id,
                'area_id': audit.area_id.id if audit.area_id else False,
                'area_name': audit.area_id.name if audit.area_id else '-',
                'template_line_name': line.template_line_id.name if line.template_line_id else '-',
                'employee_names': ', '.join(line.employee_ids.mapped('name')) if line.employee_ids else '-',
                'actual_date_end': fields.Datetime.to_string(actual_end) if actual_end else False,
                'is_fail': True,
                'note': (line.note or '').strip(),
                'rework_task_id': line.task_id.rework_task_id.id if line.task_id and line.task_id.rework_task_id else False,
                'rework_task_name': line.task_id.rework_task_id.name if line.task_id and line.task_id.rework_task_id else '-',
            })
        return result

class TtbPostAuditLine(models.Model):
    _name = 'ttb.post.audit.line'
    _description = 'Chi tiết hậu kiểm'

    post_audit_id = fields.Many2one('ttb.post.audit', string='Phiếu hậu kiểm', required=True, ondelete='cascade')
    template_line_id = fields.Many2one('ttb.work.template', string='Công việc', ondelete='set null')
    employee_ids = fields.Many2many('hr.employee', string='Nhân viên phụ trách')

    note = fields.Text(string='Ghi chú đánh giá')
    is_pass = fields.Boolean(string='Đạt')
    is_fail = fields.Boolean(string='Không đạt')
    task_id = fields.Many2one('ttb.operational.task', string='Công việc', ondelete='set null')
    rework_task_id = fields.Many2one('ttb.operational.task', string='Công việc làm lại', related='task_id.rework_task_id', readonly=True)
    state = fields.Selection(related='post_audit_id.state', store=True, readonly=True)

    proof_image = fields.Binary(string='Ảnh chứng minh')
    proof_media_type = fields.Selection([('image', 'Image'), ('video', 'Video')], string='Loại minh chứng')

    @api.constrains('is_pass', 'is_fail')
    def _check_pass_fail(self):
        for line in self:
            if line.is_pass and line.is_fail:
                label = (line.template_line_id.name if line.template_line_id else None) or (line.task_id.name if line.task_id else '')
                raise ValidationError(_('Công việc "%s": chỉ được chọn Đạt hoặc Không đạt.', label))