from odoo import models, fields, api

class ProductStockItem(models.Model):
    _name = 'product.stock.item'
    _description = 'Sản phẩm tồn kho gốc'

    name = fields.Char(string='Tên sản phẩm', index=True)
    code = fields.Char(string='Mã sản phẩm')
    price = fields.Float(string='Giá nhập')
    qty_available = fields.Float(string='Số lượng tồn')
    qty_sold = fields.Float(string='Số lượng đã bán', default=0.0)
    qty_remaining = fields.Float(string='Số lượng còn lại', compute='_compute_qty_remaining', store=True)
    donvi = fields.Char('Đơn vị tính')
    
    category_id_level_1 = fields.Many2one('product.category.training', 'MCH 1', index=True)
    category_id_level_2 = fields.Many2one('product.category.training', 'MCH 2', index=True)
    category_id_level_3 = fields.Many2one('product.category.training', 'MCH 3', index=True)
    category_id_level_4 = fields.Many2one('product.category.training', 'MCH 4', index=True)
    category_id_level_5 = fields.Many2one('product.category.training', 'MCH 5', index=True)
    ai_vector = fields.Text(
        string='AI Vector (JSON)',
        copy=False,
    )
    active = fields.Boolean(default=True)

    batch_name = fields.Char('Lô xử lý')

    @api.depends('qty_available', 'qty_sold')
    def _compute_qty_remaining(self):
        for rec in self:
            rec.qty_remaining = rec.qty_available - rec.qty_sold