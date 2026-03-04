# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime, time

_logger = logging.getLogger(__name__)

class PeriodInventory(models.Model):
    _name = "period.inventory"
    _description = "Đợt kiểm kê"

    name = fields.Char(string="Đợt kiểm kê", required=True)
    code = fields.Char(string="Mã đợt kiểm kê", required=True)
    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Period inventory must be unique.'),
    ]
    start_date = fields.Datetime(string="Ngày bắt đầu", required=True)
    end_date = fields.Datetime(string="Ngày kết thúc", required=True)
    description = fields.Text(string="Mô tả")
    state = fields.Selection([
        ('draft', 'Chưa bắt đầu'),
        ('in_progress', 'Đang kiểm kê'),
        ('done', 'Đã kết thúc'),
        ('cancelled', 'Đã hủy'),
    ], string="Trạng thái", default='draft', required=True)
    is_full_recheck_inventory = fields.Boolean(
        string="Kiểm kê lại toàn bộ",
        help="Nếu tích chọn, đợt kiểm kê này sẽ kiểm kê lại toàn bộ sản phẩm."
    )
    branch_line_ids = fields.One2many(
        "period.inventory.branch",
        "period_inventory_id",
        string="Đợt kiểm kê theo cơ sở",
    )

    @api.constrains('start_date', 'end_date')
    def _check_date_range(self):
        for rec in self:
            if rec.start_date and rec.end_date:
                if rec.start_date > rec.end_date:
                    raise UserError("Ngày bắt đầu không được lớn hơn Ngày kết thúc.")

    @api.onchange('start_date', 'end_date')
    def _onchange_dates(self):
        now = fields.Datetime.now()
        # Kiểm tra ngày bắt đầu > ngày kết thúc
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise UserError("Ngày bắt đầu không được lớn hơn Ngày kết thúc.")

    def action_start(self):
        """Bắt đầu đợt kiểm kê"""
        now = fields.Datetime.now()
        for rec in self:
            # Nếu end_date < hiện tại => đã quá hạn -> không cho start
            if rec.end_date < now:
                raise UserError("Đã qua 'Ngày kết thúc'. Không thể bắt đầu kiểm kê.")
            rec.state = 'in_progress'
            rec.branch_line_ids.filtered(lambda b: b.state == 'draft').write({'state': 'in_progress'})

    def action_done(self):
        """Hoàn thành đợt kiểm kê"""
        stocks = self.env['stock.picking'].sudo().search([('period_inventory_id', '=', self.id)])
        if any(stock.state not in ['done', 'cancel'] for stock in stocks):
            raise UserError('Đợt kiểm kê không thể hoàn thành khi vẫn còn phiếu kiểm kê chưa hoàn thành hoặc chưa hủy!!!')
        self.state = 'done'

    def action_done_force(self):
        """Hoàn thành đợt kiểm kê (bỏ qua điều kiện còn phiếu chưa hoàn tất)."""
        self.state = 'done'
        # Khi hoàn thành, đánh dấu tất cả branch lines của đợt này là done và sinh báo cáo chi tiết cho các cơ sở
        now = fields.Datetime.now()
        for rec in self:
            # set all period.inventory.branch to done (bất kể trạng thái pickings)
            rec.branch_line_ids.filtered(lambda b: b.state != 'done').write({'state': 'done', 'confirmed_at': now})

            report = self.env["kvc.inventory.report"].get_or_create_for_period(rec)
            warehouses = self.env["stock.warehouse"].search([("ttb_branch_id", "!=", False)])
            ReportBranch = self.env["kvc.inventory.report.branch"]
            for wh in warehouses:
                ReportBranch.create_for_period_branch(report, wh)

    def action_set_draft(self):
        """Đặt lại đợt kiểm kê về nháp"""
        self.state = 'draft'

    def action_cancel(self):
        """Hủy đợt kiểm kê"""
        self.state = 'cancelled'

    @api.model
    def cron_auto_start_inventory(self):
        """Hàm chạy từ ir.cron: tự động start đợt kiểm kê hôm nay"""
        now = fields.Datetime.now()
        today = now.date()
        # Chỉ chạy vào Thứ 2
        if now.weekday() != 0:
            return
        # Chỉ chạy sau 07:00
        if now.time() < time(7, 0, 0):
            return
        records = self.search([('state', '=', 'draft')])
        for rec in records:
            # Chuyển start_date về date và so sánh
            start_date = fields.Datetime.context_timestamp(rec, rec.start_date).date() if rec.start_date else None
            if start_date == today:
                rec.action_start()

    @api.model
    def cron_auto_create_inventory_weekly(self):
        """Tự động tạo đợt kiểm kê vào 24:00 Chủ nhật (00:00 Thứ 2)."""
        now = fields.Datetime.now()
        # Thứ 2: weekday == 0 (00:00 Thứ 2)
        if now.weekday() != 0:
            return

        today_str = now.strftime('%Y%m%d')
        code = f"{today_str}"
        if self.search_count([('code', '=', code)]):
            return

        start_dt = datetime.combine(now.date(), time(7, 0, 0))
        end_dt = datetime.combine(now.date(), time(23, 0, 0))
        period = self.create({
            'name': f"Đợt kiểm kê {today_str}",
            'code': code,
            'start_date': start_dt,
            'end_date': end_dt,
            'state': 'draft',
        })
        period._create_branch_lines()

    @api.model
    def cron_auto_finish_inventory_weekly(self):
        """Tự động kết thúc đợt kiểm kê vào thứ 2 hàng tuần (23:00), bỏ qua điều kiện."""
        now = fields.Datetime.now()
        if now.weekday() != 0:
            return
        # Chạy vào hoặc sau 22:00 (22:00 trở đi)
        if now.time() < time(22, 0, 0):
            return

        # Chỉ kết thúc các đợt đang kiểm kê có start_date là hôm nay
        records = self.search([('state', '=', 'in_progress')])
        for rec in records:
            start_date = fields.Datetime.context_timestamp(rec, rec.start_date).date() if rec.start_date else None
            if start_date == now.date():
                # Trước khi finish period, ép các branch chưa done thành done
                branches_to_force = rec.branch_line_ids.filtered(lambda b: b.state != 'done')
                if branches_to_force:
                    try:
                        branches_to_force.action_force_confirm()
                    except Exception:
                        _logger.exception('Failed to force confirm branch lines for period id=%s', rec.id)
                # Sau đó finish toàn bộ period (set period done + ensure reports exist)
                rec.action_done_force()

    @api.model
    def cron_auto_generate_inventory_picking_by_zone(self):
        """Tự động sinh phiếu kiểm kê từ danh sách zone lúc 06:00 thứ 2."""
        now = fields.Datetime.now()
        if now.weekday() != 0:
            return

        period = self.search([('state', '=', 'draft')], order="start_date desc", limit=1)
        if not period:
            return

        zones = self.env['shelf.location'].search([('active', '=', True)])
        if not zones:
            return

        schedule_dt = datetime.combine(now.date(), time(7, 0, 0))
        StockPicking = self.env['stock.picking']
        for zone in zones:
            # tránh tạo trùng
            exists = StockPicking.search_count([
                ('period_inventory_id', '=', period.id),
                ('picking_type_id', '=', zone.picking_type_id.id),
                ('shelf_location_id', '=', zone.id),
            ])
            if exists:
                continue

            StockPicking.create({
                'picking_type_id': zone.picking_type_id.id,
                'shelf_location_id': zone.id,
                'mch_category_id': zone.mch_category_id.id,
                'period_inventory_id': period.id,
                'scheduled_date': schedule_dt,
            })
    @api.model
    def cron_auto_create_reports(self):
        """Tự động tạo báo cáo tổng hợp vào  07:00 sáng Thứ 4 hàng tuần."""
        now = fields.Datetime.now()
        if now.weekday() != 2:
            return
        # Tìm đợt đã 'done' có end_date gần nhất so với thời điểm hiện tại.
        # Ưu tiên những đợt đã kết thúc trước hoặc đúng thời điểm hiện tại (end_date <= now),
        # và lấy đợt có end_date lớn nhất (gần nhất về phía quá khứ).
        period = self.search([
            ("state", "=", "done"),
            ("end_date", "<=", now),
        ], order="end_date desc", limit=1)

        # Nếu không tìm thấy đợt đã kết thúc trước now, fallback sang đợt 'done' mới nhất (theo end_date)
        if not period:
            period = self.search([("state", "=", "done")], order="end_date desc", limit=1)

        if not period:
            return

        report = self.env["kvc.inventory.report"].get_or_create_for_period(period, auto=True)
        ReportBranch = self.env['kvc.inventory.report.branch']
        branch_reports = ReportBranch.search([
            ('report_id.period_inventory_id', '=', period.id),
            ('state', '=', 'approved'),
        ])

        for branch_report in branch_reports:
            # Nếu báo cáo chi tiết đã thuộc chính summary report này thì bỏ qua
            if branch_report.report_id and branch_report.report_id.id == report.id:
                continue
            try:
                branch_report.write({'report_id': report.id})
            except Exception:
                _logger.exception('Failed to attach branch report id=%s to summary report id=%s', getattr(branch_report, 'id', False), getattr(report, 'id', False))

    @api.model
    def cron_auto_create_missing_branch_reports(self):
        """22:05 Thứ 2: tạo báo cáo chi tiết cho cơ sở chưa có trong đợt kiểm kê vừa đóng."""
        now = fields.Datetime.now()
        if now.weekday() != 0:
            return
        if now.time() < time(22, 5, 0):
            return

        period = self.search([("state", "=", "done")], order="end_date desc", limit=1)
        if not period:
            return

        report = self.env["kvc.inventory.report"].get_or_create_for_period(period)
        warehouses = self.env["stock.warehouse"].search([("ttb_branch_id", "!=", False)])
        ReportBranch = self.env["kvc.inventory.report.branch"]
        for wh in warehouses:
            ReportBranch.create_for_period_branch(report, wh)

    def _create_branch_lines(self):
        """Tạo các bản ghi đợt kiểm kê theo cơ sở (mỗi cơ sở 1 bản ghi)."""
        branches = self.env['ttb.branch'].search([('active', '=', True)])
        for rec in self:
            existing_branch_ids = set(rec.branch_line_ids.mapped('branch_id').ids)
            vals_list = []
            for branch in branches:
                if branch.id in existing_branch_ids:
                    continue
                vals_list.append({
                    'period_inventory_id': rec.id,
                    'branch_id': branch.id,
                    'state': 'draft',
                })
            if vals_list:
                self.env['period.inventory.branch'].create(vals_list)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._create_branch_lines()
        return records
