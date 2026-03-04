# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class ProductLabelLayout(models.TransientModel):
    _inherit = 'product.label.layout'

    available_pricelist_ids = fields.Many2many('product.pricelist')

    picking_ids = fields.Many2many('stock.picking', string="Phiếu kho liên quan")

    print_format = fields.Selection(
        selection_add=[('ttb_custom', 'Mẫu TTB')],
        ondelete={'ttb_custom': 'set default'}
    )

    pricelist_id = fields.Many2one(
        'product.pricelist',
        string="Pricelist",
        domain="[('id', 'in', available_pricelist_ids)]"
    )

    print_area = fields.Selection([
        ('retail', 'Khu bán lẻ'),
        ('entertainment', 'Khu vui chơi')
    ], string="Khu vực áp dụng", default='retail', required=True,
        help="Chọn 'Khu vui chơi' để lấy giá BB2. Chọn 'Khu bán lẻ' để lấy giá theo Cơ sở kho/người dùng.")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self._context.get('active_model') == 'stock.picking':
            active_ids = self._context.get('active_ids', [])
            if active_ids:
                res['picking_ids'] = [(6, 0, active_ids)]
        sudo_env = self.env['product.pricelist'].sudo()
        user = self.env.user
        user_branch_ids = user.sudo().ttb_branch_ids.ids or []

        # Domain: Khu vui chơi HOẶC (Thuộc branch user quản lý) HOẶC (Chưa gán branch - cho dữ liệu cũ)
        domain = [
            '|',
            ('area', '=', 'entertainment'),
            ('branch_id', 'in', user_branch_ids),
        ]
        found_pricelists = sudo_env.search(domain)
        res['available_pricelist_ids'] = [(6, 0, found_pricelists.ids)]


        # if found_pricelists and not res.get('pricelist_id'):
        #     preferred = found_pricelists.filtered(lambda p: p.branch_id.id in user_branch_ids)
        #     target_id = preferred[0].id if preferred else found_pricelists[0].id
        #     res['pricelist_id'] = target_id
        return res

    def process(self):
        self.ensure_one()
        # Nếu chọn Mẫu TTB -> Gọi Report Action riêng
        if self.print_format == 'ttb_custom':
            return self.env.ref('ttb_price_change_request.action_report_ttb_label_wizard').report_action(self)
        #
        # # Các trường hợp khác để Odoo tự xử lý
        return super().process()

    _augges_price_cache = {}

    def _get_branch_price_level(self, branch_name):

        name = (branch_name or "").strip()

        # BL: 4 cơ sở HN
        bl_names = {
            "HNI - ĐỐNG ĐA - LÁNG",
            "HNI - XUÂN THỦY - CẦU GIẤY",
            "HNI - THANH XUÂN - NGUYỄN TRÃI",
            "HNI - HOÀNG MAI - GIẢI PHÓNG",
        }
        if name in bl_names: return "bl"

        # BB4: Bình Dương
        if name in {"BDG - THỦ DẦU MỘT - CHÁNH NGHĨA", "BDG - THUẬN AN - AN PHÚ"}: return "bb4"

        # BB3: HCM
        if name == "HCM - Q12 - TRƯỜNG CHINH": return "bb3"

        # BB6: Bắc Giang
        if name == "BGG - NGÔ QUYỀN - BẮC GIANG": return "bb6"

        # BB5: Nghệ An (Vinh)
        if name == "NAN - VINH - TRẦN PHÚ": return "bb5"

        # BB1: Các tỉnh còn lại
        if name in {
            "TNN - HOÀNG VĂN THỤ - LƯƠNG NGỌC QUYẾN",
            "TBH - ĐỀ THÁM - LÝ BÔN",
            "THA - LAM SƠN - LÊ LỢI",
            "HPG - NGÔ QUYỀN - LÊ HỒNG PHONG",
        }: return "bb1"

        return "bb1"  # Mặc định

    def _get_augges_column_name(self, level):
        """Map Level giá -> Tên cột trong Database Augges"""
        mapping = {
            "sale": "Gia_Ban",  # Giá bán lẻ thường
            "bl": "Gia_Bl",
            "bb1": "Gia_Ban1",
            "bb2": "Gia_Ban2",
            "bb3": "Gia_Ban3",
            "bb4": "Gia_Ban4",
            "bb5": "Gia_Ban5",
            "bb6": "Gia_Ban6",
        }
        return mapping.get(level, "Gia_Ban1")

    def get_augges_price(self, product):
        """
        Lấy giá Augges dựa trên field 'print_area':
        1. print_area == 'entertainment' -> Lấy cứng giá BB2.
        2. print_area == 'retail' -> Tìm Branch (Picking/User) -> Map ra giá (BB1, BL...).
        """
        if not product: return 0.0
        try:
            augges_id = int(product.augges_id)
        except (ValueError, TypeError):
            return 0.0


        source_info = ""

        if self.print_area == 'entertainment':

            col_name = "Gia_Ban2"
            source_info = "User Selection (Entertainment)"
            branch_name = "Khu Vui Choi"

        else:

            branch = False

            if self.picking_ids:
                picking = self.picking_ids[0]
                if picking.picking_type_id and picking.picking_type_id.warehouse_id:
                    wh = picking.picking_type_id.warehouse_id
                    if hasattr(wh, 'ttb_branch_id') and wh.ttb_branch_id:
                        branch = wh.ttb_branch_id
                        source_info = f"Picking ({picking.name}) -> WH ({wh.name})"

            if not branch:
                user = self.env.user
                if user.ttb_branch_ids:
                    branch = user.ttb_branch_ids[:1]
                    source_info = f"User ({user.name})"
            if branch:
                branch_name = branch.name
                level = self._get_branch_price_level(branch_name)
                col_name = self._get_augges_column_name(level)
            else:
                _logger.error(f"[IN TEM] Retail Mode: No Branch found. SP: {product.default_code}")
                return 0.0

        cache_key = f"{augges_id}_{col_name}"
        if cache_key in self._augges_price_cache:
            return self._augges_price_cache[cache_key]

        price_val = 0.0
        conn = None
        cursor = None
        try:
            conn = self.env["ttb.tools"].get_mssql_connection_send()
            cursor = conn.cursor()

            query = f"SELECT {col_name} FROM DmH WHERE ID = ?"
            cursor.execute(query, (augges_id,))
            row = cursor.fetchone()

            if row:
                price_val = float(row[0] or 0.0)
                _logger.info(
                    f"[IN TEM] OK. [{source_info}] | Branch: {branch_name} | Col: {col_name} | Price: {price_val:,.0f}")
            else:
                _logger.warning(f"[IN TEM] Not Found in Augges DmH: ID={augges_id}")

        except Exception as e:
            _logger.error(f"[IN TEM] SQL Error: {str(e)}")
            price_val = 0.0
        finally:
            try:
                if cursor: cursor.close()
                if conn: conn.close()
            except Exception:
                pass

        self._augges_price_cache[cache_key] = price_val
        return price_val

    def get_barcode_to_print(self, product):
        """
        Lấy mã in theo thứ tự ưu tiên:
        1. Xét độ dài >= 11: barcode_vendor > default_code > barcode > barcode_k
        2. Nếu không thỏa mãn: barcode_vendor > default_code > barcode > barcode_k (lấy nếu tồn tại)
        """
        if not product:
            return False

        def get_val(attr_name):
            val = getattr(product, attr_name, False)
            return str(val).strip() if val else False

        fields_check = ['barcode_vendor', 'default_code', 'barcode', 'barcode_k']

        for field in fields_check:
            val = get_val(field)
            if val and len(val) >= 11:
                return val

        for field in fields_check:
            val = get_val(field)
            if val:
                return val

        return False