# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
import pandas as pd
import logging

_logger = logging.getLogger(__name__)

# Ngưỡng: nếu số dòng > này thì dùng đồng bộ CSV thay vì create()
BULK_INSERT_CSV_THRESHOLD = 5000


class XuatNhapKhoAugges(models.Model):
    _name = 'ttb.xuat.nhap.kho.augges'
    _description = 'Xuất nhập kho Augges (từ SQL Trang)'
    _order = 'insert_date desc, id desc'

    active = fields.Boolean(default=False, string='Hiện hành')
    id_kho = fields.Integer(string='ID Kho', index=True)
    co_so = fields.Char(string='Cơ sở')
    id_dv = fields.Integer(string='ID DV', index=True)
    id_nx = fields.Integer(string='ID NX', index=True)
    loai_nx = fields.Char(string='Loại NX')
    loai_phieu = fields.Char(string='Loại phiếu', index=True)  # SLNX, SLDC, SLBL
    ngay_ct = fields.Datetime(string='Ngày CT')
    sngay = fields.Char(string='SNgay', index=True)
    insert_date = fields.Datetime(string='InsertDate', index=True)
    id_phieu = fields.Integer(string='ID Phiếu', index=True)
    so_phieu = fields.Char(string='Số phiếu', index=True)
    dien_giai = fields.Char(string='Diễn giải')
    id_hang = fields.Integer(string='ID Hàng', index=True)
    ma_hang = fields.Char(string='Mã hàng', index=True)
    ma_vach = fields.Char(string='Mã vạch')
    ten_hang = fields.Char(string='Tên hàng')
    so_luong = fields.Float(string='Số lượng')

    def action_open_sync_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Đồng bộ Xuất nhập kho Augges',
            'res_model': 'ttb.xuat.nhap.kho.augges.sync.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {},
        }

    def _get_sql_template(self, date_start, date_end):
        """SQL mẫu từ Trang - dùng InsertDate, id_dv=0, kho 132-144."""
        date_start_str = date_start.strftime('%Y-%m-%d 00:00:00')
        date_end_str = date_end.strftime('%Y-%m-%d 23:59:59')
        return (
"""
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
    WHERE SlNxM.InsertDate BETWEEN '%(date_start)s' AND '%(date_end)s'
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
    WHERE SlDcM.InsertDate BETWEEN '%(date_start)s' AND '%(date_end)s'
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
    WHERE SlDcM.InsertDate BETWEEN '%(date_start)s' AND '%(date_end)s'
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
    WHERE SlBlM.InsertDate BETWEEN '%(date_start)s' AND '%(date_end)s'
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
SELECT ID_Kho,
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
        ) % {'date_start': date_start_str, 'date_end': date_end_str}

    def _co_so_from_id_kho(self, id_kho):
        m = {
            132: 'Xuân Thủy', 133: 'Nguyễn Trãi', 134: 'Nghệ An',
            135: 'Hải Phòng', 136: 'Thái Nguyên', 137: 'Thái Bình',
            138: 'Bắc Giang', 139: 'Thanh Hóa', 140: 'Láng',
            141: 'Giải Phóng', 142: 'Thuận An', 143: 'Quận 12',
            144: 'Thủ Dầu Một',
        }
        return m.get(id_kho) or 'Không xác định'

    def _row_to_vals(self, row, cols):
        """Chuyển 1 dòng DataFrame thành dict vals (không có active)."""
        vals = {}
        for c in cols:
            if c in row.index:
                v = row.get(c)
                vals[c] = None if pd.isna(v) else v
        return vals

    def _record_same_as_row(self, rec, vals):
        """So sánh bản ghi với vals (từ 1 dòng sync). Trả về True nếu giống hệt."""
        for fname, new_val in vals.items():
            old_val = rec[fname]
            if isinstance(new_val, float) and pd.isna(new_val):
                new_val = None
            if isinstance(old_val, float) and pd.isna(old_val):
                old_val = None
            if hasattr(new_val, 'to_pydatetime'):
                new_val = new_val.to_pydatetime() if new_val is not None else None
            if old_val is not None and new_val is not None:
                if hasattr(old_val, 'replace') and hasattr(new_val, 'replace') and hasattr(old_val, 'year'):
                    if old_val.replace(microsecond=0) != new_val.replace(microsecond=0):
                        return False
                    continue
            if old_val != new_val:
                return False
        return True

    def _cap_nhat_ton(self, date_start, date_end, custom_sql=None):
        """
        Đồng bộ từ Augges: không xoá hết dữ liệu.
        - Bản ghi đang hiển thị (active=True) được đánh dấu active=False.
        - Với mỗi dòng kết quả SQL: tìm bản ghi cũ (dùng with_context(active_test=False))
          theo khóa id_kho, id_phieu, loai_phieu, id_hang.
        - Nếu tìm thấy và dữ liệu không đổi: set lại active=True (giữ bản ghi cũ).
        - Nếu tìm thấy nhưng có thay đổi, hoặc không tìm thấy: tạo bản ghi mới (active=True).
        """
        Model = self.env['ttb.xuat.nhap.kho.augges']
        if custom_sql and custom_sql.strip():
            query = custom_sql.strip()
        else:
            query = Model._get_sql_template(date_start, date_end)

        conn = self.env['ttb.tools'].get_mssql_connection()
        try:
            df = pd.read_sql(query, conn)
        except Exception as e:
            raise UserError('Lỗi khi chạy SQL Augges: %s' % str(e))

        if df.empty:
            return 0

        col_map = {
            'ID_Kho': 'id_kho', 'Co_So': 'co_so', 'ID_DV': 'id_dv', 'ID_Nx': 'id_nx',
            'Loai_NX': 'loai_nx', 'Loai_Phieu': 'loai_phieu', 'Ngay_Ct': 'ngay_ct',
            'SNgay': 'sngay', 'InsertDate': 'insert_date', 'ID_Phieu': 'id_phieu',
            'SoPhieu': 'so_phieu', 'Dien_Giai': 'dien_giai', 'ID_Hang': 'id_hang',
            'Ma_Hang': 'ma_hang', 'Ma_Vach': 'ma_vach', 'ten_hang': 'ten_hang',
            'So_Luong': 'so_luong',
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

        cols = ['id_kho', 'co_so', 'id_dv', 'id_nx', 'loai_nx', 'loai_phieu', 'ngay_ct', 'sngay',
                'insert_date', 'id_phieu', 'so_phieu', 'dien_giai', 'id_hang', 'ma_hang',
                'ma_vach', 'ten_hang', 'so_luong']

        # Bước 1: đánh dấu toàn bộ bản ghi đang hiển thị (active=True) thành active=False.
        # Dùng with_context(active_test=False) khi cần tìm cả bản ghi đã ẩn.
        Model.search([('active', '=', True)]).write({'active': False})

        # Bước 2: với mỗi dòng sync, tìm bản ghi cũ (active=False) theo khóa; không đổi thì bật lại active, có đổi thì tạo mới
        ModelWithInactive = Model.sudo().with_context(active_test=False)
        reactivated = 0
        created = 0
        batch = 500
        for i in range(0, len(df), batch):
            chunk = df.iloc[i:i + batch]
            to_create = []
            for _, row in chunk.iterrows():
                vals = self._row_to_vals(row, cols)
                id_kho = vals.get('id_kho')
                id_phieu = vals.get('id_phieu')
                loai_phieu = vals.get('loai_phieu') or ''
                id_hang = vals.get('id_hang')
                domain = [
                    ('id_kho', '=', id_kho),
                    ('id_phieu', '=', id_phieu),
                    ('loai_phieu', '=', loai_phieu),
                    ('id_hang', '=', id_hang),
                    ('active', '=', False),
                ]
                existing = ModelWithInactive.search(domain, limit=1, order='id desc')
                if existing:
                    if self._record_same_as_row(existing, vals):
                        existing.sudo().write({'active': True})
                        reactivated += 1
                    else:
                        to_create.append(vals)
                else:
                    to_create.append(vals)
            if to_create:
                for v in to_create:
                    v['active'] = True
                Model.sudo().create(to_create)
                created += len(to_create)
        return reactivated + created

    def _insert_via_create_batch(self, df):
        """Insert thuần theo batch (không so khớp bản cũ). Dùng khi cần chạy nhanh kiểu cũ."""
        Model = self.env['ttb.xuat.nhap.kho.augges']
        cols = ['id_kho', 'co_so', 'id_dv', 'id_nx', 'loai_nx', 'loai_phieu', 'ngay_ct', 'sngay',
                'insert_date', 'id_phieu', 'so_phieu', 'dien_giai', 'id_hang', 'ma_hang',
                'ma_vach', 'ten_hang', 'so_luong']
        created = 0
        batch = 1000
        for i in range(0, len(df), batch):
            chunk = df.iloc[i:i + batch]
            list_vals = []
            for _, row in chunk.iterrows():
                vals = {'active': True}
                for c in cols:
                    if c in chunk.columns:
                        v = row.get(c)
                        vals[c] = None if pd.isna(v) else v
                list_vals.append(vals)
            if list_vals:
                Model.create(list_vals)
                created += len(list_vals)
        return created
