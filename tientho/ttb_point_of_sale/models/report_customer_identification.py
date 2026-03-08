from odoo import models, fields, api

class ReportCustomerIdentification(models.Model):
    _name = 'report.customer.identification'
    _inherit = 'account.report.custom.handler'
    _description = 'Báo cáo định danh khách hàng'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        options['unfold_all'] = (options.get('filter_unfold_all') or options.get('unfold_all'))
        options['hide_filter_rounding_unit'] = True
        options['column_headers'] = []
        options['columns'] = [
            {
                'name': 'Cơ sở',
                'expression_label': 'co_so',
                'class': 'text',
                'type': 'string',
                'column_group_key': '1',
            },
            {
                'name': 'Mã nhân viên',
                'expression_label': 'ma_nhan_vien',
                'class': 'text',
                'type': 'string',
                'column_group_key': '2',
            },
            {
                'name': 'Tên nhân viên',
                'expression_label': 'ten_nhan_vien',
                'class': 'text',
                'type': 'string',
                'column_group_key': '3',
            },
            {
                'name': 'Tháng',
                'expression_label': 'thang',
                'class': 'text',
                'type': 'string',
                'column_group_key': '4',
            },
            {
                'name': 'Đơn ĐD Trong Tuần',
                'expression_label': 'don_dd_trong_tuan',
                'class': 'text',
                'type': 'string',
                'column_group_key': '5',
            },
            {
                'name': 'Tổng Đơn Trong Tuần',
                'expression_label': 'tong_don_trong_tuan',
                'class': 'text',
                'type': 'string',
                'column_group_key': '6',
            },
            {
                'name': 'Tỉ Lệ Trong Tuần',
                'expression_label': 'ti_le_trong_tuan',
                'class': 'text',
                'type': 'string',
                'column_group_key': '7',
            },
            {
                'name': 'Đơn ĐD Cuối Tuần',
                'expression_label': 'don_dd_cuoi_tuan',
                'class': 'text',
                'type': 'string',
                'column_group_key': '8',
            },
            {
                'name': 'Tổng Đơn Cuối Tuần',
                'expression_label': 'tong_don_cuoi_tuan',
                'class': 'text',
                'type': 'string',
                'column_group_key': '9',
            },
            {
                'name': 'Tỉ lệ Cuối Tuần',
                'expression_label': 'ti_le_cuoi_tuan',
                'class': 'text',
                'type': 'string',
                'column_group_key': '10',
            },
            {
                'name': 'Tổng Đơn ĐD',
                'expression_label': 'tong_don_dd',
                'class': 'text',
                'type': 'string',
                'column_group_key': '11',
            },
            {
                'name': 'Tổng Đơn',
                'expression_label': 'tong_don',
                'class': 'text',
                'type': 'string',
                'column_group_key': '12',
            },
            {
                'name': 'Tỉ lệ Định Danh',
                'expression_label': 'ti_le_dinh_danh',
                'class': 'text',
                'type': 'string',
                'column_group_key': '13',
            },
        ]
    def _customize_warnings(self, report, options, all_column_groups_expression_totals, warnings):
        warnings.clear()

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals=None, warnings=None):
        lines = []

        date_from = options['date']['date_from']
        date_to = options['date']['date_to']

        if not date_from and not date_to:
            return lines

        conn = self.env['ttb.tools'].get_mssql_connection_send()

        query = f"""
                SELECT 
                    dbo.tcvntounicode(nk.Ten_Nhom) AS co_so,
                    u.LogName AS ma_nhan_vien,
                    dbo.tcvntounicode(u.FullName) AS ten_nhan_vien,
                    s.Thang AS thang,
                    -- Trong Tuần
                    s.Don_DD_TrongTuan AS don_dd_trong_tuan,
                    s.Tong_Don_TrongTuan AS tong_don_trong_tuan,
                    Round(CAST(s.Don_DD_TrongTuan AS FLOAT) / NULLIF(s.Tong_Don_TrongTuan, 0) * 100, 2) AS ti_le_trong_tuan,
                    -- Cuối Tuần
                    s.Don_DD_CuoiTuan AS don_dd_cuoi_tuan,
                    s.Tong_Don_CuoiTuan AS tong_don_cuoi_tuan,
                    Round(CAST(s.Don_DD_CuoiTuan AS FLOAT) / NULLIF(s.Tong_Don_CuoiTuan, 0) * 100, 2) AS ti_le_cuoi_tuan,
                    -- Tổng hợp
                    s.Tong_Don_Dinh_Danh AS tong_don_dd,
                    s.Tong_Don AS tong_don,
                    Round(CAST(s.Tong_Don_Dinh_Danh AS FLOAT) / NULLIF(s.Tong_Don, 0) * 100, 2) AS ti_le_dinh_danh
                FROM (
                    SELECT 
                        k.id_nkho, -- Nhóm theo ID nhóm kho (Cơ sở)
                        m.userid, 
                        SUBSTRING(CAST(m.sngay AS VARCHAR), 3, 2) AS Thang,
                        -- Tổng hợp đơn định danh và tổng đơn
                        COUNT(CASE WHEN dt.Ten_dt is not null AND dt.Dien_thoai is not null THEN 1 END) AS Tong_Don_Dinh_Danh,
                        COUNT(*) AS Tong_Don,
                        -- Xử lý Trong Tuần (Thứ 2 - Thứ 6)
                        COUNT(CASE WHEN DATEPART(dw, DATEFROMPARTS(2000 + CAST(LEFT(m.sngay, 2) AS INT), CAST(SUBSTRING(CAST(m.sngay AS VARCHAR), 3, 2) AS INT), CAST(RIGHT(m.sngay, 2) AS INT))) BETWEEN 2 AND 6 THEN 1 END) AS Tong_Don_TrongTuan,
                        COUNT(CASE WHEN dt.Ten_dt is not null AND dt.Dien_thoai is not null AND DATEPART(dw, DATEFROMPARTS(2000 + CAST(LEFT(m.sngay, 2) AS INT), CAST(SUBSTRING(CAST(m.sngay AS VARCHAR), 3, 2) AS INT), CAST(RIGHT(m.sngay, 2) AS INT))) BETWEEN 2 AND 6 THEN 1 END) AS Don_DD_TrongTuan,
                        -- Xử lý Cuối Tuần (Thứ 7 - Chủ Nhật)
                        COUNT(CASE WHEN DATEPART(dw, DATEFROMPARTS(2000 + CAST(LEFT(m.sngay, 2) AS INT), CAST(SUBSTRING(CAST(m.sngay AS VARCHAR), 3, 2) AS INT), CAST(RIGHT(m.sngay, 2) AS INT))) IN (1, 7) THEN 1 END) AS Tong_Don_CuoiTuan,
                        COUNT(CASE WHEN dt.Ten_dt is not null AND dt.Dien_thoai is not null AND DATEPART(dw, DATEFROMPARTS(2000 + CAST(LEFT(m.sngay, 2) AS INT), CAST(SUBSTRING(CAST(m.sngay AS VARCHAR), 3, 2) AS INT), CAST(RIGHT(m.sngay, 2) AS INT))) IN (1, 7) THEN 1 END) AS Don_DD_CuoiTuan
                    FROM slblm m
                    LEFT JOIN dmkho k ON m.id_kho = k.id -- Join để lấy id_nkho
                    LEFT JOIN dmdt dt ON m.id_dt = dt.id
                    WHERE m.id_dv = 0 
                      AND m.printed = 1 
                      -- AND m.sngay LIKE '25%'
                      -- AND (ISNULL(m.Tien_Hang, 0) - ISNULL(m.Tien_Giam, 0)) >= 50000
                      AND m.InsertDate >= '{date_from}'
                      AND m.InsertDate < DATEADD(DAY, 1, '{date_to}')
                      --AND dt.Ten_dt IS NOT NULL
                      --AND dt.Dien_thoai IS NOT NULL
                    GROUP BY k.id_nkho, m.userid, SUBSTRING(CAST(m.sngay AS VARCHAR), 3, 2)
                ) s
                LEFT JOIN dmuser u ON s.userid = u.id
                LEFT JOIN DmNkho nk ON s.id_nkho = nk.id -- Join trực tiếp với bảng Nhóm kho để lấy tên cơ sở
                ORDER BY s.Thang ASC, co_so ASC;

           """
        cursor = conn.cursor()
        cursor.execute(query)

        columns = [col[0] for col in cursor.description]
        result = [dict(zip(columns, row)) for row in cursor.fetchall()]

        for index, record in enumerate(result):
            line_columns = []
            for column in options['columns']:
                expr = column['expression_label']
                value = record.get(expr)
                line_columns.append(report._build_column_dict(value, column, options=options))

            lines.append({
                'id': f"~line_{index}~",
                'name': '',
                'columns': line_columns,
                'level': 1,
                'unfoldable': False,
                'unfolded': False,
            })
        return [(0, line) for line in lines]
