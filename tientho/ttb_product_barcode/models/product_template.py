from odoo import api, fields, models, _
# import pyodbc
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)

def tcvn3_to_unicode(text):
    if not text: return ''
    text = text.strip()
    """Chuyển đổi chuỗi từ TCVN3 sang Unicode theo bảng ánh xạ"""
    tcvn_chars = [
        'µ', '¸', '¶', '·', '¹', '¨', '»', '¾', '¼', '½', 'Æ',
        '©', 'Ç', 'Ê', 'È', 'É', 'Ë', '®', 'Ì', 'Ð', 'Î', 'Ï', 'Ñ',
        'ª', 'Ò', 'Õ', 'Ó', 'Ô', 'Ö', '×', 'Ý', 'Ø', 'Ü', 'Þ',
        'ß', 'ã', 'á', 'â', 'ä', '«', 'å', 'è', 'æ', 'ç', 'é',
        '¬', 'ê', 'í', 'ë', 'ì', 'î', 'ï', 'ó', 'ñ', 'ò', 'ô',
        '­', 'õ', 'ø', 'ö', '÷', 'ù', 'ú', 'ý', 'û', 'ü', 'þ',
        '¡', '¢', '§', '£', '¤', '¥', '¦'
    ]

    unicode_chars = [
        'à', 'á', 'ả', 'ã', 'ạ', 'ă', 'ằ', 'ắ', 'ẳ', 'ẵ', 'ặ',
        'â', 'ầ', 'ấ', 'ẩ', 'ẫ', 'ậ', 'đ', 'è', 'é', 'ẻ', 'ẽ', 'ẹ',
        'ê', 'ề', 'ế', 'ể', 'ễ', 'ệ', 'ì', 'í', 'ỉ', 'ĩ', 'ị',
        'ò', 'ó', 'ỏ', 'õ', 'ọ', 'ô', 'ồ', 'ố', 'ổ', 'ỗ', 'ộ',
        'ơ', 'ờ', 'ớ', 'ở', 'ỡ', 'ợ', 'ù', 'ú', 'ủ', 'ũ', 'ụ',
        'ư', 'ừ', 'ứ', 'ử', 'ữ', 'ự', 'ỳ', 'ý', 'ỷ', 'ỹ', 'ỵ',
        'Ă', 'Â', 'Đ', 'Ê', 'Ô', 'Ơ', 'Ư'
    ]

    tcvn_to_unicode_dict = {tcvn: unicode for tcvn, unicode in zip(tcvn_chars, unicode_chars)}

    return ''.join(tcvn_to_unicode_dict.get(char, char) for char in text)

thue_ra = ['R', 'R00', 'R05', 'R8', 'R10']
thue_vao = ['V', 'V00', 'V02', 'V04', 'V05', 'V08', 'V10']

