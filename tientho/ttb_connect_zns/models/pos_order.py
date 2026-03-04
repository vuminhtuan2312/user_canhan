from odoo import models, fields, _, api
import requests
import json
import logging
import re
from datetime import datetime, time
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)

class PosOrder(models.Model):
    _name = 'pos.order'
    _inherit = ['pos.order', 'api_call.base']

    is_send_sms_zalo_oa_zns = fields.Boolean(string='Gửi SMS qua Zalo OA/ZNS khi Đơn mua hàng được xác nhận', default=False)
    zns_template_id = fields.Many2one('zalo.template', string='ZNS Template ID')

    def float_to_dt(self,float_hour):
        today = fields.Date.today()
        h = int(float_hour)
        m = int(round((float_hour - h) * 60))
        return datetime.combine(today, time(h, m))

    def send_sms_zalo_oa_zns(self):
        """Gửi SMS Zalo OA/ZNS (cron-safe, limit-safe)"""

        # ------------------------------------------------------
        # 1. Thời gian & DAILY LIMIT
        # ------------------------------------------------------

        now = fields.Datetime.now()
        campaigns = self.env['period.campaign'].search([
            ('start_date', '<=', now),
            ('end_date', '>=', now),
            ('state', '=', 'running'),
        ])
        # ------------------------------------------------------
        # 2. Dữ liệu dùng chung
        # ------------------------------------------------------
        shop = self.env['zalo.shop.config'].search(
            [('active', '=', True)], limit=1
        )
        if not shop:
            _logger.warning("Không có Zalo shop config active")
            return True

        default_template = self.env['zalo.template'].search(
            [('default_template', '=', True)], limit=1
        )
        # ------------------------------------------------------
        # 3. HÀM GỬI ZNS DUY NHẤT
        # ------------------------------------------------------
        for campaign in campaigns:
            product_ids = campaign.product_ids.ids
            partner_domain = safe_eval(campaign.domain)
            partner_ids = self.env['res.partner'].search(partner_domain).ids
            minutes = int(campaign.time_send or 0)
            for condition in campaign.condition_run_campaign:
                weekday = now.weekday()
                if condition.date_in_week != str(weekday):
                    continue

                # Giờ cấu hình (VN) → UTC
                dt_from_vn = self.float_to_dt(condition.time_from)  # vd 09:00
                dt_to_vn = self.float_to_dt(condition.time_to)  # vd 21:00

                time_from = dt_from_vn - relativedelta(hours=7)
                time_to = dt_to_vn - relativedelta(hours=7)

                # Thời điểm check gửi (UTC)
                now_check = now - relativedelta(minutes=minutes)

                # Thời điểm kết thúc thực tế
                time_end = min(time_to, now_check)

                _logger.info(
                    "ZNS window UTC: from=%s to=%s now_check=%s",
                    time_from, time_to, now_check
                )

                # Nếu chưa tới giờ gửi hợp lệ → bỏ qua
                if time_end <= time_from:
                    _logger.info("Bỏ qua: chưa tới khung giờ gửi ZNS hợp lệ")
                    continue

                if len(partner_domain) > 0:
                    orders = self.search([
                        ('date_order', '>=', fields.Datetime.to_string(time_from)),
                        ('date_order', '<=', fields.Datetime.to_string(time_end)),

                        ('lines.product_id', 'in', product_ids),
                        ('is_send_sms_zalo_oa_zns', '=', False),
                        ('partner_id.phone', '!=', False),
                        ('partner_id', 'not in', shop.partner_ids.ids),
                        ('partner_id', 'in', partner_ids),
                        ('ttb_branch_id', '=', condition.ttb_branch_id.id),
                        ('state', 'not in', ['draft', 'cancel']),
                    ])
                else:
                    orders = self.search([
                        ('date_order', '>=', fields.Datetime.to_string(time_from)),
                        ('date_order', '<=', fields.Datetime.to_string(time_end)),
                        ('lines.product_id', 'in', product_ids),
                        ('is_send_sms_zalo_oa_zns', '=', False),
                        ('partner_id.phone', '!=', False),
                        ('partner_id', 'not in', shop.partner_ids.ids),
                        ('ttb_branch_id', '=', condition.ttb_branch_id.id),
                        ('state', 'not in', ['draft', 'cancel']),
                    ])

                _logger.info("Đơn hàng có sản phẩm gửi ZNS (%s)", orders)
                for order in orders:
                    if any(line.qty < 0 for line in order.lines):
                        continue
                    now = datetime.now()
                    if condition.count_sent >= condition.limit_count:
                        break
                    shop._send_zns(
                        order, condition,
                        order.zns_template_id or condition.template_id or condition.campaign_id.template_id or default_template,
                        after_sent_callback=lambda t=condition: t.write({
                            'count_sent': t.count_sent + 1
                        })
                    )
        return True
    def _fetch_augges_order_extra(self):
        """
        Fetch Augges header + totals (CTE) + warehouse + cashier/store/branch.
        Return dict for mapping 28 keys (as much as possible in 1 query).
        """
        order_id = self.id_augges
        if not order_id:
            return {}

        conn = None
        cursor = None
        try:
            conn = self.env["ttb.tools"].get_mssql_connection_send()
            cursor = conn.cursor()
        except Exception:
            _logger.exception("[Augges] Cannot open MSSQL connection for extra fields")
            return {}


        sql = """
        WITH d AS (
            SELECT
                SLBLD.Id,
                SUM(ISNULL(SLBLD.t_tien, 0))                                               AS tong_tien_hang,
                SUM(ISNULL(SLBLD.tien_ck, 0) + ISNULL(SLBLD.tien_giam, 0))                 AS total_discounts,
                -- SUM(ISNULL(SLBLD.tien_thue, 0))                                         AS total_vat,
                SUM(ISNULL(SLBLD.tien_gtgt, 0))                                            AS order_tax,
                SUM(ISNULL(SLBLD.so_luong, 0))                                             AS sum_qty,
                MAX(SLBLD.Id_Kho)                                                          AS any_id_kho
            FROM SLBLD
            WHERE SLBLD.Id = ?
            GROUP BY SLBLD.Id
        )
        SELECT
            -- 1) order_code
            m.Id                                                                           AS order_code,

            -- 2) order_name (Ma_NX + Ten_NX)
            CONCAT(ISNULL(nx.Ma_NX, ''), ISNULL(nx.Ten_NX, ''))                            AS order_name,

            -- 3) customer (id)
            dt.Id                                                                          AS customer_id,

            -- 4) phones
            dt.Dien_Thoai                                                                  AS phones,

            -- 5) emails
            dt.email                                                                       AS emails,

            -- 6) tong_tien_hang
            ISNULL(d.tong_tien_hang, 0)                                                    AS tong_tien_hang,

            -- 7) total_discounts
            ISNULL(d.total_discounts, 0)                                                   AS total_discounts,

            -- 8) order_amount (theo formula CRM: tong_tien_hang - total_discounts + total_vat)
            (ISNULL(d.tong_tien_hang, 0) - ISNULL(d.total_discounts, 0))                   AS order_amount,

            -- 9) order_tax (lặp lại)
            ISNULL(d.order_tax, 0)                                                         AS order_tax,

            -- 10) order_discount (tổng ck)
            ISNULL(d.total_discounts, 0)                                                   AS order_discount,

            -- 11) order_pretax (doanh thu trước thuế)
            (ISNULL(d.tong_tien_hang, 0) - ISNULL(d.total_discounts, 0))                   AS order_pretax,

            -- 12) order_created_on
            m.ngay_in                                                                      AS order_created_on,

            -- 13) note
            'VE'                                                                     AS note,

            -- 14) _total_data_item (ưu tiên master, fallback sum detail)
            COALESCE(d.sum_qty, 0)                                             AS _total_data_item,

            -- 15) store_name
            dbo.a2u(nk.ten_nhom)                                                                   AS store_name,

            -- 16) chi_nhanh
            nk.dia_chi                                                                     AS chi_nhanh,

            -- 17) created_at (InsertDate)
            m.InsertDate                                                                   AS created_at,

            -- 18) source
            'VE'                                                                     AS source,

            -- 19) tai_khoan_thu_ngan
            u.logname                                                                      AS tai_khoan_thu_ngan,

            -- 20) thu_ngan
            u.fullname                                                                     AS thu_ngan,

            -- 21) order_created_account
            u.fullname                                                                     AS order_created_account,

            -- 22) order_payment_account
            u.fullname                                                                     AS order_payment_account,

            -- 23) quay
            m.quay                                                                         AS quay,

            -- 24) ma_kho
            k.ma_kho                                                                       AS ma_kho,

            -- 25) ten_kho
            dbo.a2u(k.ten_kho)                                                                      AS ten_kho,

            -- 26) sp
            m.sp                                                                           AS sp

        FROM SLBLM m
        LEFT JOIN d          ON d.id  = m.Id
        LEFT JOIN DMNX nx    ON nx.id = m.ID_Nx
        LEFT JOIN DMDT dt    ON dt.Id = m.Id_Dt
        LEFT JOIN DMNKho nk    ON nk.Id = m.ID_Nh
        LEFT JOIN DMUSER u   ON u.Id  = m.UserID
        LEFT JOIN DMKHO k    ON k.Id  = m.ID_Kho
        WHERE m.Id = ?
        """

        try:
            cursor.execute(sql, (order_id, order_id))
            row = cursor.fetchone()
            if not row:
                return {}

            cols = [d[0] for d in cursor.description]
            rec = dict(zip(cols, row))

        except Exception as exc:
            _logger.exception("[Augges] CTE header+totals SQL failed for order_id=%s: %s", order_id, exc)
            return {}
        finally:
            try:
                cursor.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass

        # Normalize + build output dict (keys as BizCRM fields)
        extra = {
            "order_code": str(rec.get("order_code") or order_id),
            "order_name": str(rec.get("order_name") or rec.get("order_code") or order_id),

            # BizCRM linking will be built later as [{"id": "..."}]
            "customer": str(rec.get("customer_id") or "") or "",

            "phones": str(rec.get("phones") or "") or "",
            "emails": str(rec.get("emails") or "") or "",

            "tong_tien_hang": float(rec.get("tong_tien_hang") or 0.0),
            "total_discounts": float(rec.get("total_discounts") or 0.0),
            "order_amount": float(rec.get("order_amount") or 0.0),

            "order_tax": float(rec.get("order_tax") or 0.0),
            "order_discount": float(rec.get("order_discount") or 0.0),
            "order_pretax": float(rec.get("order_pretax") or 0.0),

            "order_created_on": rec.get("order_created_on"),
            "note": rec.get("note") or "Augges_K",

            "_total_data_item": float(rec.get("_total_data_item") or 0.0),

            "store_name": str(rec.get("store_name") or "") or "",
            "chi_nhanh": str(rec.get("chi_nhanh") or "") or "",

            "created_at": rec.get("created_at"),
            "source": rec.get("source") or "Augges_B",

            "tai_khoan_thu_ngan": str(rec.get("tai_khoan_thu_ngan") or "") or "",
            "thu_ngan": str(rec.get("thu_ngan") or "") or "",
            "order_created_account": str(rec.get("order_created_account") or "") or "",
            "order_payment_account": str(rec.get("order_payment_account") or "") or "",

            "quay": str(rec.get("quay") or "") or "",
            "ma_kho": str(rec.get("ma_kho") or "") or "",
            "ten_kho": str(rec.get("ten_kho") or "") or "",
            "sp": str(rec.get("sp") or "") or "",
        }

        # Remove only None (keep "" if you want to push empty strings)
        extra = {k: v for k, v in extra.items() if v is not None}
        return extra
