# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta


def _fetch_augges_prices(env, augges_id, conn=None, cursor=None):
    """
    Trả về dict giá từ Augges cho 1 ID hàng hóa.
    """
    if not augges_id:
        return {}

    owns_conn = False
    if not conn:
        conn = env["ttb.tools"].get_mssql_connection_send()
        owns_conn = True
        cursor = conn.cursor()
    elif not cursor:
        cursor = conn.cursor()

    cursor.execute(
        """
        SELECT Gia_Ban, Gia_Ban1, Gia_Ban2, Gia_Ban3, Gia_Ban4, Gia_Ban5, Gia_Ban6, Gia_Bl
        FROM DmH WHERE ID = ?
        """,
        (int(augges_id),)
    )
    row = cursor.fetchone()

    if owns_conn:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

    if not row:
        return {}

    # pyodbc row thường index theo vị trí
    return {
        "Gia_Ban":  float(row[0] or 0.0),
        "Gia_Ban1": float(row[1] or 0.0),
        "Gia_Ban2": float(row[2] or 0.0),
        "Gia_Ban3": float(row[3] or 0.0),
        "Gia_Ban4": float(row[4] or 0.0),
        "Gia_Ban5": float(row[5] or 0.0),
        "Gia_Ban6": float(row[6] or 0.0),
        "Gia_Bl":   float(row[7] or 0.0),
    }

def _safe_get_price_from_augges(request, product, augg_col_name):

    if not product or not product.augges_id:
        return 0.0

    cache = request._context.get("_augges_price_cache")
    if cache is None:
        cache = {}
        request = request.with_context(_augges_price_cache=cache)

    key = int(product.augges_id)
    if key not in cache:
        cache[key] = _fetch_augges_prices(request.env, key)

    return float(cache[key].get(augg_col_name) or 0.0)


