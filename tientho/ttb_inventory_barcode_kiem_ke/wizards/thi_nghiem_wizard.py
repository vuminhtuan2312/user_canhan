from odoo import fields, models, api


class ThiNghiemWizard(models.TransientModel):
    _name = 'thi.nghiem.wizard'
    _description = "Thi Nghiem Wizard"

    thi_nghiem_kiem_ke_line_id = fields.Many2one('experimental.kiemke.lines', 'Địa điểm', readonly=True)
    product_id = fields.Many2one('product.product', 'Sản phẩm', readonly=True)
    quantity = fields.Integer('Số lượng', default=0)
    order_number = fields.Integer('Vị trí', readonly=True)
    is_final_product = fields.Boolean('Sản phẩm cuối cùng?', readonly=True, default=False)

    def action_proceed(self):
        for wizard in self:
            stock_details = self.env['experimental.kiemke.lines'].browse(wizard.thi_nghiem_kiem_ke_line_id.id)
            if wizard.product_id.id == stock_details.product_id.id:
                stock_details.write({
                    'quantity': wizard.quantity
                })
                if wizard.is_final_product:
                    action = self.env["ir.actions.actions"]._for_xml_id("stock_barcode.stock_barcode_action_main_menu")
                    return action
