from odoo import api, fields, models, _
from odoo import tools

class TtbPurchaseInvoiceStockLine(models.Model):
    _name = 'ttb.purchase.invoice.stock.line'
    _description = 'Chi tiết các sản phẩm có hóa đơn'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Tên')
    company_id = fields.Many2one(comodel_name='res.company', string='Công ty', index=True, default=lambda self: self.env.company)
    ttb_branch_id = fields.Many2one(comodel_name='ttb.branch', string='Cơ sở')
    warehouse_id = fields.Many2one(comodel_name='stock.warehouse', string='Kho')
    purchase_order_line_id = fields.Many2one(comodel_name='purchase.order.line', string='Chi tiết đơn mua hàng')
    product_id = fields.Many2one(comodel_name='product.product', string='Sản phẩm')
    qty = fields.Float(string='Số lượng')


class TtbPurchaseInvoiceStock(models.Model):
    _name = 'ttb.purchase.invoice.stock'
    _description = 'Sản phẩm có hóa đơn'
    _rec_name = 'product_id'
    _auto = False

    ttb_branch_id = fields.Many2one(comodel_name='ttb.branch', string='Cơ sở',readonly=True)
    product_id = fields.Many2one(comodel_name='product.product', string='Sản phẩm',readonly=True)
    qty = fields.Float(string='Số lượng', readonly=True, help='Tổng số lượng nhập mua có hóa đơn')
    qty_invoice = fields.Float(string='Số lượng có thể xuất hóa đơn', readonly=True, help='Sản phẩm đã bán nhưng chưa xuất hóa đơn')
    qty_invoiced = fields.Float(string='Số lượng đã xuất hóa đơn', readonly=True, help='Sản phẩm đã bán và đã xuất hóa đơn')
    qty_to_invoiced = fields.Float(string='Số lượng còn lại',readonly=True, help='Số lượng - số lượng đã xuất - số lượng có thể xuất')

    def _query(self):
        return f"""
                WITH combined AS(
                select ttb_branch_id as ttb_branch_id,
                       product_id as product_id,
                       COALESCE(SUM(qty), 0) as qty,
                       0 as qty_invoice,
                       0 as qty_invoiced                       
                from ttb_purchase_invoice_stock_line
                group by ttb_branch_id, product_id
                UNION ALL
                select ttb_branch_id as ttb_branch_id,
                    product_id as product_id,
                    0 as qty,
                    COALESCE(SUM(CASE WHEN invoice_date is null THEN purchase_invoiced_qty ELSE 0 END), 0) as qty_invoice,
                    COALESCE(SUM(CASE WHEN invoice_date is not null THEN purchase_invoiced_qty ELSE 0 END), 0) as qty_invoiced
                from pos_order_line
                where purchase_invoiced_qty > 0 and ttb_branch_id is not null
                group by ttb_branch_id, product_id                         
                    ),
                aggregated AS (
                    SELECT 
                        ttb_branch_id,
                        product_id,
                        COALESCE(SUM(qty), 0) AS qty,
                        COALESCE(SUM(qty_invoice), 0) AS qty_invoice,
                        COALESCE(SUM(qty_invoiced), 0) AS qty_invoiced,
                        COALESCE(SUM(qty), 0) - COALESCE(SUM(qty_invoice), 0) - COALESCE(SUM(qty_invoiced), 0)AS qty_to_invoiced
                    FROM combined
                    GROUP BY ttb_branch_id, product_id
                )
                SELECT 
                    ROW_NUMBER() OVER (ORDER BY ttb_branch_id, product_id) AS id,
                    *
                FROM aggregated
            """

    @property
    def _table_query(self):
        return self._query()