class TtbPriceChangeRequest(models.Model):
    _name = "ttb.price.change.request"
    _description = "Phiếu yêu cầu thay đổi giá"
    _inherit = ["mail.thread", "mail.activity.mixin", "ttb.approval.mixin"]
    _order = "create_date desc"

    name = fields.Char("Mã tham chiếu", readonly=True, copy=False, default=lambda self: _("New"))
    description = fields.Char("Diễn giải", required=True, tracking=True)

    request_date = fields.Datetime("Ngày đề nghị", default=fields.Datetime.now, required=True, tracking=True)
    approved_at = fields.Datetime("Thời gian duyệt", readonly=True, tracking=True)
    effective_at = fields.Datetime("Thời gian áp dụng", tracking=True, required=True)

    requested_by = fields.Many2one("res.users", string="Người đề nghị", default=lambda self: self.env.user, required=True, tracking=True)
    approver_id = fields.Many2one("res.users", string="Người phê duyệt", tracking=True)
    supporter_id = fields.Many2one("res.users", string="Người hỗ trợ", tracking=True)
    responsible_candidate_user_ids = fields.Many2many(
        "res.users",
        compute="_compute_responsible_candidates",
        store=False,
    )
    supporter_candidate_user_ids = fields.Many2many(
        "res.users",
        compute="_compute_supporter_candidates",
        store=False,
    )
    responsible_user_ids = fields.Many2many(
        "res.users",
        string="Người phụ trách",
        relation='responsible_user_ids_rel',
        tracking=True,
        default=lambda self: self._default_responsible_users(),
    )
    supporter_user_ids = fields.Many2many(
        "res.users",
        string="Người hỗ trợ",
        relation='supporter_user_ids_rel',
        tracking=True,
        default=lambda self: self._default_supporter_users(),
    )

    @api.model
    def _default_responsible_users(self):
        branches = self.env["ttb.branch"].sudo().search([("director_id", "!=", False)])
        user_ids = branches.mapped("director_id").ids
        return [(6, 0, list(set(user_ids)))]

    @api.model
    def _default_supporter_users(self):
        branches = self.env["ttb.branch"].sudo().search([("manager_id", "!=", False)])
        user_ids = branches.mapped("manager_id").ids
        return [(6, 0, list(set(user_ids)))]

    @api.depends()
    def _compute_responsible_candidates(self):
        branches = self.env["ttb.branch"].sudo().search([("director_id", "!=", False)])
        user_ids = list(set(branches.mapped("director_id").ids))
        for rec in self:
            rec.responsible_candidate_user_ids = [(6, 0, user_ids)]

    @api.depends()
    def _compute_supporter_candidates(self):
        branches = self.env["ttb.branch"].sudo().search([("manager_id", "!=", False)])
        user_ids = list(set(branches.mapped("manager_id").ids))
        for rec in self:
            rec.supporter_candidate_user_ids = [(6, 0, user_ids)]


    state = fields.Selection([
        ("draft", "Mới"),
        ("to_approve", "Đang duyệt"),
        ("updating", "Đang cập nhật Augges"),
        ("done", "Đã cập nhật Augges"),
        ("cancel", "Hủy"),
    ], default="draft", tracking=True)

    def _classify_label_group(self, request_line, price_level):
        """
        Phân loại nhóm in nhãn A, B, C dựa trên MCH1, MCH2 và loại giá (price_level).

        Quy tắc:
        - Nhóm A: (MCH1=14 hoặc MCH2=1102) & Giá thuộc (BB1, BB3, BB4, BB5, BB6, BL)
        - Nhóm B: (MCH1=14 hoặc MCH2=1102) & Giá thuộc (BB2)
        - Nhóm C: Tất cả các trường hợp còn lại (MCH1 khác 14...)
        """
        # Lấy code MCH1
        categ_1 = request_line.categ_id_level_1
        code_1 = str(getattr(categ_1, "category_code", "") or "")

        # Lấy code MCH2 (Thêm field này vào model line bên dưới)
        categ_2 = request_line.categ_id_level_2
        code_2 = str(getattr(categ_2, "category_code", "") or "")

        # Kiểm tra điều kiện nhóm MCH1=14 và MCH2=1102
        if code_1 == "14" or code_2 == "1102":
            if price_level == "bb2":
                return "B"
            elif price_level in ["bb1", "bb3", "bb4", "bb5", "bb6", "bl"]:
                return "A"

        # Mặc định còn lại là nhóm B
        return "C"

    def _get_13_branches_for_label_orders(self):
        """
        Lấy đúng 13 cơ sở theo branch.name (bỏ HO/TNK/DC).
        """
        Branch = self.env["ttb.branch"].sudo()

        allowed_names = [
            "HNI - HOÀNG MAI - GIẢI PHÓNG",
            "HNI - THANH XUÂN - NGUYỄN TRÃI",
            "HPG - NGÔ QUYỀN - LÊ HỒNG PHONG",
            "BGG - NGÔ QUYỀN - BẮC GIANG",
            "HNI - XUÂN THỦY - CẦU GIẤY",
            "HNI - ĐỐNG ĐA - LÁNG",
            "NAN - VINH - TRẦN PHÚ",
            "THA - LAM SƠN - LÊ LỢI",
            "TBH - ĐỀ THÁM - LÝ BÔN",
            "TNN - HOÀNG VĂN THỤ - LƯƠNG NGỌC QUYẾN",
            "HCM - Q12 - TRƯỜNG CHINH",
            "BDG - THỦ DẦU MỘT - CHÁNH NGHĨA",
            "BDG - THUẬN AN - AN PHÚ",
        ]

        # Search tất cả branch có name nằm trong allowed_names
        branches = Branch.search([("name", "in", allowed_names)])

        # Sắp xếp đúng theo thứ tự allowed_names (để tạo lệnh in theo đúng thứ tự mong muốn)
        by_name = {b.name: b for b in branches}
        ordered = [by_name.get(n) for n in allowed_names if by_name.get(n)]

        # Nếu thiếu (do khác dấu/cách viết), fallback thêm bằng ilike theo key ngắn
        # if len(ordered) < len(allowed_names):
        #     # Không raise để vẫn chạy; bạn sẽ nhìn log thiếu và chỉnh lại tên
        #     missing = [n for n in allowed_names if n not in by_name]
        #     self.message_post(body=_("Thiếu cơ sở khi match theo name: %s") % ", ".join(missing))

        return self.env["ttb.branch"].browse([b.id for b in ordered])

    def _compose_label_order_ref(self, branch):
        """
        Tạo mã tham chiếu gọn cho lệnh in nhãn, không phụ thuộc mã cơ sở.
        Ví dụ: IN001/PCR00001
        """
        self.ensure_one()
        name = (branch.name or "").strip()

        # Map prefix theo 13 cơ sở
        prefix_map = {
            "HNI - HOÀNG MAI - GIẢI PHÓNG": "IN001",
            "HNI - THANH XUÂN - NGUYỄN TRÃI": "IN002",
            "HNI - ĐỐNG ĐA - LÁNG": "IN003",
            "HNI - XUÂN THỦY - CẦU GIẤY": "IN004",

            "HPG - NGÔ QUYỀN - LÊ HỒNG PHONG": "IN005",
            "TNN - HOÀNG VĂN THỤ - LƯƠNG NGỌC QUYẾN": "IN006",
            "TBH - ĐỀ THÁM - LÝ BÔN": "IN007",
            "THA - LAM SƠN - LÊ LỢI": "IN008",
            "NAN - VINH - TRẦN PHÚ": "IN009",
            "BGG - NGÔ QUYỀN - BẮC GIANG": "IN010",

            "HCM - Q12 - TRƯỜNG CHINH": "IN011",
            "BDG - THỦ DẦU MỘT - CHÁNH NGHĨA": "IN012",
            "BDG - THUẬN AN - AN PHÚ": "IN013",
        }

        prefix = prefix_map.get(name, "IN")
        return f"{prefix}/{self.name}"

    def _get_branch_price_level(self, branch):
        """
        Map cơ sở (theo branch.name) -> level giá:
        - BL: 4 CS HN: LÁNG, XUÂN THỦY, NGUYỄN TRÃI, GIẢI PHÓNG
        - BB1: Thái Nguyên, Thái Bình, Thanh Hóa, Hải Phòng
        - BB3: HCM
        - BB4: Bình Dương
        - BB5: Nghệ An (Vinh)
        - BB6: Bắc Giang
        """
        name = (branch.name or "").strip()

        # BL: 4 cơ sở HN
        bl_names = {
            "HNI - ĐỐNG ĐA - LÁNG",
            "HNI - XUÂN THỦY - CẦU GIẤY",
            "HNI - THANH XUÂN - NGUYỄN TRÃI",
            "HNI - HOÀNG MAI - GIẢI PHÓNG",
        }
        if name in bl_names:
            return "bl"

        # BB4: Bình Dương
        if name in {
            "BDG - THỦ DẦU MỘT - CHÁNH NGHĨA",
            "BDG - THUẬN AN - AN PHÚ",
        }:
            return "bb4"

        # BB3: HCM
        if name == "HCM - Q12 - TRƯỜNG CHINH":
            return "bb3"

        # BB6: Bắc Giang
        if name == "BGG - NGÔ QUYỀN - BẮC GIANG":
            return "bb6"

        # BB5: Nghệ An (Vinh)
        if name == "NAN - VINH - TRẦN PHÚ":
            return "bb5"

        # BB1: Thái Nguyên – Thái Bình – Thanh Hóa – Hải Phòng
        if name in {
            "TNN - HOÀNG VĂN THỤ - LƯƠNG NGỌC QUYẾN",  # Thái Nguyên
            "TBH - ĐỀ THÁM - LÝ BÔN",  # Thái Bình
            "THA - LAM SƠN - LÊ LỢI",  # Thanh Hóa
            "HPG - NGÔ QUYỀN - LÊ HỒNG PHONG",  # Hải Phòng
        }:
            return "bb1"

        # Default
        return "bb1"

    def _prepare_label_lines_for_branch(self, branch):
        """
        Tạo lines cho 1 lệnh in nhãn theo branch với quy tắc lọc mới:
        - TH1: Giá mới != Giá cũ (và khác 0) => TẠO
        - TH2: Giá mới != Giá cũ (nhưng Giá mới = 0) => KHÔNG TẠO
        - TH3: Giá mới == Giá cũ => KHÔNG TẠO
        """
        self.ensure_one()

        level = self._get_branch_price_level(branch)

        # Map level -> field giá trên PCR line
        field_map = {
            "bb1": ("old_bb1_price", "new_bb1_price"),
            "bb2": ("old_bb2_price", "new_bb2_price"),
            "bb3": ("old_bb3_price", "new_bb3_price"),
            "bb4": ("old_bb4_price", "new_bb4_price"),
            "bb5": ("old_bb5_price", "new_bb5_price"),
            "bb6": ("old_bb6_price", "new_bb6_price"),
            "bl": ("old_bl_price", "new_bl_price"),
        }
        old_f, new_f = field_map.get(level, ("old_bb1_price", "new_bb1_price"))
        old_f_bb2, new_f_bb2 = "old_bb2_price", "new_bb2_price"

        vals_list = []

        # Duyệt qua danh sách sản phẩm thay đổi giá (Hoặc tất cả line_ids nếu muốn check hết)
        # Tốt nhất duyệt line_ids để đảm bảo không sót
        for ln in self.line_ids:
            old_price = float(getattr(ln, old_f, 0.0) or 0.0)
            new_price = float(getattr(ln, new_f, 0.0) or 0.0)

            # --- ÁP DỤNG QUY TẮC LỌC ---

            # TH3: Giá mới = Giá cũ => Bỏ qua
            # if abs(new_price - old_price) < 0.0001:
            #     continue

            # TH2: Giá mới = 0 => Bỏ qua (Dù khác giá cũ)
            if new_price == 0:
                continue

            # TH1: Giá mới khác giá cũ và khác 0 => Xử lý tạo lệnh in

            # Phân loại nhóm A, B, C (truyền thêm level giá)
            if abs(new_price - old_price) > 0.0001 and new_price > 0:
                group_code = self._classify_label_group(ln, level)

                vals_list.append({
                    "request_line_id": ln.id,
                    "product_id": ln.product_id.id,
                    "mch1_id": ln.categ_id_level_1.id if ln.categ_id_level_1 else False,
                    "barcode": ln.barcode,
                    "default_code": ln.default_code,
                    "product_name": ln.product_id.display_name,
                    "old_price": old_price,
                    "new_price": new_price,
                    "old_kvc_price": old_price,  # tạm đồng bộ kvc = kbl
                    "new_kvc_price": new_price,  # tạm đồng bộ kvc = kbl
                    "qty": 1.0,
                    "qty_kvc": 1.0,
                    "group_code": group_code,
                })
            if level != 'bb2':
                old_bb2 = float(getattr(ln, old_f_bb2, 0.0) or 0.0)
                new_bb2 = float(getattr(ln, new_f_bb2, 0.0) or 0.0)

                if abs(new_bb2 - old_bb2) > 0.0001 and new_bb2 > 0:
                    # Yêu cầu: "sẽ được tạo ở group B"

                    vals_list.append({
                        "request_line_id": ln.id,
                        "product_id": ln.product_id.id,
                        "mch1_id": ln.categ_id_level_1.id if ln.categ_id_level_1 else False,
                        "barcode": ln.barcode,
                        "default_code": ln.default_code,
                        "product_name": ln.product_id.display_name,
                        "old_price": old_bb2,
                        "new_price": new_bb2,  # Quan trọng: Giá in ra phải là giá BB2
                        "old_kvc_price": old_bb2,
                        "new_kvc_price": new_bb2,
                        "qty": 1.0,
                        "qty_kvc": 1.0,
                        "group_code": "B",  # Cố định là nhóm B cho KVC
                    })

        return vals_list

    def _generate_label_print_orders(self):
        """PCR done -> tạo 13 lệnh in nhãn cho 13 cơ sở."""
        self.ensure_one()

        branches = self._get_13_branches_for_label_orders()
        if not branches:
            return

        Order = self.env["ttb.label.print.order"].sudo()

        # tránh tạo trùng nếu chạy lại
        existing = Order.search([("request_id", "=", self.id)])
        if existing:
            existing.unlink()

        for br in branches:
            line_vals = self._prepare_label_lines_for_branch(br)
            if not line_vals:
                continue
            order = Order.create({
                "request_id": self.id,
                "branch_id": br.id,
                "responsible_user_id": br.manager_id.id if br.manager_id else False,
                "name": self._compose_label_order_ref(br),
            })

            order.write({"line_ids": [(0, 0, v) for v in line_vals]})

    def _notify_users(self, users, message, subject=None):
        """Gửi thông báo qua chatter cho danh sách users."""
        users = users.filtered(lambda u: u and u.partner_id)
        partner_ids = users.mapped("partner_id").ids
        if not partner_ids:
            return
        self.message_post(
            body=message,
            subject=subject or False,
            partner_ids=partner_ids,
        )

    def _msg_with_ref(self, text):
        """Thay [Mã tham chiếu yêu cầu] bằng self.name"""
        return (text or "").replace("[Mã tham chiếu yêu cầu]", self.name or "")

    def _get_tncu_users(self):
        """TNCU = Người tạo phiếu"""
        return self.requested_by

    def _get_gdcu_users(self):
        """
        GĐCU = Người đang duyệt (theo ttb_approval).
        Ưu tiên current_approve_user_ids, fallback next_approve_user_ids.
        """
        if self.current_approve_user_ids:
            return self.current_approve_user_ids
        if self.next_approve_user_ids:
            return self.next_approve_user_ids
        return self.env["res.users"]

    def _get_users_after_approved(self):
        """TNCU + Người phụ trách + Người hỗ trợ"""
        users = self.env["res.users"]
        users |= self._get_tncu_users()
        users |= self.responsible_user_ids
        users |= self.supporter_user_ids
        return users

    line_ids = fields.One2many("ttb.price.change.request.line", "request_id", string="Chi tiết sản phẩm", copy=True)
    line_ids_changed = fields.One2many(
        "ttb.price.change.request.line",
        "request_id",
        string="Sản phẩm thay đổi giá",
        domain=[('is_changed', '=', True)]
    )
    line_ids_unchanged = fields.One2many(
        "ttb.price.change.request.line",
        "request_id",
        string="Sản phẩm không đổi giá",
        domain=[('is_changed', '=', False)]  # Lọc cứng tại đây
    )
    line_count = fields.Integer("Tổng số lượng sản phẩm thay đổi", compute="_compute_line_count", store=True)

    attachment_ids = fields.Many2many(
        "ir.attachment",
        "ttb_pcr_ir_attachment_rel",
        "pcr_id",
        "attachment_id",
        string="Tài liệu đính kèm",
        help="Đính kèm tài liệu liên quan (PDF, Excel, hình ảnh, ...).",
        tracking=True,
    )

    note = fields.Text(string="Ghi chú", tracking=True)

    def _get_update_columns(self):
        """Map new_* -> cột Augges + level code để lưu lịch sử."""
        return {
            "sale": ("Gia_Ban", "new_sale_price"),
            "bb1": ("Gia_Ban1", "new_bb1_price"),
            "bb2": ("Gia_Ban2", "new_bb2_price"),
            "bb3": ("Gia_Ban3", "new_bb3_price"),
            "bb4": ("Gia_Ban4", "new_bb4_price"),
            "bb5": ("Gia_Ban5", "new_bb5_price"),
            "bb6": ("Gia_Ban6", "new_bb6_price"),
            "bl": ("Gia_Bl", "new_bl_price"),
        }

    def _fetch_augges_prices_batch(self, augges_ids, cursor):
        if not augges_ids:
            return {}
        placeholders = ",".join(["?"] * len(augges_ids))
        cursor.execute(
            f"""
            SELECT ID, Gia_Ban, Gia_Ban1, Gia_Ban2, Gia_Ban3, Gia_Ban4, Gia_Ban5, Gia_Ban6, Gia_Bl
            FROM DmH WHERE ID IN ({placeholders})
            """,
            tuple(augges_ids)
        )
        rows = cursor.fetchall()
        res = {}
        for r in rows:
            rid = int(r[0])
            res[rid] = {
                "Gia_Ban": float(r[1] or 0.0),
                "Gia_Ban1": float(r[2] or 0.0),
                "Gia_Ban2": float(r[3] or 0.0),
                "Gia_Ban3": float(r[4] or 0.0),
                "Gia_Ban4": float(r[5] or 0.0),
                "Gia_Ban5": float(r[6] or 0.0),
                "Gia_Ban6": float(r[7] or 0.0),
                "Gia_Bl": float(r[8] or 0.0),
            }
        return res

    def _do_update_and_verify_augges_all(self):
        self.ensure_one()

        lines = self.line_ids.filtered(lambda l: l.product_id and l.product_id.augges_id)
        if not lines:
            raise UserError(_("Không có sản phẩm nào có augges_id để cập nhật."))

        # danh sách augges id
        augges_ids = []
        for ln in lines:
            try:
                augges_ids.append(int(ln.product_id.augges_id))
            except Exception:
                continue
        augges_ids = list(set(augges_ids))
        if not augges_ids:
            raise UserError(_("Danh sách augges_id không hợp lệ."))

        col_map = self._get_update_columns()
        history_model = self.env["ttb.pcr.update.history"].sudo()

        conn = self.env["ttb.tools"].get_mssql_connection_send()
        cursor = conn.cursor()

        try:
            # 1) đọc trước để lưu old_value chuẩn theo DB
            before_map = self._fetch_augges_prices_batch(augges_ids, cursor)

            # 2) tạo lịch sử pending + update
            history_vals = []

            for ln in lines:
                aid = int(ln.product_id.augges_id)
                before = before_map.get(aid, {})

                for level, (sql_col, new_field) in col_map.items():
                    new_val = float(getattr(ln, new_field, 0.0) or 0.0)

                    # bạn muốn update tất cả: nếu field để trống thì vẫn set 0
                    old_db = float(before.get(sql_col) or 0.0)

                    history_vals.append({
                        "request_id": self.id,
                        "request_line_id": ln.id,
                        "product_id": ln.product_id.id,
                        "augges_id": aid,
                        "price_level": level,
                        "old_value": old_db,
                        "new_value": new_val,
                        "state": "pending",
                    })

                    cursor.execute(f"UPDATE DmH SET {sql_col} = ? WHERE ID = ?", (new_val, aid))
                    # đảm bảo update đúng 1 dòng
                    if cursor.rowcount != 1:
                        raise UserError(_("Không cập nhật được Augges ID=%s (rowcount=%s).") % (aid, cursor.rowcount))

            if history_vals:
                history_model.create(history_vals)

            conn.commit()

            # 3) đọc lại để verify ngay sau commit
            after_map = self._fetch_augges_prices_batch(augges_ids, cursor)

        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            raise UserError(_("Lỗi khi cập nhật Augges: %s") % (str(e)))
        finally:
            try:
                cursor.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass

        # 4) verify + cập nhật lịch sử
        histories = history_model.search([("request_id", "=", self.id), ("state", "=", "pending")])
        mismatches = []
        has_any_success = False

        tol = 0.0001
        level_to_col = {lvl: v[0] for lvl, v in col_map.items()}

        for h in histories:
            sql_col = level_to_col.get(h.price_level)
            after = after_map.get(h.augges_id, {})
            updated_val = float(after.get(sql_col) or 0.0)

            new_val = float(h.new_value or 0.0)
            old_val = float(h.old_value or 0.0)

            # === TRƯỜNG HỢP KHÔNG ĐỔI GIÁ → BỎ QUA ===
            if abs(new_val - old_val) <= tol:
                h.write({
                    "state": "skipped",
                    "updated_value": updated_val,
                })
                continue

            # === CÓ ĐỔI GIÁ → CHECK KẾT QUẢ ===
            if abs(updated_val - new_val) <= tol:
                h.write({
                    "state": "success",
                    "updated_value": updated_val,
                })
                has_any_success = True
            else:
                h.write({
                    "state": "mismatch",
                    "updated_value": updated_val,
                })
                mismatches.append(h)

        # 5) quyết định trạng thái
        if has_any_success:
            self.write({"state": "done"})
            self.message_post(body=_("Đã cập nhật Augges thành công (có ít nhất 1 giá thay đổi hợp lệ)."))
            # tạm thời bỏ đồng bộ giá vào bảng giá
            # try:
            #     self._sync_price_to_odoo_pricelist()
            #     self.message_post(body=_("Đã đồng bộ giá mới sang Bảng giá Odoo."))
            # except Exception as e:
            #     self.message_post(body=_("Cảnh báo: Lỗi khi đồng bộ Bảng giá Odoo: %s") % str(e))
            self._generate_label_print_orders()

            body = self._msg_with_ref(
                "[Mã tham chiếu yêu cầu]-Yêu cầu thay đổi giá đã được hoàn thành"
            )
            self._notify_users(
                self._get_users_after_approved(),
                body,
                subject=_("Hoàn thành yêu cầu thay đổi giá"),
            )

        elif mismatches:
            sample = mismatches[:15]
            msg = "<br/>".join([
                f"- {x.product_id.display_name}: {x.price_level} | phiếu={x.new_value} | Augges={x.updated_value}"
                for x in sample
            ])
            self.message_post(body=_(
                "Cập nhật Augges xong nhưng dữ liệu chưa khớp. "
                "Giữ trạng thái <b>Đang cập nhật Augges</b>.<br/>%s"
            ) % msg)

        else:
            # Trường hợp toàn bộ đều skipped (không có giá nào đổi)
            self.write({"state": "done"})
            self.message_post(body=_("Không có giá nào thay đổi. Tự động hoàn tất phiếu."))

    def action_update_augges(self):
        for rec in self:
            if rec.state != "updating":
                continue
            if not (rec.approve_ok or rec.requested_by):
                raise UserError(_("Bạn không có quyền Cập nhật Augges (Chỉ Người đề nghị hoặc Người có quyền duyệt)."))
            rec._ensure_has_lines()
            rec._do_update_and_verify_augges_all()

    @api.depends("line_ids")
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    def _ensure_has_lines(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError(_("Vui lòng nhập danh sách sản phẩm cần thay đổi giá."))

    @api.model_create_multi
    def create(self, vals_list):
        # seq = self.env.ref("ttb_price_change_request.seq_price_change_request", raise_if_not_found=False)
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code("ttb.price.change.request") or _("New")
        return super().create(vals_list)

    def action_import_product(self):
        """Dùng Import base của Odoo (client action tag='import') để nhập các dòng sản phẩm."""
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "import",
            "target": "new",
            "name": _("Nhập sản phẩm"),
            "params": {
                "context": {"default_request_id": self.id},
                "active_model": "ttb.price.change.request.line",
            },
        }

    def action_submit(self):

        for rec in self:
            if rec.requested_by != self.env.user:
                raise UserError(_("Chỉ người đề nghị mới có quyền Gửi duyệt phiếu này."))
            rec._ensure_has_lines()
            if rec.state != "draft":
                continue

            process_id, approval_vals_list = rec.get_approval_line_ids()
            if not process_id:
                raise UserError(_("Không tìm thấy quy trình phê duyệt phù hợp (ttb.approval.process)."))


            rec.write({'process_id': process_id.id,
                   'date_sent': fields.Datetime.now(),
                   'state': 'to_approve',
                   'approval_line_ids': [(5, 0, 0)] + approval_vals_list})

            body = rec._msg_with_ref(
                "[Mã tham chiếu yêu cầu]-Hiện đang có phiếu yêu cầu thay đổi giá cần duyệt"
            )
            rec._notify_users(
                rec._get_gdcu_users(),
                body,
                subject=_("Yêu cầu thay đổi giá cần duyệt"),
            )

    def action_approve(self):

        for rec in self:
            rec._ensure_has_lines()
            if rec.state != "to_approve":
                continue
            if not rec.approve_ok:
                raise UserError(_("Bạn không có quyền duyệt phiếu này."))

            ok = rec.state_change("approved")
            if not ok:
                raise UserError(_("Không thể cập nhật trạng thái duyệt. Vui lòng kiểm tra cấu hình quy trình."))

            if rec.next_approve_user_ids:
                rec.send_notify(
                    message=_("Bạn có 1 phiếu cần duyệt: %s") % rec.name,
                    users=rec.next_approve_user_ids,
                    subject=_("Yêu cầu phê duyệt: %s") % rec.name,
                )

            if not rec.next_approve_line_id:
                rec.write({
                    "state": "updating",
                    "approved_at": fields.Datetime.now(),
                })
                rec.message_post(body=_("Phiếu đã được phê duyệt, chuyển sang trạng thái <b>Đang cập nhật Augges</b>."))

                body = rec._msg_with_ref(
                    "[Mã tham chiếu yêu cầu]-Yêu cầu thay đổi giá của bạn đã được duyệt"
                )
                rec._notify_users(
                    rec._get_users_after_approved(),
                    body,
                    subject=_("Yêu cầu thay đổi giá đã được duyệt"),
                )

    def action_reject(self):

        for rec in self:
            if rec.state != "to_approve":
                continue
            if not (rec.approve_ok or rec.requested_by):
                raise UserError(_("Bạn không có quyền Hủy phiếu này (Chỉ Người đề nghị hoặc Người duyệt hiện tại)."))

            ok = rec.state_change("rejected")
            if ok:
                raise UserError(_("Không thể cập nhật trạng thái từ chối."))

            rec.write({"state": "cancel"})
            rec.message_post(body=_("Phiếu đã bị hủy bởi %s") % self.env.user.name)
    def action_adjust(self):

        for rec in self:
            if rec.state != "to_approve":
                continue
            if not rec.approve_ok:
                raise UserError(_("Bạn không có quyền Từ chối (trả về) phiếu này."))
            rec.write({"state": "draft"})
            rec.message_post(body=_("Người duyệt đã từ chối và trả phiếu về trạng thái Mới để điều chỉnh."))

    def action_cancel(self):
        for rec in self:
            rec.state = "cancel"

    def action_set_done(self):
        for rec in self:
            if rec.state != "updating":
                continue
            rec.state = "done"
            rec._generate_label_print_orders()


    @api.model
    def cron_notify_unapproved_before_4h(self):
        """Chưa duyệt – trước thời gian áp dụng 4h -> GĐCU"""
        now = fields.Datetime.now()
        target_from = now + timedelta(hours=4)
        target_to = now + timedelta(hours=4, minutes=1)

        recs = self.search([
            ("state", "=", "to_approve"),
            ("effective_at", ">=", target_from),
            ("effective_at", "<", target_to),
        ])
        for rec in recs:
            body = rec._msg_with_ref(
                "[Mã tham chiếu yêu cầu]-Sắp đến thời gian áp dụng giá mới, nhưng phiếu vẫn chưa được duyệt"
            )
            rec._notify_users(
                rec._get_gdcu_users(),
                body,
                subject=_("Cảnh báo: Phiếu chưa được duyệt"),
            )

    @api.model
    def cron_notify_before_apply_10m(self):
        """Trước thời gian áp dụng 10 phút -> TNCU + Phụ trách + Hỗ trợ"""
        now = fields.Datetime.now()
        target_from = now + timedelta(minutes=10)
        target_to = now + timedelta(minutes=11)

        recs = self.search([
            ("state", "in", ["updating", "done"]),
            ("effective_at", ">=", target_from),
            ("effective_at", "<", target_to),
        ])
        for rec in recs:
            body = rec._msg_with_ref(
                "[Mã tham chiếu yêu cầu]-Sắp đến thời gian áp dụng giá mới, vui lòng chuẩn bị triển khai"
            )
            rec._notify_users(
                rec._get_users_after_approved(),
                body,
                subject=_("Nhắc việc: Sắp đến thời gian áp dụng"),
            )

    @api.model
    def cron_notify_overdue_after_5m(self):
        """Quá thời gian áp dụng 5 phút nhưng chưa done -> TNCU"""
        overdue_time = fields.Datetime.now() - timedelta(minutes=5)

        recs = self.search([
            ("state", "=", "updating"),
            ("effective_at", "<=", overdue_time),
        ])
        for rec in recs:
            body = rec._msg_with_ref(
                "[Mã tham chiếu yêu cầu]-Đã quá thời gian áp dụng nhưng chưa hoàn thành cập nhật giá"
            )
            rec._notify_users(
                rec._get_tncu_users(),
                body,
                subject=_("Cảnh báo: Quá thời gian áp dụng"),
            )

    @api.model
    def cron_auto_update_by_effective_time(self):
        """
        Cron chạy mỗi phút:
        - Tự động xử lý các phiếu ở trạng thái 'updating' có effective_at <= now
        - Thực thi update Augges + verify (dùng logic sẵn: _do_update_and_verify_augges_all)
        """
        now = fields.Datetime.now()
        recs = self.search([
            ("state", "=", "updating"),
            ("effective_at", "!=", False),
            ("effective_at", "<=", now),
        ])

        for rec in recs:
            try:
                rec._ensure_has_lines()
                rec._do_update_and_verify_augges_all()
            except Exception as e:
                rec.message_post(body=_("Cron auto update lỗi: %s") % str(e))

    # def get_barcode_to_print(self):
    #
    #     self.ensure_one()
    #     product = self.product_id
    #     if not product:
    #         return False
    #
    #     def get_val(attr_name):
    #         val = getattr(product, attr_name, False)
    #         return str(val).strip() if val else False
    #
    #     fields_check = ['barcode_vendor', 'default_code', 'barcode', 'barcode_k']
    #
    #     for field in fields_check:
    #         val = get_val(field)
    #         if val and len(val) >= 11:
    #             return val
    #
    #     # 2. Fallback
    #     for field in fields_check:
    #         val = get_val(field)
    #         if val:
    #             return val
    #
    #     return False


