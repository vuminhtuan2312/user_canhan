from odoo import models, fields, api

class TtbChangeNccWizard(models.TransientModel):
    _name = 'ttb.change.ncc.wizard'
    _description = 'Wizard để thay đổi Nhà cung cấp'

    # Giả định wizard của bạn có trường này để biết đang thao tác trên sản phẩm nào
    product_id = fields.Many2one('product.product', string="Sản phẩm", readonly=True)

    # Trường compute của bạn
    supplier_partner_ids = fields.Many2many(
        'res.partner',
        string='Nhà cung cấp có sẵn',
        compute='_compute_supplier_partner_ids'
    )
    price = fields.Float()
    # Một trường Many2one để người dùng chọn Nhà cung cấp từ danh sách trên
    selected_supplier_id = fields.Many2one(
        'res.partner',
        string="Nhà cung cấp mới",
        # Domain của trường này sẽ được cập nhật động
        domain="[('id', 'in', supplier_partner_ids)]"
    )

    # *** SỬA LẠI @api.depends ***
    # Bây giờ nó phụ thuộc vào trường 'product_id' có thật trên wizard này
    @api.depends('product_id')
    def _compute_supplier_partner_ids(self):
        for wizard in self:
            # Nếu có sản phẩm được chọn
            if wizard.product_id:
                # Lấy danh sách ID nhà cung cấp từ sản phẩm đó
                supplier_ids = wizard.product_id.seller_ids.mapped('partner_id').ids
                # price_id = wizard.product_id.seller_ids.mapped('price')
                # Gán danh sách ID này vào trường compute
                wizard.supplier_partner_ids = [(6, 0, supplier_ids)]
                # wizard.price = [(6, 0, price_id)]
            else:
                # Nếu không có sản phẩm nào, danh sách nhà cung cấp là rỗng
                wizard.supplier_partner_ids = [(6, 0, [])]

    @api.onchange('selected_supplier_id')
    def _onchange_selected_supplier_id(self):
        """
        Khi người dùng chọn một nhà cung cấp, hàm này sẽ được gọi.
        Nó sẽ tìm giá tương ứng và điền vào trường 'price'.
        """
        # Kiểm tra xem cả sản phẩm và nhà cung cấp đã được chọn chưa
        if self.product_id and self.selected_supplier_id:
            # Tìm trong danh sách seller_ids của sản phẩm, bản ghi có nhà cung cấp trùng khớp
            # Lọc ra seller tương ứng với sản phẩm và nhà cung cấp đã chọn
            seller = self.product_id.seller_ids.filtered(
                lambda s: s.partner_id == self.selected_supplier_id
            )

            # Lấy giá từ seller đầu tiên tìm thấy
            if seller:
                self.price = seller[0].price
            else:
                # Nếu không tìm thấy (trường hợp hiếm), reset giá
                self.price = 0.0
        else:
            self.price = 0.0

    def action_confirm(self):
        active_ids = self.env.context.get('active_ids')
        report_line = self.env['report.sale.pos.inventory'].browse(active_ids)
        report_line.write({'supplier_id': self.selected_supplier_id.id})
        return {'type': 'ir.actions.act_window_close'}