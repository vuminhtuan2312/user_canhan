import uuid
import pytz
import pyodbc
from datetime import datetime, time
from odoo import models, fields, _, api
from odoo.exceptions import UserError
from odoo.addons.ttb_tools.models.ttb_tcvn3 import unicode_to_tcvn3
from datetime import datetime, timedelta

import logging
_logger = logging.getLogger(__name__)

class Currency(models.Model):
    _inherit = "res.currency"

    id_augges = fields.Integer(string='ID Augges')

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    stt_augges = fields.Integer(string='ID Augges')

class StockMove(models.Model):
    _inherit = 'stock.move'

    stt_augges = fields.Integer(string='ID Detail Augges (Stt)')


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'


    is_sent_augges = fields.Boolean(string='Hiển thị button sync Augges', default=False, tracking=True)
    id_augges = fields.Integer(string='ID Augges', copy=False, tracking=True)

    # @api.model
    # def get_mssql_config(self, key, default_value):
    #     """Lấy thông số từ ir.config_parameter, nếu không có thì dùng giá trị mặc định"""
    #     return self.env["ir.config_parameter"].sudo().get_param(key, default_value)

    # def get_mssql_connection(self):
    #     """Lấy thông tin kết nối từ System Parameters"""
    #     server = self.get_mssql_config("mssql.send_server", False)
    #     database = self.get_mssql_config("mssql.send_database", "AA_augges")
    #     username = self.get_mssql_config("mssql.send_username", False)
    #     password = self.get_mssql_config("mssql.send_password", False)
    #     driver = self.get_mssql_config("mssql.driver", "ODBC Driver 18 for SQL Server")
    #     if not server or not username or not password:
    #         raise UserError(f"Không tìm thấy thông tin server, vui lòng liên hệ với admin để được hỗ trợ")
    #     conn_str = f"DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password};TrustServerCertificate=yes"
    #     return pyodbc.connect(conn_str, autocommit=False)

    # def button_sent_augges(self):
    #     self_augges = self.filtered_domain([('is_sent_augges', '=', False), ('partner_id.augges_id', '!=', False), ('warehouse_id.id_augges', '!=', False)])
    #     conn = self.env['ttb.tools'].get_mssql_connection_send()
    #     cursor = conn.cursor()
    #     list_not_done = self - self_augges
    #     for rec in self_augges:
    #         day = rec.date_order.astimezone(pytz.UTC).replace(tzinfo=None)
    #         insert_date = day.strftime("%Y-%m-%d %H:%M:%S")
    #         sql_day = day.strftime("%Y-%m-%d 00:00:00")
    #         sngay = day.strftime("%y%m%d")
    #         currency_id = rec.currency_id.id_augges or 1
    #         tien_hang = sum(line.qty_received * line.price_unit for line in rec.order_line)
    #         qty_received = sum(rec.order_line.mapped('qty_received'))
    #         cursor.execute(f"""select Top 1 sp from SlNxM order by sp desc""")
    #         result_sp = cursor.fetchall()
    #         value_sp = int(result_sp[0][0]) +1 if result_sp else 1
    #         cursor.execute(f"""INSERT INTO SlNxM
    #                            (ID_LrTd, ID_Dv, Ngay, Sngay, Ngay_Ct, 
    #                            Mau_so, Ky_Hieu, So_Ct,NgayKK, ID_Nx, 
    #                            ID_Tt, ID_Dt, ID_Kho,InsertDate, nSo_Ct, 
    #                            So_Bk, SttSp, Sp, SpTc, Ty_Gia, 
    #                            IP_ID, Tien_hang, Tong_Tien, Tien_Gtgt, Cong_SlQd, 
    #                            Cong_Sl, LastEdit, IsEHD, Tong_Nt, Vs, 
    #                            Tien_Cp, Dien_Giai, ID_Uni, LoaiCt)
    #                            VALUES
    #                            (0, 0, '{sql_day}','{sngay}','{sql_day}', 
    #                            '{rec.ttb_vendor_invoice_code or ""}', '{rec.ttb_vendor_invoice_code or ""}', '{rec.ttb_vendor_invoice_no or ""}','{sql_day}', 26,
    #                            {currency_id}, {rec.partner_id.augges_id}, {rec.warehouse_id.id_augges}, '{insert_date}', 0,
    #                            '', 0, {value_sp}, 0, 0,
    #                            0,{tien_hang}, {rec.amount_total}, {rec.amount_tax},{qty_received},
    #                            {qty_received}, '{insert_date}', 0, 0,'250103',
    #                            0, '{rec.name}', '{uuid.uuid4()}', '')
    #                            SELECT SCOPE_IDENTITY();
    #                         """)
    #         cursor.execute("SELECT SCOPE_IDENTITY();")
    #         slnxm_id = cursor.fetchone()[0]
    #         count = 1
    #         tien_ck_total = 0
    #         tax_total = 0
    #         list_insert = f"""(ID, stt, md, Sngay, ID_Dt, 
    #                        ID_Kho, ID_Hang, Sl_Qd, 
    #                        So_Luong, 
    #                        So_LuongT, 
    #                        Gia_Vat,
    #                        Gia_Kvat, Gia_Qd, Don_Gia, T_Tien, Tyle_Ck, 
    #                        ID_Tt, Ty_Gia, ID_Thue, Tien_GtGt, Hs_Qd,
    #                        Don_Gia1, T_Tien1, Sl_Yc, Gia_Nt, Tien_Nt, 
    #                        Tien_Ck, Tien_CKPb, No_Tk, Co_Tk, No_Tk1, Co_Tk1, Stt_Dh, Ghi_Chu
    #                        ) """
    #         for line in rec.order_line:
    #             taxes_id = line.taxes_id.mapped('id_augges')
    #             price_total = line.price_unit * line.qty_received
    #             tien_ck = (line.discount * price_total)/100
    #             tien_ck_total += tien_ck
    #             tax_total += line.price_tax
    #             cursor.execute(f"""INSERT INTO SlNxD
    #                                {list_insert}
    #                                VALUES
    #                                ({slnxm_id}, {count},'', '{sngay}', {rec.partner_id.augges_id}, 
    #                                 {rec.warehouse_id.id_augges}, {line.product_id.product_tmpl_id.augges_id}, {line.qty_received}, 
    #                                 {line.qty_received}, 
    #                                 {line.qty_received}, 
    #                                 {line.price_unit}, 
    #                                 {line.price_unit}, {line.price_unit}, {line.price_unit}, {price_total}, {line.discount},
    #                                 {currency_id}, {rec.currency_rate}, {taxes_id[0] if taxes_id else 'Null'}, {line.price_tax}, '',
    #                                 {line.price_unit}, {price_total}, {line.qty_received}, 0, 0,
    #                                 {tien_ck} , 0, '1561', '331', '', '', 0, '' )
    #                             """)
    #             line.write({'stt_augges': count})
    #             count += 1
    #         if tien_ck_total:
    #             cursor.execute(f"""INSERT INTO SlNxD 
    #                                {list_insert}
    #                                VALUES
    #                                ({slnxm_id}, {count}, 1, '{sngay}', {rec.partner_id.augges_id}, 
    #                                 {rec.warehouse_id.id_augges}, Null, 0, 
    #                                 0,
    #                                 0, 
    #                                 0, 
    #                                 0, 0, 0, {tien_ck_total}, 0,
    #                                 {currency_id}, {rec.currency_rate}, Null, 0, '',
    #                                 0, 0, 0, 0, 0,
    #                                 0 , 0, '1561', '331', '', '', 0, '{unicode_to_tcvn3("Chiết khấu, giảm giá")}')
    #                             """)
    #             count += 1
    #         if tax_total:
    #             cursor.execute(f"""INSERT INTO SlNxD 
    #                                {list_insert}
    #                                VALUES
    #                                ({slnxm_id}, {count}, 7, '{sngay}', {rec.partner_id.augges_id}, 
    #                                 {rec.warehouse_id.id_augges}, Null, 0, 
    #                                 0,
    #                                 0, 
    #                                 0, 
    #                                 0, 0, 0, {tax_total}, 0,
    #                                 {currency_id}, {rec.currency_rate}, Null, 0, '',
    #                                 0, 0, 0, 0, 0,
    #                                 0 , 0, '1561', '331', '', '', 0, '{unicode_to_tcvn3("Thuế GTGT")}')
    #                             """)
    #             count += 1
    #         rec.write({'id_augges': slnxm_id, 'is_sent_augges': True})
    #         cursor.commit()
    #     cursor.close()
    #     conn.close()
    #     if list_not_done:
    #         raise UserError(f"Phiếu mua hàng đã đồng bộ, vui lòng kiểm tra lại {', '.join(list_not_done.mapped('name'))}")

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_sent_augges = fields.Boolean(string='Hiển thị button sync Augges', default=False, tracking=True)
    id_augges = fields.Integer(string='ID Augges', copy=False, tracking=True)
    sp_augges = fields.Char('Số phiếu Augges', tracking=True)
    purchase_is_sent_augges = fields.Boolean(string="Đã gửi dữ liệu", related='purchase_id.is_sent_augges')
    pending_sent_augges = fields.Boolean('Chưa tạo Augges khi xác nhận', default=False)
    pending_sent_augges_message = fields.Text('Tạo Augges lỗi')

    def update_augges_invoice(self, auto_create=True, invoices_to_push=None):
        for rec_stock in self:
            if not rec_stock.id_augges:
                if auto_create:
                    rec_stock.button_sent_augges()
                    if not rec_stock.id_augges:
                        message = 'Không cập nhật được thông tin hoá đơn cho phiếu nhập Augges do không tìm thấy id_augges'
                        rec_stock.write({'pending_sent_augges': True, 'pending_sent_augges_message': f"{rec_stock.pending_sent_augges_message or ''}\n{message}"})
                        _logger.info(message)
                        continue
                else:
                    message = 'Không cập nhật được thông tin hoá đơn do chưa tạo phiếu ở Augges (chưa có id_augges)'
                    rec_stock.write({'pending_sent_augges': True, 'pending_sent_augges_message': f"{rec_stock.pending_sent_augges_message or ''}\n{message}"})
                    continue

            invoices = self.env['ttb.nimbox.invoice'].browse(invoices_to_push) if invoices_to_push is not None else rec_stock.invoice_ids
            if not invoices:
                continue

            # Ghep noi thong tin tu nhieu hoa don
            # Lấy ngày đầu tiên từ danh sách (nếu có)
            invoice_date = invoices.mapped('ttb_vendor_invoice_date')[0] if invoices.mapped('ttb_vendor_invoice_date') else None


            vendor_invoice_codes = ', '.join(set(inv.ttb_vendor_invoice_code for inv in invoices if inv.ttb_vendor_invoice_code))
            vendor_invoice_nos = ', '.join(set(inv.ttb_vendor_invoice_no for inv in invoices if inv.ttb_vendor_invoice_no))

            # logic mói 2702 lấy sngay, ngay theo thời gian được cập nhập thông tin (không sửa lại sngy và ngay)

            update_vals = {
                "Ngay_Ct": invoice_date,
                "Mau_so": vendor_invoice_codes,
                "Ky_Hieu": vendor_invoice_codes,
                "So_Ct": vendor_invoice_nos,
                # "Sngay": day.strftime('%y%m%d') if day else '',
                # "Ngay": day
            }
            # update_vals_day = {
            #     "Sngay": day.strftime('%y%m%d') if day else '',
            # }

            augges_order = self.env['ttb.augges'].update_record('SlNxM', update_vals, rec_stock.id_augges)
            # augges_order_update = self.env['ttb.augges'].update_record('SlNxD', update_vals_day, rec_stock.id_augges)

    def button_sent_augges_again(self):
        self.ensure_one()

        if not self.id_augges: 
            raise UserError('Chưa có ID Augges')
        augges_record = self.env['ttb.augges'].get_records_by_id('SlNxM', self.id_augges)
        if not augges_record:
            raise UserError('Không tìm thấy bản ghi Augges cũ, ID: %s', self.id_augges)

        _logger.info('Xoá vào tạo lại phiếu augges, id phiếu odoo: %s, id auggges: %s', self.id, self.id_augges)
        conn = self.env['ttb.tools'].get_mssql_connection_send()

        self.env['ttb.augges'].delete_record(self.id_augges, 'SlNxM', 'SlNxD', conn)
        self.button_sent_augges(conn, re_create=True)

        conn.commit()
        conn.close()

    def button_sent_augges(self, pair_conn=False, re_create=False):
        """
        Có hiện tượng phiếu nhập kho ở Augges bị giá trị 0 ở So_Luong, Thanh_Tien
        Dự đoán nguyên nhân do 1 dòng bất kỳ có So_Luong là 0 thì Augges reset hết về 0
        """
        self.ensure_one()

        if self.state != 'done':
            raise UserError('Phiếu chưa hoàn thành')
        if self.id_augges and not re_create: return

        augges_ref = self.partner_id.ref

        # Confirm: trường hợp không có thông tin nhà cung cấp đánh dấu lại và bỏ qua đi tiếp
        if not augges_ref:
            message = 'Nhà cung cấp không có thông tin Mã tham chiếu.'
            self.write({'pending_sent_augges': True, 'pending_sent_augges_message': f"{self.pending_sent_augges_message or ''}\n{message}"})
            return

        domain = f"Ma_Dt = '{augges_ref}'"
        partner_augges = self.env['ttb.augges'].get_partner(domain)
        if not partner_augges:
            message = 'Không tìm thấy nhà cung cấp ở Augges'
            self.write({'pending_sent_augges': True, 'pending_sent_augges_message': f"{self.pending_sent_augges_message or ''}\n{message}"})
            return

        augges_id = partner_augges[0]['id']

        # self_augges = self.filtered_domain([
        #     ('is_sent_augges', '=', False), 
        #     ('partner_id.augges_id', '!=', False), 
        #     ('picking_type_id.warehouse_id.id_augges', '!=', False), 
        #     ('purchase_id', '!=', False), ('purchase_id.is_sent_augges', '=', False)
        # ])
        # list_not_done = self - self_augges
        # if list_not_done:
        #     raise UserError(f"Phiếu nhập đã được tạo ở Augges, hoặc không tìm thấy thông tin NCC tương ứng ở Augges. Vui lòng kiểm tra lại {', '.join(list_not_done.mapped('name'))}")

        owns_conn = False
        conn, cursor = None, None
        if pair_conn:
            conn = pair_conn
        else:
            conn = self.env['ttb.tools'].get_mssql_connection_send()
            owns_conn = True
        cursor = conn.cursor()

        for rec_stock in self:
            _logger.info('Tạo phiếu nhập Augges cho phiếu nhập odoo id: %s, name: %s', rec_stock.id, rec_stock.name)
            rec = rec_stock.purchase_id
            # day = rec_stock.date_done.astimezone(pytz.UTC).replace(tzinfo=None)
            # day = (rec_stock.date_done or datetime.now()).astimezone(pytz.UTC).replace(tzinfo=None)
            # sql_day = day.strftime("%Y-%m-%d 00:00:00")
            # sngay = day.strftime("%y%m%d")
            invoice_date = rec_stock.invoice_ids[:1].ttb_vendor_invoice_date
            if invoice_date:
                day = invoice_date
                invoice_date = invoice_date.strftime("%Y-%m-%d")
            else:
                day = (rec_stock.date_done or datetime.now()).astimezone(pytz.UTC).replace(tzinfo=None)
                invoice_date = ''
            # logic mói 2702 lấy sngay, ngay theo thời gian được cập nhập thông tin
            day = datetime.now().astimezone(pytz.UTC).replace(tzinfo=None)
            sql_day = day.strftime("%Y-%m-%d 00:00:00")
            sngay = day.strftime("%y%m%d")
            rec_currency_id = rec_stock.currency_id or rec_stock.company_id.currency_id
            currency_id = rec_currency_id.id_augges or 1
            # tien_hang = sum(line.qty_received * line.price_unit for line in rec.order_line)
            tien_hang = sum(line.quantity * line.ttb_price_unit for line in rec_stock.move_ids_without_package)
            qty_received = sum(rec_stock.move_ids_without_package.mapped('quantity'))
            dien_giai = f'{rec.name} - {rec_stock.name}'
            user_id = False
            if rec_stock.done_user_id:
                cursor.execute(f"""select ID from DmUser where LogName='{rec_stock.done_user_id.login}'""")
                result = cursor.fetchone()
                user_id = result[0] if result else False
            if re_create and rec_stock.sp_augges:
                value_sp = rec_stock.sp_augges
            else:
                cursor.execute(f"""select Top 1 sp from SlNxM order by sp desc""")
                result_sp = cursor.fetchall()
                value_sp = int(result_sp[0][0]) +1 if result_sp else 1
            taxes_id_all = rec_stock.move_ids_without_package.ttb_taxes_id.filtered(lambda x: x.id_augges)[:1].id_augges or None
            insert_date = datetime.utcnow() + timedelta(hours=7)
            data = {
                "ID_LrTd": 0,
                "ID_Dv": 0,
                "Ngay": sql_day,
                "Sngay": sngay,
                "Ngay_Ct": invoice_date,
                "Mau_so": rec_stock.ttb_vendor_invoice_code or "",
                "Ky_Hieu": rec_stock.ttb_vendor_invoice_code or "",
                "So_Ct": rec_stock.ttb_vendor_invoice_no or "",
                "NgayKK": sql_day,
                "ID_Nx": 26,
                "ID_Tt": currency_id,
                "ID_Dt": augges_id,
                "ID_Kho": rec.warehouse_id.id_augges,
                "InsertDate": insert_date,
                "nSo_Ct": 0,
                "So_Bk": "",
                "SttSp": 0,
                "Sp": value_sp,
                "SpTc": 0,
                "Ty_Gia": 0,
                "IP_ID": 0,
                "Tien_hang": tien_hang,
                "Tong_Tien": rec_stock.amount_total,
                "Tien_Gtgt": rec_stock.amount_tax,
                "Cong_SlQd": qty_received,
                "Cong_Sl": qty_received,
                "LastEdit": datetime.now(),
                "IsEHD": 0,
                "Tong_Nt": 0,
                "Vs": '250103',
                "Tien_Cp": 0,
                "Dien_Giai": dien_giai,
                "ID_Uni": str(uuid.uuid4()),
                "LoaiCt": '',
                "UserID": user_id if user_id else None,                
                "No_Vat": '1331',
                "Co_Vat": '331',
                "ID_Thue": taxes_id_all,
            }
            no_tk_default, co_tk_default = self.env['ttb.augges'].get_no_co_from_dmnx(data['ID_Nx'], cursor)
            slnxm_id = self.env['ttb.augges'].insert_record('SlNxM', data, conn)

            count = 1
            tien_ck_total = 0
            tax_total = 0
            list_insert = f"""(
                ID, stt, md, Sngay, ID_Dt, 
                ID_Kho, ID_Hang, Sl_Qd, So_Luong, So_LuongT, Gia_Vat,
                
                Gia_Kvat, Gia_Qd, Don_Gia, T_Tien, Tyle_Ck, 
                ID_Tt, Ty_Gia, ID_Thue, Tien_GtGt, Hs_Qd,
                
                Don_Gia1, T_Tien1, Sl_Yc, Gia_Nt, Tien_Nt, 
                Tien_Ck, Tien_CKPb, No_Tk, Co_Tk, No_Tk1, Co_Tk1, Stt_Dh, Ghi_Chu
            ) """
            # for line in rec.order_line:
            AccountTax = self.env['account.tax']
            for line in rec_stock.move_ids_without_package:
                if line.quantity == 0: continue
                taxes_id = line.ttb_taxes_id.mapped('id_augges')
                price_total = line.ttb_price_unit * line.quantity
                tien_ck = (line.ttb_discount * price_total)/100
                tien_ck_total += tien_ck

                base_lines = [line._prepare_base_line_for_taxes_computation()]
                AccountTax._add_tax_details_in_base_lines(base_lines, rec_stock.company_id)
                AccountTax._round_base_lines_tax_details(base_lines, rec_stock.company_id)
                tax_totals = AccountTax._get_tax_totals_summary(
                    base_lines=base_lines,
                    currency=rec_stock.currency_id or rec_stock.company_id.currency_id,
                    company=rec_stock.company_id,
                )
                amount_tax = tax_totals['tax_amount_currency']
                tax_total += amount_tax

                data = {
                    'ID': slnxm_id,
                    'Stt': count,
                    'md': '',
                    'Sngay': sngay,
                    'ID_Dt': augges_id,
                    
                    'ID_Kho': rec.warehouse_id.id_augges,
                    'ID_Hang': line.product_id.product_tmpl_id.augges_id,
                    'Sl_Qd': line.quantity,
                    'So_Luong': line.quantity,
                    'So_LuongT': line.quantity,
                    'Gia_Vat': line.ttb_price_unit,
                    
                    'Gia_Kvat': line.ttb_price_unit,
                    'Gia_Qd': line.ttb_price_unit,
                    'Don_Gia': line.ttb_price_unit,
                    'T_Tien': price_total,
                    'Tyle_Ck': line.ttb_discount,
                    
                    'ID_Tt': currency_id,
                    'Ty_Gia': rec.currency_rate,
                    'ID_Thue': taxes_id[0] if taxes_id else None,
                    'Tien_GtGt': amount_tax,
                    'Hs_Qd': '',
                    
                    'Don_Gia1': line.ttb_price_unit,
                    'T_Tien1': price_total,
                    'Sl_Yc': line.quantity,
                    'Gia_Nt': 0,
                    'Tien_Nt': 0,
                    
                    'Tien_Ck': tien_ck,
                    'Tien_CKPb': 0,
                    'No_Tk': no_tk_default,
                    'Co_Tk': co_tk_default,
                    'No_Tk1': '',
                    'Co_Tk1': '',
                    'Stt_Dh': 0,
                    'Ghi_Chu': '',
                }
                # Gọi hàm insert, không cần lấy ID vì đã có ID + Stt
                self.env['ttb.augges'].insert_record("SlNxD", data, conn, False)
                line.write({'stt_augges': count})
                count += 1
            if tien_ck_total:
                data = {
                    'ID': slnxm_id,
                    'Stt': count,
                    'md': 1,
                    'Sngay': sngay,
                    'ID_Dt': augges_id,

                    'ID_Kho': rec.warehouse_id.id_augges,
                    'ID_Hang': None,
                    'Sl_Qd': 0,
                    'So_Luong': 0,
                    'So_LuongT': 0,
                    'Gia_Vat': 0,

                    'Gia_Kvat': 0,
                    'Gia_Qd': 0,
                    'Don_Gia': 0,
                    'T_Tien': tien_ck_total,
                    'Tyle_Ck': 0,

                    'ID_Tt': currency_id,
                    'Ty_Gia': rec.currency_rate,
                    'ID_Thue': None,
                    'Tien_GtGt': 0,
                    'Hs_Qd': '',

                    'Don_Gia1': 0,
                    'T_Tien1': 0,
                    'Sl_Yc': 0,
                    'Gia_Nt': 0,
                    'Tien_Nt': 0,

                    'Tien_Ck': 0,
                    'Tien_CKPb': 0,
                    'No_Tk': no_tk_default,
                    'Co_Tk': co_tk_default,
                    'No_Tk1': '',
                    'Co_Tk1': '',
                    'Stt_Dh': 0,
                    'Ghi_Chu': unicode_to_tcvn3("Chiết khấu, giảm giá"),
                }
                self.env['ttb.augges'].insert_record("SlNxD", data, conn, False)
                count += 1
            if tax_total:
                data = {
                    'ID': slnxm_id,
                    'Stt': count,
                    'md': 7,
                    'Sngay': sngay,
                    'ID_Dt': augges_id,

                    'ID_Kho': rec.warehouse_id.id_augges,
                    'ID_Hang': None,
                    'Sl_Qd': 0,
                    'So_Luong': 0,
                    'So_LuongT': 0,
                    'Gia_Vat': 0,

                    'Gia_Kvat': 0,
                    'Gia_Qd': 0,
                    'Don_Gia': 0,
                    'T_Tien': tax_total,
                    'Tyle_Ck': 0,

                    'ID_Tt': currency_id,
                    'Ty_Gia': rec.currency_rate,
                    'ID_Thue': taxes_id_all,
                    'Tien_GtGt': 0,
                    'Hs_Qd': '',

                    'Don_Gia1': 0,
                    'T_Tien1': 0,
                    'Sl_Yc': 0,
                    'Gia_Nt': 0,
                    'Tien_Nt': 0,

                    'Tien_Ck': 0,
                    'Tien_CKPb': 0,
                    'No_Tk': '1331',
                    'Co_Tk': '331',
                    'No_Tk1': '',
                    'Co_Tk1': '',
                    'Stt_Dh': 0,
                    'Ghi_Chu': unicode_to_tcvn3("Thuế GTGT"),
                }
                self.env['ttb.augges'].insert_record("SlNxD", data, conn, False)
                count += 1

            rec_stock.write({
                'id_augges': slnxm_id, 
                'is_sent_augges': True,
                'sp_augges': value_sp,
            })

            # TODO: Thiện nghĩ có thể Bỏ lệnh update PO dưới đây.
            rec.write({'id_augges': slnxm_id, 'is_sent_augges': True})
        if owns_conn:
            conn.commit()
            cursor.close()
            conn.close()
