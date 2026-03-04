from odoo import api, fields, models, _
from statistics import mean
from datetime import timedelta

class TtbKpiResultManager(models.Model):
    _name = 'ttb.kpi.result.manager'
    _description = 'Kết quả KPI quản lý nhà sách'

    name = fields.Char(string='Mã KPI', required=True, default='Mới')
    user_id = fields.Many2one(comodel_name="res.users", string="Nhân sự", required=True)
    user_job_id = fields.Many2one(comodel_name="hr.job", string="Chức vụ", compute="_compute_job_id", store=True)
    date_from = fields.Date(string='Từ ngày')
    date_to = fields.Date(string='Đến ngày')
    score = fields.Float(string='Kết quả đánh giá', compute='_compute_score', store=True)
    branch_id = fields.Many2one(string="Cơ sở", comodel_name="ttb.branch")

    report_ids = fields.One2many(
        comodel_name='ttb.task.report.kpi',
        string="Chi tiết phiếu",
        compute='_compute_report_ids',
        store=False
    )

    @api.depends('user_id', 'date_from', 'date_to')
    def _compute_report_ids(self):
        for rec in self:
            rec.report_ids = False
            if not rec.user_id or not rec.date_from or not rec.date_to:
                continue

            employee = rec.user_id.employee_ids[:1]
            if not employee:
                continue

            categ_ids = employee.ttb_categ_ids.ids
            area_ids = employee.ttb_area_ids.ids
            branch_ids = employee.ttb_branch_ids.ids
            domain = [
                ('date', '>=', rec.date_from),
                ('date', '<=', rec.date_to),
                ('report_id.state', '=', 'done'),
                ('group', 'in', ['region_manager', 'cross_dot_area_manager', 'branch_mannager']),
                ('user_branch_id', 'in', branch_ids),
                '|',
                '&', ('kpi_type_id.code', '=', 'VM'), ('categ_id', 'in', categ_ids),
                '&', ('kpi_type_id.code', '=', 'VS'), ('area_id', 'in', area_ids)
            ]

            rec.report_ids = self.env['ttb.task.report.kpi'].search(domain)

    @api.depends('user_id')
    def _compute_job_id(self):
        for rec in self:
            rec.user_job_id = rec.user_id.employee_ids[:1].job_id if rec.user_id.employee_ids else False

    @api.depends('user_id', 'date_from', 'date_to')
    def _compute_score(self):
        for rec in self:
            rec.score = rec._get_score()

    def _get_score(self):
        self.ensure_one()
        if not self.user_id or not self.date_from or not self.date_to:
            return 0.0

        employee = self.user_id.employee_ids[:1]
        if not employee:
            return 0.0

        categ_ids = employee.ttb_categ_ids.ids
        area_ids = employee.ttb_area_ids.ids
        branch_ids = employee.ttb_branch_ids.ids

        Report = self.env['ttb.task.report.kpi']
        common_domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('report_id.state', '=', 'done'),
            ('user_branch_id', 'in', branch_ids)
        ]

        # TB1: GĐ vùng / chấm chéo
        tb1_reports = Report.search(common_domain + [('group', 'in', ['region_manager', 'cross_dot_area_manager'])])
        vm_tb1 = tb1_reports.filtered(lambda r: r.kpi_type_id.code == 'VM' and r.categ_id.id in categ_ids and r.user_branch_id.id in branch_ids)
        vs_tb1 = tb1_reports.filtered(lambda r: r.kpi_type_id.code == 'VS' and r.area_id.id in area_ids and r.user_branch_id.id in branch_ids)

        vm_tb1_score = mean([mean(g) for g in self._group_scores(vm_tb1, 'categ_id')]) if vm_tb1 else 0
        vs_tb1_score = mean([mean(g) for g in self._group_scores(vs_tb1, 'area_id')]) if vs_tb1 else 0
        tb1_score = mean([vm_tb1_score, vs_tb1_score]) if vm_tb1_score and vs_tb1_score else vm_tb1_score or vs_tb1_score

        # TB2: GĐ nhà sách
        tb2_reports = Report.search(common_domain + [('group', '=', 'branch_mannager')])
        vm_tb2 = tb2_reports.filtered(lambda r: r.kpi_type_id.code == 'VM' and r.categ_id.id in categ_ids and r.user_branch_id.id in branch_ids)
        vs_tb2 = tb2_reports.filtered(lambda r: r.kpi_type_id.code == 'VS' and r.area_id.id in area_ids and r.user_branch_id.id in branch_ids)

        vm_tb2_score = mean([mean(g) for g in self._group_scores(vm_tb2, 'categ_id')]) if vm_tb2 else 0
        vs_tb2_score = mean([mean(g) for g in self._group_scores(vs_tb2, 'area_id')]) if vs_tb2 else 0
        tb2_score = mean([vm_tb2_score, vs_tb2_score]) if vm_tb2_score and vs_tb2_score else vm_tb2_score or vs_tb2_score

        return mean([tb1_score, tb2_score]) if tb1_score and tb2_score else tb1_score or tb2_score or 0.0

    def _group_scores(self, records, group_field):
        result = {}
        for rec in records:
            key = getattr(rec, group_field).id
            result.setdefault(key, []).append(rec.average_rate)
        return result.values()

    @api.model
    def _cron_generate_kpi_manager_result(self):
        today = fields.Date.today()
        first_day_this_month = today.replace(day=1)
        last_day_this_month = (first_day_this_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)

        employees = self.env['hr.employee'].search([('job_id.name', '=', 'Quản lý Nhà sách')])
        for emp in employees:
            if not emp.user_id:
                continue
            existing = self.search([
                ('user_id', '=', emp.user_id.id),
                ('date_from', '=', first_day_this_month),
                ('date_to', '=', last_day_this_month)
            ])
            if not existing:
                self.create({
                    'name': f'KPI-{first_day_this_month.strftime("%Y%m")}-{emp.user_id.login}',
                    'user_id': emp.user_id.id,
                    'branch_id': emp.ttb_branch_ids[:1].id,
                    'date_from': first_day_this_month,
                    'date_to': last_day_this_month,
                })

    @api.model
    def _cron_compute_kpi_result_manager(self):
        today = fields.Date.today()
        records = self.search([('date_from', '<=', today), ('date_to', '>=', today)])
        for rec in records:
            rec._compute_score()
            rec._compute_report_ids()
            rec._compute_job_id()
