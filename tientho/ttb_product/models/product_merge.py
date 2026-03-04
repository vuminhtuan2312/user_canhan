from odoo import fields, models, api
from datetime import datetime, timedelta

from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class ProductMerge(models.Model):
    _name = 'product.merge'
    _description = 'Ghép sản phẩm'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    product_a_id = fields.Many2one('product.template', string='Sản phẩm đích (A)', required=True, help='Sản phẩm đích sẽ nhận thông tin từ (B)')
    product_b_id = fields.Many2one('product.template', string='Sản phẩm bị ghép (B)', required=True, help='Sản phẩm nguồn sẽ được gộp (B)')
    barcode_a = fields.Char(string='Mã vạch A')
    default_code_a = fields.Char(string='Mã hàng A')
    default_code_b = fields.Char(string='Mã hàng B')
    barcode_b = fields.Char(string='Mã vạch B')
    state = fields.Selection([
        ('new', 'Mới'),
        ('merged', 'Đã merge'),
    ], string='Trạng thái', default='new', readonly=True, tracking=True)
    date_merge = fields.Datetime(string='Thời gian merge', readonly=True)
    merge_detail_id = fields.One2many(string='Merge Detail ID', comodel_name='product.merge.detail', inverse_name='merge_id')

    def unlink(self):
        for rec in self:
            if rec.state != 'new':
                raise UserError('Không thể xóa bản ghi đã merge sản phẩm')
        return super().unlink()

    def action_merge(self):
        for rec in self:
            product_a = rec.product_a_id
            product_b = rec.product_b_id
            TtbAugges = self.env['ttb.augges']
            if not product_a.augges_id and not product_b.augges_id:
                raise UserError("Thiếu Augges ID trong sản phẩm A hoặc B.")

            # Kết nối đến augges_id
            conn = self.env['ttb.tools'].get_mssql_connection_send()
            cursor = conn.cursor()
            try:
                id_a = product_a.augges_id
                id_b = product_b.augges_id
                field_list = [
                    'ID', 'Ma_Vach', 'Gia_Ban', 'Ma_Hang', 'Ma_Hang1', 'Ma_VachK',
                    'Gia_Ban1', 'Gia_Ban2', 'Gia_Ban3', 'Gia_Ban4', 'Gia_Ban5', 'Gia_Ban6',
                    'Gia_Ban7', 'Gia_Ban8', 'Gia_Ban9', 'Gia_Ban10', 'Gia_Ban11', 'Gia_Ban12'
                ]

                data_a_list = TtbAugges.get_records_by_id('Dmh', id_a, field_list, conn)
                data_a = data_a_list[0] if data_a_list else {}

                data_b_list = TtbAugges.get_records_by_id('Dmh', id_b, field_list, conn)
                data_b = data_b_list[0] if data_b_list else {}

                if not data_a or not data_b:
                    raise UserError("Không tìm thấy dữ liệu cho A hoặc B trong Dmh.")

                ma_vach_k_a = data_a.get('ma_vachk') or ''
                ma_hang_a = data_a.get('ma_hang') or ''
                ma_vach_k_b = data_b.get('ma_vachk') or ''
                ma_vach_b = data_b.get('ma_vach') or ''
                ma_hang_b = data_b.get('ma_hang') or ''
                ma_hang_1_b = data_b.get('ma_hang1') or ''
                gia_ban_a = float(data_a.get('gia_ban') or 0)
                gia_ban_a_1 = float(data_a.get('gia_ban1') or 0)
                gia_ban_a_2 = float(data_a.get('gia_ban2') or 0)
                gia_ban_a_3 = float(data_a.get('gia_ban3') or 0)
                gia_ban_a_4 = float(data_a.get('gia_ban4') or 0)
                gia_ban_a_5 = float(data_a.get('gia_ban5') or 0)
                gia_ban_a_6 = float(data_a.get('gia_ban6') or 0)
                gia_ban_a_7 = float(data_a.get('gia_ban7') or 0)
                gia_ban_a_8 = float(data_a.get('gia_ban8') or 0)
                gia_ban_a_9 = float(data_a.get('gia_ban9') or 0)
                gia_ban_a_10 = float(data_a.get('gia_ban10') or 0)
                gia_ban_a_11 = float(data_a.get('gia_ban11') or 0)
                gia_ban_a_12 = float(data_a.get('gia_ban12') or 0)
                gia_ban_b = float(data_b.get('gia_ban') or 0)
                gia_ban_b_1 = float(data_b.get('gia_ban1') or 0)
                gia_ban_b_2 = float(data_b.get('gia_ban2') or 0)
                gia_ban_b_3 = float(data_b.get('gia_ban3') or 0)
                gia_ban_b_4 = float(data_b.get('gia_ban4') or 0)
                gia_ban_b_5 = float(data_b.get('gia_ban5') or 0)
                gia_ban_b_6 = float(data_b.get('gia_ban6') or 0)
                gia_ban_b_7 = float(data_b.get('gia_ban7') or 0)
                gia_ban_b_8 = float(data_b.get('gia_ban8') or 0)
                gia_ban_b_9 = float(data_b.get('gia_ban9') or 0)
                gia_ban_b_10 = float(data_b.get('gia_ban10') or 0)
                gia_ban_b_11 = float(data_b.get('gia_ban11') or 0)
                gia_ban_b_12 = float(data_b.get('gia_ban12') or 0)

                merged_list = list(filter(None, [
                    ma_vach_k_a,
                    ma_hang_b,
                    ma_vach_b,
                    ma_vach_k_b,
                    ma_hang_1_b
                ]))

                # Loại bỏ mã trùng
                unique_codes = list(dict.fromkeys([code.strip() for code in ','.join(merged_list).split(',') if code.strip()]))

                merged_code = ','.join(unique_codes)

                # Cập nhật sản phẩm A
                TtbAugges.update_record(
                    table_name='DmH',
                    data={
                        'Ma_VachK': merged_code,
                        'Gia_Ban': min(gia_ban_a,gia_ban_b),
                        'Gia_Ban1': min(gia_ban_a_1,gia_ban_b_1),
                        'Gia_Ban2': min(gia_ban_a_2, gia_ban_b_2),
                        'Gia_Ban3': min(gia_ban_a_3, gia_ban_b_3),
                        'Gia_Ban4': min(gia_ban_a_4, gia_ban_b_4),
                        'Gia_Ban5': min(gia_ban_a_5, gia_ban_b_5),
                        'Gia_Ban6': min(gia_ban_a_6, gia_ban_b_6),
                        'Gia_Ban7': min(gia_ban_a_7, gia_ban_b_7),
                        'Gia_Ban8': min(gia_ban_a_8, gia_ban_b_8),
                        'Gia_Ban9': min(gia_ban_a_9, gia_ban_b_9),
                        'Gia_Ban10': min(gia_ban_a_10, gia_ban_b_10),
                        'Gia_Ban11': min(gia_ban_a_11, gia_ban_b_11),
                        'Gia_Ban12': min(gia_ban_a_12, gia_ban_b_12),
                    },
                    record_id=id_a,
                    pair_conn=conn
                )

                if merged_code:
                    list_codes = [c.strip() for c in merged_code.split(',') if c.strip()]
                    for code in list_codes:
                        # Kiểm tra mã đã tồn tại hay chưa
                        cursor.execute("SELECT COUNT(*) FROM Dmhmv WHERE Ma_Vach = ? AND ID_Hang = ?", (code, id_a))
                        exists = cursor.fetchone()[0]

                        odoo_login = self.env.user.login

                        user_data = TtbAugges.get_records(
                            table='DmUser',
                            domain=f"LogName = '{odoo_login}'",
                            field_list=['ID'],
                            get_dict=True,
                            pair_conn=conn
                        )
                        if not user_data:
                            raise UserError(f"Không tìm thấy người dùng Augges với LogName = {odoo_login}")
                        user_id = user_data[0]['id']
                        insert_date = datetime.utcnow() + timedelta(hours=7)

                        if not exists:
                            TtbAugges.insert_record(
                                table_name='Dmhmv',
                                data={
                                    'Ma_Vach': code,
                                    'ID_Hang': id_a,
                                    'UserID': user_id,
                                    'InsertDate': insert_date,
                                    'LastEdit': fields.Datetime.now()
                                },
                                pair_conn=conn,
                                get_id=False,
                                auto_id=True
                            )

                        # Cập nhật sản phẩm B
                        def add_merged_suffix(code):
                            if not code:
                                return code
                            codes = [c.strip() for c in code.split(',') if c.strip()]
                            updated_codes = []
                            for c in codes:
                                if len(c) > 2:
                                    updated_codes.append(f"{c[0]}merged{c[1:-1]}merged{c[-1]}")
                                else:
                                    updated_codes.append(f"{c}merged")
                            return ','.join(updated_codes)

                        updated_b = {
                            'Ma_Vach': add_merged_suffix(ma_vach_b),
                            'Ma_Hang': add_merged_suffix(ma_hang_b),
                            'Ma_Hang1': add_merged_suffix(ma_hang_1_b),
                            'Ma_VachK': add_merged_suffix(ma_vach_k_b),
                            'Inactive': 1,
                            'Ghi_Chu': f"Đã ghép vào mã hàng {ma_hang_a}",
                        }
                        TtbAugges.update_record(
                            table_name='Dmh',
                            data=updated_b,
                            record_id=id_b,
                            pair_conn=conn
                        )
                        self._update_related_augges_records(rec, cursor, id_a, id_b)
                self._update_related_odoo_records(rec, product_a, product_b)

                rec.write({
                    'state': 'merged',
                    'date_merge': fields.Datetime.now(),
                    'barcode_a': product_a.barcode,
                    'default_code_a': product_a.default_code,
                    'barcode_b': product_b.barcode,
                    'default_code_b': product_b.default_code
                })

                conn.commit()
                _logger.info(f"Đã merge thành công sản phẩm B(ID={id_b}) vào A(ID={id_a})")
            except Exception as e:
                conn.rollback()
                self.env.cr.rollback()
                raise UserError(f"Lỗi khi merge: {e}")

            finally:
                cursor.close()
                conn.close()

    def _update_related_augges_records(self, rec, cursor, id_a, id_b):
        ProductMergeDetail = self.env['product.merge.detail']
        augges_tables = ['SlBlD', 'SlNxD', 'SlDcD', 'SlBlSD', 'SlNxSD', 'SlDcSD', 'HtK']

        for table in augges_tables:
            # Lấy danh sách record bị ảnh hưởng trước khi cập nhật
            cursor.execute(f"SELECT ID, ID_Hang FROM {table} WHERE ID_Hang = ?", id_b)
            rows = cursor.fetchall()

            cursor.execute(f"UPDATE {table} SET ID_Hang = ? WHERE ID_Hang = ?", (id_a, id_b))

            for row in rows:
                record_id = row[0]
                old_value = row[1]

                ProductMergeDetail.create({
                    'merge_id': rec.id,
                    'merge_type': 'augges',
                    'target_model': table,
                    'record_id': record_id,
                    'update_field': 'ID_Hang',
                    'old_value': old_value,
                    'new_value': id_a,
                    'extra_info': ''
                })

    def _update_related_odoo_records(self, rec, product_a, product_b):
        cr = self.env.cr

        product_a_variant = product_a.product_variant_id
        product_b_variant = product_b.product_variant_id

        if not product_a_variant or not product_b_variant:
            raise UserError("Sản phẩm A hoặc B không có product variant")

        product_a_id = product_a_variant.id
        product_b_id = product_b_variant.id

        ProductMergeDetail = self.env['product.merge.detail']

        odoo_tables = [
            'purchase_order_line',
            'pos_order_line',
            'stock_move',
            'stock_move_line',
            'account_move_line',
            'stock_quant'
        ]
        try:
            for table in odoo_tables:
                #Lấy danh sách các record bị ảnh hưởng
                cr.execute(f"SELECT id FROM {table} WHERE product_id = %s", (product_b_id,))
                ids = [r[0] for r in cr.fetchall()]

                cr.execute(f"""UPDATE {table} SET product_id = %s WHERE product_id = %s""", (product_a_id, product_b_id))
                _logger.info(f"Merge {cr.rowcount} dòng được cập nhật trong bảng {table}")

                for record_id in ids:
                    ProductMergeDetail.create({
                        'merge_id': rec.id,
                        'merge_type': 'odoo',
                        'target_model': table,
                        'record_id': record_id,
                        'update_field': 'product_id',
                        'old_value': product_b_id,
                        'new_value': product_a_id,
                        'extra_info': ''
                    })
            cr.commit()
        except Exception as e:
            cr.rollback()
            _logger.exception("Lỗi khi cập nhật product_id trên Odoo: %s", str(e))
            raise UserError(f"Lỗi khi cập nhật Odoo: {e}")
