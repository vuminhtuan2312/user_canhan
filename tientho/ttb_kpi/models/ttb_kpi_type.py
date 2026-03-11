from odoo import api, fields, models, _
from datetime import datetime, time, timedelta
import random

class TtbKpiType(models.Model):
    _name = 'ttb.kpi.type'
    _description = 'Loại KPI'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Loại KPI', required=True)
    code = fields.Char(string='Mã loại KPI', required=True, readonly=True)
    source = fields.Selection(string='Nguồn tính', selection=[('task', 'Nhiệm vụ'), ('revenue', 'Chỉ tiêu doanh thu'), ('expend', 'Chỉ tiêu chi phí')], default='task', required=True)
    method = fields.Selection(string='Cách tính', selection=[('total', 'Tổng giá trị'), ('newest', 'Mới nhất'), ('average', 'Trung bình')], default='total', required=True)
    rate_ids = fields.One2many(string='Thang điểm', comodel_name='ttb.kpi.type.rate', inverse_name='type_id')
    company_id = fields.Many2one(comodel_name='res.company', string='Công ty', index=True, default=lambda self: self.env.company)
    is_checklist = fields.Boolean(string='Checklist')
    menu_template_id = fields.Many2one('ir.ui.menu', string='Menu Template ID')
    run_time = fields.Float(string="Giờ chạy (0-23)")
    branch_ids = fields.Many2many("ttb.branch", string="Cơ sở áp dụng")
    schedule_ids = fields.One2many('ttb.kpi.schedule', 'kpi_type_id',string="Lịch sinh phiếu")
    cron_id = fields.Many2one("ir.cron", string="Tác vụ đã lên lịch", tracking=True)
    job_ids = fields.Many2many("hr.job", string='Người đánh giá')
    is_checklist_restaurant = fields.Boolean(string='Check list nhà hàng')
    job_ids_user = fields.Many2many("hr.job", "ttb_kpi_type_user_job_rel", "kpi_type_id", "job_id",string='Người được đánh giá')
    area_ids = fields.Many2many('ttb.area', string='Khu vực')
    group_id = fields.Many2one('ttb.kpi.type.group', string='Nhóm KPI')
    need_approved_plan = fields.Boolean(string='Cần phê duyệt phương án', default=False, help='Nếu không tích chọn thì không cần duyệt phương án của người chấm đưa ra. Nếu tích chọn thì giám đốc cần duyệt phương án người chấm đưa ra')
    @api.model
    def create(self, vals):
        record = super().create(vals)

        if not record.menu_template_id:
            record._create_auto_menus(record)

        record._create_auto_cron()

        return record

    def unlink(self):
        for rec in self:
            if rec.menu_template_id:
                rec.menu_template_id.unlink()

        return super().unlink()

    def _create_auto_menus(self, record):
        menu_obj = self.env['ir.ui.menu'].sudo()
        action_obj = self.env['ir.actions.act_window'].sudo()

        # ID menu cha
        parent_checklist_template = self.env.ref("ttb_kpi.ttb_check_list_template_menu")

        # Menu template
        action_template = action_obj.create({
            'name': f'{record.name}',
            'res_model': 'ttb.task.template',
            'view_mode': 'list,form',
            'context': {
                'default_kpi_type_code': record.code,
            },
            'domain': [
                ('kpi_type_id.code', '=', record.code),
            ],
        })

        # Tạo Menu Template
        menu_template = menu_obj.create({
            'name': f'{record.name}',
            'parent_id': parent_checklist_template.id,
            'action': f'ir.actions.act_window,{action_template.id}',
        })

        record.menu_template_id = menu_template.id

    def get_nextcall(self):
        hour = int(self.run_time)
        minute = int((self.run_time - hour) * 60)

        nextcall = fields.Datetime.now().replace(
            hour=hour,
            minute=minute,
            second=0,
            microsecond=0,
        ) - timedelta(hours=7)

        return nextcall

    def _create_auto_cron(self):
        cron_obj = self.env["ir.cron"]

        cron = cron_obj.sudo().create({
            "name": f"KPI: Tạo phiếu đánh giá {self.name}",
            "model_id": self.env.ref("ttb_kpi.model_ttb_kpi_type").id,
            "state": "code",
            "code": f"model.cron_generate_task_report({self.id})",
            "interval_number": 1,
            "interval_type": "weeks",
            "active": True,
            "nextcall": self.get_nextcall(),
            "user_id": 1
        })

        self.cron_id = cron.id
    def write(self, vals):
        res = super().write(vals)

        if 'run_time' in vals:
            for rec in self:
                if not rec.cron_id or not rec.run_time:
                    continue

                rec.cron_id.sudo().write({
                    "nextcall": self.get_nextcall()
                })

        return res

    def cron_generate_task_report(self, kpi_type_id):
        kpi = self.browse(kpi_type_id)
        today = fields.Date.today()
        today_weekday = today.weekday()
        for schedule in kpi.schedule_ids:
            if today_weekday != int(schedule.day_of_week):
                return

            if schedule.interval_type == "biweekly":
                week_number = today.isocalendar()[1]
                if week_number % 2 == 0:
                    return

            start_weekday = int(schedule.day_of_week)
            deadline_weekday = int(schedule.deadline)

            delta_days = (deadline_weekday - start_weekday) % 7
            deadline_date = today + timedelta(days=delta_days)

            deadline = datetime.combine(deadline_date, time(23, 59, 59))
            self._generate_task_report(kpi, deadline)

    def _generate_task_report(self, kpi, deadline):
        today = fields.Date.today()
        task_templates = kpi.env['ttb.task.template'].search([
            ('date_from', '<=', today),
            ('date_to', '>=', today),
            ('kpi_type_id', '=', kpi.id),
        ])
        if not task_templates:
            return

        TaskReport = self.env['ttb.task.report'].sudo()

        for branch in kpi.branch_ids:
            reviewer_domain = [
                ('employee_id.job_id', 'in', kpi.job_ids.ids),
                ('ttb_branch_ids', '=', branch.id),
            ]
            if kpi.is_checklist_restaurant:
                reviewer_domain.append(
                    ('ttb_area_ids', 'in', kpi.area_ids.ids)
                )

            reviewer = self.env['res.users'].sudo().search(reviewer_domain, limit=1)

            if not reviewer:
                continue

            base_domain_exist = [
                ('kpi_type_id', '=', kpi.id),
                ('deadline', '=', deadline),
                ('user_branch_id', '=', branch.id),
            ]
            if kpi.is_checklist_restaurant:
                all_evaluate_users = self.env['res.users'].sudo().search([
                    ('employee_id.job_id', 'in', kpi.job_ids_user.ids),
                    ('ttb_branch_ids', '=', branch.id),
                ])

                if not all_evaluate_users:
                    continue

                selected_employee = random.choice(all_evaluate_users)

                domain_exist = base_domain_exist + [
                    ('user_id', '=', selected_employee.id)
                ]

                if TaskReport.search(domain_exist, limit=1):
                    continue

                TaskReport.create({
                    'kpi_type_id': kpi.id,
                    'deadline': deadline,
                    'user_branch_id': branch.id,
                    'reviewer_id': reviewer.id,
                    'reviewer_job_id': reviewer.employee_id.job_id.id if reviewer.employee_id else False,
                    'user_id': selected_employee.id,
                })
            else:
                if TaskReport.search(base_domain_exist, limit=1):
                    continue

                report = TaskReport.create({
                    'kpi_type_id': kpi.id,
                    'deadline': deadline,
                    'user_branch_id': branch.id,
                    'reviewer_id': reviewer.id,
                    'reviewer_job_id': reviewer.employee_id.job_id.id if reviewer.employee_id else False,
                })

                partner_ids = reviewer.partner_id.ids
                if partner_ids:
                    report.message_notify(
                        subject=f"Phiếu checklist mới - {kpi.name}",
                        body="Hệ thống vừa sinh phiếu checklist định kỳ.",
                        partner_ids=partner_ids,
                    )

class TtbKpiTypeRate(models.Model):
    _name = 'ttb.kpi.type.rate'
    _description = 'Thang điểm KPI '
    _inherit = ['mail.thread', 'mail.activity.mixin']

    type_id = fields.Many2one(comodel_name='ttb.kpi.type', string='Loại KPI')
    minimum = fields.Float(string='Mức tối thiểu')
    score = fields.Float(string='Điểm đạt được')
