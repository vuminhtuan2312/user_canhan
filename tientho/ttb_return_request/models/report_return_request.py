from odoo import api, fields, models

from odoo.exceptions import UserError


class ReportReturnRequest(models.Model):
    _name = 'report.return.request'
    _description = 'Báo cáo dự trù trả hàng'

    mch = fields.Char(string='MCH')
    pdcode = fields.Char(string='Mã Hàng')
    barcode = fields.Char(string='Mã vạch')
    pdname = fields.Char(string='Tên hàng')
    dvt = fields.Char(string='Đơn vị tính')
    total_sales_3m_sys = fields.Float(string="S90")
    total_sales_1m_sys = fields.Float(string="S30")
    total_sales_2w_qty = fields.Float(string="S14")
    total_sales_2w_amount = fields.Float(string="Doanh thu 2 tuần")
    stock_system_branch = fields.Float(string="Tồn kho")
    suggested_return_category = fields.Float(string="Đề xuất trả hàng")
    sale_price = fields.Float(string="Giá bán")
    total_value = fields.Float(string="Tổng giá trị hàng")
    notes = fields.Text(string="Ghi chú")
    supplier_id = fields.Many2one('res.partner', string='Nhà cung cấp')
    supplier_code = fields.Char(string='Mã NCC')
    last_purchase_price = fields.Float(string='Giá nhập')
    branch_id = fields.Many2one(string='Cơ sở', comodel_name='ttb.branch')
    incoming_qty = fields.Float(string='Hàng đang về')
    product_id = fields.Many2one(string='Sản phẩm', comodel_name='product.template')
    product_uom = fields.Many2one(string='Đơn vị tính', comodel_name='uom.uom')
    report_id = fields.Many2one('plan.return.request', string='Phiếu báo cáo', ondelete='cascade')
    categ_id_level_1 = fields.Many2one(string="MCH1", related='report_id.categ_id_level_1')
    categ_id_level_2 = fields.Many2one(string="MCH2", related='report_id.categ_id_level_2')
    categ_id_level_3 = fields.Many2one(string="MCH3", related='report_id.categ_id_level_3')
    categ_id_level_4 = fields.Many2one(string="MCH4", related='report_id.categ_id_level_4')
    categ_id_level_5 = fields.Many2one(string="MCH5", related='report_id.categ_id_level_5')
    auto_return_qty = fields.Float(string="SL trả tự động")

    def action_create_tl(self):
        TtbReturnRequest = self.env['ttb.return.request']
        TtbReturnRequestLine = self.env['ttb.return.request.line']

        report = self[0].report_id
        if not report:
            raise UserError("Không tìm thấy phiếu trả lại")

        if not report.branch_id:
            raise UserError("Vui lòng chọn Cơ sở trong phiếu báo cáo trả lại")

        lines_to_return = self.filtered(lambda l: l.suggested_return_category > 0)
        if not lines_to_return:
            raise UserError("Không có sản phẩm nào có đề xuất trả hàng.")

        lines_by_branch = {}
        for line in lines_to_return:
            branch = line.branch_id
            if not branch:
                continue
            lines_by_branch.setdefault(branch.id, []).append(line)

        created_tl_ids = []
        for branch_id, branch_lines in lines_by_branch.items():
            branch = self.env['ttb.branch'].browse(branch_id)

            tl_vals = {
                'reason': f'Yêu cầu trả hàng từ báo cáo trả hàng {report.name}',
                'request_date': fields.Date.today(),
                'requester_id': self.env.user.id,
                'branch_id': branch.id,
                'plan_tl_id': report.id,
                'supplier_id': report.supplier_ids.id
            }
            tl = TtbReturnRequest.create(tl_vals)
            for line in branch_lines:
                tl_line_vals = {
                    'request_id': tl.id,
                    'product_id': line.product_id.product_variant_ids[:1].id,
                    'quantity': line.suggested_return_category,
                    'current_stock': line.stock_system_branch,
                }
                TtbReturnRequestLine.create(tl_line_vals)
            created_tl_ids.append(tl.id)
        if report:
            report.state = 'tl_created'
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'plan.return.request',
            'res_id': report.id,
            'view_mode': 'form',
            'target': 'current',
        }
