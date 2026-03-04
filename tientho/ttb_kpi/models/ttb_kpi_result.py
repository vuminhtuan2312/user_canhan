import datetime
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class TtbKpiResult(models.Model):
    _name = 'ttb.kpi.result'
    _description = 'Kết quả KPI '
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Mã KPI', required=True, default='Mới')
    user_id = fields.Many2one(comodel_name='res.users', string='Nhân sự')
    job_id = fields.Many2one(string='Chức vụ', comodel_name='hr.job')
    warehouse_id = fields.Many2one(string='Cơ sở cũ', comodel_name='stock.warehouse')
    branch_id = fields.Many2one(string='Cơ sở', comodel_name='ttb.branch')

    @api.onchange('user_id')
    def _onchange_user_id(self):
        for rec in self:
            rec.branch_id = rec.user_id.ttb_branch_id.id
            rec.job_id = rec.user_id.employee_id.job_id.id

    company_id = fields.Many2one(comodel_name='res.company', string='Công ty', index=True, default=lambda self: self.env.company)
    date_from = fields.Date(string='Từ ngày')
    date_to = fields.Date(string='Đến ngày')
    score = fields.Float(string='Kết quả đánh giá', compute='_compute_score', store=True)
    employee_level = fields.Selection([
        ('staff', 'Nhân viên'),
        ('manager', 'Quản lý nhà sách'),
        ('branch_manager', 'Giám đốc nhà sách'),
        ('region_manager', 'Quản lý vùng'),
    ], string='Cấp bậc nhân viên', required=True, default='staff')

    @api.depends('line_ids', 'line_ids.weight', 'line_ids.score')
    def _compute_score(self):
        for rec in self:
            score = 0
            user_archive = self.env['hr.employee'].search([('id','=',rec.user_id.employee_id.id),('quit_type','=','sudden_leave')])
            if user_archive:
                score = 0
            else:
                for line in rec.line_ids:
                    score += line.weight * line.score
            rec.score = score

    template_id = fields.Many2one(comodel_name='ttb.kpi.template', string='Quy tắc tính KPI')
    line_ids = fields.One2many(string='Danh sách KPI', comodel_name='ttb.kpi.result.line', inverse_name='result_id', readonly=True)
    report_kpi_ids = fields.Many2many(string='KPI đánh giá nhiệm vụ', comodel_name='ttb.task.report.kpi', compute='_compute_report_kpi_ids', store=True)

    @api.depends('user_id', 'date_from', 'date_to')
    def _compute_report_kpi_ids(self):
        TaskReportKPI = self.env['ttb.task.report.kpi']
        for rec in self:
            domain_base = [
                ('date', '>=', rec.date_from),
                ('date', '<=', rec.date_to),
                ('report_id.state', 'in', ['done', 'cancel'])
            ]
            level = rec.employee_level
            user = rec.user_id
            report_kpi_ids = TaskReportKPI.browse([])

            def _domain(extra):
                return domain_base + extra

            if level == 'staff':
                report_kpi_ids |= TaskReportKPI.search(_domain([
                    ('report_id.kpi_type_id.code', '=', 'CSKH'),
                    '|',
                    ('report_id.user_ids', 'in', user.id),
                    ('report_id.user_id', '=', user.id),
                ]))
                report_kpi_ids |= TaskReportKPI.search(_domain([
                    ('report_id.kpi_type_id.code', '=', 'VS'),
                    ('report_id.group', '=', 'manager'),
                    ('report_id.user_ids', 'in', user.id)
                ]))
                report_kpi_ids |= TaskReportKPI.search(_domain([
                    ('report_id.kpi_type_id.code', '=', 'VS'),
                    ('report_id.group', 'in', [('branch_manager', 'region_manager')]),
                    ('report_id.user_branch_id', 'in', user.ttb_branch_ids.ids),
                    ('report_id.area_id', 'in', user.ttb_area_ids.ids)
                ]))
                report_kpi_ids |= TaskReportKPI.search(_domain([
                    ('report_id.kpi_type_id.code', '=', 'VM'),
                    ('report_id.group', '=', 'manager'),
                    ('report_id.user_ids', 'in', user.id)
                ]))
                report_kpi_ids |= TaskReportKPI.search(_domain([
                    ('report_id.kpi_type_id.code', '=', 'VM'),
                    ('report_id.group', 'in', [('branch_manager', 'region_manager')]),
                    ('report_id.user_branch_id', 'in', user.ttb_branch_ids.ids),
                    ('report_id.categ_id', 'in', user.ttb_categ_ids.ids)
                ]))
            elif level == 'manager':
                report_kpi_ids |= TaskReportKPI.search(_domain([
                    ('report_id.kpi_type_id.code', '=', 'VS'),
                    ('report_id.group', '=', 'branch_mannager'),
                    ('report_id.user_id', '=', user.id)
                ]))
                report_kpi_ids |= TaskReportKPI.search(_domain([
                    ('report_id.kpi_type_id.code', '=', 'VS'),
                    ('report_id.group', 'in', [('branch_manager', 'region_manager')]),
                    ('report_id.user_branch_id', 'in', user.ttb_branch_ids.ids),
                    ('report_id.area_id', 'in', user.ttb_area_ids.ids)
                ]))
                report_kpi_ids |= TaskReportKPI.search(_domain([
                    ('report_id.kpi_type_id.code', '=', 'VM'),
                    ('report_id.group', '=', 'branch_mannager'),
                    ('report_id.user_id', '=', user.id)
                ]))
                report_kpi_ids |= TaskReportKPI.search(_domain([
                    ('report_id.kpi_type_id.code', '=', 'VM'),
                    ('report_id.group', 'in', [('manager', 'region_manager')]),
                    ('report_id.user_branch_id', 'in', user.ttb_branch_ids.ids),
                    ('report_id.categ_id', 'in', user.ttb_categ_ids.ids)
                ]))
            elif level == 'branch_manager':
                report_kpi_ids |= TaskReportKPI.search(_domain([
                    ('report_id.kpi_type_id.code', '=', 'VS'),
                    ('report_id.user_branch_id', 'in', user.ttb_branch_ids.ids),
                ]))
                report_kpi_ids |= TaskReportKPI.search(_domain([
                    ('report_id.kpi_type_id.code', '=', 'VM'),
                    ('report_id.user_branch_id', 'in', user.ttb_branch_ids.ids),
                ]))
            elif level == 'region_manager':
                report_kpi_ids |= TaskReportKPI.search(_domain([
                    ('report_id.kpi_type_id.code', '=', 'VS'),
                    ('report_id.user_branch_id', 'in', user.ttb_branch_ids.ids),
                ]))
                report_kpi_ids |= TaskReportKPI.search(_domain([
                    ('report_id.kpi_type_id.code', '=', 'VM'),
                    ('report_id.user_branch_id', 'in', user.ttb_branch_ids.ids),
                ]))
            rec.report_kpi_ids = report_kpi_ids
    target_line_ids = fields.Many2many(string='Thực hiện chỉ tiêu', comodel_name='ttb.kpi.target.line', compute='_compute_target_line_ids', store=True)

    @api.depends('warehouse_id', 'date_from', 'date_to')
    def _compute_target_line_ids(self):
        for rec in self:
            target_line_ids = self.env['ttb.kpi.target.line'].sudo().search([('warehouse_id', '=', rec.warehouse_id.id), ('target_id.date_from', '=', rec.date_from), ('target_id.date_to', '=', rec.date_to)])
            rec.target_line_ids = target_line_ids.ids

    def _write_name(self):
        for rec in self:
            date_from = rec.date_from or datetime.date.today()
            user_id = rec.user_id or self.env.user
            rec.name = f'KPI{date_from.strftime("%Y")}{date_from.strftime("%m")}-{user_id.login}'

    @api.model_create_multi
    def create(self, vals_list):
        res = super(TtbKpiResult, self).create(vals_list)
        res._write_name()
        return res

    def write(self, values):
        res = super().write(values)
        if 'date_from' in values or 'user_id' in values:
            self._write_name()
        return res

    def _cron_create_data(self):
        self_sudo = self.sudo()
        kpi_templates = self_sudo.env['ttb.kpi.template'].search([('active', '=', True)])
        today = fields.Date.context_today(self)
        date_from = today.replace(day=1)
        date_to = today.replace(month=today.month + 1, day=1) - datetime.timedelta(days=1)
        for rec in kpi_templates:
            hr_employees = self_sudo.env['hr.employee'].search([('company_id', '=', rec.company_id.id), ('job_id', 'in', rec.job_ids.ids), ('user_id', '!=', False)])
            user_ids = hr_employees.mapped('user_id')
            check_kpi_result = self_sudo.search([('template_id', '=', rec.id), ('user_id', 'in', user_ids.ids), ('date_from', '=', date_from), ('date_to', '=', date_to), ('company_id', '=', rec.company_id.id)]).mapped('user_id')
            for emp in hr_employees:
                if emp.user_id in check_kpi_result: continue
                line_ids = []
                for line in rec.line_ids:
                    line_ids.append([0, 0, {'type_id': line.type_id.id,
                                     'weight': line.weight}])
                self_sudo.create({'user_id': emp.user_id.id,
                             'job_id': emp.job_id.id,
                             'branch_id': emp.user_id.ttb_branch_ids[:1].id if emp.user_id.ttb_branch_ids else False,
                             'company_id': rec.company_id.id,
                             'date_from': date_from,
                             'date_to': date_to,
                             'template_id': rec.id,
                             'line_ids': line_ids
                             })

    def _cron_compute_all(self):
        today = datetime.date.today()
        kpi_result = self.search([('date_from', '<=', today), ('date_to', '>=', today)])
        for rec in kpi_result:
            rec._compute_report_kpi_ids()
            rec._compute_target_line_ids()
            rec.line_ids._compute_achieve()


