from odoo import models, fields
import pandas as pd
import pytz
from io import StringIO

import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pandas")


class HangTonKho(models.Model):
    _name = 'hang.ton.kho'
    _description = 'Hàng tồn kho Lấy từ augges'
    # _auto = False


    id_kho = fields.Integer(index=True)
    id_hang = fields.Integer(index=True)
    ma_hang = fields.Char(index=True)
    ma_tong = fields.Char(index=True)
    sl_ton = fields.Float()
    so_luong = fields.Float()

    nam = fields.Integer('Năm')
    mm = fields.Integer('Tháng')
    sngay = fields.Char('Ngày', index=True)

    # Cái này anh Thiện làm, hiện không dùng tới nữa
    def cap_nhat_ton(self, day):
        # day = date_stock.astimezone(pytz.UTC).replace(tzinfo=None)
        # insert_date = day.strftime("%Y-%m-%d %H:%M:%S")
        # sql_day = day.strftime("%Y-%m-%d 00:00:00")
        nam = day.strftime("%y")
        thang = day.strftime("%m")
        sngay = day.strftime("%y%m%d")
        dau_thang = day.strftime("%y%m01")

        query = f"""
        SELECT ID_Kho, ID_Hang, Ma_Hang, Ma_Tong, SUM(Sl_Cky) AS SL_Ton, SUM(So_Luong) AS So_Luong,
            {nam} as nam,
            {thang} as mm,
            {sngay} as sngay
        FROM 
        ( 

        SELECT Htk.ID_Kho, Htk.ID_Hang, DmH.Ma_Hang, ISNULL(DmH.Ma_Tong,SPACE(25)) AS Ma_Tong, SUM(Htk.So_Luong) AS Sl_Cky, CAST(0 AS money) AS So_Luong 
        FROM Htk 
        LEFT JOIN DmKho ON Htk.ID_Kho  = DmKho.ID 
        LEFT JOIN DmH   ON Htk.ID_Hang = DmH.ID 
        LEFT JOIN DmNh  ON DmH.ID_Nhom = DmNh.ID 
        WHERE HTK.Nam = {nam} AND HtK.ID_Dv = 0 AND Htk.Mm = {thang} AND Htk.ID_Kho IS NOT NULL 
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
        WHERE SlNxM.Sngay >= '{dau_thang}' AND SlNxM.Sngay <= '{sngay}' AND SlNxM.ID_Dv = 0 AND SlNxD.ID_Kho IS NOT NULL  AND SlNxD.ID_Hang IS NOT NULL  
        GROUP BY SlNxM.ID_Kho, SlNxD.ID_Hang, DmH.Ma_Hang, DmH.Ma_Tong 

        UNION ALL 
        SELECT SlBlM.ID_Kho, SlBlD.ID_Hang, DmH.Ma_Hang, ISNULL(DmH.Ma_Tong,SPACE(25)) AS Ma_Tong, SUM(- SlBlD.So_Luong) AS Sl_Cky, 
        SUM(CASE WHEN SlBlD.SNgay >='{sngay}' THEN SlBlD.So_Luong ELSE CAST(0 AS money) END) AS So_Luong 
        FROM SlBlD 
        LEFT JOIN SlBlM ON SlBlD.ID      = SlBlM.ID 
        LEFT JOIN DmH   ON SlBlD.ID_Hang = DmH.ID 
        LEFT JOIN DmNh  ON DmH.ID_Nhom   = DmNh.ID 
        WHERE SlBlM.Sngay >= '{dau_thang}' AND SlBlM.Sngay <= '{sngay}' AND SlBlM.ID_Dv = 0 AND ISNULL(SlBlD.ID_Kho,SlBlM.ID_Kho) IS NOT NULL  AND SlBlD.ID_Hang IS NOT NULL  
        GROUP BY SlBlM.ID_Kho, SlBlD.ID_Hang, DmH.Ma_Hang, DmH.Ma_Tong 

        UNION ALL 
        SELECT SlDcD.ID_KhoX AS ID_Kho, SlDcD.ID_Hang, DmH.Ma_Hang, ISNULL(DmH.Ma_Tong,SPACE(25)) AS Ma_Tong, SUM(- SlDcD.So_Luong) AS Sl_Cky, 
        CAST(0 AS money) AS So_Luong 
        FROM SlDcD 
        LEFT JOIN SlDcM ON SlDcD.ID      = SlDcM.ID 
        LEFT JOIN DmKho ON SlDcD.ID_KhoX = DmKho.ID 
        LEFT JOIN DmH   ON SlDcD.ID_Hang = DmH.ID 
        LEFT JOIN DmNh  ON DmH.ID_Nhom   = DmNh.ID 
        WHERE SlDcM.Sngay >= '{dau_thang}' AND SlDcM.Sngay <= '{sngay}' AND SlDcM.ID_Dv = 0 AND SlDcD.ID_KhoX IS NOT NULL 
        GROUP BY SlDcD.ID_KhoX, SlDcD.ID_Hang, DmH.Ma_Hang, DmH.Ma_Tong 

        UNION ALL 
        SELECT SlDcD.ID_KhoN AS ID_Kho, SlDcD.ID_Hang, DmH.Ma_Hang, ISNULL(DmH.Ma_Tong,SPACE(25)) AS Ma_Tong, 
        SUM(SlDcD.So_Luong) AS Sl_Cky, CAST(0 AS money) AS So_Luong 
        FROM SlDcD 
        LEFT JOIN SlDcM ON SlDcD.ID      = SlDcM.ID 
        LEFT JOIN DmKho ON SlDcD.ID_KhoN = DmKho.ID 
        LEFT JOIN DmH   ON SlDcD.ID_Hang = DmH.ID 
        LEFT JOIN DmNh  ON DmH.ID_Nhom   = DmNh.ID 
        WHERE SlDcM.Sngay >= '{dau_thang}' AND SlDcM.Sngay <= '{sngay}' AND SlDcM.ID_Dv = 0 AND SlDcD.ID_KhoN IS NOT NULL 
        GROUP BY SlDcD.ID_KhoN, SlDcD.ID_Hang, DmH.Ma_Hang, DmH.Ma_Tong 

        ) AS Dt_Hang 
        WHERE Sl_Cky<>0 OR So_Luong<>0 
        GROUP BY ID_Kho, ID_Hang, Ma_Hang, Ma_Tong 
        """

        # B1. Xóa các tồn cũ nếu có
        self.env.cr.execute(f"DELETE FROM {self._table} WHERE sngay='{sngay}'")
        
        # B2. Lấy tồn mới
        conn = self.env['ttb.tools'].get_mssql_connection()
        df = pd.read_sql(query, conn)

        buffer = StringIO()
        df.to_csv(buffer, index=False, header=False)
        buffer.seek(0)

        # B3. Insert tồn mới
        self.env.cr.copy_expert(f"COPY {self._table}(id_kho, id_hang, ma_hang, ma_tong, sl_ton, so_luong, nam, mm, sngay) FROM STDIN WITH CSV", buffer)
