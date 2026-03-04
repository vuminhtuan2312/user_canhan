from odoo import models, fields, api
from odoo.exceptions import UserError
import pandas as pd
from io import StringIO
from datetime import date, datetime, time, timedelta
import logging

_logger = logging.getLogger(__name__)

class XuatNhapKho(models.Model):
    _name = 'ttb.xuat.nhap.kho'
    _description = 'Xuất nhập kho Augges'
    _order = 'insert_date desc, id desc'

    id_kho = fields.Integer(string='ID Kho', index=True)
    co_so = fields.Char(string='Cơ sở')
    id_dv = fields.Integer(string='ID DV', index=True)
    id_nx = fields.Integer(string='ID NX', index=True)
    loai_nx = fields.Char(string='Loại NX')
    loai_phieu = fields.Char(string='Loại phiếu', index=True)

    ngay_ct = fields.Datetime(string='Ngày CT')
    ngay_ct_local = fields.Datetime(string='Ngày CT*', compute='_compute_ngay_ct_local')
    sngay = fields.Char(string='SNgay', index=True)

    insert_date = fields.Datetime(string='InsertDate', index=True)
    insert_date_local = fields.Datetime(string='InsertDate*', compute='_compute_insert_date_local')
    id_phieu = fields.Integer(string='ID Phiếu', index=True)
    so_phieu = fields.Char(string='Số phiếu', index=True)
    dien_giai = fields.Char(string='Diễn giải')
    id_hang = fields.Integer(string='ID Hàng', index=True)
    ma_hang = fields.Char(string='Mã hàng', index=True)
    ma_vach = fields.Char(string='Mã vạch')
    ten_hang = fields.Char(string='Tên hàng')
    so_luong = fields.Float(string='Số lượng')

    @api.depends('insert_date')
    def _compute_insert_date_local(self):
        for record in self:
            record.insert_date_local = record.insert_date - timedelta(hours=7)

    @api.depends('ngay_ct')
    def _compute_ngay_ct_local(self):
        for record in self:
            record.ngay_ct_local = record.ngay_ct - timedelta(hours=7)

    def action_open_sync_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Đồng bộ Xuất nhập kho Augges',
            'res_model': 'ttb.xuat.nhap.kho.augges.sync.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {},
        }

    def _cap_nhat_ton(self, date_start, date_end):

        dt_start_local = fields.Datetime.context_timestamp(self, date_start)
        dt_end_local = fields.Datetime.context_timestamp(self, date_end)

        date_start_str = dt_start_local.strftime('%Y-%m-%d %H:%M:%S')
        date_end_str = dt_end_local.strftime('%Y-%m-%d %H:%M:%S')

        query = f"""
    WITH RawData AS (
        SELECT
            SlNxM.ID_Kho, SlNxM.ID_DV, DmNx.ID AS ID_Nx, dbo.tcvntounicode(DmNx.Ten_Nx) AS Loai_NX, 'SLNX' AS Loai_Phieu,
            SlNxM.Ngay_Ct, SlNxM.SNgay, CAST(SlNxM.InsertDate AS datetime2(0)) AS InsertDate, SlNxM.ID AS ID_Phieu, SlNxM.Sp AS SoPhieu,
            dbo.tcvntounicode(SlNxM.Dien_Giai) AS Dien_Giai, SlNxD.ID_Hang, DmH.Ma_Hang, DmH.Ma_Vach, dbo.tcvntounicode(DmH.ten_hang) AS ten_hang,
            CASE WHEN DmNx.Ma_Ct IN ('NK','NM','PN','NS','NL') THEN SlNxD.So_Luong ELSE -SlNxD.So_Luong END AS So_Luong,
            NULL AS NgayXn, NULL AS So_Bk
        FROM SlNxM
        JOIN SlNxD ON SlNxD.ID = SlNxM.ID
        JOIN DmNx ON DmNx.ID = SlNxM.ID_Nx
        JOIN DmH ON DmH.ID = SlNxD.ID_Hang
        WHERE SlNxM.InsertDate BETWEEN '{date_start_str}' AND '{date_end_str}'
        AND SlNxM.ID_Kho BETWEEN 132 AND 144 AND SlNxM.id_dv = 0

        UNION ALL
        SELECT
            SlDcD.ID_KhoX AS ID_Kho, SlDcM.ID_DV, DmNx.ID AS ID_Nx, dbo.tcvntounicode(DmNx.Ten_Nx) AS Loai_NX, 'SLDC' AS Loai_Phieu,
            SlDcM.Ngay_Ct, SlDcM.SNgay, CAST(SlDcM.InsertDate AS datetime2(0)) AS InsertDate, SlDcM.ID AS ID_Phieu, SlDcM.Sp AS SoPhieu,
            dbo.tcvntounicode(SlDcM.Dien_Giai) AS Dien_Giai, SlDcD.ID_Hang, DmH.Ma_Hang, DmH.Ma_Vach, dbo.tcvntounicode(DmH.ten_hang) AS ten_hang,
            -SlDcD.So_Luong AS So_Luong, SlDcM.NgayXn, SlDcM.So_Bk
        FROM SlDcM
        JOIN SlDcD ON SlDcD.ID = SlDcM.ID
        JOIN DmNx ON DmNx.ID = SlDcM.ID_Nx
        JOIN DmH ON DmH.ID = SlDcD.ID_Hang
        WHERE SlDcM.InsertDate BETWEEN '{date_start_str}' AND '{date_end_str}'
        AND SlDcD.ID_KhoX BETWEEN 132 AND 144 AND SlDcM.id_dv = 0

        UNION ALL
        SELECT
            SlDcD.ID_KhoN AS ID_Kho, SlDcM.ID_DV, DmNx.ID AS ID_Nx, dbo.tcvntounicode(DmNx.Ten_Nx) AS Loai_NX, 'SLDC' AS Loai_Phieu,
            SlDcM.Ngay_Ct, SlDcM.SNgay, CAST(SlDcM.InsertDate AS datetime2(0)) AS InsertDate, SlDcM.ID AS ID_Phieu, SlDcM.Sp AS SoPhieu,
            dbo.tcvntounicode(SlDcM.Dien_Giai) AS Dien_Giai, SlDcD.ID_Hang, DmH.Ma_Hang, DmH.Ma_Vach, dbo.tcvntounicode(DmH.ten_hang) AS ten_hang,
            SlDcD.So_Luong AS So_Luong, SlDcM.NgayXn, SlDcM.So_Bk
        FROM SlDcM
        JOIN SlDcD ON SlDcD.ID = SlDcM.ID
        JOIN DmNx ON DmNx.ID = SlDcM.ID_Nx
        JOIN DmH ON DmH.ID = SlDcD.ID_Hang
        WHERE SlDcM.InsertDate BETWEEN '{date_start_str}' AND '{date_end_str}'
        AND SlDcD.ID_KhoN BETWEEN 132 AND 144 AND SlDcM.id_dv = 0

        UNION ALL
        SELECT
            SlBlM.ID_Kho, SlBlM.ID_DV, DmNx.ID AS ID_Nx, dbo.tcvntounicode(DmNx.Ten_Nx) AS Loai_NX, 'SLBL' AS Loai_Phieu,
            SlBlM.Ngay_Ct, SlBlM.SNgay, CAST(SlBlM.InsertDate AS datetime2(0)) AS InsertDate, SlBlM.ID AS ID_Phieu, SlBlM.Sp AS SoPhieu,
            dbo.tcvntounicode(SlBlM.Dien_Giai) AS Dien_Giai, SlBlD.ID_Hang, DmH.Ma_Hang, DmH.Ma_Vach, dbo.tcvntounicode(DmH.ten_hang) AS ten_hang,
            -SlBlD.So_Luong AS So_Luong, NULL AS NgayXn, NULL AS So_Bk
        FROM SlBlM
        JOIN SlBlD ON SlBlD.ID = SlBlM.ID
        JOIN DmNx ON DmNx.ID = SlBlM.ID_Nx
        JOIN DmH ON DmH.ID = SlBlD.ID_Hang
        WHERE SlBlM.InsertDate BETWEEN '{date_start_str}' AND '{date_end_str}'
        AND SlBlM.ID_Kho BETWEEN 132 AND 144 AND SlBlM.id_dv = 0
    ),
    ProcessedData AS (
        SELECT
            *,
            DENSE_RANK() OVER (
                PARTITION BY SoPhieu, Loai_Phieu, ID_Kho
                ORDER BY
                    CASE
                        WHEN Loai_Phieu = 'SLDC' AND So_Luong > 0 THEN
                            CASE WHEN NgayXn IS NOT NULL AND So_Bk = 'XNDC' THEN 0 ELSE 1 END
                        ELSE 0
                    END ASC,
                    InsertDate DESC,
                    ID_Phieu DESC
            ) AS RowRank
        FROM RawData
    )
    SELECT
        ID_Kho,
        CASE ID_Kho
            WHEN 132 THEN N'Xuân Thủy' WHEN 133 THEN N'Nguyễn Trãi' WHEN 134 THEN N'Nghệ An'
            WHEN 135 THEN N'Hải Phòng' WHEN 136 THEN N'Thái Nguyên' WHEN 137 THEN N'Thái Bình'
            WHEN 138 THEN N'Bắc Giang' WHEN 139 THEN N'Thanh Hóa' WHEN 140 THEN N'Láng'
            WHEN 141 THEN N'Giải Phóng' WHEN 142 THEN N'Thuận An' WHEN 143 THEN N'Quận 12'
            WHEN 144 THEN N'Thủ Dầu Một' ELSE N'Không xác định'
        END AS Co_So,
        ID_DV, ID_Nx, Loai_NX, Loai_Phieu, Ngay_Ct, SNgay, InsertDate, ID_Phieu, SoPhieu,
        Dien_Giai, ID_Hang, Ma_Hang, Ma_Vach, ten_hang, So_Luong
    FROM ProcessedData
    WHERE RowRank = 1
    """

        self.env.cr.execute(f"DELETE FROM {self._table}")

        _logger.info("SYNC date_start=%s date_end=%s", date_start_str, date_end_str)

        conn = self.env['ttb.tools'].get_mssql_connection()
        df = pd.read_sql(query, conn)

        _logger.info("SYNC rows=%s", len(df))

        buffer = StringIO()
        df.to_csv(buffer, index=False, header=False)
        buffer.seek(0)

        self.env.cr.copy_expert(
            f"""
            COPY {self._table}(
                id_kho, co_so, id_dv, id_nx, loai_nx, loai_phieu,
                ngay_ct, sngay, insert_date, id_phieu, so_phieu,
                dien_giai, id_hang, ma_hang, ma_vach, ten_hang, so_luong
            )
            FROM STDIN WITH CSV
            """,
            buffer
        )

        return len(df)
