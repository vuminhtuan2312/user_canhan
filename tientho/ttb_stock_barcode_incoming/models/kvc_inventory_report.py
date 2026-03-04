from odoo import api, fields, models, _
from odoo.exceptions import UserError


class KvcInventoryReport(models.Model):
    _name = "kvc.inventory.report"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'ttb.approval.mixin']
    _description = "Báo cáo Tổng hợp KVC"

    name = fields.Char(string="Tên báo cáo", default="Báo cáo Tổng hợp KVC")
    period_inventory_id = fields.Many2one(
        "period.inventory",
        string="Đợt kiểm kê",
        ondelete="set null",
    )
    period_inventory_name = fields.Char(string="Đợt kiểm kê")
    inventory_date = fields.Date(string="Ngày kiểm kê")
    state = fields.Selection([
        ("draft", "Mới"),
        ("confirmed", "Xác nhận"),
    ], string="Trạng thái", default="draft", required=True)
    line_ids = fields.One2many(
        "kvc.inventory.report.branch",
        "report_id",
        string="Chi tiết cơ sở",
    )

    total_overage_amount = fields.Monetary(
        string="Tổng thừa tiền hàng",
        currency_field="currency_id",
        compute="_compute_totals",
        store=True,
    )
    total_shortage_amount = fields.Monetary(
        string="Tổng thiếu tiền hàng",
        currency_field="currency_id",
        compute="_compute_totals",
        store=True,
    )
    total_cash_overage_amount = fields.Monetary(
        string="Tổng thừa tiền mặt",
        currency_field="currency_id",
        compute="_compute_totals",
        store=True,
    )
    total_loss_amount = fields.Monetary(
        string="Tổng thất thoát",
        currency_field="currency_id",
        compute="_compute_totals",
        store=True,
    )
    total_revenue_kvc = fields.Monetary(
        string="Tổng doanh thu KVC",
        currency_field="currency_id",
        compute="_compute_totals",
        store=True,
    )
    allowed_loss_rate = fields.Float(
        string="Mức thất thoát cho phép",
        default=0.3,
        help="Đơn vị % (mặc định 0.3%)",
    )
    allowed_loss_value = fields.Monetary(
        string="Giá trị định mức (0.3%)",
        currency_field="currency_id",
        compute="_compute_totals",
        store=True,
    )
    compensation_amount = fields.Monetary(
        string="Phần đền bù",
        currency_field="currency_id",
        compute="_compute_totals",
        store=True,
    )
    compensation_state = fields.Selection([
        ("compensate", "Đền bù"),
        ("no_compensate", "Không đền bù"),
    ], string="Trạng thái đền bù", compute="_compute_totals", store=True)
    loss_rate_percent = fields.Float(
        string="Tỷ lệ thất thoát/DT (%)",
        compute="_compute_totals",
        store=True,
    )

    confirmed_date = fields.Date(string="Ngày xác nhận báo cáo")
    confirmed_by = fields.Many2one("res.users", string="Người xác nhận")

    currency_id = fields.Many2one(
        "res.currency",
        string="Tiền tệ",
        default=lambda self: self.env.company.currency_id.id,
    )

    @api.depends(
        "line_ids.total_overage_amount",
        "line_ids.total_shortage_amount",
        "line_ids.total_cash_overage_amount",
        "line_ids.total_revenue_kvc",
        "line_ids.inventory_date",
        "allowed_loss_rate",
    )
    def _compute_totals(self):
        for rec in self:
            total_over = sum(rec.line_ids.mapped("total_overage_amount"))
            total_short = sum(rec.line_ids.mapped("total_shortage_amount"))
            total_cash = sum(rec.line_ids.mapped("total_cash_overage_amount"))
            total_revenue = sum(rec.line_ids.mapped("total_revenue_kvc"))

            rec.total_overage_amount = total_over
            rec.total_shortage_amount = total_short
            rec.total_cash_overage_amount = total_cash
            rec.total_revenue_kvc = total_revenue
            rec.total_loss_amount = total_over + total_short + total_cash

            rec.allowed_loss_value = total_revenue * (rec.allowed_loss_rate / 100.0)
            rec.compensation_amount = rec.allowed_loss_value + rec.total_loss_amount
            rec.compensation_state = "compensate" if rec.compensation_amount < 0 else "no_compensate"
            rec.loss_rate_percent = (rec.total_loss_amount / total_revenue * 100.0) if total_revenue else 0.0

            dates = [d for d in rec.line_ids.mapped("inventory_date") if d]
            rec.inventory_date = max(dates) if dates else False

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        Period = self.env["period.inventory"]
        for rec in records:
            if not rec.period_inventory_id:
                period = Period.search([("state", "=", "done")], order="end_date desc", limit=1)
                if period:
                    rec.period_inventory_id = period.id
            if rec.period_inventory_id and not rec.period_inventory_name:
                rec.period_inventory_name = rec.period_inventory_id.name
                rec.name = f"Báo cáo Tổng hợp KVC - {rec.period_inventory_id.name}"
        return records

    @api.model
    def get_or_create_for_period(self, period, auto=False):
        report = self.search([("period_inventory_id", "=", period.id)], limit=1)
        if report:
            return report
        if auto:
            report = self.create({
                "period_inventory_id": period.id,
                "period_inventory_name": period.name,
                "name": f"Báo cáo Tổng hợp KVC - {period.name}",
                "state": "draft",
            })
        return report

    def action_fetch_data(self):
        """Quét lại tất cả báo cáo chi tiết theo Đợt kiểm kê và tính lại các số tổng.

        Dùng khi báo cáo tổng thiếu các cơ sở do tình trạng duyệt muộn; người dùng có thể
        bấm nút 'Lấy dữ liệu' để cập nhật lại.
        """
        for rec in self:
            period = rec.period_inventory_id
            if not period:
                raise UserError(_('Báo cáo chưa liên kết tới Đợt kiểm kê.'))

            # 1) Sync lines for all branches belonging to this period
            self.env['kvc.inventory.report.branch'].sync_lines_for_all_branches(period_id=period.id)

            # 2) Recompute branch-level computed fields (counts and totals)
            branches = rec.line_ids
            if branches:
                try:
                    branches._compute_branch_totals()
                except Exception:
                    # đảm bảo không phá flow nếu compute gặp lỗi
                    pass
                try:
                    branches._compute_counts()
                except Exception:
                    pass
                try:
                    branches._compute_inventory_date()
                except Exception:
                    pass

            # 3) Recompute report-level totals
            try:
                rec._compute_totals()
            except Exception:
                pass

        return True

    def action_confirm_report(self):
        """Xác nhận Báo cáo Tổng: chỉ cho phép khi có đủ 13 báo cáo chi tiết đã ở trạng thái 'approved'.

        Trước khi kiểm tra, gọi `action_fetch_data` để đảm bảo dữ liệu được cập nhật.
        """
        for rec in self:
            # đảm bảo dữ liệu cập nhật
            try:
                rec.action_fetch_data()
            except Exception:
                # không block nếu fetch gặp lỗi; vẫn tiếp tục kiểm tra hiện trạng
                pass

            period = rec.period_inventory_id
            if not period:
                raise UserError(_('Báo cáo chưa liên kết tới Đợt kiểm kê.'))

            # đếm số báo cáo chi tiết cùng period có state = 'approved'
            branch_model = self.env['kvc.inventory.report.branch']
            approved_count = branch_model.search_count([
                ('report_id.period_inventory_id', '=', period.id),
                ('state', '=', 'approved'),
            ])

            if approved_count < self.env['ttb.branch'].search_count([('active', '=', True)]):
                raise UserError(_('Vui lòng kiểm tra lại trạng thái duyệt của các cơ sở trước khi xác nhận'))

            # nếu đủ, thực hiện xác nhận
            rec.write({
                'state': 'confirmed',
                'confirmed_date': fields.Date.context_today(rec),
                'confirmed_by': rec.env.user.id,
            })
        return True


