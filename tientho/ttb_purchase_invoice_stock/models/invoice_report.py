from odoo.exceptions import UserError
from odoo import api, fields, models
from .const import purchase_invoice_stock_summary, purchase_invoice_stock_summary2

class BaocaoCongnocohoadon(models.Model):
    _name = 'cong.no.co.hoa.don'
    _description = 'Báo cáo công nợ có hóa đơn'
    _auto = False
    _table = 'purchase_invoice_stock_summary'

    id = fields.Integer(string='ID', readonly=True)
    ttb_vendor_invoice_no = fields.Char(string='Số hóa đơn', readonly=True)
    ttb_price_unit = fields.Float(string='Số tiền hóa đơn', readonly=True)
    partner_name = fields.Char(string='Tên nhà cung cấp', readonly=True)
    vat = fields.Char(string='Mã số thuế', readonly=True)
    invoice_code = fields.Char(string='Ký hiệu hóa đơn NCC', readonly=True)
    invoice_date = fields.Date(string="Ngày hóa đơn", readonly=True)
    po_name = fields.Char(string='Tên đơn hàng', readonly=True)
    sp_name = fields.Char(string='Tên phiếu nhận', readonly=True)
    amount_total = fields.Float(string='Số tiền phiếu nhận', readonly=True)
    received_amount_total = fields.Float(string='Số tiền đơn nhận', readonly=True)
    compare_invoice = fields.Selection([
        ('matching', 'Khớp'),
        ('money', 'Chênh lệch tiền'),
        ('quantity', 'Chênh lệch số lượng'),
        ('none', 'Chưa so sánh')
    ], string='Trạng thái so sánh', readonly=True)

    def init(self):
        """Khởi tạo model - không tạo materialized view"""
        pass

    @api.model
    def refresh_materialized_view_with_conditions(self, partner_id=None, start_date=None, end_date=None):
        """
        Refresh materialized view với điều kiện partner_id và khoảng thời gian
        
        Args:
            partner_id (int): ID của partner cần lọc
            start_date (str): Ngày bắt đầu (format: 'YYYYMMDD')
            end_date (str): Ngày kết thúc (format: 'YYYYMMDD')
        """
        # Xóa materialized view cũ
        self.env.cr.execute("DROP MATERIALIZED VIEW IF EXISTS purchase_invoice_stock_summary;")
        
        # Tạo câu SQL động với điều kiện
        dynamic_sql = self._build_dynamic_sql(partner_id, start_date, end_date)
        
        # Tạo materialized view mới
        self.env.cr.execute(dynamic_sql)
        self.env.cr.commit()
        
        return True

    def _build_dynamic_sql(self, partner_id=None, start_date=None, end_date=None):
        """Xây dựng câu SQL động với điều kiện"""
        base_sql = purchase_invoice_stock_summary
        
        # Thêm điều kiện partner_id
        if partner_id:
            base_sql += f" and po.partner_id = {partner_id}"
        
        # Thêm điều kiện khoảng thời gian
        if start_date and end_date:
            base_sql += f" and po.create_date between '{start_date}' and '{end_date}'"
        elif start_date:
            base_sql += f" and po.create_date >= '{start_date}'"
        elif end_date:
            base_sql += f" and po.create_date <= '{end_date}'"
        
        base_sql += purchase_invoice_stock_summary2
        
        return base_sql

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """Override để hỗ trợ groupby và aggregation"""
        return super(BaocaoCongnocohoadon, self).read_group(
            domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy
        )


