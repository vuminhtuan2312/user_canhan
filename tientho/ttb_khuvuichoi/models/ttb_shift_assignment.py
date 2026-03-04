# -*- coding: utf-8 -*-
from odoo import models, fields, api, Command
from odoo.exceptions import UserError
from datetime import datetime, timedelta


class TtbShiftAssignment(models.Model):
    _name = 'ttb.shift.assignment'
    _description = 'Phiếu phân công ca'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Mã phiếu', required=True, copy=False, readonly=True, default=lambda self: self.env['ir.sequence'].next_by_code('ttb.shift.assignment'))
    date = fields.Date(string='Ngày phân công', default=fields.Date.context_today)

    shift_id = fields.Many2one('resource.calendar', string='Ca làm việc', required=True)
    branch_id = fields.Many2one('ttb.branch', string='Cơ sở', required=True)
    manager_id = fields.Many2one('hr.employee', string='Quản lý ca')

    state = fields.Selection(
        selection=[
            ('draft', 'Mới'),
            ('assigning', 'Đang phân công'),
            ('done', 'Đã phân công'),
            ('cancel', 'Hủy')
        ],
        string='Trạng thái',
        default='draft',
        tracking=True
    )

    post_audit_generated = fields.Boolean(string='Phiếu hậu kiểm', default=False, readonly=True)

    line_ids = fields.One2many(
        'ttb.shift.assignment.line',
        'assignment_id',
        string='Chi tiết phân công'
    )

    adhoc_task_ids = fields.One2many(
        'ttb.operational.task',
        'assignment_id',
        string='Công việc phát sinh',
        domain = [('is_adhoc', '=', True)]
    )

    # ---------------------------------------------------------
    # CRON: Tự động sinh phiếu phân công hàng ngày
    # ---------------------------------------------------------
    @api.model
    def _cron_generate_daily_assignments(self):
        today = fields.Date.context_today(self)
        shifts = self.env['resource.calendar'].search([
            ('active', '=', True),
            ('ttb_branch_ids', '!=', False)
        ])
        assignments_to_create = []

        for shift in shifts:
            for branch in shift.ttb_branch_ids:
                domain = [
                    ('date', '=', today),
                    ('shift_id', '=', shift.id),
                    ('branch_id', '=', branch.id)
                ]
                if self.search_count(domain) == 0:
                    assignments_to_create.append({
                        'date': today,
                        'shift_id': shift.id,
                        'branch_id': branch.id,
                        'state': 'draft',
                    })

        if assignments_to_create:
            self.create(assignments_to_create)

    # ---------------------------------------------------------
    # ACTIONS: Phân công
    # ---------------------------------------------------------
    def _unlink_unfinished_tasks(self):
        self.ensure_one()
        Task = self.env['ttb.operational.task']
        to_unlink = Task.search([
            ('assignment_id', '=', self.id),
            ('state', 'not in', ['done', 'delayed', 'suspended']),
            ('is_late', '=', False),
            ('is_adhoc', '=', False),
        ])
        if to_unlink:
            to_unlink.unlink()

    def _unlink_tasks_for_cancel(self):
        self.ensure_one()
        Task = self.env['ttb.operational.task']
        to_unlink = Task.search([
            ('assignment_id', '=', self.id),
            ('state', '!=', 'done'),
        ])
        if to_unlink:
            to_unlink.unlink()

    def action_start_assign(self):
        """
        Bắt đầu phân công: chuyển sang 'assigning', load danh sách Khu vực thuộc cơ sở vào chi tiết.
        """
        self.ensure_one()
        if not self.branch_id:
            raise UserError("Vui lòng chọn Cơ sở trước khi bắt đầu phân công.")

        self._unlink_unfinished_tasks()

        areas = self.env['ttb.area'].search([('ttb_branch_ids', 'in', self.branch_id.id)])
        lines_commands = []
        existing_area_ids = self.line_ids.mapped('area_id.id')

        for area in areas:
            if area.id not in existing_area_ids:
                lines_commands.append(Command.create({
                    'area_id': area.id,
                    'employee_ids': False
                }))

        self.write({
            'state': 'assigning',
            'line_ids': lines_commands,
            'manager_id': self.env.user.employee_id.id
        })

    def action_confirm(self):
        """Xác nhận & sinh việc tự động."""
        self.ensure_one()

        self._generate_automatic_tasks()

        if not self.manager_id:
            self.write({'manager_id': self.env.user.employee_id.id})

        self.write({'state': 'done'})

    def action_cancel(self):
        self.ensure_one()
        self._unlink_tasks_for_cancel()
        self.write({'state': 'cancel'})

    # ---------------------------------------------------------
    # HELPER: Sinh task tự động
    # ---------------------------------------------------------
    def _generate_automatic_tasks(self):
        TaskObj = self.env['ttb.operational.task']
        start_dt, end_dt = self._get_shift_time_range()
        tasks_to_create = []

        existing_kept_keys = set()
        existing_kept_tasks = TaskObj.search([
            ('assignment_id', '=', self.id),
            ('template_id', '!=', False),
            ('area_id', '!=', False),
            ('planned_date_start', '!=', False),
            '|',
            ('state', 'in', ['done', 'delayed', 'suspended']),
            ('is_late', '=', True),
        ])
        for t in existing_kept_tasks:
            existing_kept_keys.add((
                t.template_id.id,
                t.area_id.id,
                fields.Datetime.to_string(t.planned_date_start),
            ))

        for line in self.line_ids:
            area = line.area_id
            assigned_employees = line.employee_ids
            if not assigned_employees:
                continue

            templates = self.env['ttb.work.template'].search([
                ('area_ids', 'in', area.id),
                ('is_active', '=', True)
            ])

            for template in templates:
                active_delays = TaskObj.search([
                    ('area_id', '=', area.id),
                    ('template_id', '=', template.id),
                    ('state', '=', 'delayed'),
                    ('delay_until', '>', start_dt)
                ])

                freq = template.frequency_minutes or 60
                duration = template.duration_minutes or 15
                current_time = start_dt
                emp_idx = 0

                while current_time < end_dt:
                    planned_end = current_time + timedelta(minutes=freq)

                    is_blocked = False
                    for delay in active_delays:
                        if current_time < delay.delay_until:
                            is_blocked = True
                            break

                    if is_blocked:
                        current_time += timedelta(minutes=freq)
                        continue

                    key = (template.id, area.id, fields.Datetime.to_string(current_time))
                    if key in existing_kept_keys:
                        current_time += timedelta(minutes=freq)
                        continue

                    employee = assigned_employees[emp_idx % len(assigned_employees)]
                    emp_idx += 1

                    display_time = (current_time + timedelta(hours=7)).strftime('%H:%M')
                    tasks_to_create.append({
                        'name': f"{template.name} ({display_time})",
                        'assignment_id': self.id,
                        'template_id': template.id,
                        'area_id': area.id,
                        'employee_id': employee.id,
                        'planned_date_start': current_time,
                        'planned_date_end': planned_end,
                        'state': 'waiting',
                        'is_adhoc': False,
                    })

                    current_time += timedelta(minutes=freq)

        if tasks_to_create:
            TaskObj.create(tasks_to_create)

    def _get_shift_time_range(self):
        """
        Lấy thời gian bắt đầu và kết thúc ca theo shift_id (resource.calendar) trong ngày phân công.
        Dùng attendance_ids của ca: theo ngày trong tuần (và week_type nếu lịch 2 tuần), lấy min hour_from
        và max hour_to. Trừ 7 tiếng để lưu UTC, UI +7 hiển thị đúng giờ VN.
        """
        self.ensure_one()
        utc_offset_hours = 7
        shift = self.shift_id
        dayofweek = str(self.date.weekday())  # 0=Monday, 6=Sunday
        attendances = shift.attendance_ids.filtered(
            lambda a: a.dayofweek == dayofweek and not a.display_type
            and (not a.date_from or a.date_from <= self.date)
            and (not a.date_to or a.date_to >= self.date)
        )
        if shift.two_weeks_calendar:
            week_type = self.env['resource.calendar.attendance'].get_week_type(self.date)
            attendances = attendances.filtered(lambda a: a.week_type == str(week_type))

        if attendances:
            hour_from = min(attendances.mapped('hour_from'))
            hour_to = max(attendances.mapped('hour_to'))
        else:
            # Fallback: cả ngày 08:00–17:00 giờ VN
            hour_from, hour_to = 8.0, 17.0

        start_local = datetime.combine(self.date, datetime.min.time()) + timedelta(hours=hour_from)
        end_local = datetime.combine(self.date, datetime.min.time()) + timedelta(hours=hour_to)
        start_time = start_local - timedelta(hours=utc_offset_hours)
        end_time = end_local - timedelta(hours=utc_offset_hours)
        return start_time, end_time


class TtbShiftAssignmentLine(models.Model):
    _name = 'ttb.shift.assignment.line'
    _description = 'Chi tiết phân công tự động'

    assignment_id = fields.Many2one('ttb.shift.assignment', string='Phiếu phân công', ondelete='cascade')
    area_id = fields.Many2one('ttb.area', string='Khu vực', required=True)
    employee_ids = fields.Many2many('hr.employee', string='Nhân viên phụ trách', domain="[('ttb_branch_ids', 'in', branch_id)]")
    branch_id = fields.Many2one('ttb.branch', string='Cơ sở', related='assignment_id.branch_id')
