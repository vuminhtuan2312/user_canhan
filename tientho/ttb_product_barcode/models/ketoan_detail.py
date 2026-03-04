# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
# Import thêm nếu cần thiết, ví dụ Decimal cho digits
# from odoo.addons import decimal_precision as dp

import pandas as pd
import pytz
from io import StringIO

import logging
_logger = logging.getLogger(__name__)

class XuatNhapDetail(models.Model):
    _name = 'xuatnhap.detail'
    _description = 'Chi tiết Xuất/Nhập (Dựa trên SlblD)'
    _order = 'stt asc' # Sắp xếp theo Stt tăng dần

    # --- Các trường từ bảng SlblD ---

    # ID (int, NO) - Odoo tự động tạo trường id, không cần định nghĩa lại

    # --- Trường liên kết với model cha ---
    xuatnhap_id = fields.Many2one(
        'xuatnhap.baocao',         # Tên model cha
        string='Chứng từ Xuất/Nhập', # Nhãn hiển thị
        required=False,             # Bắt buộc phải có liên kết này
        ondelete='cascade',        # Nếu xóa bản ghi cha, dòng chi tiết này cũng bị xóa
        index=True                 # Tạo index để tăng tốc truy vấn
    )

    slnxm_id = fields.Integer()
    id_hang = fields.Integer()
    # ten_hang = fields.Char()
    product_id = fields.Many2one('product.product')



    stt = fields.Integer(
        string='Số thứ tự',
        required=True,
        default=0 # Giá trị mặc định từ (0)
    )
    sngay = fields.Char(
        string='Ngày (chuỗi)', # nchar(6) - có thể cần xử lý/chuyển đổi nếu muốn dùng kiểu Date/Datetime
        size=6
    )
    md = fields.Char(
        string='Md', # nchar(1)
        size=1
    )

    # --- Khóa ngoại (CẦN XÁC NHẬN MODEL LIÊN KẾT) ---
    # Thay 'your.model.name' bằng tên model Odoo tương ứng
    # kho_id = fields.Many2one(
    #     'stock.warehouse', # Giả định là Kho (stock.warehouse), CẦN XÁC NHẬN
    #     string='Kho'
    # )
    # product_id = fields.Many2one(
    #     'product.product', # Giả định là Hàng hóa (product.product), CẦN XÁC NHẬN
    #     string='Hàng hóa'
    # )
    # hkm_id = fields.Many2one(
    #     'your.hkm.model', # CẦN XÁC NHẬN model cho ID_HKM
    #     string='Hàng KM?'
    # )
    # uom_id = fields.Many2one(
    #     'uom.uom', # Giả định là Đơn vị tính (uom.uom), CẦN XÁC NHẬN
    #     string='Đơn vị tính'
    # )
    # lh_id = fields.Many2one(
    #     'your.lh.model', # CẦN XÁC NHẬN model cho ID_Lh
    #     string='Loại hàng?'
    # )
    # mv_id = fields.Many2one(
    #     'your.mv.model', # CẦN XÁC NHẬN model cho ID_Mv
    #     string='Mã vụ?'
    # )
    # tax_id = fields.Many2one(
    #     'account.tax', # Giả định là Thuế (account.tax), CẦN XÁC NHẬN
    #     string='Thuế suất'
    # )
    # the_id = fields.Many2one(
    #     'your.the.model', # CẦN XÁC NHẬN model cho ID_The
    #     string='Thẻ'
    # )
    # csb_id = fields.Many2one(
    #     'your.csb.model', # CẦN XÁC NHẬN model cho ID_CSB
    #     string='CSB?'
    # )
    # nh_id = fields.Many2one(
    #     'your.nh.model', # CẦN XÁC NHẬN model cho ID_Nh (Có thể là product.category?)
    #     string='Nhóm hàng?'
    # )
    # user_id = fields.Many2one(
    #     'res.users', # Giả định là Nhân viên (res.users hoặc hr.employee), CẦN XÁC NHẬN
    #     string='Nhân viên'
    # )
    # lydo_id = fields.Many2one(
    #     'your.lydo.model', # CẦN XÁC NHẬN model cho ID_LyDo
    #     string='Lý do'
    # )
    # l_id = fields.Many2one(
    #     'your.l.model', # CẦN XÁC NHẬN model cho ID_L
    #     string='L?'
    # )

    # --- Số lượng & Tiền tệ (Float) ---
    # Sử dụng digits để kiểm soát độ chính xác
    # Có thể dùng dp.get_precision('Tên Precision') hoặc tuple (tổng_số_chữ_số, số_sau_dấu_phẩy)
    # Ví dụ: digits='Product Unit of Measure' cho số lượng, digits='Product Price' cho đơn giá, digits='Account' cho tiền
    sl_qd = fields.Float(
        string='Số lượng quy đổi',
        # digits='Product Unit of Measure' # (19, 4) - Precision cao
    )
    hs_qd = fields.Char(
        string='Hệ số quy đổi', # nvarchar(25)
        size=25
    )
    so_luong = fields.Float(
        string='Số lượng',
        # digits='Product Unit of Measure' # (19, 4)
    )
    gia_nt = fields.Float(
        string='Giá ngoại tệ',
        # digits='Product Price' # (19, 4) - Có thể cần fields.Monetary nếu có nhiều loại tiền tệ
    )
    tien_nt = fields.Float(
        string='Tiền ngoại tệ',
        # digits='Account' # (19, 4) - Có thể cần fields.Monetary
    )
    gia_ban = fields.Float(
        string='Giá bán',
        # digits='Product Price' # (19, 4)
    )
    gia_qd = fields.Float(
        string='Giá quy đổi',
        # digits='Product Price' # (19, 4)
    )
    don_gia = fields.Float(
        string='Đơn giá',
        # digits='Product Price' # (19, 4)
    )
    t_tien = fields.Float(
        string='Thành tiền',
        # digits='Account' # (19, 4)
    )
    tyle_giam = fields.Float(
        string='Tỷ lệ giảm (%)',
        # digits=(6, 2) # numeric(6, 2)
    )
    tien_giam = fields.Float(
        string='Tiền giảm',
        # digits='Account' # (19, 4)
    )
    tien_ck = fields.Float(
        string='Tiền chiết khấu',
        # digits='Account' # (19, 4)
    )
    ck_the = fields.Float(
        string='CK Thẻ',
        # digits='Account' # (19, 4)
    )
    ck_the_mg = fields.Float( # CK_TheMg
        string='CK Thẻ Mg',
        # digits='Account' # (19, 4)
    )
    thue = fields.Float(
        string='Thuế (%)',
        # digits=(6, 2) # numeric(6, 2)
    )
    gia_kvat = fields.Float( # Gia_KVat
        string='Giá K Vat',
        # digits='Account' # (19, 4)
    )
    tien_kvat = fields.Float( # Tien_KVat
        string='Tiền K Vat',
        # digits='Account' # (19, 4)
    )
    tien_gtgt = fields.Float( # Tien_GtGt
        string='Tiền GTGT',
        # digits='Account' # (19, 4)
    )
    don_gia1 = fields.Float( # Don_Gia1
        string='Đơn giá 1',
        # digits='Product Price' # (19, 4)
    )
    t_tien1 = fields.Float( # T_Tien1
        string='Thành tiền 1',
        # digits='Account' # (19, 4)
    )
    ck_the_cn = fields.Float( # Ck_TheCn
        string='CK Thẻ CN',
        # digits='Account' # (19, 4)
    )
    sl_yc = fields.Float( # Sl_Yc
        string='Số lượng YC',
        # digits='Product Unit of Measure' # (19, 4)
    )
    pb_ck_131 = fields.Float( # PbCk_131
        string='PB CK 131',
        # digits='Account' # (19, 4)
    )
    pb_diem_tt = fields.Float( # Pb_DiemTt
        string='PB Điểm TT',
        # digits='Account' # (19, 4)
    )
    tyle_the = fields.Float( # TyLe_The
        string='Tỷ lệ thẻ (%)',
        # digits=(6, 2) # numeric(6, 2)
    )

    gia_vat = fields.Float(
        string='Giá bán',
        # digits='Product Price' # (19, 4)
    )
    so_luongt = fields.Float(
        string='Số lượngT',
        # digits='Product Unit of Measure' # (19, 4)
    )

    # --- Tài khoản (Char) ---
    # Có thể xem xét dùng Many2one nếu cần liên kết đầy đủ đến account.account
    no_tk = fields.Char(string='TK Nợ', size=10) # nvarchar(10)
    co_tk = fields.Char(string='TK Có', size=10) # nvarchar(10)
    no_tk1 = fields.Char(string='TK Nợ 1', size=10) # nvarchar(10)
    co_tk1 = fields.Char(string='TK Có 1', size=10) # nvarchar(10)
    no_tk_cn = fields.Char(string='TK Nợ CN', size=10) # nvarchar(10)
    co_tk_cn = fields.Char(string='TK Có CN', size=10) # nvarchar(10)

    # --- Thời gian (Char) ---
    # nvarchar(12) - Lưu dưới dạng chuỗi, có thể cần xử lý thêm nếu muốn tính toán
    cook_time = fields.Char(string='Cook Time', size=12)
    insert_time = fields.Char(string='Insert Time', size=12)

    # --- Thông tin khác ---
    ghi_chu = fields.Text(string='Ghi chú') # nvarchar(100) -> Text cho linh hoạt
    printed = fields.Boolean(string='Đã in') # bit
    is_ck_hd = fields.Boolean(string='Là CK HĐ') # IsCkHD - bit
    ten_hang_k = fields.Char(string='Tên hàng K', size=120) # Ten_HangK - nvarchar(120)
    is_am = fields.Boolean(string='Là Âm?') # IsAm - bit
    c_status = fields.Char(string='Trạng thái (chuỗi)', size=5) # cStatus - nvarchar(5) - Có thể dùng fields.Selection nếu biết các giá trị có thể có

    # --- Cần thêm các trường Odoo khác nếu cần ---
    # Ví dụ: liên kết ngược lại với model cha (nếu đây là dòng chi tiết)
    # parent_id = fields.Many2one('xuatnhap.master', string='Chứng từ cha', ondelete='cascade')


    def get_xuatnhap_detail(self):

        # B1. Xóa các tồn cũ nếu có
        self.env.cr.execute(f"truncate table {self._table}")
        self.env.cr.commit()
        
        # B2. Lấy tồn mới
        conn = self.env['ttb.tools'].get_mssql_connection()

        paging = 50000
        page_id = 0
        page_id_next = page_id + paging
        _logger.info('bắt đầu lấy dữ liệu')
        while True:
            _logger.info('bắt đầu lấy paging 50k')
            query = f"""
                SELECT
                    d.ID,
                    d.Stt,
                    d.ID_Hang,
                    -- dmh.Ten_Hang,
                    d.So_Luong,
                    d.Don_Gia,
                    d.Don_Gia1,
                    d.Gia_KVat,
                    d.Gia_Ban,
                    d.T_Tien,
                    d.T_Tien1,

                    d.Gia_Vat,
                    d.Sl_Qd,
                    d.Gia_Qd,
                    d.So_LuongT
                FROM
                    SlNxD d
                    JOIN SlNxM m ON m.ID = d.ID
                    LEFT JOIN DmNx nx ON m.ID_Nx = nx.ID
                    LEFT JOIN DmNKho kho ON m.ID_Kho = kho.ID
                    LEFT JOIN DmDt dt ON m.ID_Dt = dt.ID
                    LEFT JOIN data_ncc_mst dnm ON dnm.code_augges = dt.Ma_Dt

                    LEFT JOIN DmH dmh on dmh.ID = d.ID_Hang
                WHERE
                    d.ID >= {page_id} and d.ID < {page_id_next}
                    AND kho.Ten_Nhom IS NOT NULL
                    AND m.ID_Dt IS NOT NULL
                    AND nx.Ma_Ct = 'NM'

                    AND d.ID_Hang is not null
            """
            page_id = page_id_next
            page_id_next += paging
            
            df = pd.read_sql(query, conn)

            if df.empty:
                break

            buffer = StringIO()
            df.to_csv(buffer, index=False, header=False)
            buffer.seek(0)

            # B3. Insert tồn mới
            self.env.cr.copy_expert(
                f"""COPY {self._table}(
                        slnxm_id, 
                        stt, 
                        id_hang,
                        so_luong,
                        don_gia,
                        don_gia1,
                        gia_kvat,
                        gia_ban,
                        t_tien,
                        t_tien1,

                        gia_vat,
                        sl_qd,
                        gia_qd,
                        so_luongt
                    ) FROM STDIN WITH CSV
                """, buffer)
            self.env.cr.commit()
            _logger.info('Lấy paging 50k id %s' % page_id)
        
        self.env.cr.execute(f"""
            update xuatnhap_detail 
            set xuatnhap_id = data.xuatnhap_id

            from (
                select xnd.id, xnm.id xuatnhap_id
                from xuatnhap_detail xnd join xuatnhap_baocao xnm on xnm.augges_id = xnd.slnxm_id
            ) data

            where data.id = xuatnhap_detail.id;

            update xuatnhap_detail 
            set product_id = data.product_id

            from (
                select xnd.id, pp.id product_id
                from 
                    xuatnhap_detail xnd 
                    join product_template pt on pt.augges_id = xnd.id_hang 
                    join product_product pp on pp.product_tmpl_id = pt.id
            ) data

            where data.id = xuatnhap_detail.id;
        """)




