from odoo import fields, models, api
from datetime import datetime

class ReportAccumulatePoints(models.AbstractModel):
    _name = 'report.accumulate.points'
    _inherit = 'account.report.custom.handler'
    _description = 'Báo cáo khách hàng phát sinh tích điểm'


    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        options['unfold_all'] = (options.get('filter_unfold_all') or options.get('unfold_all'))
        options['hide_filter_rounding_unit'] = True
        options['column_headers'] = []
        options['columns'] = [
            {
                'name': 'Mã đơn hàng',
                'expression_label': 'ID',
                'class': 'text',
                'type': 'string',
                'column_group_key': '1',
            },
            {
                'name': 'Ngày in',
                'expression_label': 'Ngay_In',
                'class': 'text',
                'type': 'date',
                'column_group_key': '2',
            },
            {
                'name': 'Số điện thoại',
                'expression_label': 'So_The',
                'class': 'text',
                'type': 'string',
                'column_group_key': '3',
            },
            {
                'name': 'Mã kho',
                'expression_label': 'Ma_Kho',
                'class': 'text',
                'type': 'string',
                'column_group_key': '3',
            },
            {
                'name': 'Tên kho',
                'expression_label': 'Ten_Kho',
                'class': 'text',
                'type': 'string',
                'column_group_key': '4',
            },
            {
                'name': 'Tên nhóm',
                'expression_label': 'Ten_Nhom',
                'class': 'text',
                'type': 'string',
                'column_group_key': '5',
            },
            {
                'name': 'Tên sản phẩm',
                'expression_label': 'Ten_Hang_List',
                'class': 'text',
                'type': 'string',
                'column_group_key': '6',
            },
            {
                'name': 'Tiền hàng',
                'expression_label': 'Tien_Hang',
                'class': 'text',
                'type': 'string',
                'column_group_key': '7',
            },
            {
                'name': 'Chiết khấu',
                'expression_label': 'Ck_Gg',
                'class': 'text',
                'type': 'string',
                'column_group_key': '8',
            },
            {
                'name': 'Số tiền',
                'expression_label': 'So_Tien',
                'class': 'text',
                'type': 'string',
                'column_group_key': '9',
            },
            {
                'name': 'Tuần bắt đầu',
                'expression_label': 'WeekStart',
                'class': 'text',
                'type': 'string',
                'column_group_key': '10',
            },
            {
                'name': 'Số lần trong tuần',
                'expression_label': 'SoLan_Trong_Tuan',
                'class': 'text',
                'type': 'string',
                'column_group_key': '11',
            },
            {
                'name': 'Điểm Tiêu',
                'expression_label': 'Diem_Tt',
                'class': 'text',
                'type': 'string',
                'column_group_key': '12',
            },
            {
                'name': 'Mã nhân viên',
                'expression_label': 'LogName',
                'class': 'text',
                'type': 'string',
                'column_group_key': '13',
            },
            {
                'name': 'Tên nhân viên',
                'expression_label': 'Ten_NV',
                'class': 'text',
                'type': 'string',
                'column_group_key': '14',
            },
            {
                'name': 'Điểm tích',
                'expression_label': 'Diem_Tich',
                'class': 'text',
                'type': 'string',
                'column_group_key': '15',
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

        date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
        date_to = datetime.strptime(date_to, '%Y-%m-%d').date()

        # Số ngày chênh lệch
        delta_days = (date_to - date_from).days + 1

        if delta_days > 7:
            return lines

        date_from_mssql = date_from.strftime('%y%m%d')
        date_to_mssql = date_to.strftime('%y%m%d')

        conn = self.env['ttb.tools'].get_mssql_connection_send()

        query = f"""
             WITH F AS (
                SELECT
                    D.ID,
                    D.ID_Hang,
                    D.ID_CSB,
                    D.Tien_Giam,
                    D.Tien_Ck,
                    D.CK_TheMg,
                    D.T_Tien,
            
                    M.ID_The,
                    M.ID_LThe,
                    M.Sp,
                    M.ID_Kho,
                    M.ID_Dv,
                    M.Tyle_DS,
                    M.Diem_Tt,             
                    M.Ngay_In AS Ngay_HD,
            
                    us.LogName,
                    dbo.TCVNToUnicode(us.FullName) AS ten_NV,  
                    Th.So_The,
                    ISNULL(M.ID_LThe, Th.ID_LThe) AS ID_LThe_ThucTe
                FROM SlBlD AS D
                JOIN SlBlM AS M          ON D.ID = M.ID
                LEFT JOIN DmThe AS Th    ON M.ID_The = Th.ID
                LEFT JOIN dbo.DmUser AS us ON us.ID = m.UserID
                WHERE D.Sngay >= '{date_from_mssql}'
                  AND D.Sngay <= '{date_to_mssql}'
                  AND M.ID_Dv >= 0
                  AND D.Hs_Qd <> 'THEMG'
                  AND ISNULL(M.ID_LThe, Th.ID_LThe) IN (14, 15)
                  AND M.ID_The <> '128969'
            ),
            T AS (
                SELECT
                    F.ID,
                    F.ID_The,
                    F.ID_LThe,
                    F.Sp,
            
                    MIN(F.Ngay_HD) AS Ngay_HD,
                    MAX(F.So_The) AS So_The,
            
                    MAX(K.Ma_Kho) AS Ma_Kho,
                    MAX(dbo.TCVNToUnicode(K.Ten_Kho)) AS Ten_Kho,
            
                    MAX(dbo.TCVNToUnicode(NK.Ten_Nhom)) AS Ten_Nhom,
            
                    STRING_AGG(
                        CAST(dbo.TCVNToUnicode(H.Ten_Hang) AS nvarchar(max)), N', '
                    ) WITHIN GROUP (ORDER BY H.Ten_Hang) AS Ten_Hang_List,
            
                    SUM(CASE WHEN F.ID_Hang IS NOT NULL AND F.ID_CSB IS NULL AND F.Tien_Giam = 0
                         THEN F.T_Tien ELSE CAST(0 AS money) END) AS So_TienNg,
            
                    SUM(CASE WHEN F.ID_Hang IS NOT NULL THEN F.T_Tien ELSE CAST(0 AS money) END) AS Tien_Hang,
            
                    SUM(CASE WHEN F.ID_Hang IS NOT NULL
                         THEN ISNULL(F.Tien_Giam,0)+ISNULL(F.Tien_Ck,0)-F.CK_TheMg
                         ELSE CAST(0 AS money) END) AS Ck_Gg,
            
                    SUM(CASE WHEN F.ID_Hang IS NOT NULL
                         THEN F.T_Tien - (ISNULL(F.Tien_Giam,0)+ISNULL(F.Tien_Ck,0)-F.CK_TheMg)
                         ELSE CAST(0 AS money) END) AS So_Tien,
            
                    ISNULL(F.Tyle_DS, ISNULL(CkDs.Tyle_Ds, ISNULL(LThe.Tyle_Ds, 0))) AS Tyle_Ds,
            
                    MAX(F.Diem_Tt) AS Diem_Tt,
            
                    MAX(F.LogName) AS LogName,
                    MAX(F.ten_NV)  AS Ten_NV
                FROM F
                LEFT JOIN DmH        AS H    ON F.ID_Hang = H.ID
                LEFT JOIN DmKho      AS K    ON F.ID_Kho  = K.ID
                LEFT JOIN DmNKho     AS NK   ON NK.ID     = K.ID_NKho
                LEFT JOIN DmLThe     AS LThe ON F.ID_LThe = LThe.ID
                LEFT JOIN DmLTheCkDs AS CkDs ON F.ID_LThe = CkDs.ID_LThe AND H.ID_Nhom = CkDs.ID_Nhom
                GROUP BY
                    F.ID,
                    F.ID_The,
                    F.ID_LThe,
                    F.Sp,
                    ISNULL(F.Tyle_DS, ISNULL(CkDs.Tyle_Ds, ISNULL(LThe.Tyle_Ds, 0)))
            ),
            T2 AS (
                SELECT
                    T.*,
                    DATEADD(day, -DATEDIFF(day, 0, T.Ngay_HD) % 7, CAST(T.Ngay_HD AS date)) AS WeekStart,
                    COUNT(*) OVER (
                        PARTITION BY T.So_The,
                        DATEADD(day, -DATEDIFF(day, 0, T.Ngay_HD) % 7, CAST(T.Ngay_HD AS date))
                    ) AS SoLan_Trong_Tuan
                FROM T
            )
            SELECT
                T2.ID,
                T2.ID_The,
                T2.ID_LThe,
                T2.Sp,
                T2.Ngay_HD AS Ngay_In,
                T2.So_The,
                T2.Ma_Kho,
                T2.Ten_Kho,
            T2.Ten_Nhom,
                T2.Ten_Hang_List,
                T2.So_TienNg,
                T2.Tien_Hang,
                T2.Ck_Gg,
                T2.So_Tien,
                T2.Tyle_Ds,
                T2.WeekStart,
                T2.SoLan_Trong_Tuan,
                T2.Diem_Tt,
                T2.LogName,
                T2.Ten_NV,
                CAST(FLOOR(CONVERT(decimal(18,2), T2.So_Tien) / 50000) AS int) AS Diem_Tich
            FROM T2
            WHERE T2.SoLan_Trong_Tuan >= 6;

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
                if expr == 'So_Tien' and value is not None:
                    value = f"{int(value):,}".replace(",", ".")
                if expr == 'Tien_Hang' and value is not None:
                    value = f"{int(value):,}".replace(",", ".")
                if expr == 'Ck_Gg' and value is not None:
                    value = f"{int(value):,}".replace(",", ".")
                if expr == 'Diem_Tt' and value is not None:
                    value = f"{int(value):,}".replace(",", ".")
                line_columns.append(report._build_column_dict(value, column, options=options))

            lines.append({
                'id': f"~line_{record['ID']}~",
                'name': '',
                'columns': line_columns,
                'level': 1,
                'unfoldable': False,
                'unfolded': False,
            })
        return [(0, line) for line in lines]
