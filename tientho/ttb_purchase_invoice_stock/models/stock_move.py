from odoo import models, fields


class StockMove(models.Model):
    _inherit = 'stock.move'

    pos_order_line_id = fields.Many2one('pos.order.line', string='Dòng đơn POS', index=True)

    def _merge_moves(self, merge_into=False):
        if self.env.context.get('ignore_merge_moves'):
            return self
        return super()._merge_moves(merge_into)

    # Bỏ qua định giá tồn kho
    def _create_in_svl(self, forced_quantity=None):
        return self.env['stock.valuation.layer']

    def _create_out_svl(self, forced_quantity=None):
        return self.env['stock.valuation.layer']

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'
    
    def _update_svl_quantity(self, added_qty):
        # Bỏ qua định giá tồn kho tăng tốc độ
        return


class StockQuant(models.Model):
    _inherit = 'stock.quant'
    
    # Thêm auto join để tìm theo điều kiện giá sản phẩm nhanh hơn
    product_id = fields.Many2one(auto_join=True)
