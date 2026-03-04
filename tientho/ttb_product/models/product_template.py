from odoo import api, fields, models, _
import json

from odoo.tools import config
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging
_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    default_code = fields.Char(copy=False)
    season_type_id = fields.Many2one(comodel_name='season.type', string='Loại mùa vụ')

    top_supplier_id = fields.Many2one(
        'res.partner',
        string="Tên nhà cung cấp",
        compute='_compute_top_supplier',
        store=False
    )

    top_supplier_price = fields.Float(
        string="Giá nhập",
        compute='_compute_top_supplier',
        store=False
    )
    top_supplier_date_start = fields.Date(
        string="Thời gian bắt đầu",
        compute='_compute_top_supplier',
        store=False
    )
    top_supplier_date_end = fields.Date(
        string="Thời gian kết thúc",
        compute='_compute_top_supplier',
        store=False
    )
    @api.depends('product_variant_ids')
    def _compute_top_supplier(self):
        PurchaseOrderLine = self.env['purchase.order.line']
        now = fields.Date.today()
        six_months_ago = now - relativedelta(months=6)

        for product in self:
            variants = product.product_variant_ids.ids
            if not variants:
                product.top_supplier_id = False
                product.top_supplier_price = 0
                product.top_supplier_date_start = False
                product.top_supplier_date_end = False
                continue

            # Tìm PO line 6 tháng gần nhất
            po_lines = PurchaseOrderLine.search([
                ('product_id', 'in', variants),
                ('order_id.state', 'in', ['purchase', 'done']),
                ('order_id.date_approve', '>=', six_months_ago),
            ])

            if not po_lines:
                product.top_supplier_id = False
                product.top_supplier_price = 0
                product.top_supplier_date_start = False
                product.top_supplier_date_end = False
                continue

            supplier_count = {}
            for line in po_lines:
                supplier = line.order_id.partner_id.id
                supplier_count[supplier] = supplier_count.get(supplier, 0) + 1

            # NCC có nhiều PO nhất
            best_supplier_id = max(supplier_count, key=supplier_count.get)
            product.top_supplier_id = best_supplier_id

            # Lấy giá nhập từ supplierinfo
            seller = product.seller_ids.filtered(lambda s: s.partner_id.id == best_supplier_id)

            if seller:
                seller = seller.sorted(lambda s: s.date_start or fields.Date.from_string("1900-01-01"), reverse=True)[0]
                product.top_supplier_price = seller.price
                product.top_supplier_date_start = seller.date_start
                product.top_supplier_date_end = seller.date_end
            else:
                product.top_supplier_price = 0
                product.top_supplier_date_start = False
                product.top_supplier_date_end = False

    @api.model_create_multi
    def create(self, vals_list):

        res = super().create(vals_list)
        for record in res:
            if not record.categ_id_level_2 or record.default_code: continue

            categ_id = record.categ_id_level_2
            if categ_id.ttb_sequence_id:
                record.default_code = categ_id.ttb_sequence_id.next_by_id()

        return res

    ttb_product_status = fields.Selection(string='Trạng thái sản phẩm', selection=[('zz', 'ZZ- Mở toàn bộ'),
                                                                                        ('z1', 'Z1 – Đóng bán hàng'),
                                                                                        ('z0', 'Z0 – Đóng mua hàng'),
                                                                                        ('za', 'ZA – Đóng toàn bộ'), ],
                                          required=True, default='zz')
    product_status_ids = fields.One2many(string='Trạng thái sản phẩm theo cơ sở', comodel_name='ttb.product.status', inverse_name='product_id')

    # add tracking to base field
    categ_id = fields.Many2one(tracking=True)
    name = fields.Char(tracking=True)

    categ_id_level_1 = fields.Many2one('product.category',
                                       string='MCH1',
                                       domain="[('parent_id', '=', False),('category_level', '=', 1)]",
                                       compute='_compute_categ_id_level_all',
                                       store=True, readonly=False, tracking=True,
                                       )
    categ_id_level_2 = fields.Many2one('product.category',
                                       string='MCH2',
                                       domain="[('parent_id', '=?', categ_id_level_1),('category_level', '=', 2)]",
                                       compute='_compute_categ_id_level_all',
                                       store=True, readonly=False, tracking=True,
                                       )
    categ_id_level_3 = fields.Many2one('product.category',
                                       string='MCH3',
                                       domain="[('parent_id', '=?', categ_id_level_2),('category_level', '=', 3)]",
                                       compute='_compute_categ_id_level_all',
                                       store=True, readonly=False, tracking=True,
                                       )
    categ_id_level_4 = fields.Many2one('product.category',
                                       string='MCH4',
                                       domain="[('parent_id', '=?', categ_id_level_3),('category_level', '=', 4)]",
                                       compute='_compute_categ_id_level_all',
                                       store=True, readonly=False, tracking=True,
                                       )
    categ_id_level_5 = fields.Many2one('product.category',
                                       string='MCH5',
                                       domain="[('parent_id', '=?', categ_id_level_4),('category_level', '=', 5)]",
                                       compute='_compute_categ_id_level_all',
                                       store=True, readonly=False, tracking=True,
                                       )
    mch_description = fields.Html(string='Hướng dẫn', compute='_compute_mch_description')

    barcode_vendor = fields.Char('Ma_Hang1 (Mã nhà cung cấp)', index=True, copy=False)
    barcode_k = fields.Char('Ma_VachK', index=True, copy=False)

    ttb_product_template_image_ids = fields.One2many(
        string="Extra Product Media",
        comodel_name='ttb.product.image',
        inverse_name='product_tmpl_id',
        copy=True,
    )
    augges_id = fields.Integer("Auggess ID", index=True, help="ID của sản phẩm trong Augges")  # ID duy nhất từ MSSQL

    last_image_1920 = fields.Image("Ảnh chụp điện thoại", compute='_compute_last_image_1920', inverse='_set_last_image_1920')

    augges_info = fields.Text(string="Thông tin Augges")

    def _compute_last_image_1920(self):
        """Get the image from the template if no image is set on the variant."""
        for record in self:
            record.last_image_1920 = record.image_1920

    def _set_last_image_1920(self):
        for record in self:
            record.image_1920 = record.last_image_1920
            if record.last_image_1920:
                self.env['ttb.product.image'].create({
                    'name': self.env.user.name,
                    'image_1920': record.last_image_1920,
                    'product_tmpl_id': record.id,
                    # 'product_variant_id': record.
                })

    ttb_substitute_product_ids = fields.One2many(string='Sản phẩm thay thế', comodel_name='ttb.substitute.product', inverse_name='product_template_id')
    alternative_product_ids = fields.Many2many('product.template', string='Nguyên vật liệu thay thế', relation='product_template_alternative_rel', column1='product_id', column2='alternative_id')

    parent_product_id = fields.Many2one('product.template', string='Sản phẩm gốc', index=True, copy=False)
    child_product_ids = fields.One2many('product.template', 'parent_product_id', string='Sản phẩm con')

    @api.depends('categ_id', 'categ_id.parent_id')
    def _compute_categ_id_level_all(self):
        for rec in self:
            categ_id = rec.categ_id
            for level in range(5, 0, -1):
                is_match = categ_id and categ_id.category_level == level
                rec[f'categ_id_level_{level}'] = categ_id.id if is_match else False
                if is_match:
                    categ_id = categ_id.parent_id

    def onchange_level(self, level):
        categ_id = self[f'categ_id_level_{level}']
        # Gán lại cha. Chỉ cần gán lại 1 cấp sau đó sẽ có hiệu ứng dây chuyền
        if level > 1 and categ_id:
            self[f'categ_id_level_{level - 1}'] = categ_id.parent_id

        # Gán cấp con bằng False nếu không thỏa mãn quan hệ cha con.
        # Gán tất cả để tính được categ_id
        for level_up in range(level + 1, 6):
            key = f'categ_id_level_{level_up}'
            key_parent = f'categ_id_level_{level_up - 1}'

            if not self[key_parent] or (self[key] and self[key].parent_id != self[key_parent]):
                self[key] = False

        for level_categ in range(5, 0, -1):
            key = f'categ_id_level_{level_categ}'
            if self[key] or level_categ == 1:
                self.categ_id = self[key]
                break

    @api.onchange('categ_id_level_1')
    def onchange_level_1(self):
        self.onchange_level(1)

    @api.onchange('categ_id_level_2')
    def onchange_level_2(self):
        self.onchange_level(2)

    @api.onchange('categ_id_level_3')
    def onchange_level_3(self):
        self.onchange_level(3)

    @api.onchange('categ_id_level_4')
    def onchange_level_4(self):
        self.onchange_level(4)

    @api.onchange('categ_id_level_5')
    def onchange_level_5(self):
        self.onchange_level(5)

    @api.depends('categ_id_level_5', 'categ_id_level_4', 'categ_id_level_3', 'categ_id_level_2', 'categ_id_level_1')
    def _compute_mch_description(self):
        for rec in self:
            rec.mch_description = rec.categ_id_level_5.mch_description or rec.categ_id_level_4.mch_description or rec.categ_id_level_3.mch_description or rec.categ_id_level_2.mch_description or rec.categ_id_level_1.mch_description

    def write(self, vals):
        # if vals.get('categ_id_level_2') and not vals.get('default_code'):
        #     categ_id = self.env['product.category'].browse(vals.get('categ_id_level_2'))
        #     for product in self:
        #         if product.categ_id_level_2 != categ_id and (not product.default_code or ('default_code' in vals and not vals.get('default_code'))):
        #             product.default_code = categ_id.ttb_sequence_id.next_by_id()
        if 'categ_id' not in vals:
            for level in range(5, 0, -1):
                key = f'categ_id_level_{level}'
                if vals.get(key):
                    vals['categ_id'] = vals[key]
                    return super().write(vals)

            if len(self) == 1:
                for level in range(1, 6):
                    key = f'categ_id_level_{level}'
                    if key in vals:
                        if level > 1:
                            vals['categ_id'] = self[f'categ_id_level_{level - 1}'].id
                        else:
                            vals['categ_id'] = self.env.ref('product.product_category_all').id
                            vals['categ_id_level_1'] = self.env.ref('product.product_category_all').id
                        return super().write(vals)
        return super().write(vals)

    def action_update_attribute(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Cập nhật thuộc tính',
            'res_model': 'update.product.attribute.value.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_product_id': self.id,
            }
        }

    # def get_max_id_dmh(self):
    #     records = self.env['ttb.augges'].get_records(table="DmH",
    #         domain="1=1",
    #         field_list=["MAX(ID) AS max_id"],
    #         get_dict=True
    #     )
    #     if records and records[0].get("max_id") is not None:
    #         return records[0]["max_id"]N
    #     return 0

    def action_update_augges(self):
        self._update_augges(raise_exception=True)
        self.action_refresh_augges_info()

    def action_create_augges(self):
        self._create_augges(raise_exception=True)
        self.action_refresh_augges_info()

    def action_refresh_augges_info(self):
        for product in self:
            info = self.env['ttb.augges'].get_product_full_info(product.augges_id) if product.augges_id else {
                'error': 'Sản phẩm không có augges_id'}
            product.augges_info = json.dumps(info, indent=4, ensure_ascii=False, default=str)

    def _get_augges_product_data(self):
        """
        Helper to get product data dictionary for Augges.
        This function prepares a dictionary with data from an Odoo product record,
        ready to be inserted or updated into Augges's DmH table.
        """
        self.ensure_one()
        product = self

        # 1. Get taxes (ThueV for purchase, Thue for sale)
        thue_v, thue = 0, 0
        if product.supplier_taxes_id:
            tax_purchase = product.supplier_taxes_id[0]
            thue_v = tax_purchase.amount if tax_purchase.amount_type == "percent" else 0
        if product.taxes_id:
            tax_sell = product.taxes_id[0]
            thue = tax_sell.amount if tax_sell.amount_type == "percent" else 0

        # 2. Get product category (Nganh Hang)
        category_id_augges = None
        if product.categ_id_level_1 and product.categ_id_level_1.code_augges:
            category_code = product.categ_id_level_1.code_augges
            category_records = self.env['ttb.augges'].get_records(
                table="DmNganh",
                domain=f"Ma_Nganh = '{category_code}'",
                field_list=["ID"],
                get_dict=True
            )
            if category_records:
                category_id_augges = category_records[0]['id']

        # 3. Get unit of measure (Don Vi Tinh)
        dvt_id_augges = None
        if product.uom_id and hasattr(product.uom_id, 'code_augges') and product.uom_id.code_augges:
            dvt_code = product.uom_id.code_augges
            dvt_records = self.env['ttb.augges'].get_records(
                table="DmDvt",
                domain=f"Ma_Dvt = '{dvt_code}'",
                field_list=["ID"],
                get_dict=True
            )
            if dvt_records:
                dvt_id_augges = dvt_records[0]['id']

        # 4. Construct the data dictionary
        return {
            'Ma_Hang': product.barcode or '',
            'Ma_Hang1': product.barcode_vendor or '',
            'Ma_Vach': product.default_code or '',
            'Ma_VachK': product.barcode_k or '',
            'Ten_Hang': product.name or '',
            'Ten_HangE': product.name.upper() or '',
            'Ten_HangU': product.name.upper() or '',
            'Mo_Ta': product.description_sale or '',
            'Gia_Nhap': product.standard_price or 0,
            'Gia_Ban': product.list_price or 0,
            'Gia_Ban1': product.list_price or 0,
            'Gia_Ban2': product.list_price or 0,
            'Gia_Ban3': product.list_price or 0,
            'Gia_Ban4': product.list_price or 0,
            'Gia_Ban5': product.list_price or 0,
            'Gia_Ban6': product.list_price or 0,
            'Inactive': 0 if product.active else 1,
            'InactiveX': 0 if product.sale_ok else 1,
            'InactiveN': 0 if product.purchase_ok else 1,
            'ID_DvCs': dvt_id_augges,
            'ID_Dvt': dvt_id_augges,
            'Thue': thue,
            'ThueV': thue_v,
            'ID_Nganh': category_id_augges,
            'LastEdit': datetime.now(),
            'UserID': (self.env.uid if hasattr(self, 'env') else 1),
            'IsEdit': 1,
        }

    def _augment_augges_create_defaults(self, base_data):
        """
        Thêm các cột mặc định mà trước đây bạn set ở hàm _create_augges.
        (UPDATE sẽ KHÔNG dùng phần này để giữ nguyên logic cũ.)
        """
        insert_date = datetime.utcnow() + timedelta(hours=7)
        defaults = {
            'ID_Dv': 0,
            'Tk_Hh': 1561,
            'Tk_Dt': 5111,
            'Tk_Gv': 632,
            'Tk_HbTl': 5212,

            'Thue_XNK': 0,
            'Thue_TTDB': 0,

            # Mặc định khác
            'Tk_Kg': '',
            'Tk_Ck': '',
            'Gioi_Tinh': '',
            'Bao_Hanh': 0,
            'Luu_Kho': 0,
            'Gia_Nk': 0,
            'Gia_Bl': 0,
            'Tyle_GNM': 0,
            'Tyle_GBL': 0,
            'Sl_Max': 0,
            'Sl_Min': 0,
            'Tinh_Gv': 0,
            'T_Luong': 0,
            'T_LuongGoi': 0,
            'T_LuongTT': 0,
            'The_Tich': 0,
            'Vi_Tri': 0,
            'Chuc_Nang': 0,
            'TyLe_Giam': 0,
            'Tien_Giam': 0,
            'TyLe_Lai': 0,
            'Tien_Lai': 0,
            'TyLe_CLGB': 0,
            'Lam_Tron': 0,
            'Ty_Gia': 0,
            'Cp_Gv': 0,
            'ChkTon': 0,
            'XuatAm': 0,
            'Ton_Dt': 0,
            'IsBOG': 0,

            'Ngay_Nhap': insert_date,
            'InsertDate': insert_date,
            'LastEdit': fields.Datetime.now(),

            'ID_Loai': 0,
            'ID_NhomN': 0,
            'ID_DongH': 0,
            'ID_ChungL': 0,

            'Ghi_Chu': '',
            'KTon': 0,
            'ID_HMM': 0,
            'IsHMM': 0,

            'LoaiH': 0,
        }
        # gộp vào base_data nhưng không ghi đè base_data
        merged = dict(defaults)
        merged.update(base_data or {})
        return merged


    def _create_augges(self, cursor=False, raise_exception=False):
        product = self

        if product.augges_id:
            message = 'Sản phẩm id: %s đã có augges_id %s' % (self.id, self.augges_id)
            _logger.info(message)
            if raise_exception:
                raise Exception(message)
            return
        conn = self.env['ttb.tools'].get_mssql_connection_send()
        if not cursor:
            cursor = conn.cursor()
        
        try:
            base = self._get_augges_product_data()
            data = self._augment_augges_create_defaults(base)
            new_id = self.env['ttb.augges'].insert_record('DmH', data, conn, auto_id=True)

            # Gán lại vào Odoo
            product.sudo().write({'augges_id': new_id})
            _logger.info(f"Đã tạo sản phẩm {product.name} bên MSSQL với ID {new_id}")

            self.env.cr.commit()
            conn.commit()
        except Exception as e:
            _logger.error(f"Lỗi khi đồng bộ sản phẩm {product.name}: {e}")
            conn.rollback()
            if raise_exception:
                raise

    def _update_augges(self, cursor=False, raise_exception=False):
        """Helper function to update a single product to Augges."""
        product = self
        if not product.augges_id:
            _logger.warning(f"Sản phẩm {product.name} (ID: {product.id}) không có augges_id, bỏ qua cập nhật.")
            return

        conn = self.env['ttb.tools'].get_mssql_connection_send()
        if not cursor:
            cursor = conn.cursor()

        try:
            data_to_update = self._get_augges_product_data()
            set_clauses = ", ".join([f"[{key}] = ?" for key in data_to_update])
            params = list(data_to_update.values()) + [product.augges_id]

            cursor.execute(f"UPDATE DmH SET {set_clauses} WHERE ID = ?", params)
            _logger.info(f"Đã chuẩn bị lệnh UPDATE cho sản phẩm {product.name} (Augges ID: {product.augges_id})")
            conn.commit()
        except Exception as e:
            _logger.error(f"Lỗi khi cập nhật sản phẩm {product.name} sang Augges: {e}")
            conn.rollback()
            if raise_exception:
                raise


    @api.model
    def sync_products_to_mssql_create(self):
        """Đồng bộ các sản phẩm từ Odoo sang MSSQL (Augges) với những sản phẩm chưa có auggess_id"""
        conn = self.env['ttb.tools'].get_mssql_connection_send()
        cursor = conn.cursor()

        # Lấy tất cả sản phẩm chưa có augges_id
        products = self.env['product.template'].sudo().search([('augges_id', '=', False)])
        _logger.info(f"Tìm thấy {len(products)} sản phẩm cần đồng bộ")

        for product in products:
            product._create_augges(cursor)

        cursor.close()
        conn.close()
        _logger.info("Đồng bộ sản phẩm thành công!")

    @api.model
    def sync_products_to_mssql_update(self, product_ids=None):
        """
        Đồng bộ các thay đổi từ Odoo sang MSSQL (Augges).
        - Nếu `product_ids` được cung cấp, chỉ đồng bộ các sản phẩm đó.
        - Nếu không, sẽ tự động tìm và đồng bộ các sản phẩm đã thay đổi kể từ lần cuối.
        """
        _logger.info("Bắt đầu phiên đồng bộ cập nhật sản phẩm sang Augges (MSSQL).")

        if product_ids:
            products_to_update = self.browse(product_ids)
        else:
            products_to_update = self.search([
                ('augges_id', '!=', 0)
            ])

        if not products_to_update:
            _logger.info("Không có sản phẩm nào cần cập nhật.")
            return

        _logger.info(f"Tìm thấy {len(products_to_update)} sản phẩm cần cập nhật.")

        conn = self.env['ttb.tools'].get_mssql_connection_send()
        cursor = conn.cursor()

        for product in products_to_update:
            product._update_augges(cursor=cursor)

        _logger.info("Hoàn tất phiên đồng bộ cập nhật sản phẩm.")

    def sync_sgk_parent_child(self):
        """
        Đồng bộ ghép sản phẩm SGK:
        - Bảng MSSQL: thien_sgk_dmh_moi_cu
            + id_hang_moi -> sản phẩm gốc (parent_product_id)
            + id_hang_cu  -> sản phẩm con  (child, trỏ parent_product_id tới gốc)
        - Map theo product.template.augges_id
        """

        AUGGES_FIELD = 'augges_id'

        conn = None
        owns_conn = False

        try:
            # 1. Kết nối MSSQL
            conn = self.env['ttb.tools'].get_mssql_connection_send()
            owns_conn = True
            cursor = conn.cursor()

            # 2. Lấy dữ liệu map từ bảng SGK
            sql = """
                SELECT id_hang_moi, id_hang_cu
                FROM thien_sgk_dmh_moi_cu
                WHERE id_hang_moi IS NOT NULL
                  AND id_hang_cu  IS NOT NULL
            """
            cursor.execute(sql)
            rows = cursor.fetchall()

            if not rows:
                _logger.info("SGK sync: không có dữ liệu trong thien_sgk_dmh_moi_cu")
                return

            # 3. Gom tất cả ID để load 1 lần trên Odoo
            all_ids = set()
            for r in rows:
                all_ids.add(str(r[0]).strip())  # id_hang_moi
                all_ids.add(str(r[1]).strip())  # id_hang_cu

            # lấy cả sản phẩm đã lưu trữ (active & inactive)
            ProductTmpl = self.env['product.template'].with_context(active_test=False)
            products = ProductTmpl.search([(AUGGES_FIELD, 'in', list(all_ids))])

            # map augg es_id -> product.template
            by_augges = {}
            for p in products:
                if p.augges_id:
                    key = str(p.augges_id).strip()
                    by_augges[key] = p

            updated = 0
            missing_parent = 0
            missing_child = 0

            # 4. Duyệt từng dòng map và gán parent cho child
            for r in rows:
                id_moi = str(r[0]).strip()  # sản phẩm gốc (parent)
                id_cu = str(r[1]).strip()  # sản phẩm con  (child)

                parent = by_augges.get(id_moi)
                child = by_augges.get(id_cu)

                if not parent:
                    missing_parent += 1
                    _logger.warning("SGK sync: không tìm thấy SP gốc %s=%s", AUGGES_FIELD, id_moi)
                    continue

                if not child:
                    missing_child += 1
                    _logger.warning("SGK sync: không tìm thấy SP con %s=%s", AUGGES_FIELD, id_cu)
                    continue

                # Nếu child chưa trỏ đúng về parent thì cập nhật
                if child.parent_product_id.id != parent.id:
                    child.sudo().write({'parent_product_id': parent.id})
                    updated += 1

            _logger.info(
                "SGK sync DONE: rows=%s, updated=%s, missing_parent=%s, missing_child=%s",
                len(rows), updated, missing_parent, missing_child,
            )

        except Exception as e:
            _logger.exception("Lỗi SGK sync: %s", e)
            # Nếu muốn xuất hiện trên UI khi chạy tay:
            # raise UserError(_("Lỗi đồng bộ SGK: %s") % e)
            raise
        finally:
            if owns_conn and conn:
                try:
                    conn.close()
                except Exception:
                    pass
