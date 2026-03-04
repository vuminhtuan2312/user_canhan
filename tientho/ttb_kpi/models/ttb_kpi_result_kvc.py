from odoo import fields, models, api
from collections import defaultdict
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class TtbKpiResultKvc(models.Model):
    _name = 'ttb.kpi.result.kvc'
    _description = 'Kết quả KPI khu vui chơi'

    name = fields.Char(string="Mã KPI")
    branch_id = fields.Many2one(string='Cơ sở', comodel_name="ttb.branch")
    avg_score = fields.Float(string='Điểm trung bình')
    period = fields.Date(string='Kỳ sinh phiếu')

    @api.model
    def cron_generate_kvc_result(self, target_date=None):
        kpi_type_id = self.env.ref('ttb_kpi.ttb_kpi_type_kvc').id

        if target_date:
            today = fields.Date.from_string(target_date)
        else:
            today = (datetime.now() + relativedelta(hours=7)).date()

        # Xác định kỳ hiện tại
        def get_current_period(today):
            day = today.day
            if 1 <= day <= 7:
                return 1
            elif 8 <= day <= 14:
                return 2
            elif 15 <= day <= 22:
                return 3
            else:
                return 4

        def get_period_date_range(period, target_date):
            month_start = target_date.replace(day=1)
            if period == 1:
                start = month_start
                end = month_start + timedelta(days=6)
            elif period == 2:
                start = month_start + timedelta(days=7)
                end = month_start + timedelta(days=13)
            elif period == 3:
                start = month_start + timedelta(days=14)
                end = month_start + timedelta(days=21)
            else:
                start = month_start + timedelta(days=22)
                last_day = (month_start + relativedelta(months=1) - timedelta(days=1)).day
                end = month_start.replace(day=last_day)
            return start, end

        current_period = get_current_period(today)
        if current_period == 1:
            target_month = today - relativedelta(months=1)
            target_period = 4
        else:
            target_month = today
            target_period = current_period - 1

        period_start, period_end = get_period_date_range(target_period, target_month)

        reports = self.env['ttb.task.report'].search([
            ('kpi_type_id', '=', kpi_type_id),
            ('state', '=', 'done'),
            ('date', '>=', period_start),
            ('date', '<=', period_end),
        ])

        grouped = defaultdict(list)
        for rep in reports:
            key = rep.user_branch_id.id
            grouped[key].append(rep)

        for branch_id, reps in grouped.items():
            scores = [r.average_rate_report for r in reps if r.average_rate_report is not None]
            if not scores:
                continue

            avg = sum(scores) / len(scores)
            existing = self.search([
                ('branch_id', '=', branch_id),
                ('period', '=', period_start)
            ], limit=1)

            branch = self.env['ttb.branch'].browse(branch_id)
            if not existing:
                self.create({
                    'name': f'KVC-{branch.name}-{period_start.strftime("%Y%m%d")}',
                    'branch_id': branch_id,
                    'avg_score': avg,
                    'period': period_start
                })
