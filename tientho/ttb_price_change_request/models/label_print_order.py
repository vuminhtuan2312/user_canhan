# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

import base64
import io
from openpyxl import Workbook


class TtbLabelPrintOrder(models.Model):
    _name = "ttb.label.print.order"
    _description = "Lệnh in nhãn"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(string="Mã tham chiếu", readonly=True, copy=False)

    request_id = fields.Many2one("ttb.price.change.request", required=True, ondelete="cascade", index=True)
    branch_id = fields.Many2one("ttb.branch", string="Cơ sở", required=True, index=True)

    responsible_user_id = fields.Many2one(
        "res.users",
        string="Người phụ trách",
        readonly=True,
        tracking=True,
        help="Lấy từ ttb.branch.manager_id",
    )

    executor_user_ids = fields.Many2many(
        "res.users",
        "ttb_label_print_order_executor_rel",
        "order_id",
        "user_id",
        string="Người thực hiện",
        tracking=True,
    )

    execute_date = fields.Datetime(string="Ngày thực hiện", default=fields.Datetime.now, tracking=True)

    note = fields.Text(string="Ghi chú", tracking=True)

    state = fields.Selection([
        ("printing", "Thực hiện in và dán"),
        ("audit", "Đang hậu kiểm"),
        ("done", "Hoàn thành"),
        ("cancel", "Hủy"),
    ], default="printing", tracking=True)

    print_state = fields.Selection(
        [
            ("draft", "Mới"),
            ("exported", "Đã xuất Excel"),
            ("labeled", "Đã dán"),
            ("checked", "Đã hậu kiểm"),
        ],
        string="Trạng thái",
        default="draft",
        tracking=True,
        required=True,
    )

    line_ids = fields.One2many("ttb.label.print.order.line", "order_id", string="Chi tiết", copy=True)

    # dùng để hiển thị theo tab A/B
    line_a_ids = fields.One2many(
        "ttb.label.print.order.line", "order_id",
        string="Tem kệ khu bán lẻ", domain=[("group_code", "=", "A")], readonly=True
    )
    line_b_ids = fields.One2many(
        "ttb.label.print.order.line", "order_id",
        string="Tem kệ khu vui chơi", domain=[("group_code", "=", "B")], readonly=True
    )

    line_c_ids = fields.One2many(
        "ttb.label.print.order.line", "order_id",
        string="Tem dán sản phẩm", domain=[("group_code", "=", "C")], readonly=True
    )

    def action_mark_labeled(self):
        self.ensure_one()

        if self.print_state != "exported":
            raise UserError("Chỉ có thể xác nhận Đã dán khi lệnh đã xuất Excel.")

        self.print_state = "labeled"

    def action_mark_checked(self):
        self.ensure_one()
        if self.responsible_user_id != self.env.user:
            raise UserError(
                _("Chỉ người phụ trách (%s) mới có quyền xác nhận Hậu kiểm.") % self.responsible_user_id.name)
        if self.print_state != "labeled":
            raise UserError("Chỉ có thể hậu kiểm khi lệnh đã ở trạng thái Đã dán.")

        self.print_state = "checked"

    def action_to_audit(self):
        for rec in self:
            rec.state = "audit"

    def action_done(self):
        for rec in self:
            rec.state = "done"

    def action_cancel(self):
        for rec in self:
            rec.state = "cancel"

    def action_print_and_update_state(self):
        """
        Hàm thực hiện 2 việc:
        1. Cập nhật trạng thái sang 'exported' (Đã xuất/Đang in)
        2. Trả về hành động tải file PDF
        """
        self.ensure_one()
        # Hoàn thiện logic sẽ thêm sau
        # if self.print_state == 'draft':
        self.write({'print_state': 'exported', 'execute_date': fields.Datetime.now()})

        return self.env.ref('ttb_price_change_request.action_report_ttb_label_print').report_action(self)

    def action_export_price_tag_group_a_xlsx(self):
        """
        Xuất file Excel tem giá dán cho Nhóm A.
        Cột theo yêu cầu:
        - ma_vach  : barcode sản phẩm
        - ten_hang : tên sản phẩm
        - d_v      : đơn vị tính (product.uom_id.name)
        - don_gia  : giá bán
        - So_luong : mặc định = 1
        - ngay_in  : ngày + thời điểm bấm nút xuất Excel
        """
        self.ensure_one()

        # Lấy dòng nhóm A
        lines = self.line_ids.filtered(lambda l: l.group_code == "A")
        if not lines:
            self.message_post(body="Không có dòng Nhóm A để xuất Excel.")
            return {"type": "ir.actions.act_window_close"}
        self.print_state = "exported"
        wb = Workbook()
        ws = wb.active
        ws.title = "Nhom A"

        # Header (GIỮ ĐÚNG THEO FILE MẪU)
        ws.append([
            "ma_vach",
            "ten_hang",
            "d_v",
            "don_gia",
            "So_luong",
            "ngay_in",
            "Quầy",
        ])

        # Thời điểm xuất
        ngay_in = fields.Date.context_today(self)

        # Rows
        for ln in lines:
            product = ln.product_id

            ma_vach = (product.barcode or "").strip()
            ten_hang = (product.name or "").strip()
            d_v = product.uom_id.name if product.uom_id else ""
            don_gia = ln.new_price or 0.0
            so_luong = ln.qty or 0.0
            quay = ln.mch1_id.display_name or ""
            ws.append([
                ma_vach,
                ten_hang,
                d_v,
                don_gia,
                so_luong,
                ngay_in,
                quay,
            ])

        # (Tuỳ chọn) chỉnh độ rộng cột cho giống file Excel mẫu
        ws.column_dimensions["A"].width = 18
        ws.column_dimensions["B"].width = 45
        ws.column_dimensions["C"].width = 10
        ws.column_dimensions["D"].width = 12
        ws.column_dimensions["E"].width = 10
        ws.column_dimensions["F"].width = 20
        ws.column_dimensions["G"].width = 20

        # Save to bytes
        buff = io.BytesIO()
        wb.save(buff)
        buff.seek(0)
        data = buff.read()

        filename = f"tem_gia_nhom_A_{(self.name or 'LENH_IN').replace('/', '_')}.xlsx"
        attachment = self.env["ir.attachment"].sudo().create({
            "name": filename,
            "type": "binary",
            "datas": base64.b64encode(data),
            "res_model": self._name,
            "res_id": self.id,
            "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        })
        self.env.cr.commit()
        return {
            "type": "ir.actions.client",
            "tag": "action_download_and_reload",  # Tên action đã đăng ký trong JS
            "params": {
                "url": f"/web/content/{attachment.id}?download=true",
            },
        }
        # return {
        #     "type": "ir.actions.act_url",
        #     "url": f"/web/content/{attachment.id}?download=true",
        #     "target": "self",
        # }

    def action_export_price_tag_group_b_xlsx(self):
        """
        Xuất file Excel tem giá dán cho Nhóm B.
        Cột theo yêu cầu:
        - ma_vach  : barcode (chi tiết lệnh in)
        - ten_hang : product_name (chi tiết lệnh in)
        - don_gia  : new_price (chi tiết lệnh in)
        - (cột trống): blank bắt buộc
        - so_luong : số lượng KBL (ưu tiên field qty_kbl nếu có, fallback qty)
        """
        self.ensure_one()
        self.write({'print_state': 'exported'})
        # Lấy dòng nhóm B
        lines = self.line_ids.filtered(lambda l: l.group_code == "B")
        if not lines:
            # Không raise để user vẫn bấm được; tuỳ bạn muốn UserError thì đổi
            self.message_post(body="Không có dòng Nhóm B để xuất Excel.")
            return {"type": "ir.actions.act_window_close"}
        self.print_state = "exported"
        wb = Workbook()
        ws = wb.active
        ws.title = "Nhom B"

        # Header (giữ đúng như file mẫu)
        ws.append(["ma_vach", "ten_hang", "don_gia", "", "So_luong"])

        # Rows
        for ln in lines:
            barcode = (ln.barcode or "").strip()
            ten_hang = (ln.product_name or "").strip()
            don_gia = ln.new_price or 0.0

            # số lượng KBL: ưu tiên field qty_kbl nếu module bạn có, fallback qty
            if "qty_kbl" in ln._fields:
                so_luong = ln.qty_kbl or 0.0
            else:
                so_luong = ln.qty or 0.0

            ws.append([barcode, ten_hang, don_gia, "", so_luong])

        # (Tuỳ chọn) chỉnh độ rộng cột cho dễ nhìn
        ws.column_dimensions["A"].width = 18
        ws.column_dimensions["B"].width = 55
        ws.column_dimensions["C"].width = 12
        ws.column_dimensions["D"].width = 6
        ws.column_dimensions["E"].width = 10

        # Save to bytes
        buff = io.BytesIO()
        wb.save(buff)
        buff.seek(0)
        data = buff.read()

        filename = f"tem_gia_nhom_B_{(self.name or 'LENH_IN').replace('/', '_')}.xlsx"
        attachment = self.env["ir.attachment"].sudo().create({
            "name": filename,
            "type": "binary",
            "datas": base64.b64encode(data),
            "res_model": self._name,
            "res_id": self.id,
            "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        })
        self.env.cr.commit()
        return {
            "type": "ir.actions.client",
            "tag": "action_download_and_reload",  # Tên action đã đăng ký trong JS
            "params": {
                "url": f"/web/content/{attachment.id}?download=true",
            },
        }
        # return {
        #     "type": "ir.actions.act_url",
        #     "url": f"/web/content/{attachment.id}?download=true",
        #     "target": "self",
        # }

    def _get_realtime_stock_from_augges(self, branch_warehouse_ids, product_augges_ids):
        """
        Lấy tồn kho realtime từ Augges
        Return:
            {
                product_augges_id: {
                    'SL_Ton': Decimal
                }
            }
        """
        if not branch_warehouse_ids or not product_augges_ids:
            return {}

        conn = self.env['ttb.tools'].get_mssql_connection()

        # đảm bảo luôn là list
        if isinstance(branch_warehouse_ids, int):
            branch_warehouse_ids = [branch_warehouse_ids]
        if isinstance(product_augges_ids, int):
            product_augges_ids = [product_augges_ids]

        ids_kho_str = ','.join(map(str, branch_warehouse_ids))
        ids_hang_str = ','.join(map(str, product_augges_ids))

        sql = f""" SELECT ID_Kho, ID_Hang, Ma_Hang, Ma_Tong, SUM(Sl_Cky) AS SL_Ton, SUM(So_Luong) AS So_Luong
            FROM ( SELECT Htk.ID_Kho, Htk.ID_Hang, DmH.Ma_Hang, ISNULL(DmH.Ma_Tong, SPACE(25)) AS Ma_Tong, SUM(Htk.So_Luong) AS Sl_Cky, CAST(0 AS money) AS So_Luong
            FROM Htk LEFT JOIN DmKho ON Htk.ID_Kho = DmKho.ID
            LEFT JOIN DmH ON Htk.ID_Hang = DmH.ID
            LEFT JOIN DmNh ON DmH.ID_Nhom = DmNh.ID 
            WHERE Htk.ID_Kho IN ({ids_kho_str}) AND Htk.ID_Hang IN ({ids_hang_str}) GROUP BY Htk.ID_Kho, Htk.ID_Hang, DmH.Ma_Hang, DmH.Ma_Tong 
                                
              UNION ALL 
              SELECT SlNxM.ID_Kho, SlNxD.ID_Hang, 
              DmH.Ma_Hang, ISNULL(DmH.Ma_Tong, SPACE(25)) AS Ma_Tong, SUM( CASE WHEN DmNx.Ma_Ct IN ('NK','NM','PN','NS','NL') THEN SlNxD.So_Luong ELSE -SlNxD.So_Luong END ) AS Sl_Cky, SUM( CASE WHEN DmNx.Ma_Ct IN ('XK','XB','NL') THEN CASE WHEN DmNx.Ma_Ct IN ('XK','XB') THEN SlNxD.So_Luong ELSE -SlNxD.So_Luong END ELSE CAST(0 AS money) END ) AS So_Luong 
              FROM SlNxD 
              LEFT JOIN SlNxM ON SlNxD.ID = SlNxM.ID 
              LEFT JOIN DmNx ON SlNxM.ID_Nx = DmNx.ID 
              LEFT JOIN DmH ON SlNxD.ID_Hang = DmH.ID 
              LEFT JOIN DmNh ON DmH.ID_Nhom = DmNh.ID 
              WHERE SlNxM.ID_Dv = 0 AND SlNxD.ID_Kho IN ({ids_kho_str}) AND SlNxD.ID_Hang IN ({ids_hang_str}) 
              GROUP BY SlNxM.ID_Kho, SlNxD.ID_Hang, DmH.Ma_Hang, DmH.Ma_Tong 

              UNION ALL 
              SELECT SlBlM.ID_Kho, SlBlD.ID_Hang, DmH.Ma_Hang, ISNULL(DmH.Ma_Tong, SPACE(25)) AS Ma_Tong, SUM(-SlBlD.So_Luong) AS Sl_Cky, CAST(0 AS money) AS So_Luong 
              FROM SlBlD 
              LEFT JOIN SlBlM ON SlBlD.ID = SlBlM.ID 
              LEFT JOIN DmH ON SlBlD.ID_Hang = DmH.ID 
              LEFT JOIN DmNh ON DmH.ID_Nhom = DmNh.ID 
              WHERE SlBlM.ID_Dv = 0 AND ISNULL(SlBlD.ID_Kho, SlBlM.ID_Kho) IN ({ids_kho_str}) AND SlBlD.ID_Hang IN ({ids_hang_str}) 
              GROUP BY SlBlM.ID_Kho, SlBlD.ID_Hang, DmH.Ma_Hang, DmH.Ma_Tong 

              UNION ALL 
              SELECT SlDcD.ID_KhoX AS ID_Kho, SlDcD.ID_Hang, DmH.Ma_Hang, ISNULL(DmH.Ma_Tong, SPACE(25)) AS Ma_Tong, SUM(-SlDcD.So_Luong) AS Sl_Cky, CAST(0 AS money) AS So_Luong 
              FROM SlDcD 
              LEFT JOIN SlDcM ON SlDcD.ID = SlDcM.ID 
              LEFT JOIN DmKho ON SlDcD.ID_KhoX = DmKho.ID 
              LEFT JOIN DmH ON SlDcD.ID_Hang = DmH.ID 
              LEFT JOIN DmNh ON DmH.ID_Nhom = DmNh.ID 
              WHERE SlDcM.ID_Dv = 0 AND SlDcD.ID_KhoX IN ({ids_kho_str}) AND SlDcD.ID_Hang IN ({ids_hang_str}) 
              GROUP BY SlDcD.ID_KhoX, SlDcD.ID_Hang, DmH.Ma_Hang, DmH.Ma_Tong 

              UNION ALL 
              SELECT SlDcD.ID_KhoN AS ID_Kho, SlDcD.ID_Hang, DmH.Ma_Hang, ISNULL(DmH.Ma_Tong, SPACE(25)) AS Ma_Tong, SUM(SlDcD.So_Luong) AS Sl_Cky, CAST(0 AS money) AS So_Luong 
              FROM SlDcD 
              LEFT JOIN SlDcM ON SlDcD.ID = SlDcM.ID 
              LEFT JOIN DmKho ON SlDcD.ID_KhoN = DmKho.ID 
              LEFT JOIN DmH ON SlDcD.ID_Hang = DmH.ID 
              LEFT JOIN DmNh ON DmH.ID_Nhom = DmNh.ID 
              WHERE SlDcM.ID_Dv = 0 AND SlDcD.ID_KhoN IN ({ids_kho_str}) AND SlDcD.ID_Hang IN ({ids_hang_str}) 
              GROUP BY SlDcD.ID_KhoN, SlDcD.ID_Hang, DmH.Ma_Hang, DmH.Ma_Tong 
              ) AS Dt_Hang 
              WHERE Sl_Cky <> 0 OR So_Luong <> 0 
              GROUP BY ID_Kho, ID_Hang, Ma_Hang, Ma_Tong 
            """

        cr = conn.cursor()
        cr.execute(sql)
        rows = cr.fetchall()

        result = {}
        for row in rows:
            _id_kho = row[0]
            _id_hang = row[1]
            sl_ton = row[4] or 0

            # gộp tồn theo ID_Hang
            result.setdefault(_id_hang, {'SL_Ton': 0})
            result[_id_hang]['SL_Ton'] += sl_ton

        return result

    def action_update_qty_from_augges(self):
        self.ensure_one()

        product_line_map = {
            line.product_id.augges_id: line
            for line in self.line_ids
            if line.product_id and line.product_id.augges_id
        }

        warehouses = self.env['stock.warehouse'].search([
            ('ttb_branch_id', '=', self.branch_id.id)
        ])

        stock_data = self._get_realtime_stock_from_augges(
            branch_warehouse_ids=warehouses.mapped('id_augges'),
            product_augges_ids=list(product_line_map.keys())
        )

        for augges_id, line in product_line_map.items():
            line.qty_kvc = stock_data.get(augges_id, {}).get('SL_Ton', 0)

class TtbLabelPrintOrderLine(models.Model):
    _name = "ttb.label.print.order.line"
    _description = "Chi tiết lệnh in nhãn"
    _order = "id"

    order_id = fields.Many2one("ttb.label.print.order", required=True, ondelete="cascade", index=True)
    request_line_id = fields.Many2one("ttb.price.change.request.line", string="Dòng phiếu giá", ondelete="set null")

    product_id = fields.Many2one("product.product", string="Sản phẩm", required=True, index=True)

    mch1_id = fields.Many2one("product.category", string="MCH1", readonly=True)
    barcode = fields.Char(string="Mã vạch", readonly=True)
    default_code = fields.Char(string="Mã sản phẩm", readonly=True)
    product_name = fields.Char(string="Tên sản phẩm", readonly=True)

    old_price = fields.Float(string="Giá cũ")
    new_price = fields.Float(string="Giá mới")
    old_kvc_price = fields.Float(string="Giá KVC cũ")
    new_kvc_price = fields.Float(string="Giá KVC mới")

    qty = fields.Float(string="Số lượng kbl", default=1.0)  # tạm thời luôn = 1
    qty_kvc = fields.Float(string="Số lượng kvc", default=1.0)  # tạm thời luôn = 1

    group_code = fields.Selection([("A", "Tem kệ khu bán lẻ"), ("B", "Tem kệ khu vui chơi"), ("C", "Tem dán sản phẩm")], default="A", index=True)

    def get_barcode_to_print(self):
        self.ensure_one()
        product = self.product_id
        if not product:
            return False

        def get_val(attr_name):
            val = getattr(product, attr_name, False)
            return str(val).strip() if val else False

        fields_check = ['barcode_vendor', 'default_code', 'barcode', 'barcode_k']

        for field in fields_check:
            val = get_val(field)
            if val and len(val) >= 11:
                return val

        for field in fields_check:
            val = get_val(field)
            if val:
                return val

        return False