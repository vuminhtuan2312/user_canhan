from odoo import api, fields, models, _
from statistics import mean
from datetime import date, timedelta

class TtbKpiResultBranch(models.Model):
    _name = 'ttb.kpi.result.branch'
    _description = "Kết quả KPI cơ sở"

    name = fields.Char(string='Mã KPI', required=True, default='Mới')
    branch_id = fields.Many2one(comodel_name='ttb.branch', string='Cơ sở')
    date_from = fields.Date(string='Từ ngày')
    date_to = fields.Date(string='Đến ngày')
    score = fields.Float(string='Kết quả đánh giá', compute='_compute_score', store=True)
    avg_vs_score = fields.Float(string='Điểm Vệ sinh', compute='_compute_score', store=True)
    avg_vm_score = fields.Float(string='Điểm trưng bày hàng hóa', compute='_compute_score', store=True)

    report_ids = fields.One2many(
        comodel_name='ttb.task.report.kpi',
        string="Chi tiết phiếu",
        compute='_compute_report_ids',
        store=False
    )

    @api.depends('branch_id', 'date_from', 'date_to')
    def _compute_report_ids(self):
        for rec in self:
            if not rec.branch_id or not rec.date_from or not rec.date_to:
                rec.report_ids = False
                continue

            domain = [
                ('user_branch_id', '=', rec.branch_id.id),
                ('kpi_type_id.code', 'in', ['VM', 'VS']),
                ('group', 'in', ['region_manager', 'cross_dot_area_manager']),
                ('date', '>=', rec.date_from),
                ('date', '<=', rec.date_to),
                ('report_id.state', '=', 'done'),
            ]
            rec.report_ids = self.env['ttb.task.report.kpi'].search(domain)

    @api.depends('branch_id', 'date_from', 'date_to')
    def _compute_score(self):
        for rec in self:
            score, avg_vm_score, avg_vs_score = rec._get_score_details()
            rec.score = score
            rec.avg_vm_score = avg_vm_score
            rec.avg_vs_score = avg_vs_score

    def _get_score_details(self):
        self.ensure_one()
        if not self.branch_id or not self.date_from or not self.date_to:
            return 0.0, 0.0, 0.0

        domain = [
            ('user_branch_id', '=', self.branch_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('report_id.state', '=', 'done'),
        ]

        reports = self.env['ttb.task.report.kpi'].search(domain)

        # --- Điểm VS ---
        vs_direct = reports.filtered(
            lambda r: r.group == 'region_manager' and r.kpi_type_id.code == 'VS' and r.area_id)
        vs_cross = reports.filtered(
            lambda r: r.group == 'cross_dot_area_manager' and r.kpi_type_id.code == 'VS' and r.area_id)

        vs_direct_map = {}
        for r in vs_direct:
            vs_direct_map.setdefault(r.area_id.id, []).append(r.average_rate)
        vs_direct_avg = mean([mean(vals) for vals in vs_direct_map.values()]) if vs_direct_map else 0

        vs_cross_map = {}
        for r in vs_cross:
            vs_cross_map.setdefault(r.area_id.id, []).append(r.average_rate)
        vs_cross_avg = mean([mean(vals) for vals in vs_cross_map.values()]) if vs_cross_map else 0

        avg_vs_score = mean([vs_direct_avg, vs_cross_avg]) if (
                    vs_direct_avg and vs_cross_avg) else vs_direct_avg or vs_cross_avg

        # --- Điểm VM ---
        vm_direct = reports.filtered(
            lambda r: r.group == 'region_manager' and r.kpi_type_id.code == 'VM' and r.categ_id)
        vm_cross = reports.filtered(
            lambda r: r.group == 'cross_dot_area_manager' and r.kpi_type_id.code == 'VM' and r.categ_id)

        vm_direct_map = {}
        for r in vm_direct:
            vm_direct_map.setdefault(r.categ_id.id, []).append(r.average_rate)
        vm_direct_avg = mean([mean(vals) for vals in vm_direct_map.values()]) if vm_direct_map else 0

        vm_cross_map = {}
        for r in vm_cross:
            vm_cross_map.setdefault(r.categ_id.id, []).append(r.average_rate)
        vm_cross_avg = mean([mean(vals) for vals in vm_cross_map.values()]) if vm_cross_map else 0

        avg_vm_score = mean([vm_direct_avg, vm_cross_avg]) if (vm_direct_avg and vm_cross_avg) else vm_direct_avg or vm_cross_avg

        # Tổng điểm
        final_score = mean([avg_vm_score, avg_vs_score]) if (avg_vm_score and avg_vs_score) else avg_vm_score or avg_vs_score

        return final_score, avg_vm_score, avg_vs_score

    @api.model
    def _cron_generate_kpi_results(self):
        branch_model = self.env['ttb.branch']
        today = fields.Date.today()
        first_day_this_month = today.replace(day=1)
        last_day_this_month = (first_day_this_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)

        branches = branch_model.search([])
        for branch in branches:
            existing = self.search([
                ('branch_id', '=', branch.id),
                ('date_from', '=', first_day_this_month),
                ('date_to', '=', last_day_this_month),
            ])
            if existing:
                existing.write(
                    {'branch_id': branch.id, 'date_from': first_day_this_month, 'date_to': last_day_this_month})
            else:
                # Tạo mới record
                self.create({
                    'name': f'KPI-{branch.name}-{first_day_this_month.strftime("%Y%m")}',
                    'branch_id': branch.id,
                    'date_from': first_day_this_month,
                    'date_to': last_day_this_month,
                })

    @api.model
    def _cron_compute_kpi_result_branch(self):
        today = fields.Date.today()
        records = self.search([('date_from', '<=', today), ('date_to', '>=', today)])
        for rec in records:
            rec._compute_score()
            rec._compute_report_ids()
