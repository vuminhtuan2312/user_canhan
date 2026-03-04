from odoo import models, api, fields
from odoo.exceptions import UserError
import pandas as pd

import logging
_logger = logging.getLogger(__name__)

import logging
_logger = logging.getLogger(__name__)


class TtbAugges(models.AbstractModel):
    _name = 'ttb.augges'
    _description = 'Các hàm lấy dữ liệu từ Augges'

    def get_product_full_info(self, product_id):
        sql = self.env['ir.config_parameter'].sudo().get_param(
            "product.augges_json_sql",
            """
                SELECT
                    h.ID,
                    dbo.TCVNToUnicode(h.Ten_Hang) Ten_Hang,
                    h.Thue, h.ThueV,
                    dbo.TCVNToUnicode(n.Ten_Nganh) Ten_Nganh,
                    dbo.TCVNToUnicode(d.Ten_Dvt) Ten_Dvt
                FROM
                    DmH h
                    LEFT JOIN DmNganh n ON h.ID_Nganh = n.ID
                    LEFT JOIN DmDvt d ON h.ID_Dvt = d.ID
                WHERE h.ID = ?
            """
        )
        conn = self.env['ttb.tools'].get_mssql_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (product_id,))
        row = cursor.fetchone()

        if not row:
            return {}

        columns = [desc[0] for desc in cursor.description]
        result = dict(zip(columns, row))

        cursor.close()
        conn.close()
        return result

    def do_query(self, query, get_dict=True):
        conn = self.env['ttb.tools'].get_mssql_connection()
        
        try:
            cursor = conn.cursor()

            cursor.execute(query)
            rows = cursor.fetchall()

            if not get_dict:
                return rows

            # Lấy tên cột
            columns = [desc[0].lower() for desc in cursor.description]
            result = [dict(zip(columns, row)) for row in rows]
            return result
        finally:
            cursor.close()
            conn.close()

    def get_records_by_id(self, table, record_id, field_list=['ID'], pair_conn=None):
        return self.get_records(table, f'ID={record_id}', field_list, pair_conn=pair_conn)

    def get_records(self, table, domain, field_list=None, get_dict=True, pair_conn=None):
        """
        Lấy dữ liệu từ bảng MSSQL theo điều kiện.

        :param table: tên bảng cần select
        :param domain: chuỗi điều kiện WHERE, ví dụ: "ID = 123 AND Stt = 1"
        :param field_list: danh sách cột cần lấy, nếu không có thì lấy tất cả
        :param get_dict: nếu True thì trả về list[dict], ngược lại trả về list[tuple]
        :param pair_conn: connection nếu có, nếu không sẽ tự mở
        :return: list dữ liệu phù hợp
        """
        owns_conn = False
        conn, cursor = None, None

        try:
            if pair_conn:
                conn = pair_conn
            else:
                conn = self.env['ttb.tools'].get_mssql_connection()
                owns_conn = True

            cursor = conn.cursor()
            field_string = ', '.join(field_list) if field_list else '*'
            query = f"SELECT {field_string} FROM {table} WHERE {domain}"

            cursor.execute(query)
            rows = cursor.fetchall()
            if not rows:
                return []

            if not get_dict:
                return rows

            # Lấy tên cột
            columns = [desc[0].lower() for desc in cursor.description]
            result = [dict(zip(columns, row)) for row in rows]
            return result

        except Exception as e:
            _logger.exception("[SELECT] Lỗi khi lấy dữ liệu từ bảng %s: %s", table, str(e))
            raise

        finally:
            try:
                if cursor:
                    cursor.close()
            except Exception:
                pass
            if owns_conn and conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def get_partner(self, domain, field_list=[]):
        return self.get_records('DmDt', domain, field_list)

    # def update_record(self, table, record_id, vals_string, id_field='ID', domain='', pair_cursor=False):
    #     add_domain = f'AND {domain}' if domain else ''
    #     query = f'''
    #         UPDATE {table} SET {vals_string} WHERE {id_field}={record_id} {add_domain}
    #     '''
    #     if not pair_cursor:
    #         conn = self.env['ttb.tools'].get_mssql_connection_send()
    #         cursor = conn.cursor()
    #         cursor.execute(query)
    #         cursor.commit()
    #         cursor.close()
    #         conn.close()
    #     else:
    #         pair_cursor.execute(query)

    def delete_record(self, record_id, table1, table2='', pair_conn=False):
        query = f'''
            DELETE FROM {table1} WHERE ID={record_id};
        '''
        if table2:
            query += f'''
            DELETE FROM {table2} WHERE ID={record_id};
        '''
        owns_conn = False
        conn, cursor = None, None
        if pair_conn:
            conn = pair_conn
        else:
            conn = self.env['ttb.tools'].get_mssql_connection_send()
            owns_conn = True
        
        cursor = conn.cursor()
        cursor.execute(query)
        _logger.info("[DELETE] Table: %s, ID: %s", table1 + ' ' + table2, record_id)

        if owns_conn:
            conn.commit()
            cursor.close()
            conn.close()
            

    def insert_record(self, table_name, data, pair_conn=None, get_id=True, log_info=True, auto_id=False, auto_sp=False):
        """
        Insert bản ghi vào bảng, có thể lấy ID hoặc không.

        :param table_name: Tên bảng cần insert, ví dụ 'SlNxM' hoặc 'SlNxD'
        :param data: dict dữ liệu cần insert (đối với bảng có PK là ID + Stt, cần truyền sẵn ID và Stt)
        :param pair_conn: pyodbc connection, nếu không có thì tự tạo
        :param get_id: nếu True thì trả về ID vừa insert (dùng cho bảng có PK = ID), nếu False thì không
        :return: ID nếu get_id=True, còn lại trả về None
        """
        owns_conn = False
        conn, cursor = None, None

        try:
            if pair_conn:
                conn = pair_conn
            else:
                conn = self.env['ttb.tools'].get_mssql_connection_send()
                owns_conn = True

            cursor = conn.cursor()

            if auto_id and 'ID' not in data:
                # Tự tính ID mới dựa trên MAX(ID)
                cursor.execute(f"SELECT ISNULL(MAX(ID), 0) + 1 FROM {table_name}")
                new_id = cursor.fetchone()[0]

                data['ID'] = new_id

            if auto_sp and 'Sp' not in data:
                # Tự tính ID mới dựa trên MAX(ID)
                cursor.execute(f"SELECT ISNULL(MAX(Sp), 0) + 1 FROM {table_name}")
                new_sp = cursor.fetchone()[0]

                data['Sp'] = new_sp

            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?' for _ in data])
            values = list(data.values())

            new_id = None
            get_id_string = 'OUTPUT INSERTED.ID' if get_id else ''
            query = f"INSERT INTO {table_name} ({columns}) {get_id_string} VALUES ({placeholders})"
            cursor.execute(query, values)

            if get_id:
                new_id = cursor.fetchone()[0]
                if not new_id:
                    raise UserError("Insert lỗi, không lấy được ID bản ghi")

            if log_info:
                _logger.info("[INSERT] Table: %s, New ID: %s, \nQuery: %s\nValues: %s", table_name, new_id, query, values)

            if owns_conn:
                conn.commit()

            return new_id

        except Exception as e:
            _logger.exception("[INSERT] Lỗi khi insert vào bảng %s: %s", table_name, str(e))
            if owns_conn and conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            raise

        finally:
            try:
                if cursor:
                    cursor.close()
            except Exception:
                pass

            if owns_conn and conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def update_record_by_field(self, table_name, data, field_name, field_value, stt=None, pair_conn=None):
        """
        Cập nhật bản ghi theo một field bất kỳ (vd: So_Ct, Code...)
        và có thể kèm Stt nếu bảng có PK là (field, Stt).

        :param table_name: Tên bảng cần update
        :param data: dict dữ liệu cần cập nhật
        :param field_name: Tên field dùng làm điều kiện (vd: 'So_Ct')
        :param field_value: Giá trị của field
        :param stt: Stt nếu có
        :param pair_conn: pyodbc connection nếu có, nếu không thì tự tạo
        :return: Giá trị field_value đã update
        """
        owns_conn = False
        conn, cursor = None, None

        try:
            if pair_conn:
                conn = pair_conn
            else:
                conn = self.env['ttb.tools'].get_mssql_connection_send()
                owns_conn = True

            cursor = conn.cursor()

            set_clause = ", ".join([f"{col} = ?" for col in data.keys()])
            values = list(data.values())

            if stt is not None:
                where_clause = f"WHERE {field_name} = ? AND Stt = ?"
                values += [field_value, stt]
            else:
                where_clause = f"WHERE {field_name} = ?"
                values.append(field_value)

            query = f"UPDATE {table_name} SET {set_clause} {where_clause}"
            _logger.info("[UPDATE-BY-FIELD] Table: %s\nQuery: %s\nValues: %s", table_name, query, values)

            cursor.execute(query, values)

            if owns_conn:
                conn.commit()

            return field_value

        except Exception as e:
            _logger.exception("[UPDATE-BY-FIELD] Lỗi khi update bảng %s: %s", table_name, str(e))
            if owns_conn and conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            raise

        finally:
            try:
                if cursor:
                    cursor.close()
            except Exception:
                pass

            if owns_conn and conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def update_record(self, table_name, data, record_id, stt=None, pair_conn=None):
        """
        Cập nhật bản ghi theo ID (và Stt nếu có) trong bảng SQL Server.

        :param table_name: Tên bảng cần update
        :param data: dict dữ liệu cần cập nhật
        :param record_id: ID của bản ghi
        :param stt: Stt nếu có (dùng cho bảng có PK là ID + Stt)
        :param pair_conn: pyodbc connection nếu có, nếu không thì tự tạo
        :return: ID bản ghi đã cập nhật
        """
        owns_conn = False
        conn, cursor = None, None

        try:
            if pair_conn:
                conn = pair_conn
            else:
                conn = self.env['ttb.tools'].get_mssql_connection_send()
                owns_conn = True

            cursor = conn.cursor()

            set_clause = ', '.join([f"{key} = ?" for key in data])
            values = list(data.values())

            if stt is not None:
                where_clause = "WHERE ID = ? AND Stt = ?"
                values += [record_id, stt]
            else:
                where_clause = "WHERE ID = ?"
                values += [record_id]

            query = f"UPDATE {table_name} SET {set_clause} {where_clause}"
            _logger.info("[UPDATE] Table: %s\nQuery: %s\nValues: %s", table_name, query, values)

            cursor.execute(query, values)

            if owns_conn:
                conn.commit()

            return record_id

        except Exception as e:
            _logger.exception("[UPDATE] Lỗi khi update bảng %s: %s", table_name, str(e))
            if owns_conn and conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            raise

        finally:
            try:
                if cursor:
                    cursor.close()
            except Exception:
                pass

            if owns_conn and conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def diff_record(self, table_name, data, record_id, stt=None, pair_conn=None):
        """
        So sánh dữ liệu hiện tại trong DB với dữ liệu truyền vào.
        Trả về dict các trường có sự thay đổi.

        :param table_name: Tên bảng cần kiểm tra
        :param data: dict dữ liệu truyền vào
        :param record_id: ID của bản ghi
        :param stt: Stt nếu có (PK dạng ID + Stt)
        :param pair_conn: connection nếu có, nếu không thì tự tạo
        :return: dict các trường có sự thay đổi: {field: {"old": ..., "update": ...}, ...}
        """
        owns_conn = False
        conn, cursor = None, None
        try:
            if pair_conn:
                conn = pair_conn
            else:
                conn = self.env['ttb.tools'].get_mssql_connection()
                owns_conn = True

            cursor = conn.cursor()

            # Tạo WHERE
            if stt is not None:
                where_clause = "WHERE ID = ? AND Stt = ?"
                where_values = [record_id, stt]
            else:
                where_clause = "WHERE ID = ?"
                where_values = [record_id]

            # Tạo câu SELECT với đúng các cột có trong `data`
            columns = ', '.join(data.keys())
            query = f"SELECT {columns} FROM {table_name} {where_clause}"

            cursor.execute(query, where_values)
            row = cursor.fetchone()
            if not row:
                return None

            # So sánh giá trị từng cột
            db_data = dict(zip(data.keys(), row))
            diff = {}

            for key in data:
                db_value = db_data.get(key)
                input_value = data.get(key)

                # So sánh theo kiểu giá trị tương đương
                if db_value != input_value:
                    diff[key] = {"old": db_value, "update": input_value}

            return diff

        except Exception as e:
            _logger.exception("[DIFF] Lỗi khi so sánh dữ liệu bảng %s: %s", table_name, str(e))
            raise

        finally:
            try:
                if cursor:
                    cursor.close()
            except Exception:
                pass

            if owns_conn and conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def get_augges_quantity(self, id_kho, id_hang, conn=False):
        if not id_kho or not id_hang:
            raise Exception('Dữ liệu không hợp lệ, id_kho: %s, id_hang: %s' % (id_kho, id_hang))

        day = fields.Date.today()
        # nam = day.strftime("%Y")
        nam = 2026
        thang = day.strftime("01")
        sngay = day.strftime("%y%m%d")
        dau_nam = "260101"

        query = f"""
        SELECT 
            -- ID_Kho, ID_Hang, Ma_Hang, Ma_Tong, 
            SUM(Sl_Cky) AS SL_Ton
            -- , SUM(So_Luong) AS So_Luong
        FROM 
        ( 

        SELECT Htk.ID_Kho, Htk.ID_Hang, DmH.Ma_Hang, ISNULL(DmH.Ma_Tong,SPACE(25)) AS Ma_Tong, SUM(Htk.So_Luong) AS Sl_Cky, CAST(0 AS money) AS So_Luong 
        FROM Htk 
        LEFT JOIN DmKho ON Htk.ID_Kho  = DmKho.ID 
        LEFT JOIN DmH   ON Htk.ID_Hang = DmH.ID 
        LEFT JOIN DmNh  ON DmH.ID_Nhom = DmNh.ID 
        WHERE HTK.Nam = {nam} AND HtK.ID_Dv = 0 AND Htk.Mm = {thang} AND Htk.ID_Kho = {id_kho} AND Htk.ID_Hang = {id_hang}
        GROUP BY Htk.ID_Kho, Htk.ID_Hang, DmH.Ma_Hang, DmH.Ma_Tong 

        UNION ALL 
        SELECT SlNxM.ID_Kho, SlNxD.ID_Hang, DmH.Ma_Hang, ISNULL(DmH.Ma_Tong,SPACE(25)) AS Ma_Tong, 
        SUM(CASE WHEN DmNx.Ma_Ct IN ('NK','NM','PN','NS','NL') THEN SlNxD.So_Luong ELSE -SlNxD.So_Luong END) AS Sl_Cky, 
        SUM(CASE WHEN SlNxD.SNgay >='{sngay}' AND DmNx.Ma_Ct IN ('XK','XB','NL') THEN (CASE WHEN DmNx.Ma_Ct IN ('XK','XB') THEN SlNxD.So_Luong ELSE -SlNxD.So_Luong END) ELSE CAST(0 AS money) END) AS So_Luong 
        FROM SlNxD 
        LEFT JOIN SlNxM ON SlNxD.ID      = SlNxM.ID 
        LEFT JOIN DmNx  ON SlNxM.ID_Nx   = DmNx.ID 
        LEFT JOIN DmH   ON SlNxD.ID_Hang = DmH.ID 
        LEFT JOIN DmNh  ON DmH.ID_Nhom   = DmNh.ID 
        WHERE SlNxM.Sngay >= '{dau_nam}' AND SlNxM.Sngay <= '{sngay}' AND SlNxM.ID_Dv = 0 AND SlNxD.ID_Kho = {id_kho}  AND SlNxD.ID_Hang = {id_hang}  
        GROUP BY SlNxM.ID_Kho, SlNxD.ID_Hang, DmH.Ma_Hang, DmH.Ma_Tong 

        UNION ALL 
        SELECT SlBlM.ID_Kho, SlBlD.ID_Hang, DmH.Ma_Hang, ISNULL(DmH.Ma_Tong,SPACE(25)) AS Ma_Tong, SUM(- SlBlD.So_Luong) AS Sl_Cky, 
        SUM(CASE WHEN SlBlD.SNgay >='{sngay}' THEN SlBlD.So_Luong ELSE CAST(0 AS money) END) AS So_Luong 
        FROM SlBlD 
        LEFT JOIN SlBlM ON SlBlD.ID      = SlBlM.ID 
        LEFT JOIN DmH   ON SlBlD.ID_Hang = DmH.ID 
        LEFT JOIN DmNh  ON DmH.ID_Nhom   = DmNh.ID 
        WHERE SlBlM.Sngay >= '{dau_nam}' AND SlBlM.Sngay <= '{sngay}' AND SlBlM.ID_Dv = 0 AND ISNULL(SlBlD.ID_Kho,SlBlM.ID_Kho) = {id_kho}  AND SlBlD.ID_Hang = {id_hang}  
        GROUP BY SlBlM.ID_Kho, SlBlD.ID_Hang, DmH.Ma_Hang, DmH.Ma_Tong 

        UNION ALL 
        SELECT SlDcD.ID_KhoX AS ID_Kho, SlDcD.ID_Hang, DmH.Ma_Hang, ISNULL(DmH.Ma_Tong,SPACE(25)) AS Ma_Tong, SUM(- SlDcD.So_Luong) AS Sl_Cky, 
        CAST(0 AS money) AS So_Luong 
        FROM SlDcD 
        LEFT JOIN SlDcM ON SlDcD.ID      = SlDcM.ID 
        LEFT JOIN DmKho ON SlDcD.ID_KhoX = DmKho.ID 
        LEFT JOIN DmH   ON SlDcD.ID_Hang = DmH.ID 
        LEFT JOIN DmNh  ON DmH.ID_Nhom   = DmNh.ID 
        WHERE SlDcM.Sngay >= '{dau_nam}' AND SlDcM.Sngay <= '{sngay}' AND SlDcM.ID_Dv = 0 AND SlDcD.ID_KhoX = {id_kho} AND SlDcD.ID_Hang = {id_hang} 
        GROUP BY SlDcD.ID_KhoX, SlDcD.ID_Hang, DmH.Ma_Hang, DmH.Ma_Tong 

        UNION ALL 
        SELECT SlDcD.ID_KhoN AS ID_Kho, SlDcD.ID_Hang, DmH.Ma_Hang, ISNULL(DmH.Ma_Tong,SPACE(25)) AS Ma_Tong, 
        SUM(SlDcD.So_Luong) AS Sl_Cky, CAST(0 AS money) AS So_Luong 
        FROM SlDcD 
        LEFT JOIN SlDcM ON SlDcD.ID      = SlDcM.ID 
        LEFT JOIN DmKho ON SlDcD.ID_KhoN = DmKho.ID 
        LEFT JOIN DmH   ON SlDcD.ID_Hang = DmH.ID 
        LEFT JOIN DmNh  ON DmH.ID_Nhom   = DmNh.ID 
        WHERE SlDcM.Sngay >= '{dau_nam}' AND SlDcM.Sngay <= '{sngay}' AND SlDcM.ID_Dv = 0 AND SlDcD.ID_KhoN = {id_kho} AND SlDcD.ID_Hang = {id_hang}
        GROUP BY SlDcD.ID_KhoN, SlDcD.ID_Hang, DmH.Ma_Hang, DmH.Ma_Tong 

        ) AS Dt_Hang 
        WHERE Sl_Cky<>0 OR So_Luong<>0 
        GROUP BY ID_Kho, ID_Hang, Ma_Hang, Ma_Tong 
        """
        conn = conn or self.env['ttb.tools'].get_mssql_connection()
        df = pd.read_sql(query, conn)
        sl_ton = df['SL_Ton'].iloc[0] if not df.empty else 0.0
        if pd.isna(sl_ton):
            sl_ton = 0.0

        return sl_ton

    def get_user_id_augges(self, cursor=False, user=False):
        user = user or self.env.user

        if not user or not user.login: return False
        
        if not cursor:
            conn = self.env['ttb.tools'].get_mssql_connection()
            cursor = conn.cursor()

        cursor.execute(f"""select ID from DmUser where LogName='{user.login}'""")
        result = cursor.fetchone()
        user_augges = result[0] if result else False

        return user_augges

    @api.model
    def get_no_co_from_dmnx(self, id_nx, cursor=None):
        """
        Trả về tuple (No_Tk, Co_Tk) theo ID_Nx trong bảng DmNX.
        Nếu không tìm thấy -> trả ('1561', '331')
        """
        no_tk_default, co_tk_default = '1561', '331'
        if not id_nx:
            return no_tk_default, co_tk_default

        owns_conn = False
        try:
            if cursor is None:
                conn = self.env['ttb.tools'].get_mssql_connection_send()
                cursor = conn.cursor()
                owns_conn = True

            sql = f"SELECT No_Tk, Co_Tk FROM DmNX WHERE ID = {id_nx}"
            _logger.info(f"[AUGGES] SQL get_no_co_from_dmnx: {sql}")
            cursor.execute(sql)
            row = cursor.fetchone()
            if row and len(row) >= 2:
                no_tk_default = row[0] or no_tk_default
                co_tk_default = row[1] or co_tk_default
        except Exception as e:
            _logger.warning(f"[AUGGES] Lỗi lấy No_Tk/Co_Tk từ DmNX (ID={id_nx}): {e}")
        finally:
            if owns_conn:
                cursor.close()
                conn.close()

        return no_tk_default, co_tk_default


    def create_slnx(self, master_data, detail_datas, pair_conn=False):
        owns_conn = False
        conn, cursor = None, None

        if pair_conn:
            conn = pair_conn
        else:
            conn = self.env['ttb.tools'].get_mssql_connection_send()
            owns_conn = True

        cursor = conn.cursor()
        total_quantity = sum([line.get('So_Luong', 0) for line in detail_datas])
        if master_data.get('Cong_SlQd') is None or master_data.get('Cong_Sl') is None:
            master_data.update({
                'Cong_SlQd': total_quantity,
                'Cong_Sl': total_quantity,
            })
        # logic lấy tài khoản No_Tk, Co_Tk theo DmNX
        id_nx = master_data.get('ID_Nx')
        no_tk_default, co_tk_default = self.env['ttb.augges'].get_no_co_from_dmnx(id_nx, cursor)
        slnxm_id = self.env['ttb.augges'].insert_record('SlNxM', master_data, conn, auto_sp=True)
        count = 1
        for detail_data in detail_datas:
            detail_data.update({
                'ID': slnxm_id,
                'STT': count,

                'ID_Kho': master_data.get('ID_Kho', False),
                'sngay': master_data.get('sngay', False),
                'ID_Dt': master_data.get('ID_Dt', False),

                'No_Tk': no_tk_default,
                'Co_Tk': co_tk_default,
            })
            self.env['ttb.augges'].insert_record("SlNxD", detail_data, conn, False)
            count += 1

        if owns_conn:
            conn.commit()
            cursor.close()
            conn.close()

        return slnxm_id

