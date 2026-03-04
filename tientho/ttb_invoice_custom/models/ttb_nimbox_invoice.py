from odoo import api, fields, models, _, SUPERUSER_ID


class TtbNimboxInvoice(models.Model):
    _inherit = 'ttb.nimbox.invoice'
	
    # use_state = fields.Boolean('Trạng thái sử dụng', help='Hoá đơn nào không sử dụng thì để bằng False', default=True)
    use_state = fields.Boolean('Hoá đơn đầu vào', help='False nếu là hoá đơn chi phí', default=True)
    invoice_type = fields.Selection([
        ('Chi phí', 'Chi phí'), 
        ('Hàng hoá', 'Hàng hoá'), 
        ('Nguyên vật liệu', 'Nguyên vật liệu'), 
        ('Xây dựng cơ bản', 'Xây dựng cơ bản'), 
        ('Vật tư tiêu hao', 'Vật tư tiêu hao')
    ], 'Loại hoá đơn')
    in_branch_id = fields.Many2one('ttb.branch', string='Cở sở đã ghép', help='Cơ sở được chọn của hoá đơn của kho chung')
    manual_import = fields.Boolean('Import thủ công', default=False)

    out_product_ids = fields.One2many('ttb.inout.product.mapper', 'nimbox_invoice_id', 'Các sản phẩm bán ra')
    out_invoice_ids = fields.One2many('ttb.inout.invoice.mapper', string='Các dòng hoá đơn bán ra', compute="compute_out_invoice_ids")
    def compute_out_invoice_ids(self):
        for rec in self:
            rec.out_invoice_ids = self.env['ttb.inout.invoice.mapper'].search([('in_line_id', 'in', rec.nimbox_line_ids.ids)])

    total_soluong_used = fields.Float(' Tổng số lượng đã sử dụng', compute='_compute_total_soluong_used', store=True)
    @api.depends('nimbox_line_ids.soluong_used')
    def _compute_total_soluong_used(self):
        for rec in self:
            total_used = sum(rec.nimbox_line_ids.mapped('soluong_used'))
            rec.total_soluong_used = total_used

    is_out_used = fields.Boolean('Đã sử dụng để xuất kho', compute='compute_is_out_used')
    def compute_is_out_used(self):
        for rec in self:
            out_used = self.env['ttb.inout.invoice.mapper'].search_count([('in_line_id', 'in', rec.nimbox_line_ids.ids), ('state', '=', 'done')])
            rec.is_out_used = out_used > 0
