from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PeriodInventoryBranch(models.Model):
    _name = "period.inventory.branch"
    _description = "Đợt kiểm kê theo cơ sở"

    period_inventory_id = fields.Many2one(
        "period.inventory",
        string="Đợt kiểm kê",
        required=True,
        ondelete="cascade",
        index=True,
    )
    branch_id = fields.Many2one(
        "ttb.branch",
        string="Cơ sở",
        required=True,
        index=True,
    )
    code = fields.Char(string="Mã đợt kiểm kê", related="period_inventory_id.code", store=True, readonly=True)
    name = fields.Char(string="Tên đợt kiểm kê", related="period_inventory_id.name", store=True, readonly=True)
    start_date = fields.Datetime(string="Ngày bắt đầu", related="period_inventory_id.start_date", store=True, readonly=True)
    end_date = fields.Datetime(string="Ngày kết thúc", related="period_inventory_id.end_date", store=True, readonly=True)
    state = fields.Selection([
        ('draft', 'Chưa bắt đầu'),
        ('in_progress', 'Đang kiểm kê'),
        ('done', 'Hoàn tất'),
        ('cancelled', 'Đã hủy'),
    ], string="Trạng thái", default='draft', required=True)
    confirmed_at = fields.Datetime(string="Thời điểm xác nhận")

    _sql_constraints = [
        ('period_branch_unique', 'unique(period_inventory_id, branch_id)', 'Đợt kiểm kê theo cơ sở đã tồn tại.'),
    ]

    def _get_warehouse_for_branch(self):
        self.ensure_one()
        return self.env['stock.warehouse'].search([('ttb_branch_id', '=', self.branch_id.id)], limit=1)

    def action_confirm(self):
        """Xác nhận hoàn tất đợt kiểm kê tại cơ sở.

        Nếu tất cả phiếu kiểm kê (stock.picking) cùng period và cùng warehouse đã ở trạng thái
        'done' hoặc 'cancel', thì kết thúc ngay. Ngược lại mở wizard xác nhận để cho phép ép kết thúc.
        """
        self.ensure_one()
        StockPicking = self.env['stock.picking']
        warehouse = self._get_warehouse_for_branch()
        if not warehouse:
            raise UserError(_('Không tìm thấy kho tương ứng với cơ sở. Vui lòng cấu hình kho cho cơ sở này.'))

        period = self.period_inventory_id
        domain = [
            ('period_inventory_id', '=', period.id),
            ('picking_type_id.code', '=', 'inventory_counting'),
            ('location_dest_id.warehouse_id', '=', warehouse.id),
        ]
        pickings = StockPicking.search(domain)

        all_closed = all(p.state in ('done', 'cancel') for p in pickings)
        if all_closed:
            # trực tiếp kết thúc
            self._finish_and_create_report()
            return True

        # còn pickings chưa đóng -> mở wizard xác nhận
        return {
            'name': _('Xác nhận hoàn tất đợt kiểm kê'),
            'type': 'ir.actions.act_window',
            'res_model': 'period.inventory.branch.finish.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_branch_id': self.id, 'default_pickings_count': len(pickings)},
        }

    def _finish_and_create_report(self):
        """Đánh dấu branch là done và sinh báo cáo chi tiết tự động."""
        now = fields.Datetime.now()
        self.write({'state': 'done', 'confirmed_at': now})
        # tạo báo cáo chi tiết (kvc.inventory.report.branch)
        period = self.period_inventory_id
        warehouse = self._get_warehouse_for_branch()
        if period and warehouse:
            report = self.env['kvc.inventory.report'].get_or_create_for_period(period)
            self.env['kvc.inventory.report.branch'].create_for_period_branch(report, warehouse)

    def action_force_confirm(self):
        """Ép kết thúc đợt kiểm kê tại cơ sở (bỏ qua trạng thái các phiếu kiểm kê)."""
        for rec in self:
            rec._finish_and_create_report()


class PeriodInventoryBranchFinishWizard(models.TransientModel):
    _name = 'period.inventory.branch.finish.wizard'
    _description = 'Wizard Xác nhận hoàn tất đợt kiểm kê tại cơ sở'

    branch_id = fields.Many2one('period.inventory.branch', string='Đợt kiểm kê (Cơ sở)', required=True)
    pickings_count = fields.Integer(string='Số phiếu kiểm kê', readonly=True)

    def action_confirm_finish(self):
        """Người dùng xác nhận ép kết thúc đợt kiểm kê tại cơ sở."""
        self.ensure_one()
        if not self.branch_id:
            return {'type': 'ir.actions.act_window_close'}
        # Gọi action_force_confirm trên branch
        try:
            self.branch_id.action_force_confirm()
        except Exception:
            raise
        return {'type': 'ir.actions.act_window_close'}

