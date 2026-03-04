from odoo import models, fields, api, _
import pandas as pd

class CheckInventoryWizard(models.Model):
    _name = 'check.inventory.wizard'
    _description = 'Wizard cập nhật tồn thực tế'

    line_id = fields.Many2one('stock.check.line', string='Dòng kiểm tồn', required=True)
    qty_real = fields.Float(string='Tồn thực tế mới', required=True)
    def get_augges_quantity(self, id_kho, id_hang):
        day = fields.Date.today()
        nam = day.strftime("%Y")
        thang = day.strftime("01")
        sngay = day.strftime("%y%m%d")
        dau_nam = "260101"

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
        conn = self.env['ttb.tools'].get_mssql_connection()
        df = pd.read_sql(query, conn)
        sl_ton = df['SL_Ton'].iloc[0] if not df.empty else 0.0
        if pd.isna(sl_ton):
            sl_ton = 0.0

        return sl_ton
    def action_confirm(self):
        for wizard in self:
            line = wizard.line_id
            line.qty_real = wizard.qty_real
            line.user_perform = "[" + self.env.user.login + "] " + self.env.user.name
            line.time_done_real = fields.Datetime.now()
            line.state_check = 'done'
            if line.product_id and line.product_id.product_tmpl_id.augges_id:
                # Mapping branch -> kho
                branch_default_kho = {
                    14: 8,
                    15: 77,
                    16: 25,
                    17: 11,
                    18: 2,
                    19: 1,
                    20: 39,
                    21: 26,
                    22: 16,
                    23: 13,
                    24: 57,
                    25: 67,
                    26: 58
                }
                branch_id = line.session_id.branch_id.id
                id_kho = branch_default_kho.get(branch_id)
                id_hang = line.product_id.product_tmpl_id.augges_id

                if id_kho and id_hang:
                    line.stock_qty = self.get_augges_quantity(id_kho, id_hang)

        return {'type': 'ir.actions.act_window_close'}
