from odoo import models, fields, api


class ProductSaleItem(models.Model):
    _inherit = 'product.sale.item'

    misa_product_id = fields.Many2one('product.sale.item', 'Sản phẩm đầu ra Misa', auto_join=True)

    count_out_product = fields.Integer('Số sản phẩm ghép', compute='compute_count_out_product', help='Đánh dấu các SP đầu vào bị ghép nhiều SP đầu ra', store=True)
    @api.depends('out_product_ids')
    def compute_count_out_product(self):
        for rec in self:
            rec.count_out_product = len(rec.out_product_ids)

    out_product_ids = fields.One2many('ttb.inproduct.outproduct.mapper', 'in_product_id', 'Sản phẩm đầu vào đã map')

    # Ghép MCH 1
    check_mch = fields.Char('Check MCH')
    ten_nhom = fields.Char('Tên nhóm')
    ten_nganh = fields.Char('Tên ngành')
    mch1_theo_ten_nganh = fields.Many2one('product.category.training', 'MCH 1', index=True, domain="[('category_level', '=', 1)]", tracking=True)
    mch1_manual = fields.Many2one('product.category.training', 'MCH thủ công', index=True, domain="[('category_level', '=', 1)]", tracking=True)

class ProductCategoryTraining(models.Model):
    """
    Model lưu trữ dữ liệu thô (tên sản phẩm và tên danh mục tương ứng)
    dùng để làm đầu vào cho thuật toán trích xuất từ khóa phân loại.
    """
    # --- THAY ĐỔI TẠI ĐÂY ---
    _inherit = 'product.product.category.training'

    donvi = fields.Char('Đơn vị tính')
    dongia = fields.Float('Giá')