class KvcInventoryReportBranch(models.Model):
    _name = "kvc.inventory.report.branch"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'ttb.approval.mixin']
    _description = "Báo cáo Chi tiết KVC theo cơ sở"

    report_id = fields.Many2one("kvc.inventory.report", string="Báo cáo tổng hợp", required=True, ondelete="cascade")
    warehouse_id = fields.Many2one("stock.warehouse", string="Cơ sở", required=True)
    state = fields.Selection([
        ("draft", "Mới"),
        ("in_review", "Đang duyệt"),
        ("approved", "Đã duyệt"),
    ], string="Trạng thái", default="draft", required=True)

    line_ids = fields.One2many(
        "kvc.inventory.report.branch.line",
        "report_branch_id",
        string="Dòng chi tiết SP",
    )

    total_overage_amount = fields.Monetary(
        string="Tổng thừa tiền hàng",
        currency_field="currency_id",
        compute="_compute_branch_totals",
        store=True,
    )
    total_shortage_amount = fields.Monetary(
        string="Tổng thiếu tiền hàng",
        currency_field="currency_id",
        compute="_compute_branch_totals",
        store=True,
    )
    total_cash_overage_amount = fields.Monetary(
        string="Tổng thừa tiền mặt",
        currency_field="currency_id",
        default=0.0,
    )
    total_revenue_kvc = fields.Monetary(
        string="Tổng doanh thu KVC",
        currency_field="currency_id",
        default=0.0,
    )

    total_pickings = fields.Integer(string="Tổng số phiếu kiểm kê", compute="_compute_counts", store=True)
    total_done = fields.Integer(string="Số phiếu đã hoàn tất", compute="_compute_counts", store=True)
    total_draft = fields.Integer(string="Số phiếu nháp", compute="_compute_counts", store=True)
    total_ready = fields.Integer(string="Số phiếu chưa hoàn tất", compute="_compute_counts", store=True)
    total_cancel = fields.Integer(string="Số phiếu hủy", compute="_compute_counts", store=True)

    approval_flow_id = fields.Many2one("ttb.approval", string="Quy trình duyệt")
    reason = fields.Text(string="Nguyên nhân")
    submit_date = fields.Date(string="Ngày gửi duyệt")
    approve_date = fields.Date(string="Ngày duyệt")
    confirmed_by = fields.Many2one("res.users", string="Người xác nhận")

    inventory_date = fields.Date(string="Ngày kiểm kê", compute="_compute_inventory_date", store=True)

    currency_id = fields.Many2one(
        "res.currency",
        string="Tiền tệ",
        related="report_id.currency_id",
        store=True,
        readonly=True,
    )

    @api.depends("line_ids.overage_amount", "line_ids.shortage_amount")
    def _compute_branch_totals(self):
        for rec in self:
            rec.total_overage_amount = sum(rec.line_ids.mapped("overage_amount"))
            rec.total_shortage_amount = sum(rec.line_ids.mapped("shortage_amount"))

    @api.depends("report_id.period_inventory_id", "warehouse_id")
    def _compute_counts(self):
        for rec in self:
            total = done = draft = ready = cancel = 0
            if rec.report_id.period_inventory_id and rec.warehouse_id:
                domain = [
                    ("period_inventory_id", "=", rec.report_id.period_inventory_id.id),
                    ("picking_type_id.code", "=", "inventory_counting"),
                    ("location_dest_id.warehouse_id", "=", rec.warehouse_id.id),
                ]
                total = self.env["stock.picking"].search_count(domain)
                done = self.env["stock.picking"].search_count(domain + [("state", "=", "done")])
                draft = self.env["stock.picking"].search_count(domain + [("state", "=", "draft")])
                ready = self.env["stock.picking"].search_count(domain + [("state", "=", "assigned")])
                cancel = self.env["stock.picking"].search_count(domain + [("state", "=", "cancel")])
            rec.total_pickings = total
            rec.total_done = done
            rec.total_draft = draft
            rec.total_ready = ready
            rec.total_cancel = cancel

    @api.depends("line_ids.inventory_date")
    def _compute_inventory_date(self):
        for rec in self:
            dates = [d for d in rec.line_ids.mapped("inventory_date") if d]
            rec.inventory_date = max(dates) if dates else False

    def action_sync_lines(self):
        """Lấy dòng chi tiết từ stock.picking (Kiểm kê, Done)."""
        StockPicking = self.env["stock.picking"]
        for rec in self:
            if not rec.report_id.period_inventory_id:
                continue
            domain = [
                ("period_inventory_id", "=", rec.report_id.period_inventory_id.id),
                ("picking_type_id.code", "=", "inventory_counting"),
                ("location_dest_id.warehouse_id", "=", rec.warehouse_id.id),
                ("state", "=", "done"),
            ]
            pickings = StockPicking.search(domain)
            rec.line_ids.unlink()
            lines = []
            for picking in pickings:
                moves = picking.move_ids_without_package
                for move in moves:
                    lines.append({
                        "report_branch_id": rec.id,
                        "picking_id": picking.id,
                        "product_id": move.product_id.id,
                        "qty_theoretical": move.stock_qty,
                        "qty_counted": move.quantity,
                        "price": move.product_id.list_price,
                        "mch2": picking.mch_category_id.name if picking.mch_category_id else "",
                        "inventory_date": picking.date_done.date() if picking.date_done else False,
                    })
            if lines:
                self.env["kvc.inventory.report.branch.line"].create(lines)

    @api.model
    def sync_lines_for_all_branches(self, period_id=None):
        """Tìm các stock.picking theo điều kiện và chạy action_sync_lines."""
        domain = []
        if period_id:
            domain.append(("report_id.period_inventory_id", "=", period_id))
        branches = self.search(domain)
        for branch in branches:
            branch.action_sync_lines()

    @api.model
    def create_for_period_branch(self, report, warehouse):
        exists = self.search_count([
            ("report_id", "=", report.id),
            ("warehouse_id", "=", warehouse.id),
        ])
        if exists:
            return self.search([("report_id", "=", report.id), ("warehouse_id", "=", warehouse.id)], limit=1)
        return self.create({
            "report_id": report.id,
            "warehouse_id": warehouse.id,
            "state": "draft",
        })

    def action_send_for_approval(self):
        """Nút [Gửi duyệt]: Chuyển trạng thái từ 'draft' -> 'in_review' và khóa dữ liệu."""
        for rec in self:
            process_id, approval_line_ids = rec.get_approval_line_ids()
            rec.write({'process_id': process_id.id,
                        'date_sent': fields.Datetime.now(),
                        'state': 'in_review',
                        'approval_line_ids': [(5, 0, 0)] + approval_line_ids})
            rec.with_context(bypass_in_review_check=True).submit_date = fields.Date.context_today(self)

    def action_edit(self):
        """Nút [Chỉnh sửa]: Chuyển trạng thái từ 'in_review' -> 'draft' để mở khóa."""
        for rec in self:
            if rec.state != 'in_review':
                continue
            # Cho phép ghi đè khi chuyển trạng thái (bypass check)
            rec.with_context(bypass_in_review_check=True).write({'state': 'draft'})

    def action_confirm_approval(self):
        """Nút [Xác nhận Duyệt]: Chuyển trạng thái từ 'in_review' -> 'approved' và ghi ngày/người duyệt."""
        for rec in self:
            if rec.state != 'in_review':
                continue
            vals = {
                'state': 'approved',
                'approve_date': fields.Date.context_today(self),
                'confirmed_by': self.env.user.id,
            }
            rec.with_context(bypass_in_review_check=True).write(vals)

    def write(self, vals):
        # Chặn tất cả thao tác ghi khi record đang ở trạng thái 'in_review', trừ khi có context cho phép
        if not self.env.context.get('bypass_in_review_check'):
            for rec in self:
                if rec.state == 'in_review':
                    raise UserError('Không thể chỉnh sửa khi báo cáo đang ở trạng thái "Đang duyệt". Vui lòng nhấn "Chỉnh sửa" để mở khóa.')
        return super(KvcInventoryReportBranch, self).write(vals)

    def unlink(self):
        if not self.env.context.get('bypass_in_review_check'):
            for rec in self:
                if rec.state == 'in_review':
                    raise UserError('Không thể xóa báo cáo khi đang ở trạng thái "Đang duyệt".')
        return super(KvcInventoryReportBranch, self).unlink()


