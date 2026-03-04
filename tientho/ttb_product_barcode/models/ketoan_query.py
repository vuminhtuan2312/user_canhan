from odoo import models, fields, api
from odoo.addons.ttb_product_barcode.models.product_template import tcvn3_to_unicode

import logging
_logger = logging.getLogger(__name__)

class XuatNhapBaoCao(models.Model):
    _name = 'xuatnhap.baocao'
    _description = 'Báo cáo xuất nhập từ hệ thống khác'
    _order = 'sngay desc'

    augges_id = fields.Integer("ID SlNxM", index=True)
    sngay = fields.Char("Ngày", index=True)
    ngay_ct = fields.Date("Ngày chứng từ")
    ky_hieu = fields.Char("Ký hiệu")
    mau_so = fields.Char("Mẫu số")
    so_ct = fields.Char("Số CT")
    sp = fields.Char("SP")
    id_nx = fields.Char("ID NX")
    ma_ct = fields.Char("Mã CT")
    id_kho = fields.Char("ID Kho")
    ten_nhom = fields.Char("Tên Nhóm Kho")
    id_dt = fields.Char("ID Đối Tượng")
    ten_dt = fields.Char("Tên Đối Tượng")
    mst = fields.Char("Mã số thuế")
    cong_slqd = fields.Float("cong_slqd")
    cong_sl = fields.Float("cong_sl")
    tien_hang = fields.Float("Tiền hàng")
    id_thue = fields.Char("ID Thuế")
    tien_gtgt = fields.Float("Tiền GTGT")
    tong_tien = fields.Float("Tổng tiền")

    detail_ids = fields.One2many('xuatnhap.detail', 'xuatnhap_id')


    @api.model
    def cron_sync_data_create(self):
        # Lấy ID lần đồng bộ cuối cùng
        config_param = self.env['ir.config_parameter']
        last_sync_id = int(config_param.get_param('mssql.ke_toan.last_sync_id_create', 0))

        # Kết nối MSSQL
        conn = self.env['ttb.tools'].get_mssql_connection()
        cursor = conn.cursor()

        while True:
            # Gửi query có phân trang theo ID
            query = f"""
            SELECT TOP 1000 
                m.ID, m.Sngay, m.ngay_ct, m.Ky_hieu, m.Mau_so, m.so_Ct,
                m.Sp, m.ID_Nx, nx.Ma_Ct, m.ID_kho, kho.Ten_Nhom,
                m.ID_Dt, dt.Ten_Dt, 
                -- dt.MST,
                dnm.tax_code as MST, 
                m.Cong_SlQd, m.Cong_Sl,
                m.Tien_hang, m.ID_Thue, m.Tien_Gtgt, m.Tong_Tien
            FROM SlNxM m  
            LEFT JOIN DmNx nx ON m.ID_Nx = nx.ID  
            LEFT JOIN DmNKho kho ON m.ID_kho = kho.ID  
            LEFT JOIN DmDt dt ON m.ID_Dt = dt.ID

            LEFT JOIN data_ncc_mst dnm on dnm.code_augges = dt.Ma_Dt
            WHERE 
                kho.Ten_Nhom IS NOT NULL
                AND m.ID_DT IS NOT NULL
                AND nx.Ma_Ct = 'NM'
                AND m.ID > {last_sync_id}
            ORDER BY m.ID ASC;
            """

            cursor.execute(query)
            rows = cursor.fetchall()
            if not rows: break

            for row in rows:
                if row.ID > last_sync_id:
                    last_sync_id = row.ID
                if self.search([('augges_id', '=', row.ID)], limit=1): continue
                self.create({
                    'augges_id': row.ID,
                    'sngay': row.Sngay,
                    'ngay_ct': row.ngay_ct,
                    'ky_hieu': row.Ky_hieu,
                    'mau_so': row.Mau_so,
                    'so_ct': row.so_Ct,
                    'sp': row.Sp,
                    'id_nx': row.ID_Nx,
                    'ma_ct': row.Ma_Ct,
                    'id_kho': row.ID_kho,
                    'ten_nhom': tcvn3_to_unicode(row.Ten_Nhom),
                    'id_dt': row.ID_Dt,
                    'ten_dt': tcvn3_to_unicode(row.Ten_Dt),
                    'mst': row.MST,
                    'cong_slqd': row.Cong_SlQd,
                    'cong_sl': row.Cong_Sl,
                    'tien_hang': row.Tien_hang,
                    'id_thue': row.ID_Thue,
                    'tien_gtgt': row.Tien_Gtgt,
                    'tong_tien': row.Tong_Tien,
                })

            # Cập nhật last_sync_id
            config_param.set_param('mssql.ke_toan.last_sync_id_create', str(last_sync_id))
            self.env.cr.commit()
            _logger.info('Đồng bộ được 1000 bản ghi xuất nhập')
        config_param.set_param('mssql.ke_toan.last_sync_id_create', str(last_sync_id))

        cursor.close()
        conn.close()

    # class XuatNhapDetail(models.Model):
        