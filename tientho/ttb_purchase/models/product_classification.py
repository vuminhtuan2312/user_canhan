from odoo import *
from odoo import api, Command, fields, models, SUPERUSER_ID, _
from odoo.exceptions import UserError
import logging
from datetime import timedelta

_logger = logging.getLogger(__name__)

class ProductClassification(models.Model):
    _name = 'product.classification'
    _description = 'Danh mục Phân loại sản phẩm'

    name = fields.Char(string='Tên', required=True, help="VD: Nhóm 1 - 30% đầu tiên, Nhóm 2 - 20% tiếp theo")
    from_cumulative_percent = fields.Float(string='Từ % doanh thu lũy kế')
    to_cumulative_percent = fields.Float(string='Đến % doanh thu lũy kế')
    note = fields.Text(string='Ghi chú')

    @api.model
    def cron_update_classification(self):

        # Bước 1: lấy dữ liệu khoảng thời gian cần xét
        weeks_param = self.env['ir.config_parameter'].sudo().get_param('ttb_purchase.classification_weeks', '2')
        try:
            weeks = int(weeks_param)
        except ValueError:
            weeks = 2
            _logger.warning("Tham số ttb_purchase.classification_weeks không hợp lệ, dùng mặc định 2 tuần.")

        date_from = fields.Datetime.now() - timedelta(weeks=weeks)
        date_to = fields.Datetime.now()

        # Bước 2: lấy tất cả các đơn hàng pos.order trong khoảng thời gian
        # (Lấy luôn cả order line để tiện gom nhóm theo product.template)
        # Giả sử pos order ở trạng thái đã thanh toán/xuất kho (như 'paid', 'done', 'invoiced')
        # Để an toàn, tuỳ thuộc vào quy trình Pos. Ta xét state in ('paid', 'done', 'invoiced')
        self.env.cr.execute("""
                SELECT pt.id as product_template_id, SUM(pol.price_subtotal_incl) as template_revenue
                FROM pos_order_line pol
                JOIN pos_order po ON po.id = pol.order_id
                JOIN product_product pp ON pp.id = pol.product_id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                WHERE po.date_order >= %s AND po.date_order <= %s
                  AND po.state IN ('paid', 'done', 'invoiced')
                GROUP BY pt.id
                ORDER BY template_revenue DESC
            """, (date_from, date_to))

        revenue_data = self.env.cr.dictfetchall()
        if not revenue_data:
            _logger.info("Không có dữ liệu đơn hàng POS trong khoảng thời gian để phân loại.")
            return

        # Bước 3: tính tổng doanh thu hệ thống từ các đơn hàng tìm được
        total_revenue = sum(row['template_revenue'] for row in revenue_data)
        if total_revenue <= 0:
            _logger.info("Tổng doanh thu <= 0, không thể tính phần trăm.")
            return

        # Lấy tất cả các classification
        classifications = self.env['product.classification'].search([], order='to_cumulative_percent desc')

        cumulative_revenue = 0.0

        for row in revenue_data:
            pt_id = row['product_template_id']
            revenue = row['template_revenue']

            # Bước 4 & 5: tính doanh thu lũy kế
            # Mặc dù yêu cầu "Cộng dồn các sản phẩm trước, rồi cộng cả sp hiện tại"
            # -> Theo logic ABC analysis, cumulative bao gồm cả nó.
            cumulative_revenue += revenue
            cumulative_percent = (cumulative_revenue / total_revenue) * 100

            # Bước 6: So sánh với classifications
            matched_class = False
            for c in classifications:
                if c.from_cumulative_percent <= cumulative_percent <= c.to_cumulative_percent:
                    matched_class = c
                    break  # Vì đã order theo to_cumulative_percent desc nên sẽ lấy khoảng trên lớn hơn

            if matched_class:
                self.env['product.template'].browse(pt_id).write({'classification_id': matched_class.id})
            else:
                _logger.info(
                    'Sản phẩm %s với doanh thu là %s, doanh thu lũy kế là %s không thuộc khoảng phân loại doanh thu lũy kế nào',
                    pt_id, revenue, cumulative_percent)
