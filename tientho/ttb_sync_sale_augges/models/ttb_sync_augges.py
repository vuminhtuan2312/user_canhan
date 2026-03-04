from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.addons.ttb_tools.models.ttb_tcvn3 import tcvn3_to_unicode
import datetime
import math
from datetime import timedelta
import pyodbc
import logging
_logger = logging.getLogger(__name__)
import ast

class SyncAuggesPending(models.Model):
    _name = 'ttb.sync.augges.pending'
    _description = 'Các ID có ở augges nhưng chưa đồng bộ về Odoo'

    augges_id = fields.Integer('ID đơn Augges')
    finish_state = fields.Integer(string='0: pending, 1: sync again', default=0)
    insert_date = fields.Datetime('Ngày tạo Augges', default=fields.Datetime.now)



class TtbSyncAugges(models.Model):
    _name = "ttb.sync.augges"
    _description = "Đồng bộ hệ thống Augges"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    def _get_pos_points_from_augges(self, conn, cursor, pos_id):
        """
        Lấy tổng điểm tích và điểm tiêu cho 1 đơn POS trên Augges (SlBlD.ID / SlBlM.ID).
        Điểm tích  = floor( So_Tien * (Tyle_DS / 100) )
        Điểm tiêu  = Diem_Tt (trên SlBlM)
        return (point_earn, point_spent)
        """
        if not pos_id:
            return 0.0, 0.0

        # Lấy So_Tien và Tyle_Ds
        sql_sum = """
            SELECT 
                SUM(
                    CASE 
                        WHEN SlBlD.ID_Hang IS NOT NULL 
                        THEN SlBlD.T_Tien 
                             - (ISNULL(SlBlD.Tien_Giam, 0)
                                + ISNULL(SlBlD.Tien_Ck, 0)
                                - SlBlD.CK_TheMg)
                        ELSE CAST(0 AS money)
                    END
                ) AS So_Tien,
                ISNULL(SlBlM.Tyle_DS, ISNULL(DmLTheCkDs.Tyle_Ds, ISNULL(DmLThe.Tyle_Ds, 0))) AS Tyle_Ds
            FROM SlBlD
                LEFT JOIN SlBlM ON SlBlD.ID       = SlBlM.ID
                LEFT JOIN DmThe  ON SlBlM.ID_The  = DmThe.ID
                LEFT JOIN DmLThe ON SlBlM.ID_LThe = DmLThe.ID
                LEFT JOIN DmH    ON SlBlD.ID_Hang = DmH.ID
                LEFT JOIN DmLTheCkDs 
                       ON SlBlM.ID_LThe = DmLTheCkDs.ID_LThe 
                      AND DmH.ID_Nhom   = DmLTheCkDs.ID_Nhom
            WHERE 
                SlBlM.ID_Dv >= 0
                AND SlBlD.Hs_Qd <> 'THEMG'
                AND SlBlD.ID = ?
            GROUP BY 
                SlBlD.Sngay,
                SlBlM.ID, 
                SlBlM.ID_The, 
                SlBlM.ID_LThe,
                ISNULL(SlBlM.Tyle_DS, ISNULL(DmLTheCkDs.Tyle_Ds, ISNULL(DmLThe.Tyle_Ds, 0)))
        """

        cursor.execute(sql_sum, (int(pos_id),))
        row1 = cursor.fetchone()
        if not row1:
            return 0.0, 0.0

        # pyodbc xử lý: có thể truy cập theo tên
        so_tien = float(row1.So_Tien or 0.0)
        tyle_ds = float(row1.Tyle_Ds or 0.0)

        # Điểm tích = floor( (So_Tien * (Tyle_Ds / 100)) /1000)
        point_earn = math.floor((so_tien * (tyle_ds / 100))/1000) if tyle_ds else 0.0

        # 2) Lấy Diem_Tt (điểm tiêu)
        sql_diem_tt = """
            SELECT 
                ISNULL(MAX(SlBlM.Diem_Tt), 0) AS Diem_Tt
            FROM SlBlD
                JOIN SlBlM ON SlBlM.ID = SlBlD.ID
            WHERE SlBlD.ID = ?
            GROUP BY SlBlD.ID, SlBlM.Diem_Tt
        """
        cursor.execute(sql_diem_tt, (int(pos_id),))
        row2 = cursor.fetchone()
        point_spent = float(row2.Diem_Tt or 0.0) if row2 else 0.0

        return point_earn, point_spent


    def get_tax_ids(self, augges_id, product_id):
        """
        Thay đổi ngày 29/5: Bỏ qua logic tự điền thuế. Để lại nguyên gốc thuế của Augges đã điền.
        Ở chức năng xuất hddt sẽ có chức năng hiện đơn thiếu thuế.
        """
        tax_ids = self.env["account.tax"]
        if augges_id:
            try:
                augges_id_int = int(augges_id)
                tax_ids = self.env["account.tax"].sudo().with_context(active_test=False).search([("id_augges", "=", augges_id_int)], limit=1)
            except:
                pass
            if not tax_ids:
                _logger.info('Không tìm thấy thuế tương ứng trên Odoo, ID Thuế Augges: %s' % augges_id)
                raise UserError('Không tìm thấy thuế tương ứng trên Odoo, ID Thuế Augges: %s' % augges_id)
            return tax_ids
        return tax_ids

        # # _logger.info('Đơn augges ko có thuế')
        # if not tax_ids:
        #     tax_ids = product_id.taxes_id

        # # _logger.info('Sản phẩm không có thuế')
        # if not tax_ids:
        #     tax_ids = self.env["account.tax"].sudo().search([
        #         ('type_tax_use', '=', 'sale'),
        #         ('amount', '=', 10),
        #         ('price_include_override', '=', 'tax_included'),
        #     ], limit=1)
        #     if not tax_ids:
        #         tax_ids = self.env["account.tax"].sudo().create({
        #             'name': 'Thuế bán hàng 10% (hệ thống tự tạo)',
        #             'type_tax_use': 'sale',
        #             'amount': 10,
        #             'price_include_override': 'tax_included',
        #         })
        # return tax_ids

    def check_ok(self, tien_hang, amount_total):
        return abs(tien_hang - amount_total) < 1

    def calculate_discount(self, line, order_discount_plus):
        """
        Tính % chiết khấu của line
        """
        amount_origin = float(line['T_Tien'])
        if amount_origin == 0:
            return 0

        tien_ck = float(line.get('Tien_CK', 0)) + float(line.get('Tien_Giam', 0))
        tien_ck_them = order_discount_plus * (amount_origin - tien_ck)

        return ((tien_ck + tien_ck_them) / amount_origin) * 100

    def get_lines(self, order_data, cursor_line, row_id, raise_exception=False, tien_hang=None):
        # Lấy thông tin THẺ từ master SlBlM (để biết có THECK cấp đơn)
        cursor_line.execute(f"""
                SELECT ID_The, ID_LThe
                FROM dbo.SlBlM
                WHERE ID = {row_id}
            """)
        m_row = cursor_line.fetchone()
        m_id_the = m_row[0] if m_row else None
        m_id_lthe = m_row[1] if m_row else None
        order_has_card_discount = bool(m_id_the or m_id_lthe)

        # Lấy các dòng chi tiết từ SlBlD (KHÔNG join tên)
        cursor_line.execute(f"""
            SELECT ID, ID_L, Stt, ID_Hang, So_Luong, Gia_Ban, Don_Gia, TyLe_Giam, Tien_Giam, Tien_CK, T_Tien, CK_The, CK_TheMg, Thue, Tien_GtGt, No_Tk, Gia_Kvat, ID_Thue, ID_CSB, ID_The 
            FROM dbo.SLBLD 
            WHERE ID = {row_id}
                and Md not in (2, 7)
            -- and ID_Hang is not null
        """)
        result = [column[0] for column in cursor_line.description]
        result_line = [dict(zip(result, row)) for row in cursor_line.fetchall()]

        # B1. Tính tổng chiết khấu và tổng chiết khấu đã phân bổ
        tong_ck = 0
        tong_ck_da_phan_bo = 0
        # Đoạn này tính chiết khấu thì tính luôn loại chiết khấu.
        # version 1: Loại chiết khấu điền chung cho tất cả các dòng đơn hàng
        for line in result_line:
            if line['ID_Hang']:
                tong_ck_da_phan_bo += float(line['Tien_Giam'] or 0) + float(line['Tien_CK'] or 0)
            else:
                tong_ck += float(line['T_Tien'] or 0)

        if abs(tong_ck) > abs(tien_hang):
            tong_ck = tien_hang
        if abs(tong_ck_da_phan_bo) > abs(tien_hang):
            tong_ck_da_phan_bo = tien_hang
        
        tong_ck_chua_phan_bo = tong_ck - tong_ck_da_phan_bo
        tien_hang_sau_phan_bo = tien_hang - tong_ck_da_phan_bo

        # Chiết khấu bổ sung bằng [Chiết khấu chưa phân bổ] / [Tiền hàng sau phân bổ]
        order_discount_plus = tong_ck_chua_phan_bo / tien_hang_sau_phan_bo if tien_hang_sau_phan_bo != 0 else 0

        order_line = [[5,0,0]]
        augges_no_tk = False
        for line in result_line:
            if not line['ID_Hang']: continue

            product_template_id = self.env['product.template'].with_context(active_test=False).sudo().search([('augges_id', '=', line['ID_Hang'])], limit=1)
            if not product_template_id:
                if raise_exception:
                    raise UserError('Đồng bộ POS - Không tìm thấy sản phẩm, ID_Hang: %s' % line['ID_Hang'])
                _logger.info('Đồng bộ POS - Không tìm thấy sản phẩm, ID_Hang: %s', line['ID_Hang'])
                continue
            product_id = self.env['product.product'].with_context(active_test=False).sudo().search([('product_tmpl_id', '=', product_template_id.id)], limit=1)
            if not product_id:
                if raise_exception:
                    raise UserError('Đồng bộ POS - Odoo Không tìm thấy sản phẩm (product.product), ID_Hang: %s' % line['ID_Hang'])
                _logger.info('Đồng bộ POS - Odoo Không tìm thấy sản phẩm (product.product), ID_Hang: %s', line['ID_Hang'])
                continue
            # lưu ý những đơn 2021 thì không có id thuế, ko map được thuế
            tax_ids = self.get_tax_ids(line.get("ID_Thue"), product_id)
            discount = 0
            tien_ck = float(line.get('Tien_CK', 0)) + float(line.get('Tien_Giam', 0))
            amount_origin = float(line['T_Tien'])
            if not float(line['So_Luong']):
                _logger.info('Đồng bộ POS - Bỏ qua line ko số lượng, ID, STT: %s', line['ID'], line['Stt'])
                continue
            if order_discount_plus != 0:
                _logger.info('Chiết khấu chưa phân bổ hết. Đơn: %s, ID_Hang: %s', line['ID'], line['ID_Hang'])
                discount = self.calculate_discount(line, order_discount_plus)
            elif tien_ck and amount_origin:
                discount = tien_ck/amount_origin * 100

            line_tk = line.get('No_Tk', False)
            if not augges_no_tk:
                augges_no_tk = line_tk
            elif augges_no_tk != line_tk:
                _logger.info('Đồng bộ POS tk các line khác nhau, row_id: %s, tk1: %s, tk2: %s', row_id, augges_no_tk, line_tk)

            # Gắn nhãn CTKM (text) cho TỪNG DÒNG
            labels = []
            # CSB theo dòng
            if line.get('ID_CSB'):
                labels.append('CSB')
            # Chiết khấu thẻ: nếu cấp đơn hoặc cấp dòng có ID_The
            if order_has_card_discount or line.get('ID_The'):
                labels.append('THECK')

            promo_text = ', '.join(labels) if labels else False
            order_line.append((0, 0, {'name': f'{product_id.name}/AUGGES/{line["ID"]}/{line["Stt"]}',
                         'product_id': product_id.id,
                         'price_unit': float(line['T_Tien'])/float(line['So_Luong']),
                         'qty': float(line['So_Luong']),
                         'price_subtotal': 1,
                         'price_subtotal_incl': 1,
                         'augges_no_tk': line.get('No_Tk', False),
                         'discount': discount,
                         'tax_ids': [(6, 0, tax_ids.ids)],
                         'promotion_program_name': promo_text,
                         }))
        order_data['lines'] = order_line
        order_data['augges_no_tk'] = augges_no_tk or ''
        return order_data

    @api.model
    def sync_orders_from_mssql_create(self, 
            number_sync=5, reset=False, date_from=False, augges_ids=False, config_name='mssql.last_synced_order_id', 
            sync_hdt=True, sync_normal=True, create_order=True, write_order=True, date_to=False, id_from=False, id_to=False, printed_only=True, write_check=True):
        """Hàm đồng bộ đơn hàng từ MSSQL về Odoo"""
        conn = self.env['ttb.tools'].get_mssql_connection()
        cursor = conn.cursor()
        last_synced_id = int(self.env['ttb.tools'].get_mssql_config(config_name, "0"))
        max_id = 0 if reset else last_synced_id
        count_sync = 0
        currency_id = self.env.company.currency_id
        warehouse_augges = self.env['stock.warehouse'].search([('code', '=', 'AUG')], limit=1)
        if not warehouse_augges:
            warehouse_augges = self.env['stock.warehouse'].create({'code': 'AUG', 'name': 'Kho AUG'})
        session_id = self.env['pos.session'].sudo().search([('config_id.warehouse_id', '=', warehouse_augges.id), ('state', '!=', 'closed')], limit=1)
        if not session_id:
            pos_config = self.env['pos.config'].sudo().search([('warehouse_id', '=', warehouse_augges.id)], limit=1)
            if not pos_config:
                pos_config = self.env['pos.config'].sudo().create({'name': f'POS-{warehouse_augges.display_name}','warehouse_id': warehouse_augges.id, 'picking_type_id': warehouse_augges.pos_type_id.id})
            session_id = self.env['pos.session'].sudo().create({'config_id': pos_config.id})
        invoice_partner_id = self.env['ir.config_parameter'].sudo().get_param('ttb_purchase_invoice_stock.invoice_partner_id')
        while True:
            if number_sync and count_sync > number_sync: break
            count_sync += 1
            
            sql_augges_ids = f"""and SLBLM.ID in ({', '.join(str(x) for x in augges_ids)}) """ if augges_ids else ''
            sql_id_from = f" AND ID >= {id_from}" if id_from else ""
            sql_id_to = f" AND ID <= {id_to}" if id_to else ""
            sql_date_from = f"""and SLBLM.InsertDate >= '{date_from}' """ if date_from else ''
            sql_date_to = f"""and SLBLM.InsertDate <= '{date_to}' """ if date_to else ''

            cursor.execute(f"""SELECT TOP 10000
                               SLBLM.ID, SLBLM.ID_Kho, SLBLM.Sp, SLBLM.Quay, SLBLM.Tien_Hang, SLBLM.Tien_CK, SLBLM.Tien_Giam, SLBLM.Tien_GtGt, SLBLM.InsertDate, dmkho.Ma_kho, SLBLM.Printed
                               FROM SLBLM
                               LEFT JOIN dmkho on SLBLM.ID_Kho = dmkho.ID 
                               WHERE SLBLM.ID > {max_id} and SLBLM.ID_Kho is not null 
                               AND SlBlM.InsertDate < DATEADD(SECOND, -10, GETDATE())
                               {sql_augges_ids}
                               {sql_id_from} {sql_id_to}
                               {sql_date_from} {sql_date_to}
                               ORDER BY SLBLM.ID ASC""")
            columns = [column[0] for column in cursor.description]
            orders = [dict(zip(columns, row)) for row in cursor.fetchall()]

            if not orders: break
            
            #Ghi các đơn gọi lại vào thông số => Sau đó sẽ có 1 job lấy ra gọi lại
            for row in orders:
                if not augges_ids:
                    max_id = max(max_id, row['ID'])

                printed = row['Printed']

                if not printed:
                    _logger.info(f"Đơn pos order chưa Printed: {row['ID']}")
                    self.env['ttb.sync.augges.pending'].create({
                        'augges_id': row['ID'],
                        'finish_state': 0,
                        'insert_date': row['InsertDate'],
                    })
                    self.env.cr.commit()
                    if printed_only: continue
                
                insert_date = fields.Datetime.to_datetime(row['InsertDate']) - datetime.timedelta(hours=7)
                new_session_id = self.env['pos.session']
                ma_kho = row['Ma_kho']
                warehouse = self.env['stock.warehouse'].search([('code_augges', '=', ma_kho)], limit=1)
                if warehouse:
                    new_pos_config = self.env['pos.config'].sudo().search([('warehouse_id', '=', warehouse.id)], limit=1)
                    if not new_pos_config:
                        new_pos_config = self.env['pos.config'].sudo().create({'name': f'POS-{warehouse.display_name}','warehouse_id': warehouse.id, 'picking_type_id': warehouse.pos_type_id.id})
                    new_session_id = self.env['pos.session'].sudo().search([('config_id', '=', new_pos_config.id), ('state', '!=', 'closed')], limit=1)
                    if not new_session_id:
                        new_session_id = self.env['pos.session'].sudo().create({'config_id': new_pos_config.id})
                #Sinh phiếu dựa vào kho hoá đơn
                invoice_session_id = self.env['pos.session']
                invoice_warehouse = warehouse or warehouse_augges
                if invoice_warehouse:
                    invoice_warehouse = invoice_warehouse.ttb_branch_id.vat_warehouse_id
                    if not invoice_warehouse:
                        _logger.info(f"Không thể đồng bộ đơn do không tìm thấy kho thuế: {row['ID']}")
                        return
                    invoice_session_id = self.env['pos.session'].sudo().search(
                        [('config_id.warehouse_id', '=', invoice_warehouse.id), ('state', '!=', 'closed')], limit=1)
                    if not invoice_session_id:
                        invoice_pos_config = self.env['pos.config'].sudo().search(
                            [('warehouse_id', '=', invoice_warehouse.id)], limit=1)
                        if not invoice_pos_config:
                            invoice_pos_config = self.env['pos.config'].sudo().create(
                                {'name': f'POS-{invoice_warehouse.display_name}', 'warehouse_id': invoice_warehouse.id,
                                 'picking_type_id': invoice_warehouse.pos_type_id.id})
                        invoice_session_id = self.env['pos.session'].sudo().create({'config_id': invoice_pos_config.id})
                
                order_data = {
                    'name': f'''AUGGES/{row["ID"]}/{row['Quay']}/{row['Sp']}''',
                    'user_id': 2,
                    'session_id': new_session_id.id or session_id.id,
                    'id_augges': int(row['ID']),
                    'id_kho_augges': int(row['ID_Kho']),
                    'id_quay_augges': row['Quay'],
                    'sp_augges': row['Sp'],
                    'amount_tax': float(row['Tien_GtGt']),
                    'amount_paid': float(row['Tien_Hang']) - float(row.get('Tien_Ck', 0)) - float(row.get('Tien_Giam', 0)),
                    'amount_total': float(row['Tien_Hang']) - float(row.get('Tien_Ck', 0)) - float(row.get('Tien_Giam', 0)),
                    'amount_return': 0,
                    'currency_id': currency_id.id,
                    'state': 'done',
                    'date_order': insert_date.strftime('%Y-%m-%d %H:%M:%S'),
                    # 'augges_no_tk': augges_no_tk or '',
                }
                invoice_order_data = {
                    'name': f'''HDT/{row["ID"]}/{row['Quay']}/{row['Sp']}''',
                    'user_id': 2,
                    'warehouse_origin_id': warehouse.id or warehouse_augges.id,
                    'partner_id': int(invoice_partner_id) if invoice_partner_id else False,
                    'session_id': invoice_session_id.id,
                    'id_augges': int(row['ID']),
                    'id_kho_augges': int(row['ID_Kho']),
                    'id_quay_augges': row['Quay'],
                    'sp_augges': row['Sp'],
                    'amount_tax': float(row['Tien_GtGt']),
                    'amount_paid': float(row['Tien_Hang']) - float(row.get('Tien_Ck', 0)) - float(row.get('Tien_Giam', 0)),
                    'amount_total': float(row['Tien_Hang']) - float(row.get('Tien_Ck', 0)) - float(row.get('Tien_Giam', 0)),
                    'amount_return': 0,
                    'currency_id': currency_id.id,
                    'state': 'draft',
                    'date_order': insert_date.strftime('%Y-%m-%d %H:%M:%S'),
                    # 'augges_no_tk': augges_no_tk or '',
                }

                # Đơn thường
                if sync_normal:
                    existing_pos_order = self.env["pos.order"].sudo().with_context(active_test=False).search([("id_augges", "=", row['ID']), ('warehouse_origin_id', '=', False)], limit=1)
                    if not existing_pos_order and create_order:
                        new_pos_order = self.env["pos.order"].sudo().create(self.get_lines(order_data, cursor, row['ID'], tien_hang=float(row['Tien_Hang'])))
                        for line in new_pos_order.lines:
                            line._onchange_amount_line_all()
                        new_pos_order._compute_prices()
                        _logger.info(f"Created new pos order: {row['ID']}")
                    if existing_pos_order and write_order:
                        to_write = not write_check or not self.check_ok(float(row['Tien_Hang']), existing_pos_order.amount_total)
                        if to_write:
                            existing_pos_order.with_context(allow_delete=True).write(self.get_lines(order_data, cursor, row['ID'], tien_hang=float(row['Tien_Hang'])))
                            for line in existing_pos_order.lines:
                                line._onchange_amount_line_all()
                            existing_pos_order._compute_prices()
                            _logger.info(f"Write pos order: {row['ID']}")
                        else:
                            _logger.info(f"Not Write pos order: {row['ID']}")
                
                # Đơn POS dùng xuất Hoá đơn
                if sync_hdt and printed and float(row['Tien_Hang']) > 1:
                    existing_invoice_order_data = self.env["pos.order"].sudo().with_context(active_test=False).search([("id_augges", "=", row['ID']), ('warehouse_origin_id', '!=', False)], limit=1)
                    if not existing_invoice_order_data and create_order:
                        new_invoice_order_data = self.env["pos.order"].sudo().create(self.get_lines(invoice_order_data, cursor, row['ID'], tien_hang=float(row['Tien_Hang'])))
                        for line in new_invoice_order_data.lines:
                            line._onchange_amount_line_all()
                        new_invoice_order_data._compute_prices()
                        _logger.info(f"Created new pos invoice order: {row['ID']}")
                    if existing_invoice_order_data and write_order and existing_invoice_order_data.state == 'draft':
                        existing_invoice_order_data.with_context(allow_delete=True).write(self.get_lines(invoice_order_data, cursor, row['ID'], tien_hang=float(row['Tien_Hang'])))
                        for line in existing_invoice_order_data.lines:
                            line._onchange_amount_line_all()
                        existing_invoice_order_data._compute_prices()
                        _logger.info(f"Write pos invoice order: {row['ID']}")

                if not augges_ids:
                    self.env["ir.config_parameter"].sudo().set_param(config_name, str(max_id))
                self.env.cr.commit()

            if augges_ids:
                # Nếu đồng bộ theo id chỉ định thì xong 1 lượt là thoát
                break
        
        if not augges_ids:
            self.env["ir.config_parameter"].sudo().set_param(config_name, str(max_id))
        cursor.close()
        conn.close()
        _logger.info("pos order sync completed successfully!")

    def get_point(self, row, order_data, conn, cursor):
        pos_id = row['ID']
        id_the = row['ID_The']
        id_lthe = row['ID_LThe']
        sngay_hien_tai = row['Sngay']

        if not id_the or not id_lthe:
            return

        card_info = self.env['ttb.augges'].get_records_by_id('dmthe', id_the, ['Tu_Ngay', 'Den_Ngay'], conn)
        if not card_info:
            _logger.info('Đồng bộ POS lỗi: không thấy thông tin thẻ khách hàng')
            return

        tu_ngay = card_info[0]['tu_ngay']
        sngay_dau_ky = tu_ngay.strftime("%y%m%d")

        query = f"""
            SELECT
                SUM(Diem_The) AS Diem_The,
                SUM(Diem_The1) AS Diem_The1,
                SUM(Diem_Tt) AS Diem_Tt,
                SUM(DiemTang) AS DiemTang
            FROM
                (
                    SELECT
                        SlBan.ID,
                        SlBlM.Diem_Tt,
                        SlBlM.DiemTang,
                        (
                            CASE WHEN ISNULL(SlBlM.TheDiem0, 0)<> 1 THEN (
                                CAST(
                                    SlBan.So_Tien / DmLThe.Doanh_So AS INT
                                )* DmLThe.Diem_The
                            )*(
                                CASE WHEN SlBlM.DiemX > 1 THEN SlBlM.DiemX ELSE 1 END
                            ) ELSE CAST(0 AS money) END
                        ) AS Diem_The,
                        (
                            CASE WHEN ISNULL(SlBlM.TheDiem0, 0)<> 1
                            AND SlBlM.SNgay >= '      ' THEN (
                                CAST(
                                    SlBan.DS_CK / DmLThe.Doanh_So AS INT
                                )* DmLThe.Diem_The
                            )*(
                                CASE WHEN SlBlM.DiemX > 1 THEN SlBlM.DiemX ELSE 1 END
                            ) ELSE CAST(0 AS money) END
                        ) AS Diem_The1
                    FROM
                        (
                            SELECT
                                SlThe.ID,
                                SlThe.ID_The,
                                SlThe.ID_LThe,
                                SUM(SlThe.So_Tien) AS So_Tien,
                                SUM(
                                    CASE WHEN SlThe.Tyle_DS > 0 THEN (SlThe.Tyle_DS * SlThe.So_Tien)/ 100 ELSE SlThe.So_Tien END
                                ) AS DS_CK
                            FROM
                                (
                                    SELECT
                                        SlBlM.ID,
                                        SlBlM.ID_The,
                                        SlBlM.ID_LThe,
                                        SUM(
                                            CASE WHEN SlBlD.Md = ' '
                                            AND SlBlD.ID_CSB IS NULL
                                            AND SlBlD.Tien_Giam = 0 THEN SlBlD.T_Tien ELSE CAST(0 AS money) END
                                        ) AS So_TienNg,
                                        SUM(
                                            CASE WHEN SlBlD.Md IN (' ', 'K') THEN SlBlD.T_Tien - (
                                                ISNULL(SlBlD.Tien_Giam, 0)+ ISNULL(SlBlD.Tien_CK, 0)- SlBlD.CK_TheMg
                                            ) ELSE CAST(0 AS money) END
                                        ) AS So_Tien,
                                        ISNULL(
                                            SlBlM.Tyle_DS,
                                            ISNULL(
                                                DmLTheCkDs.Tyle_DS,
                                                ISNULL(DmLThe.Tyle_DS, 0)
                                            )
                                        ) AS Tyle_DS
                                    FROM
                                        SlBlD
                                        LEFT JOIN SlBlM ON SlBlD.ID = SlBlM.ID
                                        LEFT JOIN DmThe ON SlBlM.ID_The = DmThe.ID
                                        LEFT JOIN DmLThe ON SlBlM.ID_LThe = DmLThe.ID
                                        LEFT JOIN DmH ON SlBlD.ID_Hang = DmH.ID
                                        LEFT JOIN DmLTheCkDs ON SlBlM.ID_LThe = DmLTheCkDs.ID_LThe
                                        AND DmH.ID_Nhom = DmLTheCkDs.ID_Nhom
                                    WHERE
                                        SlBlM.SNgay >= '{sngay_dau_ky}'
                                        AND SlBlM.SNgay <= '{sngay_hien_tai}'
                                        AND SlBlM.ID_DV >= 0
                                        AND SlBlM.ID_The = {id_the}
                                        AND SlBlM.ID < {pos_id}
                                        AND DmLThe.Diem_The > 0
                                        AND DmLThe.Doanh_So > 0
                                        AND (
                                            ISNULL(SlBlM.ID_LThe, 0) = 0
                                            OR SlBlM.ID_LThe = {id_lthe}
                                        )
                                    GROUP BY
                                        SlBlM.ID,
                                        SlBlM.ID_The,
                                        SlBlM.ID_LThe,
                                        ISNULL(
                                            SlBlM.Tyle_DS,
                                            ISNULL(
                                                DmLTheCkDs.Tyle_DS,
                                                ISNULL(DmLThe.Tyle_DS, 0)
                                            )
                                        )
                                ) SlThe
                            GROUP BY
                                SlThe.ID,
                                SlThe.ID_The,
                                SlThe.ID_LThe
                        ) SlBan
                        LEFT JOIN SlBlM ON SlBan.ID = SlBlM.ID
                        LEFT JOIN DmLThe ON SlBan.ID_LThe = DmLThe.ID
                    WHERE
                        SlBan.So_Tien <> 0
                        OR SlBlM.DiemTang <> 0
                        OR SlBlM.Diem_Tt <> 0
                ) AS Sl_The
        """
        cursor.execute(query)
        columns = [column[0] for column in cursor.description]
        points = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        remaining_accumulated_points = redeemed_accumulated_points = 0
        if points and len(points) > 0:
            # điểm còn lại
            remaining_accumulated_points = points[0]['Diem_The1'] or 0
            # điểm đã sử dụng
            redeemed_accumulated_points = points[0]['Diem_Tt'] or 0
        
        order_data['total_accumulated_points'] = remaining_accumulated_points + redeemed_accumulated_points
        order_data['redeemed_accumulated_points'] = redeemed_accumulated_points
        order_data['remaining_accumulated_points'] = remaining_accumulated_points

        return True

    def _map_cashier_user_from_code(self, code):
        """Trả về res.users theo mã NV (LogName) lấy từ Augges."""
        if not code:
            return self.env['res.users'].browse(2)  # Admin

        Users = self.env['res.users'].sudo()

        # 1) thẳng theo login = mã
        user = Users.search([('login', '=', code)], limit=1)
        if user:
            return user
        return self.env['res.users'].browse(2)  # Admin

    @api.model
    def sync_orders_from_mssql_create_ngay_in(self, 
            number_sync=5, reset=False, date_from=False, augges_ids=False, config_name='mssql.last_synced_order_ngay_in', 
            sync_hdt=True, sync_normal=True, create_order=True, write_order=True, date_to=False, id_from=False, id_to=False, printed_only=True, write_check=True, ngay_in=False, raise_exception=False):
        """Hàm đồng bộ đơn hàng từ MSSQL về Odoo"""
        conn = self.env['ttb.tools'].get_mssql_connection()
        cursor = conn.cursor()
        last_synced_id = self.env['ttb.tools'].get_mssql_config(config_name, '')
        max_id = 0 if reset else last_synced_id
        count_sync = 0
        currency_id = self.env.company.currency_id
        warehouse_augges = self.env['stock.warehouse'].search([('code', '=', 'AUG')], limit=1)
        if not warehouse_augges:
            warehouse_augges = self.env['stock.warehouse'].create({'code': 'AUG', 'name': 'Kho AUG'})
        session_id = self.env['pos.session'].sudo().search([('config_id.warehouse_id', '=', warehouse_augges.id), ('state', '!=', 'closed')], limit=1)
        if not session_id:
            pos_config = self.env['pos.config'].sudo().search([('warehouse_id', '=', warehouse_augges.id)], limit=1)
            if not pos_config:
                pos_config = self.env['pos.config'].sudo().create({'name': f'POS-{warehouse_augges.display_name}','warehouse_id': warehouse_augges.id, 'picking_type_id': warehouse_augges.pos_type_id.id})
            session_id = self.env['pos.session'].sudo().create({'config_id': pos_config.id})
        invoice_partner_id = self.env['ir.config_parameter'].sudo().get_param('ttb_purchase_invoice_stock.invoice_partner_id')

        if not ngay_in:
            ngay_in = fields.Datetime.now() - datetime.timedelta(seconds=10) + datetime.timedelta(hours=7)
            ngay_in = fields.Datetime.to_string(ngay_in)

        while True:
            if number_sync and count_sync > number_sync: break
            count_sync += 1
            
            sql_augges_ids = f"""and SLBLM.ID in ({', '.join(str(x) for x in augges_ids)}) """ if augges_ids else ''
            sql_id_from = f" AND ID >= {id_from}" if id_from else ""
            sql_id_to = f" AND ID <= {id_to}" if id_to else ""
            sql_date_from = f"""and SLBLM.InsertDate >= '{date_from}' """ if date_from else ''
            sql_date_to = f"""and SLBLM.InsertDate <= '{date_to}' """ if date_to else ''
            
            sql_ngay_in_from = f"AND SLBLM.Ngay_In > '{max_id}'" if max_id else ''
            sql_ngay_in_to = f"AND SLBLM.Ngay_In <= '{ngay_in}'" if ngay_in else ''

            query = f"""
                SELECT
                    SLBLM.ID, SLBLM.ID_Kho, SLBLM.Sp, SLBLM.Quay, SLBLM.Tien_Hang, SLBLM.Tien_CK, SLBLM.Tien_Giam, SLBLM.Tien_GtGt, 
                    SLBLM.Ngay_In, dmkho.Ma_kho, SLBLM.Printed, SLBLM.ID_Dt,
                    SLBLM.ID_The, SLBLM.ID_LThe, SLBLM.Sngay,
                    du.LogName AS CashierCode
                FROM SLBLM
                    LEFT JOIN dmkho on SLBLM.ID_Kho = dmkho.ID
                    LEFT JOIN DmUser du ON du.ID = SLBLM.UserID 
                WHERE 1=1
                    and Printed > 0
                    and SLBLM.ID_Kho is not null 
                    {sql_augges_ids}
                    {sql_id_from} {sql_id_to}
                    {sql_date_from} {sql_date_to}

                    {sql_ngay_in_from}
                    {sql_ngay_in_to}

                ORDER BY SLBLM.ID ASC
            """
            cursor.execute(query)
            columns = [column[0] for column in cursor.description]
            orders = [dict(zip(columns, row)) for row in cursor.fetchall()]

            if not orders: break
            
            #Ghi các đơn gọi lại vào thông số => Sau đó sẽ có 1 job lấy ra gọi lại
            for row in orders:
                need_create = False
                if sync_normal:
                    existing_pos_order = self.env["pos.order"].sudo().with_context(active_test=False).search([("id_augges", "=", row['ID']), ('warehouse_origin_id', '=', False)], limit=1)
                    if not existing_pos_order:
                        need_create = True

                if sync_hdt:
                    existing_invoice_order_data = self.env["pos.order"].sudo().with_context(active_test=False).search([("id_augges", "=", row['ID']), ('warehouse_origin_id', '!=', False)], limit=1)
                    if not existing_invoice_order_data:
                        need_create = True

                if not need_create:
                    _logger.info('Skip sync create pos row_id %s', row['ID'])
                    continue

                insert_date = fields.Datetime.to_datetime(row['Ngay_In']) - datetime.timedelta(hours=7)
                new_session_id = self.env['pos.session']
                ma_kho = row['Ma_kho']
                warehouse = self.env['stock.warehouse'].search([('code_augges', '=', ma_kho)], limit=1)
                if warehouse:
                    new_pos_config = self.env['pos.config'].sudo().search([('warehouse_id', '=', warehouse.id)], limit=1)
                    if not new_pos_config:
                        new_pos_config = self.env['pos.config'].sudo().create({'name': f'POS-{warehouse.display_name}','warehouse_id': warehouse.id, 'picking_type_id': warehouse.pos_type_id.id})
                    new_session_id = self.env['pos.session'].sudo().search([('config_id', '=', new_pos_config.id), ('state', '!=', 'closed')], limit=1)
                    if not new_session_id:
                        new_session_id = self.env['pos.session'].sudo().create({'config_id': new_pos_config.id})
                elif raise_exception:
                    raise UserError('Không tìm thấy kho, mã: %s' % ma_kho)
                
                #Sinh phiếu dựa vào kho hoá đơn
                invoice_session_id = self.env['pos.session']
                invoice_warehouse = warehouse or warehouse_augges
                if invoice_warehouse:
                    invoice_warehouse = invoice_warehouse.ttb_branch_id.vat_warehouse_id
                    if not invoice_warehouse:
                        _logger.info(f"Không thể đồng bộ đơn do không tìm thấy kho thuế: {row['ID']}")
                        return
                    invoice_session_id = self.env['pos.session'].sudo().search(
                        [('config_id.warehouse_id', '=', invoice_warehouse.id), ('state', '!=', 'closed')], limit=1)
                    if not invoice_session_id:
                        invoice_pos_config = self.env['pos.config'].sudo().search(
                            [('warehouse_id', '=', invoice_warehouse.id)], limit=1)
                        if not invoice_pos_config:
                            invoice_pos_config = self.env['pos.config'].sudo().create(
                                {'name': f'POS-{invoice_warehouse.display_name}', 'warehouse_id': invoice_warehouse.id,
                                 'picking_type_id': invoice_warehouse.pos_type_id.id})
                        invoice_session_id = self.env['pos.session'].sudo().create({'config_id': invoice_pos_config.id})
                elif raise_exception:
                    raise UserError('Không tìm thấy kho hoá đơn, mã: %s' % ma_kho)
                cashier_code = (row.get('CashierCode') or '').strip()
                cashier_user = self._map_cashier_user_from_code(cashier_code)

                # LẤY ĐIỂM TÍCH / TIÊU TỪ AUGGES CHO ĐƠN NÀY <<<<<
                point_earn, point_spent = self._get_pos_points_from_augges(conn, cursor, row['ID'])

                order_data = {
                    'name': f'''AUGGES/{row["ID"]}/{row['Quay']}/{row['Sp']}''',
                    'user_id': cashier_user.id,
                    'session_id': new_session_id.id or session_id.id,
                    'id_augges': int(row['ID']),
                    'id_kho_augges': int(row['ID_Kho']),
                    'id_quay_augges': row['Quay'],
                    'sp_augges': row['Sp'],
                    'amount_tax': float(row['Tien_GtGt']),
                    'amount_paid': float(row['Tien_Hang']) - float(row.get('Tien_Ck', 0)) - float(row.get('Tien_Giam', 0)),
                    'amount_total': float(row['Tien_Hang']) - float(row.get('Tien_Ck', 0)) - float(row.get('Tien_Giam', 0)),
                    'amount_return': 0,
                    'currency_id': currency_id.id,
                    'state': 'done',
                    'date_order': insert_date.strftime('%Y-%m-%d %H:%M:%S'),
                    'ttb_total_point_earn': point_earn,
                    'ttb_total_point_spent': point_spent,
                    # 'augges_no_tk': augges_no_tk or '',
                }
                invoice_order_data = {
                    'name': f'''HDT/{row["ID"]}/{row['Quay']}/{row['Sp']}''',
                    'user_id': cashier_user.id,
                    'warehouse_origin_id': warehouse.id or warehouse_augges.id,
                    'partner_id': int(invoice_partner_id) if invoice_partner_id else False,
                    'session_id': invoice_session_id.id,
                    'id_augges': int(row['ID']),
                    'id_kho_augges': int(row['ID_Kho']),
                    'id_quay_augges': row['Quay'],
                    'sp_augges': row['Sp'],
                    'amount_tax': float(row['Tien_GtGt']),
                    'amount_paid': float(row['Tien_Hang']) - float(row.get('Tien_Ck', 0)) - float(row.get('Tien_Giam', 0)),
                    'amount_total': float(row['Tien_Hang']) - float(row.get('Tien_Ck', 0)) - float(row.get('Tien_Giam', 0)),
                    'amount_return': 0,
                    'currency_id': currency_id.id,
                    'state': 'draft',
                    'date_order': insert_date.strftime('%Y-%m-%d %H:%M:%S'),
                    'ttb_total_point_earn': point_earn,
                    'ttb_total_point_spent': point_spent,
                    # 'augges_no_tk': augges_no_tk or '',
                }

                # Đơn thường
                if sync_normal and not existing_pos_order:
                    id_dt = row['ID_Dt']
                    if id_dt:
                        partner = self.env['res.partner'].search([('augges_id', '=', id_dt)], limit=1)
                        if not partner:
                            _logger.warning(f"Tạo mới khách hàng do Không tìm thấy đối tác với ID_Dt: {id_dt}")
                            partner = self.env['res.partner'].sync_customer(id_dt)
                            if not partner:
                                partner_data = {
                                    'augges_id': id_dt,
                                    # 'ref': ma_dt,
                                    'name': f'''{id_dt} at AUGGES/{row["ID"]}/{row['Quay']}/{row['Sp']}''',
                                    # 'vat': mst,
                                    # 'street': dia_chi,
                                    # 'phone': dien_thoai,
                                    'customer_rank': 1,
                                }
                                partner = self.env['res.partner'].create(partner_data)
                        order_data['partner_id'] = partner.id
                        # Tính điểm bị chậm, không đồng bộ kịp phiếu. Tạm ngắt để không bị trễ doanh thu
                        # if self.get_point(row, order_data, conn, cursor):
                        #     partner.write({
                        #         'total_accumulated_points': order_data.get('total_accumulated_points', 0),
                        #         'redeemed_accumulated_points': order_data.get('redeemed_accumulated_points', 0),
                        #         'remaining_accumulated_points': order_data.get('remaining_accumulated_points', 0),
                        #     })
                    vals = self.get_lines(order_data, cursor, row['ID'], raise_exception=raise_exception, tien_hang=float(row['Tien_Hang']))                    

                    new_pos_order = self.env["pos.order"].sudo().create(vals)
                    for line in new_pos_order.lines:
                        line._onchange_amount_line_all()
                    new_pos_order._compute_prices()
                    # TODO: fix ngày stock.move.line
                    # new_pos_order._create_order_picking()
                    _logger.info(f"Created new pos order: {row['ID']}")

                    # Tự động tạo Happy Call nếu đơn hàng trên mức quy định
                    try:
                        happy_call_rule = self.env['ttb.happy.call.rule'].search([], limit=1, order='id desc')
                        min_amount = happy_call_rule.amount_total if happy_call_rule else 50000

                        if new_pos_order.amount_total > min_amount:
                            partner = new_pos_order.partner_id
                            if partner and partner.phone:
                                existing_happy_call = self.env['ttb.happy.call'].search([('last_order_id', '=', new_pos_order.id)], limit=1)
                                if not existing_happy_call:
                                    happy_call_vals = {
                                        'name': f'HPC cho đơn hàng {new_pos_order.name}',
                                        'partner_id': partner.id,
                                        'partner_phone': partner.phone,
                                        'last_order_id': new_pos_order.id,
                                        'create_date': fields.Datetime.now(),
                                    }
                                    self.env['ttb.happy.call'].sudo().create(happy_call_vals)
                                    _logger.info(f"Auto-created Happy Call for order: {new_pos_order.name}")
                    except Exception as e:
                        _logger.error(f"Failed to create Happy Call for order {row['ID']}: {e}")
                    
                
                # Đơn POS dùng xuất Hoá đơn
                if sync_hdt and not existing_invoice_order_data:
                    new_invoice_order_data = self.env["pos.order"].sudo().create(self.get_lines(invoice_order_data, cursor, row['ID'], raise_exception=raise_exception, tien_hang=float(row['Tien_Hang'])))
                    for line in new_invoice_order_data.lines:
                        line._onchange_amount_line_all()
                    new_invoice_order_data._compute_prices()
                    _logger.info(f"Created new pos invoice order: {row['ID']}")
                    
                self.env.cr.commit()

            if augges_ids:
                # Nếu đồng bộ theo id chỉ định thì xong 1 lượt là thoát
                break
        
        if not augges_ids:
            self.env["ir.config_parameter"].sudo().set_param(config_name, ngay_in)
        cursor.close()
        conn.close()
        _logger.info("pos order sync completed successfully!")

    @api.model
    def sync_orders_from_mssql_write_ngay_in(self, 
            number_sync=5, reset=False, date_from=False, augges_ids=False, config_name='mssql.last_synced_order_ngay_in_write', 
            sync_hdt=True, sync_normal=True, create_order=True, write_order=True, date_to=False, id_from=False, id_to=False, printed_only=True, write_check=True, ngay_in=False):
        """Hàm đồng bộ đơn hàng từ MSSQL về Odoo"""
        conn = self.env['ttb.tools'].get_mssql_connection()
        cursor = conn.cursor()
        last_synced_id = self.env['ttb.tools'].get_mssql_config(config_name, '')
        max_id = 0 if reset else last_synced_id
        count_sync = 0
        currency_id = self.env.company.currency_id
        warehouse_augges = self.env['stock.warehouse'].search([('code', '=', 'AUG')], limit=1)
        if not warehouse_augges:
            warehouse_augges = self.env['stock.warehouse'].create({'code': 'AUG', 'name': 'Kho AUG'})
        session_id = self.env['pos.session'].sudo().search([('config_id.warehouse_id', '=', warehouse_augges.id), ('state', '!=', 'closed')], limit=1)
        if not session_id:
            pos_config = self.env['pos.config'].sudo().search([('warehouse_id', '=', warehouse_augges.id)], limit=1)
            if not pos_config:
                pos_config = self.env['pos.config'].sudo().create({'name': f'POS-{warehouse_augges.display_name}','warehouse_id': warehouse_augges.id, 'picking_type_id': warehouse_augges.pos_type_id.id})
            session_id = self.env['pos.session'].sudo().create({'config_id': pos_config.id})
        invoice_partner_id = self.env['ir.config_parameter'].sudo().get_param('ttb_purchase_invoice_stock.invoice_partner_id')

        if not ngay_in:
            ngay_in = fields.Datetime.now() - datetime.timedelta(seconds=10) + datetime.timedelta(hours=7)
            ngay_in = fields.Datetime.to_string(ngay_in)

        while True:
            if number_sync and count_sync > number_sync: break
            count_sync += 1
            
            sql_augges_ids = f"""and SLBLM.ID in ({', '.join(str(x) for x in augges_ids)}) """ if augges_ids else ''
            sql_id_from = f" AND ID >= {id_from}" if id_from else ""
            sql_id_to = f" AND ID <= {id_to}" if id_to else ""
            sql_date_from = f"""and SLBLM.InsertDate >= '{date_from}' """ if date_from else ''
            sql_date_to = f"""and SLBLM.InsertDate <= '{date_to}' """ if date_to else ''
            
            sql_ngay_in_from = f"AND SLBLM.Ngay_In > '{max_id}'" if max_id else ''
            sql_ngay_in_to = f"AND SLBLM.Ngay_In <= '{ngay_in}'" if ngay_in else ''

            query = f"""
                SELECT
                    SLBLM.ID, SLBLM.ID_Kho, SLBLM.Sp, SLBLM.Quay, SLBLM.Tien_Hang, SLBLM.Tien_CK, SLBLM.Tien_Giam, SLBLM.Tien_GtGt, 
                    SLBLM.Ngay_In, dmkho.Ma_kho, SLBLM.Printed
                FROM SLBLM
                    LEFT JOIN dmkho on SLBLM.ID_Kho = dmkho.ID 
                WHERE 1=1
                    and Printed > 0
                    and SLBLM.ID_Kho is not null 
                    {sql_augges_ids}
                    {sql_id_from} {sql_id_to}
                    {sql_date_from} {sql_date_to}

                    {sql_ngay_in_from}
                    {sql_ngay_in_to}

                ORDER BY SLBLM.ID ASC
            """
            cursor.execute(query)
            columns = [column[0] for column in cursor.description]
            orders = [dict(zip(columns, row)) for row in cursor.fetchall()]

            if not orders: break
            
            #Ghi các đơn gọi lại vào thông số => Sau đó sẽ có 1 job lấy ra gọi lại
            for row in orders:
                need_write = False
                if sync_normal:
                    existing_pos_order = self.env["pos.order"].sudo().with_context(active_test=False).search([("id_augges", "=", row['ID']), ('warehouse_origin_id', '=', False)], limit=1)
                    if existing_pos_order:
                        need_write = True

                if sync_hdt:
                    existing_invoice_order_data = self.env["pos.order"].sudo().with_context(active_test=False).search([("id_augges", "=", row['ID']), ('warehouse_origin_id', '!=', False)], limit=1)
                    if existing_invoice_order_data:
                        need_write = True

                if not need_write:
                    _logger.info('Skip sync write pos row_id %s', row['ID'])
                    continue

                insert_date = fields.Datetime.to_datetime(row['Ngay_In']) - datetime.timedelta(hours=7)
                new_session_id = self.env['pos.session']
                ma_kho = row['Ma_kho']
                warehouse = self.env['stock.warehouse'].search([('code_augges', '=', ma_kho)], limit=1)
                if warehouse:
                    new_pos_config = self.env['pos.config'].sudo().search([('warehouse_id', '=', warehouse.id)], limit=1)
                    if not new_pos_config:
                        new_pos_config = self.env['pos.config'].sudo().create({'name': f'POS-{warehouse.display_name}','warehouse_id': warehouse.id, 'picking_type_id': warehouse.pos_type_id.id})
                    new_session_id = self.env['pos.session'].sudo().search([('config_id', '=', new_pos_config.id), ('state', '!=', 'closed')], limit=1)
                    if not new_session_id:
                        new_session_id = self.env['pos.session'].sudo().create({'config_id': new_pos_config.id})
                #Sinh phiếu dựa vào kho hoá đơn
                invoice_session_id = self.env['pos.session']
                invoice_warehouse = warehouse or warehouse_augges
                if invoice_warehouse:
                    invoice_warehouse = invoice_warehouse.ttb_branch_id.vat_warehouse_id
                    if not invoice_warehouse:
                        _logger.info(f"Không thể đồng bộ đơn do không tìm thấy kho thuế: {row['ID']}")
                        return
                    invoice_session_id = self.env['pos.session'].sudo().search(
                        [('config_id.warehouse_id', '=', invoice_warehouse.id), ('state', '!=', 'closed')], limit=1)
                    if not invoice_session_id:
                        invoice_pos_config = self.env['pos.config'].sudo().search(
                            [('warehouse_id', '=', invoice_warehouse.id)], limit=1)
                        if not invoice_pos_config:
                            invoice_pos_config = self.env['pos.config'].sudo().create(
                                {'name': f'POS-{invoice_warehouse.display_name}', 'warehouse_id': invoice_warehouse.id,
                                 'picking_type_id': invoice_warehouse.pos_type_id.id})
                        invoice_session_id = self.env['pos.session'].sudo().create({'config_id': invoice_pos_config.id})
                
                order_data = {
                    'name': f'''AUGGES/{row["ID"]}/{row['Quay']}/{row['Sp']}''',
                    'user_id': 2,
                    'session_id': new_session_id.id or session_id.id,
                    'id_augges': int(row['ID']),
                    'id_kho_augges': int(row['ID_Kho']),
                    'id_quay_augges': row['Quay'],
                    'sp_augges': row['Sp'],
                    'amount_tax': float(row['Tien_GtGt']),
                    'amount_paid': float(row['Tien_Hang']) - float(row.get('Tien_Ck', 0)) - float(row.get('Tien_Giam', 0)),
                    'amount_total': float(row['Tien_Hang']) - float(row.get('Tien_Ck', 0)) - float(row.get('Tien_Giam', 0)),
                    'amount_return': 0,
                    'currency_id': currency_id.id,
                    'state': 'done',
                    'date_order': insert_date.strftime('%Y-%m-%d %H:%M:%S'),
                    # 'augges_no_tk': augges_no_tk or '',
                }
                invoice_order_data = {
                    'name': f'''HDT/{row["ID"]}/{row['Quay']}/{row['Sp']}''',
                    'user_id': 2,
                    'warehouse_origin_id': warehouse.id or warehouse_augges.id,
                    'partner_id': int(invoice_partner_id) if invoice_partner_id else False,
                    'session_id': invoice_session_id.id,
                    'id_augges': int(row['ID']),
                    'id_kho_augges': int(row['ID_Kho']),
                    'id_quay_augges': row['Quay'],
                    'sp_augges': row['Sp'],
                    'amount_tax': float(row['Tien_GtGt']),
                    'amount_paid': float(row['Tien_Hang']) - float(row.get('Tien_Ck', 0)) - float(row.get('Tien_Giam', 0)),
                    'amount_total': float(row['Tien_Hang']) - float(row.get('Tien_Ck', 0)) - float(row.get('Tien_Giam', 0)),
                    'amount_return': 0,
                    'currency_id': currency_id.id,
                    'state': 'draft',
                    'date_order': insert_date.strftime('%Y-%m-%d %H:%M:%S'),
                    # 'augges_no_tk': augges_no_tk or '',
                }

                # Đơn thường
                if sync_normal and existing_pos_order:
                    to_write = not write_check or not self.check_ok(float(row['Tien_Hang']), existing_pos_order.amount_total)
                    if to_write:
                        existing_pos_order.with_context(allow_delete=True).write(self.get_lines(order_data, cursor, row['ID'], tien_hang=float(row['Tien_Hang'])))
                        for line in existing_pos_order.lines:
                            line._onchange_amount_line_all()
                        existing_pos_order._compute_prices()
                        _logger.info(f"Write pos order: {row['ID']}")
                    else:
                        _logger.info(f"Not Write pos order: {row['ID']}")
                
                # Đơn POS dùng xuất Hoá đơn
                if sync_hdt and existing_invoice_order_data and existing_invoice_order_data.state == 'draft':
                    to_write = not write_check or not self.check_ok(float(row['Tien_Hang']), existing_invoice_order_data.amount_total)
                    if to_write:
                        existing_invoice_order_data.with_context(allow_delete=True).write(self.get_lines(invoice_order_data, cursor, row['ID'], tien_hang=float(row['Tien_Hang'])))
                        for line in existing_invoice_order_data.lines:
                            line._onchange_amount_line_all()
                        existing_invoice_order_data._compute_prices()
                        _logger.info(f"Write pos invoice order: {row['ID']}")
                    else:
                        _logger.info(f"Not Write pos invoice order: {row['ID']}")

                self.env.cr.commit()

            if augges_ids:
                # Nếu đồng bộ theo id chỉ định thì xong 1 lượt là thoát
                break
        
        if not augges_ids:
            self.env["ir.config_parameter"].sudo().set_param(config_name, ngay_in)
        cursor.close()
        conn.close()
        _logger.info("pos order sync completed successfully!")


    @api.model
    def sync_pos_order_hdt(self, 
            augges_ids=False, create_order=True, write_order=False, id_from=False, id_to=False, date_from=False, date_to=False,
            fixed_domain = "AND SlBlM.Tien_Hang > 1 AND SlBlM.ID_Kho is not null AND SlBlM.InsertDate < DATEADD(SECOND, -10, GETDATE())"
        ):
        """Hàm đồng bộ đơn hàng từ MSSQL về Odoo"""
        conn = self.env['ttb.tools'].get_mssql_connection()
        cursor = conn.cursor()

        config_name='mssql.last_id_slblm_hdt'
        max_id = int(self.env['ttb.tools'].get_mssql_config(config_name, "0"))

        currency_id = self.env.company.currency_id
        warehouse_augges = self.env['stock.warehouse'].search([('code', '=', 'AUG')], limit=1)
        if not warehouse_augges:
            warehouse_augges = self.env['stock.warehouse'].create({'code': 'AUG', 'name': 'Kho AUG'})
        session_id = self.env['pos.session'].sudo().search([('config_id.warehouse_id', '=', warehouse_augges.id), ('state', '!=', 'closed')], limit=1)
        if not session_id:
            pos_config = self.env['pos.config'].sudo().search([('warehouse_id', '=', warehouse_augges.id)], limit=1)
            if not pos_config:
                pos_config = self.env['pos.config'].sudo().create({'name': f'POS-{warehouse_augges.display_name}','warehouse_id': warehouse_augges.id, 'picking_type_id': warehouse_augges.pos_type_id.id})
            session_id = self.env['pos.session'].sudo().create({'config_id': pos_config.id})
        invoice_partner_id = self.env['ir.config_parameter'].sudo().get_param('ttb_purchase_invoice_stock.invoice_partner_id')
        
        while True:
            sql_id = f"AND SLBLM.ID > {max_id}"
            sql_augges_ids = "AND SLBLM.ID IN %s" % str(augges_ids).replace('[', '(').replace(']', ')') if augges_ids else ''
            sql_id_from = f"AND ID >= {id_from}" if id_from else ""
            sql_id_to = f" AND ID <= {id_to}" if id_to else ""
            sql_date_from = f"AND SLBLM.InsertDate >= '{date_from}'" if date_from else ''
            sql_date_to = f"AND SLBLM.InsertDate <= '{date_to}' " if date_to else ''

            cursor.execute(f"""
                SELECT TOP 1000
                SLBLM.ID, SLBLM.ID_Kho, SLBLM.Sp, SLBLM.Quay, SLBLM.Tien_Hang, SLBLM.Tien_CK, SLBLM.Tien_Giam, SLBLM.Tien_GtGt, SLBLM.InsertDate, dmkho.Ma_kho, SLBLM.Printed
                FROM SLBLM
                LEFT JOIN dmkho on SLBLM.ID_Kho = dmkho.ID 
                WHERE 1=1 
                    {fixed_domain}
                    {sql_id} {sql_augges_ids}
                    {sql_id_from} {sql_id_to}
                    {sql_date_from} {sql_date_to}
                ORDER BY SLBLM.ID ASC
            """)
            columns = [column[0] for column in cursor.description]
            orders = [dict(zip(columns, row)) for row in cursor.fetchall()]

            if not orders: break
            
            #Ghi các đơn gọi lại vào thông số => Sau đó sẽ có 1 job lấy ra gọi lại
            for row in orders:
                max_id = row['ID']
                insert_date = fields.Datetime.to_datetime(row['InsertDate']) - datetime.timedelta(hours=7)

                if not row['Printed']:
                    _logger.info(f"Đơn pos order chưa Printed: {row['ID']}")
                    self.env['ttb.sync.augges.pending'].create({
                        'augges_id': row['ID'],
                        'finish_state': 0,
                        'insert_date': insert_date,
                    })
                    self.env.cr.commit()
                    continue
                
                new_session_id = self.env['pos.session']
                ma_kho = row['Ma_kho']
                warehouse = self.env['stock.warehouse'].search([('code_augges', '=', ma_kho)], limit=1)
                if warehouse:
                    new_pos_config = self.env['pos.config'].sudo().search([('warehouse_id', '=', warehouse.id)], limit=1)
                    if not new_pos_config:
                        new_pos_config = self.env['pos.config'].sudo().create({'name': f'POS-{warehouse.display_name}','warehouse_id': warehouse.id, 'picking_type_id': warehouse.pos_type_id.id})
                    new_session_id = self.env['pos.session'].sudo().search([('config_id', '=', new_pos_config.id), ('state', '!=', 'closed')], limit=1)
                    if not new_session_id:
                        new_session_id = self.env['pos.session'].sudo().create({'config_id': new_pos_config.id})
                
                #Sinh phiếu dựa vào kho hoá đơn
                invoice_session_id = self.env['pos.session']
                invoice_warehouse = warehouse or warehouse_augges
                if invoice_warehouse:
                    invoice_warehouse = invoice_warehouse.ttb_branch_id.vat_warehouse_id
                    if not invoice_warehouse:
                        _logger.info(f"Không thể đồng bộ đơn do không tìm thấy kho thuế: {row['ID']}")
                        return
                    invoice_session_id = self.env['pos.session'].sudo().search(
                        [('config_id.warehouse_id', '=', invoice_warehouse.id), ('state', '!=', 'closed')], limit=1)
                    if not invoice_session_id:
                        invoice_pos_config = self.env['pos.config'].sudo().search(
                            [('warehouse_id', '=', invoice_warehouse.id)], limit=1)
                        if not invoice_pos_config:
                            invoice_pos_config = self.env['pos.config'].sudo().create(
                                {'name': f'POS-{invoice_warehouse.display_name}', 'warehouse_id': invoice_warehouse.id,
                                 'picking_type_id': invoice_warehouse.pos_type_id.id})
                        invoice_session_id = self.env['pos.session'].sudo().create({'config_id': invoice_pos_config.id})
                cursor.execute(f"""SELECT ID, ID_L, Stt, ID_Hang, So_Luong, Gia_Ban, Don_Gia, TyLe_Giam, Tien_Giam, Tien_CK, T_Tien, CK_The, CK_TheMg, Thue, Tien_GtGt, No_Tk, Gia_Kvat, ID_Thue FROM dbo.SLBLD WHERE ID = {row["ID"]} and ID_Hang is not null""")
                result = [column[0] for column in cursor.description]
                result_line = [dict(zip(result, row)) for row in cursor.fetchall()]
                order_line = [[5,0,0]]
                augges_no_tk = False
                for line in result_line:
                    product_template_id = self.env['product.template'].with_context(active_test=False).sudo().search([('augges_id', '=', line['ID_Hang'])], limit=1)
                    if not product_template_id:
                        continue
                    product_id = self.env['product.product'].with_context(active_test=False).sudo().search([('product_tmpl_id', '=', product_template_id.id)], limit=1)
                    if not product_id:
                        continue
                    # lưu ý những đơn 2021 thì không có id thuế, ko map được thuế
                    tax_ids = self.get_tax_ids(line.get("ID_Thue"), product_id)
                    discount = 0
                    tien_ck = float(line.get('Tien_CK', 0)) + float(line.get('Tien_Giam', 0))
                    amount_origin = float(line['T_Tien'])
                    if not float(line['So_Luong']):
                        continue
                    if tien_ck and amount_origin:
                        discount = tien_ck/amount_origin * 100
                    if not augges_no_tk:
                        augges_no_tk = line.get('No_Tk', False)
                    order_line.append((0, 0, {'name': f'AUGGES/{line["ID"]}/{line["Stt"]}',
                                 'product_id': product_id.id,
                                 'price_unit': float(line['T_Tien'])/float(line['So_Luong']),
                                 'qty': float(line['So_Luong']),
                                 'price_subtotal': 1,
                                 'price_subtotal_incl': 1,
                                 'augges_no_tk': line.get('No_Tk', False),
                                 'discount': discount,
                                 'tax_ids': [(6, 0, tax_ids.ids)]
                                 }))
                
                invoice_order_data = {
                    'name': f'''HDT/{row["ID"]}/{row['Quay']}/{row['Sp']}''',
                    'user_id': 2,
                    'warehouse_origin_id': warehouse.id or warehouse_augges.id,
                    'partner_id': int(invoice_partner_id) if invoice_partner_id else False,
                    'session_id': invoice_session_id.id,
                    'id_augges': int(row['ID']),
                    'id_kho_augges': int(row['ID_Kho']),
                    'id_quay_augges': row['Quay'],
                    'sp_augges': row['Sp'],
                    'amount_tax': float(row['Tien_GtGt']),
                    'amount_paid': float(row['Tien_Hang']) - float(row.get('Tien_Ck', 0)) - float(row.get('Tien_Giam', 0)),
                    'amount_total': float(row['Tien_Hang']) - float(row.get('Tien_Ck', 0)) - float(row.get('Tien_Giam', 0)),
                    'amount_return': 0,
                    'currency_id': currency_id.id,
                    'state': 'draft',
                    'date_order': insert_date.strftime('%Y-%m-%d %H:%M:%S'),
                    'augges_no_tk': augges_no_tk or '',
                    'lines': order_line,
                }
                
                existing_invoice_order_data = self.env["pos.order"].sudo().with_context(active_test=False).search([("id_augges", "=", row['ID']), ('warehouse_origin_id', '!=', False)], limit=1)

                if not existing_invoice_order_data and create_order:
                    existing_invoice_order_data = self.env["pos.order"].sudo().create(invoice_order_data)
                    for line in existing_invoice_order_data.lines:
                        line._onchange_amount_line_all()
                    existing_invoice_order_data._compute_prices()
                    _logger.info(f"Created new pos invoice order: {row['ID']}")

                if existing_invoice_order_data and write_order and existing_invoice_order_data.state == 'draft':
                    existing_invoice_order_data.with_context(allow_delete=True).write(invoice_order_data)
                    for line in existing_invoice_order_data.lines:
                        line._onchange_amount_line_all()
                    existing_invoice_order_data._compute_prices()
                    _logger.info(f"Write pos invoice order: {row['ID']}")

                if not augges_ids:
                    self.env["ir.config_parameter"].sudo().set_param(config_name, str(max_id))
                self.env.cr.commit()

            if augges_ids:
                # Nếu đồng bộ theo id chỉ định thì xong 1 lượt là thoát
                break
        
        if not augges_ids:
            self.env["ir.config_parameter"].sudo().set_param(config_name, str(max_id))
        # cursor.close()
        cursor.close()
        conn.close()
        _logger.info("pos order sync completed successfully!")

    @api.model
    def sync_orders_from_mssql_with_pos_printed_ids(self, pos_printed_ids=False, skip_old_pos=False):
        if not pos_printed_ids:
            # pos_printed_ids = self.env['ir.config_parameter'].sudo().get_param('ttb_purchase_invoice_stock.pos_printed_ids', False)
            domain = [('finish_state', '=', 0)]
            if skip_old_pos:
                domain.append(('insert_date', '>=', fields.Datetime.now()-datetime.timedelta(hours=31)))
            pos_printeds = self.env['ttb.sync.augges.pending'].sudo().search(domain)
            if pos_printeds:
                pos_printeds.finish_state = 1
                pos_printed_ids = pos_printeds.mapped('augges_id')

        if pos_printed_ids:
            self.sync_orders_from_mssql_create(reset=True, augges_ids=pos_printed_ids)


    @api.model
    def sync_tax_from_mssql(self):
        conn = self.env['ttb.tools'].get_mssql_connection()
        cursor = conn.cursor()
        last_synced_id = int(self.env['ttb.tools'].get_mssql_config("mssql.last_synced_tax_id", "0"))
        max_id = last_synced_id
        while True:
            cursor.execute(f"""SELECT TOP 100 *
                               FROM DmThue
                               WHERE ID > {max_id}
                               ORDER BY ID ASC""")
            columns = [column[0] for column in cursor.description]
            taxes = [dict(zip(columns, row)) for row in cursor.fetchall()]
            if not taxes: break
            id_auggest = []
            for row in taxes:
                id_auggest.append(row['ID'])
                value = {'id_augges': int(row['ID']),
                         'ma_thue_augges': row['Ma_Thue'],
                         'vao_ra': row['Vao_Ra'],
                         'khau_tru': row['Khau_Tru'],
                         'name': tcvn3_to_unicode(row['Ten_Thue']),
                         'amount': float(row['Thue_Gtgt']),
                         'type_tax_use': 'sale' if row['Vao_Ra'] == '2' else 'purchase',
                         }
                existing_taxe = self.env["account.tax"].sudo().with_context(active_test=False).search([("ma_thue_augges", "=", row['Ma_Thue'])], limit=1)
                if not existing_taxe:
                    self.env["account.tax"].sudo().create(value)
                else:
                    existing_taxe.write(value)
                self.env.cr.commit()
            max_id = max(id_auggest)
        self.env["ir.config_parameter"].sudo().set_param("mssql.last_synced_tax_id", str(max_id))
        cursor.close()
        conn.close()

    @api.model
    def sync_uom_uom(self):
        conn = self.env['ttb.tools'].get_mssql_connection()
        cursor = conn.cursor()
        cursor.execute(f"""SELECT * FROM DmDvt ORDER BY ID ASC""")
        columns = [column[0] for column in cursor.description]
        uom_uom = [dict(zip(columns, row)) for row in cursor.fetchall()]
        category_id = self.env['uom.category'].search([('name', '=', 'DVT AUGGES')], limit=1)
        if not category_id:
            category_id = self.env['uom.category'].create({'name': 'DVT AUGGES'})
            self.env["uom.uom"].sudo().create({'name': 'DVT AUGGES', 'category_id': category_id.id, 'uom_type': 'reference'})
        for row in uom_uom:
            value = {'id_augges': int(row['ID']),
                     'name': tcvn3_to_unicode(row['Ten_Dvt']),
                     'code_augges': tcvn3_to_unicode(row['Ma_Dvt']),
                     'category_id': category_id.id,
                     'uom_type': 'bigger',
                     'factor': 1,
                     }
            existing_taxe = self.env["uom.uom"].sudo().with_context(active_test=False).search([("id_augges", "=", int(row['ID']))], limit=1)
            if not existing_taxe:
                self.env["uom.uom"].sudo().create(value)
            else:
                existing_taxe.write(value)
            self.env.cr.commit()

    @api.model
    def sync_orders_from_mssql_gau_ghe(self, date_from=False, date_to=False, raise_exception=False):
        """Hàm đồng bộ đơn hàng từ MSSQL về Odoo"""
        conn = self.env['ttb.tools'].get_mssql_connection()
        cursor = conn.cursor()

        currency_id = self.env.company.currency_id
        warehouse_augges = self.env['stock.warehouse'].search([('code', '=', 'AUG')], limit=1)
        if not warehouse_augges:
            warehouse_augges = self.env['stock.warehouse'].create({'code': 'AUG', 'name': 'Kho AUG'})
        session_id = self.env['pos.session'].sudo().search([('config_id.warehouse_id', '=', warehouse_augges.id), ('state', '!=', 'closed')], limit=1)
        if not session_id:
            pos_config = self.env['pos.config'].sudo().search([('warehouse_id', '=', warehouse_augges.id)], limit=1)
            if not pos_config:
                pos_config = self.env['pos.config'].sudo().create({'name': f'POS-{warehouse_augges.display_name}','warehouse_id': warehouse_augges.id, 'picking_type_id': warehouse_augges.pos_type_id.id})
            session_id = self.env['pos.session'].sudo().create({'config_id': pos_config.id})        

        if not date_from:
            date_from = fields.Date.to_string(fields.Date.today())

        if not date_to:
            date_to = fields.Datetime.now() - datetime.timedelta(seconds=10) + datetime.timedelta(hours=7)
            date_to = fields.Datetime.to_string(date_to)

        sql_date_from = f"""and SLBLM.InsertDate >= '{date_from}' """ if date_from else ''
        sql_date_to = f"""and SLBLM.InsertDate <= '{date_to}' """ if date_to else ''
        
        query = f"""
            SELECT
                SLBLM.ID, SLBLM.ID_Kho, SLBLM.Sp, SLBLM.Quay, SLBLM.Tien_Hang, SLBLM.Tien_CK, SLBLM.Tien_Giam, SLBLM.Tien_GtGt, 
                SLBLM.Ngay_In, dmkho.Ma_kho, SLBLM.Printed, SLBLM.ID_Dt, SLBLM.InsertDate
            FROM SLBLM
                join SlBlD ON SlBlD.ID = SlBlM.ID
                LEFT JOIN dmkho on SLBLM.ID_Kho = dmkho.ID 
            WHERE 1=1
                AND SLBLD.ID_Hang in (433062, 432940, 298327, 298328)
                {sql_date_from} {sql_date_to}
                and SLBLM.ID_Kho is not null 

            GROUP BY 
                SLBLM.ID, SLBLM.ID_Kho, SLBLM.Sp, SLBLM.Quay, SLBLM.Tien_Hang, SLBLM.Tien_CK, SLBLM.Tien_Giam, SLBLM.Tien_GtGt, 
                SLBLM.Ngay_In, dmkho.Ma_kho, SLBLM.Printed, SLBLM.ID_Dt, SLBLM.InsertDate
        """
        cursor.execute(query)
        columns = [column[0] for column in cursor.description]
        orders = [dict(zip(columns, row)) for row in cursor.fetchall()]

        #Ghi các đơn gọi lại vào thông số => Sau đó sẽ có 1 job lấy ra gọi lại
        for row in orders:
            date_order = row['Ngay_In'] or row['InsertDate']
            insert_date = fields.Datetime.to_datetime(date_order) - datetime.timedelta(hours=7) if date_order else datetime.now()
            new_session_id = self.env['pos.session']
            ma_kho = row['Ma_kho']
            warehouse = self.env['stock.warehouse'].search([('code_augges', '=', ma_kho)], limit=1)
            if warehouse:
                new_pos_config = self.env['pos.config'].sudo().search([('warehouse_id', '=', warehouse.id)], limit=1)
                if not new_pos_config:
                    new_pos_config = self.env['pos.config'].sudo().create({'name': f'POS-{warehouse.display_name}','warehouse_id': warehouse.id, 'picking_type_id': warehouse.pos_type_id.id})
                new_session_id = self.env['pos.session'].sudo().search([('config_id', '=', new_pos_config.id), ('state', '!=', 'closed')], limit=1)
                if not new_session_id:
                    new_session_id = self.env['pos.session'].sudo().create({'config_id': new_pos_config.id})
            elif raise_exception:
                raise UserError('Không tìm thấy kho, mã: %s' % ma_kho)
            
            #Sinh phiếu dựa vào kho hoá đơn
            invoice_session_id = self.env['pos.session']
            invoice_warehouse = warehouse or warehouse_augges
            if invoice_warehouse:
                invoice_warehouse = invoice_warehouse.ttb_branch_id.vat_warehouse_id
                if not invoice_warehouse:
                    _logger.info(f"Gấu, ghế: Không thể đồng bộ đơn do không tìm thấy kho thuế: {row['ID']}")
                    return
                invoice_session_id = self.env['pos.session'].sudo().search(
                    [('config_id.warehouse_id', '=', invoice_warehouse.id), ('state', '!=', 'closed')], limit=1)
                if not invoice_session_id:
                    invoice_pos_config = self.env['pos.config'].sudo().search(
                        [('warehouse_id', '=', invoice_warehouse.id)], limit=1)
                    if not invoice_pos_config:
                        invoice_pos_config = self.env['pos.config'].sudo().create(
                            {'name': f'POS-{invoice_warehouse.display_name}', 'warehouse_id': invoice_warehouse.id,
                             'picking_type_id': invoice_warehouse.pos_type_id.id})
                    invoice_session_id = self.env['pos.session'].sudo().create({'config_id': invoice_pos_config.id})
            elif raise_exception:
                raise UserError('Không tìm thấy kho hoá đơn, mã: %s' % ma_kho)
            
            order_data = {
                'name': f'''AUGGES/{row["ID"]}/{row['Quay']}/{row['Sp']}''',
                'user_id': 2,
                'session_id': new_session_id.id or session_id.id,
                'id_augges': int(row['ID']),
                'id_kho_augges': int(row['ID_Kho']),
                'id_quay_augges': row['Quay'],
                'sp_augges': row['Sp'],
                'amount_tax': float(row['Tien_GtGt']),
                'amount_paid': float(row['Tien_Hang']) - float(row.get('Tien_Ck', 0)) - float(row.get('Tien_Giam', 0)),
                'amount_total': float(row['Tien_Hang']) - float(row.get('Tien_Ck', 0)) - float(row.get('Tien_Giam', 0)),
                'amount_return': 0,
                'currency_id': currency_id.id,
                'state': 'done',
                'date_order': insert_date.strftime('%Y-%m-%d %H:%M:%S'),
                # 'augges_no_tk': augges_no_tk or '',
            }
            
            # Đơn thường
            id_dt = row['ID_Dt']
            if id_dt:
                partner = self.env['res.partner'].search([('augges_id', '=', id_dt)], limit=1)
                if not partner:
                    _logger.warning(f"Gấu, ghế: Tạo mới khách hàng do Không tìm thấy đối tác với ID_Dt: {id_dt}")
                    partner = self.env['res.partner'].sync_customer(id_dt)
                    if not partner:
                        partner_data = {
                            'augges_id': id_dt,
                            # 'ref': ma_dt,
                            'name': f'''{id_dt} at AUGGES/{row["ID"]}/{row['Quay']}/{row['Sp']}''',
                            # 'vat': mst,
                            # 'street': dia_chi,
                            # 'phone': dien_thoai,
                            'customer_rank': 1,
                        }
                        partner = self.env['res.partner'].create(partner_data)
                order_data['partner_id'] = partner.id
            
            existing_pos_order = self.env["pos.order"].sudo().with_context(active_test=False).search([("id_augges", "=", row['ID']), ('warehouse_origin_id', '=', False)], limit=1)
            
            # Nếu tồn tại đơn cũ và khác số tiền thì xoá đơn đi tạo lại từ đầu
            if existing_pos_order:
                if existing_pos_order.amount_total != order_data['amount_total']:
                    existing_pos_order.with_context(allow_delete=True).write(self.get_lines(order_data, cursor, row['ID'], tien_hang=float(row['Tien_Hang'])))
                    for line in existing_pos_order.lines:
                        line._onchange_amount_line_all()
                    existing_pos_order._compute_prices()
            else:
                new_pos_order = self.env["pos.order"].sudo().create(self.get_lines(order_data, cursor, row['ID'], raise_exception=raise_exception, tien_hang=float(row['Tien_Hang'])))
                for line in new_pos_order.lines:
                    line._onchange_amount_line_all()
                new_pos_order._compute_prices()
                # TODO: fix ngày stock.move.line
                # new_pos_order._create_order_picking()
                _logger.info(f"Gấu, ghế: Created new pos order: {row['ID']}")
        
        cursor.close()
        conn.close()
        _logger.info("Gấu, ghế: pos order sync completed successfully!")