class TtbPriceChangeRequestLine(models.Model):
    _name = "ttb.price.change.request.line"
    _description = "Dòng sản phẩm thay đổi giá"
    _order = "id"

    request_id = fields.Many2one("ttb.price.change.request", required=True, ondelete="cascade")
    product_id = fields.Many2one("product.product", string="Sản phẩm", required=True, domain=[("sale_ok", "=", True)])
    categ_id_level_1 = fields.Many2one('product.category',string="MCH1",related='product_id.categ_id_level_1',store=True)
    default_code = fields.Char("Mã sản phẩm", related="product_id.default_code", store=True, readonly=True)
    barcode = fields.Char("Mã vạch", related="product_id.barcode", store=True, readonly=True)

    # Giá cũ / mới
    old_sale_price = fields.Float("Giá bán cũ", readonly=True)
    new_sale_price = fields.Float("Giá bán mới")

    old_bl_price = fields.Float("Giá BL cũ", readonly=True)
    new_bl_price = fields.Float("Giá BL mới")

    old_bb1_price = fields.Float("Giá BB1 cũ", readonly=True)
    new_bb1_price = fields.Float("Giá BB1 mới")

    old_bb2_price = fields.Float("Giá BB2 cũ", readonly=True)
    new_bb2_price = fields.Float("Giá BB2 mới")

    old_bb3_price = fields.Float("Giá BB3 cũ", readonly=True)
    new_bb3_price = fields.Float("Giá BB3 mới")

    old_bb4_price = fields.Float("Giá BB4 cũ", readonly=True)
    new_bb4_price = fields.Float("Giá BB4 mới")

    old_bb5_price = fields.Float("Giá BB5 cũ", readonly=True)
    new_bb5_price = fields.Float("Giá BB5 mới")

    old_bb6_price = fields.Float("Giá BB6 cũ", readonly=True)
    new_bb6_price = fields.Float("Giá BB6 mới")

    is_changed = fields.Boolean(
        string="Có thay đổi giá",
        compute="_compute_is_changed",
        store=True,
        help="Đánh dấu dòng có ít nhất 1 loại giá mới khác giá cũ"
    )

    categ_id_level_2 = fields.Many2one(
        'product.category',
        string="MCH2",
        related='product_id.categ_id_level_2',
        store=True
    )

    @api.depends(
        'old_sale_price', 'new_sale_price',
        'old_bl_price', 'new_bl_price',
        'old_bb1_price', 'new_bb1_price',
        'old_bb2_price', 'new_bb2_price',
        'old_bb3_price', 'new_bb3_price',
        'old_bb4_price', 'new_bb4_price',
        'old_bb5_price', 'new_bb5_price',
        'old_bb6_price', 'new_bb6_price',
    )
    def _compute_is_changed(self):
        """
        Quy tắc: Chỉ cần 1 giá BB mới bất kì khác với giá BB cũ sẽ được tính là bị đổi giá.
        """
        price_fields = [
            ('old_sale_price', 'new_sale_price'),
            ('old_bl_price', 'new_bl_price'),
            ('old_bb1_price', 'new_bb1_price'),
            ('old_bb2_price', 'new_bb2_price'),
            ('old_bb3_price', 'new_bb3_price'),
            ('old_bb4_price', 'new_bb4_price'),
            ('old_bb5_price', 'new_bb5_price'),
            ('old_bb6_price', 'new_bb6_price'),
        ]

        for line in self:
            changed = False
            for old_f, new_f in price_fields:
                old_val = getattr(line, old_f) or 0.0
                new_val = getattr(line, new_f) or 0.0
                # So sánh sai số float
                if abs(old_val - new_val) > 0.0001:
                    changed = True
                    break
            line.is_changed = changed

    def _fill_old_prices_from_augges(self):
        """
        Override/Extend: Lấy giá cũ từ Augges.
        Sau đó áp dụng logic:
        - Nếu tạo thủ công (hoặc import null): Default Giá Mới = Giá Cũ.
        """
        for line in self:
            if not line.product_id or not line.request_id:
                continue

            p = line.product_id
            req = line.request_id

            # Nếu chưa có giá cũ (do mới tạo), thì fetch từ Augges
            # Map field Odoo -> Cột SQL Augges
            mapping = {
                "sale": ("old_sale_price", "new_sale_price", "Gia_Ban"),
                "bl": ("old_bl_price", "new_bl_price", "Gia_Bl"),
                "bb1": ("old_bb1_price", "new_bb1_price", "Gia_Ban1"),
                "bb2": ("old_bb2_price", "new_bb2_price", "Gia_Ban2"),
                "bb3": ("old_bb3_price", "new_bb3_price", "Gia_Ban3"),
                "bb4": ("old_bb4_price", "new_bb4_price", "Gia_Ban4"),
                "bb5": ("old_bb5_price", "new_bb5_price", "Gia_Ban5"),
                "bb6": ("old_bb6_price", "new_bb6_price", "Gia_Ban6"),
            }

            for key, (f_old, f_new, col_sql) in mapping.items():
                # 1. Lấy giá cũ nếu chưa có
                current_old = getattr(line, f_old)
                if not current_old:
                    fetched_old = _safe_get_price_from_augges(req, p, col_sql)
                    setattr(line, f_old, fetched_old)
                    current_old = fetched_old

                current_new = getattr(line, f_new)

                # Ở đây giả định giá bán luôn > 0.
                if current_new == 0.0:
                    setattr(line, f_new, current_old)

    # def _fill_old_prices_from_augges(self):
    #     """
    #     Fill giá cũ từ Augges.
    #     """
    #     for line in self:
    #         if not line.product_id or not line.request_id:
    #             continue
    #
    #         p = line.product_id
    #         req = line.request_id
    #
    #         if not p.augges_id:
    #             continue
    #
    #         def _set(field, col):
    #             if not getattr(line, field):
    #                 setattr(line, field, _safe_get_price_from_augges(req, p, col))
    #
    #         _set("old_sale_price", "Gia_Ban")
    #         _set("old_bl_price", "Gia_Bl")
    #         _set("old_bb1_price", "Gia_Ban1")
    #         _set("old_bb2_price", "Gia_Ban2")
    #         _set("old_bb3_price", "Gia_Ban3")
    #         _set("old_bb4_price", "Gia_Ban4")
    #         _set("old_bb5_price", "Gia_Ban5")
    #         _set("old_bb6_price", "Gia_Ban6")

    @api.onchange("product_id")
    def _onchange_product_id_fill_old(self):
        for line in self:
            line._fill_old_prices_from_augges()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._fill_old_prices_from_augges()
        records._compute_is_changed()
        return records

    def write(self, vals):
        result = super(TtbPriceChangeRequestLine, self).write(vals)

        if any(f in vals for f in
               ['new_sale_price', 'old_sale_price', 'new_bb1_price', 'old_bb1_price', 'old_bl_price', 'new_bl_price',
                'new_bb2_price', 'old_bb2_price','new_bb3_price', 'old_bb3_price','new_bb4_price', 'old_bb4_price',
                'new_bb5_price', 'old_bb5_price','new_bb6_price', 'old_bb6_price',]):
            self._compute_is_changed()

        return result
