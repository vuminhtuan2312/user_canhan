from odoo.exceptions import UserError
from odoo import api, fields, models
from .const import purchase_invoice_stock_summary, purchase_invoice_stock_summary2, purchase_invoice_stock_summary_without_nibot


class BaocaoCongnocohoadon(models.Model):
    _name = 'cong.no.khong.hoa.don'
    _description = 'Báo cáo công nợ không có hóa đơn'
    _auto = False
    _table = 'purchase_invoice_stock_summary_without_nibot'

    id = fields.Integer(string='ID', readonly=True)
    partner_name = fields.Char(string='Tên nhà cung cấp', readonly=True)
    vat = fields.Char(string='Mã số thuế', readonly=True)
    po_name = fields.Char(string='Tên đơn hàng', readonly=True)
    sp_name = fields.Char(string='Tên phiếu nhận', readonly=True)
    amount_total = fields.Float(string='Số tiền phiếu nhận', readonly=True)

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
        self.env.cr.execute("DROP MATERIALIZED VIEW IF EXISTS purchase_invoice_stock_summary_without_nibot;")

        # Tạo câu SQL động với điều kiện
        dynamic_sql = self._build_dynamic_sql(partner_id, start_date, end_date)

        # Tạo materialized view mới
        self.env.cr.execute(dynamic_sql)
        self.env.cr.commit()

        return True

    def _build_dynamic_sql(self, partner_id=None, start_date=None, end_date=None):
        """Xây dựng câu SQL động với điều kiện"""
        base_sql = purchase_invoice_stock_summary_without_nibot

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

        base_sql += f" group by sp_name,  rp.name, rp.vat,po.name, sp.amount_total"

        return base_sql

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """Override để hỗ trợ groupby và aggregation"""
        return super(BaocaoCongnocohoadon, self).read_group(
            domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy
        )