class TtbKpiResultLine(models.Model):
    _name = 'ttb.kpi.result.line'
    _description = 'Chi tiết quy tắc tính KPI '
    _inherit = ['mail.thread', 'mail.activity.mixin']

    result_id = fields.Many2one(string='Kết quả KPI', comodel_name='ttb.kpi.result', required=True)
    type_id = fields.Many2one(string='Loại KPI', comodel_name='ttb.kpi.type', required=True)
    weight = fields.Float(string='Trọng số', readonly=True)
    achieve = fields.Float(string='Điểm đạt được', compute='_compute_achieve', store=True)
    overdue_rate = fields.Float(string='Tỷ lệ phạt phiếu quá hạn')
    overdue_count = fields.Integer(string='Số phiếu quá hạn', compute='_compute_overdue_info', store=True)
    overdue_point = fields.Float(string='Điểm phạt phiếu quá hạn', compute='_compute_overdue_info', store=True)

    @api.depends('type_id', 'type_id.source')
    def _compute_achieve(self):
        for rec in self.sudo():
            achieve = 0
            if rec.type_id.source == 'expend':
                target_line_ids = rec.result_id.target_line_ids.filtered_domain([('target_type', '=', 'expend')])
            elif rec.type_id.source == 'revenue':
                target_line_ids = rec.result_id.target_line_ids.filtered_domain([('target_type', '=', 'revenue')])
            else:
                target_line_ids = rec.result_id.report_kpi_ids.filtered_domain([('kpi_type', '=', rec.type_id.id), ('report_id.state', '=', 'done')])
            if rec.type_id.method == 'newest' and target_line_ids:
                sort_target_line_ids = target_line_ids.sorted(key='id', reverse=True)
                if rec.type_id.source in ['expend', 'revenue']:
                    achieve = sort_target_line_ids[:1].current_rate
                else:
                    achieve = sort_target_line_ids[:1].total_rate
            elif rec.type_id.method == 'total' and target_line_ids:
                if rec.type_id.source in ['expend', 'revenue']:
                    achieve = sum(target_line_ids.mapped('current_rate'))
                else:
                    group_target = set(target_line_ids.report_id.mapped('group'))
                    achieve_group = 0
                    template_detail_id = rec.result_id.template_id.detail_ids.filtered_domain([('type_id', '=', rec.type_id.id)])
                    for group in group_target:
                        template_detail_group = template_detail_id.filtered_domain([('group', '=', group)])
                        weight = template_detail_group[:1].weight or 0
                        target_line_group_ids = target_line_ids.filtered_domain([('report_id.group', '=', group)])
                        achieve_group += max(0, 1 - sum(target_line_group_ids.mapped('total_rate'))) * weight
                    achieve = achieve_group
            elif rec.type_id.method == 'average' and target_line_ids:
                if rec.type_id.source in ['expend', 'revenue']:
                    total_achieve = sum(target_line_ids.mapped('current_rate'))
                    achieve = total_achieve / len(target_line_ids)
                else:
                    group_target = set(target_line_ids.report_id.mapped('group'))
                    achieve_group = 0
                    template_detail_id = rec.result_id.template_id.detail_ids.filtered_domain([('type_id', '=', rec.type_id.id)])
                    for group in group_target:
                        template_detail_group = template_detail_id.filtered_domain([('group', '=', group)])
                        weight = template_detail_group[:1].weight or 0
                        target_line_group_ids = target_line_ids.filtered_domain([('report_id.group', '=', group)])
                        achieve_group += (sum(target_line_group_ids.mapped('average_rate'))/len(target_line_group_ids)) * weight
                    achieve = achieve_group
            rec.achieve = achieve

    score = fields.Float(string='Kết quả', compute='_compute_score', compute_sudo=True, store=True, aggregator="avg", digits=(16, 1))
    @api.depends('result_id.report_kpi_ids')
    def _compute_overdue_info(self):
        for rec in self:
            overdue = rec.result_id.report_kpi_ids.filtered(lambda r: r.report_id.report_status == 'overdue')
            rec.overdue_point = len(overdue) * rec.overdue_rate

    @api.depends('achieve', 'overdue_point')
    def _compute_score(self):
        for rec in self:
            score = 0
            if rec.type_id.code == 'CSKH':
                all_reports = rec.result_id.report_kpi_ids.filtered(
                    lambda r: r.kpi_type.code == 'CSKH' and r.report_id.state == 'done'
                )
                # Phân loại phiếu của QLCS và GS
                manager_reports = all_reports.filtered(lambda r: r.report_id.group == 'manager')
                cskh_reports = all_reports.filtered(lambda r: r.report_id.group == 'cs')

                adjusted_scores = []
                for manager in manager_reports:
                    # Tìm phiếu GS chấm lại phiếu QLCS này
                    gs_related = cskh_reports.filtered(
                        lambda g: g.report_id.origin_report_id.id == manager.report_id.id)
                    if gs_related:
                        gs_score = gs_related[0].total_rate
                        adjusted_scores.append(min(manager.total_rate, gs_score))
                    else:
                        adjusted_scores.append(manager.total_rate)

                # Điểm trung bình QLCS (NV)
                manager_avg = sum(adjusted_scores) / len(adjusted_scores) if adjusted_scores else 0

                # Điểm GS: chỉ tính nếu có phiếu đạt 100
                gs_final = 1 if any(gs.total_rate == 1 for gs in cskh_reports) else 0

                # Công thức tổng hợp KPI
                score = (manager_avg * 0.3) + (gs_final * 0.7)

                rec.score = score * 100
                continue

            # KPI khác vẫn giữ nguyên công thức cũ (có liên quan tới achieve)
            template_line_ids = rec.result_id.template_id.line_ids.filtered_domain([
                ('type_id', '=', rec.type_id.id)
            ])
            user_archive = self.env['hr.employee'].search([
                ('id', '=', rec.user_id.employee_id.id),
                ('quit_type', '=', 'sudden_leave')
            ])
            if user_archive:
                score = 0
            elif template_line_ids:
                effective_score = rec.achieve - rec.overdue_point
                min_score = template_line_ids[0].min_score
                max_score = template_line_ids[0].max_score

                if effective_score < min_score:
                    score = 0
                elif min_score <= effective_score <= max_score:
                    score = effective_score
                else:
                    score = max_score

            rec.score = score * 100
    user_id = fields.Many2one(string='Nhân viên', related='result_id.user_id', store=True)
    branch_id = fields.Many2one(string='Cơ sở', related='result_id.branch_id', store=True)
    date_from = fields.Date(string='Kỳ đánh giá', related='result_id.date_from', store=True)
