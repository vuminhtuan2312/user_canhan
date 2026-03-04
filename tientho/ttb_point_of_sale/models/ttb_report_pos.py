from odoo import models, fields, api

from odoo.exceptions import UserError


class ReportSalePosInventory(models.Model):
    _name = 'report.sale.pos.inventory'
    _description = 'Báo cáo POS và tồn kho'

    mch_5 = fields.Char(string='mch_5')
    mch = fields.Char(string='MCH')
    pdcode = fields.Char(string='Mã Hàng')
    barcode = fields.Char(string='Mã vạch')
    pdname = fields.Char(string='Tên hàng')
    dvt = fields.Char(string='Đơn vị tính')
    total_sales_3m_sys = fields.Float(string="S90")
    total_sales_1m_sys = fields.Float(string="S30")
    stock_system_branch = fields.Float(string="Tồn kho")
    actual_stock_branch = fields.Float(string="SL tồn thực tế của cơ sở")
    suggested_order_category = fields.Float(string="Đề xuất đặt ngành hàng")
    suggested_order_branch = fields.Float(string="Đề xuất đặt cơ sở")
    sale_price = fields.Float(string="Giá bán")
    total_value = fields.Float(string="Tổng giá trị hàng")
    estimated_days_in_stock = fields.Float(string="Số ngày bán hàng", compute="_compute_days_of_stock", store=True)
    classify_14_days = fields.Char(string="Phân loại hàng theo 14 ngày")
    notes = fields.Text(string="Ghi chú")
    supplier_id = fields.Many2one('res.partner', string='Nhà cung cấp')
    supplier_code = fields.Char(string='Mã NCC')
    last_purchase_price = fields.Float(string='Giá nhập')
    total_sales_2w_qty = fields.Float(string="S14")
    total_sales_2w_amount = fields.Float(string="Doanh thu 2 tuần")
    branch_id = fields.Many2one(string='Cơ sở', comodel_name='ttb.branch')
    incoming_qty = fields.Float(string='Hàng đang về')
    product_id = fields.Many2one(string='Sản phẩm', comodel_name='product.template')
    product_uom = fields.Many2one(string='Đơn vị tính', comodel_name='uom.uom')
    report_id = fields.Many2one('ttb.report.pos.action', string='Phiếu báo cáo', ondelete='cascade')
    categ_id_level_1 = fields.Many2one(string="MCH1", related='report_id.categ_id_level_1')
    categ_id_level_2 = fields.Many2one(string="MCH2", related='report_id.categ_id_level_2')
    categ_id_level_3 = fields.Many2one(string="MCH3", related='report_id.categ_id_level_3')
    categ_id_level_4 = fields.Many2one(string="MCH4", related='report_id.categ_id_level_4')
    categ_id_level_5 = fields.Many2one(string="MCH5", related='report_id.categ_id_level_5')
    warehouse_type = fields.Selection([('st', 'Siêu thị'), ('kvc', 'Khu vui chơi')], string='Kho')
    warning_note = fields.Char(string="Cảnh báo", compute="_compute_days_of_stock", store=True)
    duplicate_products = fields.Char(string='Mã sản phẩm trùng')
    auto_order_qty = fields.Float(string="SL đặt tự động")
    def get_category_threshold(self, category):
        while category:
            if category.order_threshold:
                return category.order_threshold
            category = category.parent_id
        return 0.0
    @api.depends('suggested_order_category', 'stock_system_branch', 'incoming_qty', 'total_sales_1m_sys')
    def _compute_days_of_stock(self):
        for rec in self:
            total_sales_1m = rec.total_sales_1m_sys or 0.0
            if total_sales_1m > 0:
                total_qty_available = (rec.suggested_order_category or 0.0) + (rec.stock_system_branch or 0.0) + (rec.incoming_qty or 0.0)
                days_of_stock = round(total_qty_available / total_sales_1m, 1)
                rec.estimated_days_in_stock = days_of_stock
            else:
                days_of_stock = 0.0
                rec.estimated_days_in_stock = 0.0

            threshold = rec.get_category_threshold(rec.product_id.categ_id) if rec.product_id and rec.product_id.categ_id else False
            if threshold and days_of_stock > threshold:
                rec.warning_note = f"Cảnh báo: Số ngày tồn vượt ngưỡng ({days_of_stock:.1f} > {threshold})"
            else:
                rec.warning_note = ''
    def action_create_pr(self):
        TtbPurchaseRequest = self.env['ttb.purchase.request']
        TtbPurchaseRequestLine = self.env['ttb.purchase.request.line']

        report = self[0].report_id
        if not report:
            raise UserError("Không tìm thấy phiếu báo cáo POS gốc.")

        if not report.branch_id:
            raise UserError("Vui lòng chọn Cơ sở trong phiếu báo cáo POS.")

        lines_to_order = self.filtered(lambda l: l.suggested_order_category > 0)
        if not lines_to_order:
            raise UserError("Không có sản phẩm nào có đề xuất đặt hàng.")

        lines_by_branch = {}
        for line in lines_to_order:
            branch = line.branch_id
            if not branch:
                continue
            lines_by_branch.setdefault(branch.id, []).append(line)

        created_pr_ids = []
        for branch_id, branch_lines in lines_by_branch.items():
            branch = self.env['ttb.branch'].browse(branch_id)

            pr_vals = {
                'type': 'sale',
                'description': f'Yêu cầu mua từ báo cáo bán hàng {report.name}',
                'date': fields.Date.today(),
                'user_id': self.env.user.id,
                'branch_id': branch.id,
                'report_pr_id': report.id
            }
            pr = TtbPurchaseRequest.create(pr_vals)

            for line in branch_lines:
                pr_line_vals = {
                    'request_id': pr.id,
                    'product_id': line.product_id.product_variant_ids[:1].id,
                    'demand_qty': line.suggested_order_category,
                    'uom_id': line.product_uom.id,
                    'description': line.product_id.name,
                    'partner_id': line.supplier_id.id if line.supplier_id else ""
                }
                TtbPurchaseRequestLine.create(pr_line_vals)

            created_pr_ids.append(pr.id)
        if report:
            report.state = 'pr_created'
        return {
                'type': 'ir.actions.act_window',
                'res_model': 'ttb.report.pos.action',
                'res_id': report.id,
                'view_mode': 'form',
                'target': 'current',
            }
    def action_change_ncc(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Chọn nhà cung cấp',
            'res_model': 'ttb.change.ncc.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_product_id': self.product_id.id,
            }
        }