class ProductTemplate(models.Model):
    _inherit = "product.template"

    #     return self._set_template_field('image_1920', 'image_variant_1920')

    # def _set_template_field(self, template_field, variant_field):
    #     for record in self:
    #         if (
    #             # We are trying to remove a field from the variant even though it is already
    #             # not set on the variant, remove it from the template instead.
    #             (not record[template_field] and not record[variant_field])
    #             # We are trying to add a field to the variant, but the template field is
    #             # not set, write on the template instead.
    #             or (record[template_field] and not record.product_tmpl_id[template_field])
    #             # There is only one variant, always write on the template.
    #             or self.search_count([
    #                 ('product_tmpl_id', '=', record.product_tmpl_id.id),
    #                 ('active', '=', True),
    #             ]) <= 1
    #         ):
    #             record[variant_field] = False
    #             record.product_tmpl_id[template_field] = record[template_field]
    #         else:
    #             record[variant_field] = record[template_field]

    # @api.model
    # def get_mssql_config(self, key, default_value):
    #     """Lấy thông số từ ir.config_parameter, nếu không có thì dùng giá trị mặc định"""
    #     return self.env["ir.config_parameter"].sudo().get_param(key, default_value)

    # def get_mssql_connection(self):
    #     """Lấy thông tin kết nối từ System Parameters"""
    #     server = self.get_mssql_config("mssql.server", "103.157.218.16,52021")
    #     database = self.get_mssql_config("mssql.database", "AA_augges")
    #     username = self.get_mssql_config("mssql.username", "test")
    #     password = self.get_mssql_config("mssql.password", "TT@2025")
    #     driver = self.get_mssql_config("mssql.driver", "ODBC Driver 18 for SQL Server")

    #     conn_str = f"DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password};TrustServerCertificate=yes"
    #     return pyodbc.connect(conn_str, autocommit=False)

    @api.model
    def sync_products_from_mssql_create(self):
        """Hàm đồng bộ dữ liệu sản phẩm từ MSSQL về Odoo"""
        conn = self.env['ttb.tools'].get_mssql_connection()
        cursor = conn.cursor()

        last_sync_id = int(self.env['ttb.tools'].get_mssql_config("mssql.last_synced_id", "0"))
        max_id = last_sync_id

        while True:

            # Lấy dữ liệu từ bảng sản phẩm MSSQL
            cursor.execute(f"""
                SELECT TOP 10000 
                    ID, Ma_Hang, Ma_Vach, Ten_Hang, Mo_Ta, Gia_Nhap, Gia_Ban, 
                    ID_Nhom, ID_Dvt, ID_Sx, ID_Th, Inactive, InactiveX, InactiveN,
                    Ma_VachK, Ma_Hang1, Thue, ThueV, ID_DvCs
                FROM DmH WHERE ID > {last_sync_id} ORDER BY ID ASC
            """)

            products = cursor.fetchall()
            if not products: break

            for row in products:
                ma_hang = row.Ma_Hang.strip() if row.Ma_Hang else ''
                ma_hang1 = row.Ma_Hang1.strip() if row.Ma_Hang1 else ''
                ma_vach = row.Ma_Vach.strip() if row.Ma_Vach else ''
                ma_vachk = row.Ma_VachK.strip() if row.Ma_VachK else ''
                taxes_id = self._get_sale_tax_id(float(row.Thue))
                supplier_taxes_id = self._get_tax_id(float(row.ThueV), False)
                uom_id = self.env['uom.uom']
                if row.ID_DvCs:
                    uom_id = self.env['uom.uom'].search([('id_augges', '=', int(row.ID_DvCs))], limit=1)
                _logger.info(f'Bắt đầu đồng bộ mới {row.ID} {row.Ten_Hang}')
                product_data = {
                    'augges_id': row.ID,
                    # Tạm thời đổi chỗ ma_hang, ma_vach. Sau này muốn đổi lại cho đúng có thể dùng SQL
                    'default_code': ma_vach,  # Mã nội bộ (Tạm thời comment)
                    'barcode': ma_hang,  # Mã vạch
                    'barcode_vendor': ma_hang1,
                    'barcode_k': ma_vachk,

                    'name': tcvn3_to_unicode(row.Ten_Hang),  # Chuyển mã TCVN3 sang Unicode
                    'description_sale': tcvn3_to_unicode(row.Mo_Ta),  # Chuyển mã TCVN3 sang Unicode
                    'list_price': row.Gia_Ban or 0,  # Giá bán
                    'standard_price': row.Gia_Nhap or 0,  # Giá nhập
                    # 'categ_id': self._get_category_id(row.ID_Nhom),  # Nhóm sản phẩm
                    # 'uom_id': self._get_uom_id(row.ID_Dvt),  # Không đồng bộ tạm thời
                    # 'manufacturer_id': self._get_manufacturer_id(row.ID_Sx),  # Không đồng bộ tạm thời
                    # 'brand_id': self._get_brand_id(row.ID_Th),  # Không đồng bộ tạm thời
                    'active': not bool(row.Inactive),  # Trạng thái hoạt động
                    'sale_ok': not bool(row.InactiveX),
                    'purchase_ok': not bool(row.InactiveN),
                    'uom_id': uom_id.id or self.env.ref('uom.product_uom_unit').id,
                    'uom_po_id': uom_id.id or self.env.ref('uom.product_uom_unit').id,
                    'taxes_id': [(6, 0, taxes_id)] if taxes_id else False,
                    'supplier_taxes_id': [(6, 0, supplier_taxes_id)] if supplier_taxes_id else False,
                }

                # Kiểm tra nếu sản phẩm đã tồn tại trong Odoo
                existing_product = self.sudo().with_context(active_test=False).search([("augges_id", "=", row.ID)], limit=1)

                if not existing_product:
                    self.env["product.template"].create(product_data)
                    _logger.info(f"Created new product: {row.Ten_Hang}")

                last_sync_id = max(last_sync_id, row.ID)
                # Cập nhật ID lớn nhất đã đồng bộ
                if last_sync_id - max_id > 1000:
                    self.env["ir.config_parameter"].sudo().set_param("mssql.last_synced_id", str(last_sync_id))
                    max_id = last_sync_id
                self.env.cr.commit()  # Commit từng bản ghi sau khi insert/update
            self.env["ir.config_parameter"].sudo().set_param("mssql.last_synced_id", str(last_sync_id))
            self.env.cr.commit()
        cursor.close()
        conn.close()
        _logger.info("Product sync completed successfully!")

    @api.model
    def sync_products_from_mssql_update(self, data_field=False, from_begin=False):
        """Hàm đồng bộ dữ liệu sản phẩm từ MSSQL về Odoo"""
        conn = self.env['ttb.tools'].get_mssql_connection()
        cursor = conn.cursor()

        last_updated_id = int(self.env['ttb.tools'].get_mssql_config("mssql.last_updated_id", "0")) if not from_begin else 0
        max_id = last_updated_id
        while True:
            # Lấy dữ liệu từ bảng sản phẩm MSSQL
            cursor.execute(f"""
                SELECT TOP 10000 
                    ID, Ma_Hang, Ma_Vach, Ten_Hang, Mo_Ta, Gia_Nhap, Gia_Ban, 
                    ID_Nhom, ID_Dvt, ID_Sx, ID_Th, Inactive, InactiveX, InactiveN,
                    Ma_VachK, Ma_Hang1, Thue, ThueV, ID_DvCs
                FROM DmH WHERE ID > {last_updated_id} ORDER BY ID ASC
            """)

            products = cursor.fetchall()
            if not products: break

            for row in products:
                ma_hang = row.Ma_Hang.strip() if row.Ma_Hang else ''
                ma_hang1 = row.Ma_Hang1.strip() if row.Ma_Hang1 else ''
                ma_vach = row.Ma_Vach.strip() if row.Ma_Vach else ''
                ma_vachk = row.Ma_VachK.strip() if row.Ma_VachK else ''
                taxes_id = self._get_tax_id(float(row.Thue), True)
                supplier_taxes_id = self._get_tax_id(float(row.ThueV), False)
                uom_id = self.env['uom.uom']
                if row.ID_DvCs:
                    uom_id = self.env['uom.uom'].search([('id_augges', '=', int(row.ID_DvCs))], limit=1)
                _logger.info(f'Bắt đầu đồng bộ cập nhật {row.ID} {row.Ten_Hang}')
                product_data = {
                    # Tạm thời đổi chỗ ma_hang, ma_vach. Sau này muốn đổi lại cho đúng có thể dùng SQL
                    'default_code': ma_vach,  # Mã nội bộ (Tạm thời comment)
                    'barcode': ma_hang,  # Mã vạch
                    'barcode_vendor': ma_hang1,
                    'barcode_k': ma_vachk,
                    'uom_id': uom_id.id or self.env.ref('uom.product_uom_unit').id,
                    'uom_po_id': uom_id.id or self.env.ref('uom.product_uom_unit').id,
                    'taxes_id': [(6,0, taxes_id)] if taxes_id else False,
                    'supplier_taxes_id': [(6, 0, supplier_taxes_id)] if supplier_taxes_id else False,
                    'active': not row.Inactive,
                    'name': tcvn3_to_unicode(row.Ten_Hang),
                    'list_price': row.Gia_Ban or 0,  # Giá bán
                }
                if data_field:
                    product_data_field = {}
                    for field in data_field:
                        product_data_field[field] = product_data[field]
                    product_data = product_data_field

                # Kiểm tra nếu sản phẩm đã tồn tại trong Odoo
                existing_product = self.sudo().with_context(active_test=False).search([("augges_id", "=", row.ID)], limit=1)

                if existing_product:
                    existing_product.write(product_data)
                    _logger.info(f"Updated product: {row.Ten_Hang}")

                last_updated_id = max(last_updated_id, row.ID)
                # Cập nhật ID lớn nhất đã đồng bộ
                if last_updated_id - max_id > 1000:
                    self.env["ir.config_parameter"].sudo().set_param("mssql.last_updated_id", str(last_updated_id))
                    max_id = last_updated_id
                self.env.cr.commit()  # Commit từng bản ghi sau khi insert/update

        cursor.close()
        conn.close()
        _logger.info("Product update completed successfully!")

    @api.model
    def sync_products_from_mssql_update_from_to(self, data_field=False, id_from=1, id_to=1):
        """Hàm đồng bộ dữ liệu sản phẩm từ MSSQL về Odoo"""
        conn = self.env['ttb.tools'].get_mssql_connection()
        cursor = conn.cursor()

        # last_updated_id = int(self.get_mssql_config("mssql.last_updated_id", "0")) if not from_begin else 0
        # max_id = last_updated_id
        while True:
            # Lấy dữ liệu từ bảng sản phẩm MSSQL
            cursor.execute(f"""
                SELECT 
                    ID, Ma_Hang, Ma_Vach, Ten_Hang, Mo_Ta, Gia_Nhap, Gia_Ban, 
                    ID_Nhom, ID_Dvt, ID_Sx, ID_Th, Inactive, InactiveX, InactiveN,
                    Ma_VachK, Ma_Hang1, Thue, ThueV, ID_DvCs
                FROM DmH WHERE ID >= {id_from} and ID <= {id_to} ORDER BY ID ASC
            """)

            products = cursor.fetchall()
            if not products: break

            for row in products:
                ma_hang = row.Ma_Hang.strip() if row.Ma_Hang else ''
                ma_hang1 = row.Ma_Hang1.strip() if row.Ma_Hang1 else ''
                ma_vach = row.Ma_Vach.strip() if row.Ma_Vach else ''
                ma_vachk = row.Ma_VachK.strip() if row.Ma_VachK else ''
                # taxes_id = self._get_tax_id(float(row.Thue), True)
                taxes_id = self._get_sale_tax_id(float(row.Thue))
                supplier_taxes_id = self._get_tax_id(float(row.ThueV), False)
                uom_id = self.env['uom.uom']
                if row.ID_DvCs:
                    uom_id = self.env['uom.uom'].search([('id_augges', '=', int(row.ID_DvCs))], limit=1)
                _logger.info(f'Bắt đầu đồng bộ cập nhật {row.ID} {row.Ten_Hang}')
                product_data = {
                    # Tạm thời đổi chỗ ma_hang, ma_vach. Sau này muốn đổi lại cho đúng có thể dùng SQL
                    'default_code': ma_vach,  # Mã nội bộ (Tạm thời comment)
                    'barcode': ma_hang,  # Mã vạch
                    'barcode_vendor': ma_hang1,
                    'barcode_k': ma_vachk,
                    'uom_id': uom_id.id or self.env.ref('uom.product_uom_unit').id,
                    'uom_po_id': uom_id.id or self.env.ref('uom.product_uom_unit').id,
                    'taxes_id': [(6,0, taxes_id)] if taxes_id else False,
                    'supplier_taxes_id': [(6, 0, supplier_taxes_id)] if supplier_taxes_id else False,
                    'active': not row.Inactive,
                    'name': tcvn3_to_unicode(row.Ten_Hang),
                    'list_price': row.Gia_Ban or 0,  # Giá bán
                }
                if data_field:
                    product_data_field = {}
                    for field in data_field:
                        product_data_field[field] = product_data[field]
                    product_data = product_data_field

                # Kiểm tra nếu sản phẩm đã tồn tại trong Odoo
                existing_product = self.sudo().with_context(active_test=False).search([("augges_id", "=", row.ID)], limit=1)

                if existing_product:
                    existing_product.write(product_data)
                    _logger.info(f"Updated product: {row.Ten_Hang}")

                # last_updated_id = max(last_updated_id, row.ID)
                # Cập nhật ID lớn nhất đã đồng bộ
                # if last_updated_id - max_id > 1000:
                #     self.env["ir.config_parameter"].sudo().set_param("mssql.last_updated_id", str(last_updated_id))
                #     max_id = last_updated_id
                self.env.cr.commit()  # Commit từng bản ghi sau khi insert/update
            break
        cursor.close()
        conn.close()
        _logger.info("Product update completed successfully!")


    @api.model
    def sync_products_from_mssql_update_by_code(self, data_field=False, barcode=''):
        """Hàm đồng bộ dữ liệu sản phẩm từ MSSQL về Odoo"""
        conn = self.env['ttb.tools'].get_mssql_connection()
        cursor = conn.cursor()

        # last_updated_id = int(self.get_mssql_config("mssql.last_updated_id", "0")) if not from_begin else 0
        # max_id = last_updated_id
        while True:
            # Lấy dữ liệu từ bảng sản phẩm MSSQL
            cursor.execute(f"""
                SELECT 
                    ID, Ma_Hang, Ma_Vach, Ten_Hang, Mo_Ta, Gia_Nhap, Gia_Ban, 
                    ID_Nhom, ID_Dvt, ID_Sx, ID_Th, Inactive, InactiveX, InactiveN,
                    Ma_VachK, Ma_Hang1, Thue, ThueV, ID_DvCs
                FROM DmH WHERE Ma_Vach like '%{barcode}%' 
                   OR Ma_Hang like '%{barcode}%' 
                   OR Ma_Hang1 like '%{barcode}%' 
                   OR Ma_VachK like '%{barcode}%';
            """)

            products = cursor.fetchall()
            if not products: break

            for row in products:
                ma_hang = row.Ma_Hang.strip() if row.Ma_Hang else ''
                ma_hang1 = row.Ma_Hang1.strip() if row.Ma_Hang1 else ''
                ma_vach = row.Ma_Vach.strip() if row.Ma_Vach else ''
                ma_vachk = row.Ma_VachK.strip() if row.Ma_VachK else ''
                taxes_id = self._get_tax_id(float(row.Thue), True)
                supplier_taxes_id = self._get_tax_id(float(row.ThueV), False)
                uom_id = self.env['uom.uom']
                if row.ID_DvCs:
                    uom_id = self.env['uom.uom'].search([('id_augges', '=', int(row.ID_DvCs))], limit=1)
                _logger.info(f'Bắt đầu đồng bộ cập nhật {row.ID} {row.Ten_Hang}')
                product_data = {
                    # Tạm thời đổi chỗ ma_hang, ma_vach. Sau này muốn đổi lại cho đúng có thể dùng SQL
                    'default_code': ma_vach,  # Mã nội bộ (Tạm thời comment)
                    'barcode': ma_hang,  # Mã vạch
                    'barcode_vendor': ma_hang1,
                    'barcode_k': ma_vachk,
                    'uom_id': uom_id.id or self.env.ref('uom.product_uom_unit').id,
                    'uom_po_id': uom_id.id or self.env.ref('uom.product_uom_unit').id,
                    'taxes_id': [(6,0, taxes_id)] if taxes_id else False,
                    'supplier_taxes_id': [(6, 0, supplier_taxes_id)] if supplier_taxes_id else False,
                    'active': not row.Inactive,
                    'name': tcvn3_to_unicode(row.Ten_Hang),
                    'list_price': row.Gia_Ban or 0,  # Giá bán
                }
                if data_field:
                    product_data_field = {}
                    for field in data_field:
                        product_data_field[field] = product_data[field]
                    product_data = product_data_field

                # Kiểm tra nếu sản phẩm đã tồn tại trong Odoo
                existing_product = self.sudo().with_context(active_test=False).search([("augges_id", "=", row.ID)], limit=1)

                if existing_product:
                    existing_product.write(product_data)
                    _logger.info(f"Updated product: {row.Ten_Hang}")

                # last_updated_id = max(last_updated_id, row.ID)
                # Cập nhật ID lớn nhất đã đồng bộ
                # if last_updated_id - max_id > 1000:
                #     self.env["ir.config_parameter"].sudo().set_param("mssql.last_updated_id", str(last_updated_id))
                #     max_id = last_updated_id
                self.env.cr.commit()  # Commit từng bản ghi sau khi insert/update
            break
        cursor.close()
        conn.close()
        _logger.info("Product update completed successfully!")
        

    def _get_uom_id(self, uom_id):
        """Tìm hoặc tạo đơn vị tính"""
        if not uom_id:
            return False
        uom = self.env["uom.uom"].search([("augges_id", "=", uom_id)], limit=1)
        if not uom:
            uom = self.env["uom.uom"].create({
                "name": f"Đơn vị {uom_id}",
                "augges_id": uom_id,
            })
        return uom.id

    def _get_manufacturer_id(self, manufacturer_id):
        """Tìm hoặc tạo nhà sản xuất"""
        if not manufacturer_id:
            return False
        manufacturer = self.env["res.partner"].search([("augges_id", "=", manufacturer_id)], limit=1)
        if not manufacturer:
            manufacturer = self.env["res.partner"].create({
                "name": f"Nhà sản xuất {manufacturer_id}",
                "augges_id": manufacturer_id,
            })
        return manufacturer.id

    def _get_brand_id(self, brand_id):
        """Tìm hoặc tạo thương hiệu"""
        if not brand_id:
            return False
        brand = self.env["product.brand"].search([("augges_id", "=", brand_id)], limit=1)
        if not brand:
            brand = self.env["product.brand"].create({
                "name": f"Thương hiệu {brand_id}",
                "augges_id": brand_id,
            })
        return brand.id

    def _get_sale_tax_id(self, tax):
        # KCT
        if tax < 0:
            return [15]
        
        tax_ids = self.env['account.tax'].sudo().search([
            ('amount', '=', tax),
            ('type_tax_use', '=', 'sale'),
            ('amount_type', '=', 'percent'),
            ('price_include_override', '=', 'tax_included')
        ], limit=1)
        if not tax_ids:
            raise UserError('Chưa đồng bộ Thuế Augges về Odoo. Thuế: %s' % tax)
        return tax_ids.ids

    def _get_tax_id(self, tax, is_sale=True):
        if is_sale:
            return self._get_sale_tax_id(tax)

        # KCT
        if tax == -1:
            return [5]
        if tax < -1:
            return False

        if tax == 0:
            return [4]
        if tax == 5:
            return [3]
        if tax == 8:
            return [2]
        if tax == 10:
            return [1]

        return False


        # if not tax:
        #     return False
        # ma_thue = thue_ra if is_sale else thue_vao
        # tax = self.env['account.tax'].sudo().search([('amount', '=', tax), ('ma_thue_augges', 'in', ma_thue)], limit=1)
        # return tax.ids