class KvcInventoryReportBranchLine(models.Model):
    _name = "kvc.inventory.report.branch.line"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Dòng chi tiết SP KVC"

    report_branch_id = fields.Many2one("kvc.inventory.report.branch", string="Báo cáo chi tiết", required=True, ondelete="cascade")
    picking_id = fields.Many2one("stock.picking", string="Phiếu kiểm kê")
    product_id = fields.Many2one("product.product", string="Sản phẩm")
    barcode = fields.Char(string="Mã vạch", related="product_id.barcode", store=True, readonly=True)
    inventory_date = fields.Date(string="Ngày kiểm kê")

    qty_theoretical = fields.Float(string="SL tồn lý thuyết")
    qty_counted = fields.Float(string="SL kiểm kê")
    diff_qty = fields.Float(string="Chênh lệch", compute="_compute_diff", store=True)
    price = fields.Monetary(string="Giá bán", currency_field="currency_id")
    shortage_amount = fields.Monetary(string="Tiền thiếu", currency_field="currency_id", compute="_compute_amounts", store=True)
    overage_amount = fields.Monetary(string="Tiền thừa", currency_field="currency_id", compute="_compute_amounts", store=True)
    mch2 = fields.Char(string="MCH2")
    explanation = fields.Text(string="Giải trình")

    currency_id = fields.Many2one("res.currency", related="report_branch_id.currency_id", store=True, readonly=True)
    # Thêm trường warehouse_id để có thể group/column theo Cơ sở trong pivot
    warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Cơ sở",
        related="report_branch_id.warehouse_id",
        store=True,
        readonly=True,
    )

    # Trường tổng hợp tiền chênh lệch (thừa + thiếu). shortage_amount có thể là số âm,
    # nên cộng trực tiếp để có giá trị ròng.
    amount_diff = fields.Monetary(
        string="Tiền chênh lệch",
        currency_field="currency_id",
        compute="_compute_amount_diff",
        store=True,
    )

    @api.depends("qty_counted", "qty_theoretical")
    def _compute_diff(self):
        for rec in self:
            rec.diff_qty = (rec.qty_counted or 0.0) - (rec.qty_theoretical or 0.0)

    @api.depends("diff_qty", "price")
    def _compute_amounts(self):
        for rec in self:
            if rec.diff_qty < 0:
                rec.shortage_amount = rec.diff_qty * (rec.price or 0.0)
                rec.overage_amount = 0.0
            elif rec.diff_qty > 0:
                rec.overage_amount = rec.diff_qty * (rec.price or 0.0)
                rec.shortage_amount = 0.0
            else:
                rec.shortage_amount = 0.0
                rec.overage_amount = 0.0

    @api.depends("shortage_amount", "overage_amount")
    def _compute_amount_diff(self):
        for rec in self:
            # shortage_amount có thể là số âm theo logic hiện tại
            rec.amount_diff = (rec.overage_amount or 0.0) + (rec.shortage_amount or 0.0)

    @api.model_create_multi
    def create(self, vals_list):
        # Không cho tạo dòng mới khi parent đang ở trạng thái 'in_review'
        for vals in vals_list:
            rb_id = vals.get('report_branch_id')
            if rb_id:
                rb = self.env['kvc.inventory.report.branch'].browse(rb_id)
                if rb and rb.state == 'in_review':
                    raise UserError('Không thể thêm dòng khi báo cáo đang ở trạng thái "Đang duyệt".')
        return super(KvcInventoryReportBranchLine, self).create(vals_list)

    def write(self, vals):
        for rec in self:
            if rec.report_branch_id and rec.report_branch_id.state == 'in_review' and not self.env.context.get('bypass_in_review_check'):
                raise UserError('Không thể chỉnh sửa dòng khi báo cáo đang ở trạng thái "Đang duyệt".')
        return super(KvcInventoryReportBranchLine, self).write(vals)

    def unlink(self):
        for rec in self:
            if rec.report_branch_id and rec.report_branch_id.state == 'in_review' and not self.env.context.get('bypass_in_review_check'):
                raise UserError('Không thể xóa dòng khi báo cáo đang ở trạng thái "Đang duyệt".')
        return super(KvcInventoryReportBranchLine, self).unlink()
