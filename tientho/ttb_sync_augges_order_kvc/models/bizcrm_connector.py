# -*- coding: utf-8 -*-
import hashlib
import hmac
import json
import logging
import re
import time
import pytz
from datetime import timedelta
from odoo.addons.ttb_tools.models.ttb_tcvn3 import tcvn3_to_unicode


import requests

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class TtbBizCRMConnector(models.AbstractModel):
    _name = "ttb.bizcrm.connector"
    _description = "BizCRM Connector"
    _inherit = "api_call.base"

    _api_type = "bizcrm"

    BASE_URL = "https://api.bizfly.vn/crm/_api"

    ACCESS_KEY = "mKGVUYUv61c555966a214fabaca63f3495459523E58fm1Ef"
    SECRET_KEY = "90bf12ea85c5e3a73add163213bcd9570f7e004a"
    PROJECT_TOKEN = "77ee5e75-90f2-442e-9b37-0310229d3ed0"

    TABLE_CUSTOMER = "data_customer"
    TABLE_ORDER = "data_order"

    # ---------------------------------------------------------------------
    # api_call_base integration
    # ---------------------------------------------------------------------
    def _create_log(self, url, method="GET", headers=None, data=None, resp=None, res_model=None, res_id=None):
        """
        Allow callers to attach logs to arbitrary records via context.

        Context keys:
          - api_call_res_model
          - api_call_res_id
        """
        res_model = self.env.context.get("api_call_res_model") or res_model
        res_id = self.env.context.get("api_call_res_id") or res_id
        return super()._create_log(url, method=method, headers=headers, data=data, resp=resp, res_model=res_model, res_id=res_id)

    # ---------------------------------------------------------------------
    # Signing + headers
    # ---------------------------------------------------------------------
    def _bizcrm_sign(self, ts):
        raw = ("%s%s" % (ts, self.PROJECT_TOKEN)).encode("utf-8")
        secret = (self.SECRET_KEY or "").encode("utf-8")
        return hmac.new(secret, raw, hashlib.sha512).hexdigest()

    def _headers(self):
        ts = str(int(time.time()))
        return {
            "Content-Type": "application/json",
            "cb-access-key": self.ACCESS_KEY,
            "cb-project-token": self.PROJECT_TOKEN,
            "cb-access-timestamp": ts,
            "cb-access-sign": self._bizcrm_sign(ts),
        }

    # ---------------------------------------------------------------------
    # Request wrapper (logs to api_call.log) - DO NOT TOUCH _call_api
    # We use requests.post(json=payload) because you confirmed _call_api returns empty data.
    # But we still persist logs via _create_log (api_call_base).
    # ---------------------------------------------------------------------
    def _request(self, endpoint, payload, timeout=30):
        url = "%s%s" % (self.BASE_URL, endpoint)
        headers = self._headers()

        # Masked logs for console
        safe_headers = dict(headers or {})
        if safe_headers.get("cb-access-key"):
            safe_headers["cb-access-key"] = safe_headers["cb-access-key"][:4] + "********************************************"
        if safe_headers.get("cb-access-sign"):
            safe_headers["cb-access-sign"] = safe_headers["cb-access-sign"][:8] + "************************************************************************************************************************"

        _logger.info("BizCRM Request URL: %s", url)
        _logger.info("BizCRM Request Headers: %s", json.dumps(safe_headers, ensure_ascii=False))
        _logger.info("BizCRM Request Payload: %s", json.dumps(payload, ensure_ascii=False))

        # Create api_call_base log record (request)
        # Store full headers (unmasked) + body (JSON string) for audit
        req_body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        log_rec = None
        try:
            log_rec = self._create_log(
                url=url,
                method="POST",
                headers=json.dumps(headers, ensure_ascii=False),
                data=req_body,
                resp=None,
            )
        except Exception:
            # Do not break business flow if logging fails
            _logger.exception("[BizCRM] Failed to create api_call log (request)")

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        except Exception as exc:
            # Update log with exception text
            try:
                if log_rec:
                    log_rec.write({"resp": str(exc)})
            except Exception:
                _logger.exception("[BizCRM] Failed to update api_call log (exception)")

            raise UserError("BizCRM request failed: %s" % (exc,))

        # Try parse JSON
        try:
            data = resp.json()
        except Exception:
            data = {
                "status": -1,
                "msg": "Non-JSON response",
                "http_status": resp.status_code,
                "text": (resp.text or "")[:2000],
            }

        # Update api_call log with response
        try:
            if log_rec:
                log_rec.write({"resp": json.dumps(data, ensure_ascii=False)})
        except Exception:
            _logger.exception("[BizCRM] Failed to update api_call log (response)")

        _logger.info("BizCRM Response JSON: %s", json.dumps(data, ensure_ascii=False))

        # BizCRM convention: status=1 success, status=-1 error
        if isinstance(data, dict) and data.get("status") not in (1, True):
            raise UserError("BizCRM API error for %s: %s" % (endpoint, data))
        return data

    # ---------------------------------------------------------------------
    # Normalizers
    # ---------------------------------------------------------------------
    @api.model
    def _normalize_phone(self, phone):
        if not phone:
            return ""
        digits = re.sub(r"\D", "", phone or "")
        if not digits:
            return ""
        # VN common normalization
        if digits.startswith("0") and len(digits) in (10, 11):
            return "+84" + digits[1:]
        if digits.startswith("84") and len(digits) in (11, 12):
            return "+" + digits
        if (phone or "").strip().startswith("+"):
            return "+" + digits
        return digits

    @api.model
    def _phone_variants(self, phone):
        raw_digits = re.sub(r"\D", "", phone or "")
        variants = []
        if not raw_digits:
            return variants

        variants.append(raw_digits)

        if raw_digits.startswith("0") and len(raw_digits) in (10, 11):
            variants.append("+84" + raw_digits[1:])
            variants.append("84" + raw_digits[1:])
        elif raw_digits.startswith("84"):
            variants.append("+" + raw_digits)
            if len(raw_digits) >= 3:
                variants.append("0" + raw_digits[2:])

        out = []
        for v in variants:
            if v and v not in out:
                out.append(v)
        return out

    # ---------------------------------------------------------------------
    # BizCRM helpers: convert dict->fields list
    # ---------------------------------------------------------------------
    @staticmethod
    def _fields_dict_to_list(fields_dict):
        return [{"key": k, "value": v} for k, v in fields_dict.items()]

    def _to_bizcrm_iso(self, dt):
        if not dt:
            return None
        dt = fields.Datetime.to_datetime(dt)
        dt_local = fields.Datetime.context_timestamp(self.with_context(tz="Asia/Ho_Chi_Minh"), dt)
        return dt_local.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    # ---------------------------------------------------------------------
    # Augges: fetch 28 key values by SQL (header + totals + cashier + warehouse...)
    # ---------------------------------------------------------------------
    def _extract_augges_order_id(self, order):
        """
        Try to extract numeric Augges order id from pos_reference/name.
        Example: "AUGGES/22107735/BG-ST-03/7" -> 22107735
        """
        candidates = []
        for s in [getattr(order, "pos_reference", ""), getattr(order, "name", ""), getattr(order, "display_name", "")]:
            if s:
                candidates.append(s)
        text = " ".join([c for c in candidates if c])

        m = re.search(r"(\d{5,})", text or "")
        if m:
            return m.group(1)
        return None


    def _fetch_augges_order_extra(self, order):
        """
        Fetch Augges header + totals (CTE) + warehouse + cashier/store/branch.
        Return dict for mapping 28 keys (as much as possible in 1 query).
        """
        order_id = self._extract_augges_order_id(order)
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
            nk.ten_nhom                                                                    AS store_name,

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
            k.ten_kho                                                                      AS ten_kho,

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


    def _bizcrm_find_customer_by_phone(self, phone):
        if not phone:
            return None

        for p in self._phone_variants(phone):
            payload = {
                "table": self.TABLE_CUSTOMER,
                "limit": 1,
                "skip": 0,
                "select": ["__id", "name", "created_at", "phones"],
                "query": {"phones.value": p},
                "output": "by-key",
            }
            res = self._request("/base-table/find", payload)
            rows = res.get("data") or []
            if rows:
                return rows[0]
        return None

    def _bizcrm_create_or_update_customer(self, partner, phone):
        if not partner:
            raise UserError("Missing partner for BizCRM customer sync")

        phone_norm = self._normalize_phone(phone)
        if not phone_norm:
            raise UserError("Partner %s: missing phone/mobile" % (partner.id,))

        # attach logs to the partner
        self = self.with_context(api_call_res_model="res.partner", api_call_res_id=partner.id)

        existing = self._bizcrm_find_customer_by_phone(phone_norm)

        fields_dict = {
            "name": {"value": partner.name or phone_norm, "key": partner.name or phone_norm},
            "phones": [{"value": phone_norm}],
        }

        data_item = {"fields": self._fields_dict_to_list(fields_dict)}

        # UPDATE
        if existing and existing.get("__id"):
            data_item["id"] = existing["__id"]
            payload = {"table": self.TABLE_CUSTOMER, "data": [data_item]}
            res = self._request("/base-table/update", payload)
            return existing["__id"], res

        # CREATE
        payload = {"table": self.TABLE_CUSTOMER, "data": [data_item]}
        res = self._request("/base-table/update", payload)

        created_id = None
        rows = res.get("data") or []
        if isinstance(rows, list) and rows:
            created_id = rows[0].get("__id") or rows[0].get("id")
        if not created_id:
            raise UserError("BizCRM create customer did not return id: %s" % (res,))
        return created_id, res

    def _bizcrm_find_order_by_code(self, order_code):
        if not order_code:
            return None
        payload = {
            "table": self.TABLE_ORDER,
            "limit": 1,
            "skip": 0,
            "select": ["__id", "order_code", "created_at"],
            "query": {"order_code": order_code},
            "output": "by-key",
        }
        res = self._request("/base-table/find", payload)
        rows = res.get("data") or []
        if rows and rows[0].get("__id"):
            return rows[0]["__id"]
        return None

    def _tax_percent(self, pos_line):
        pct = 0.0
        taxes = getattr(pos_line, "tax_ids", False)
        if taxes:
            for t in taxes:
                if getattr(t, "amount_type", "") == "percent":
                    pct += float(t.amount or 0.0)
        return pct

    def _bizcrm_create_or_update_order(self, order, bizcrm_customer_id):
        if not order:
            raise UserError("Missing POS order for BizCRM sync")
        if not bizcrm_customer_id:
            raise UserError("Missing BizCRM customer id for order sync")

        # attach logs to the POS order
        self = self.with_context(api_call_res_model="pos.order", api_call_res_id=order.id)

        # Base code/name
        order_code = order.id_augges or order.name or str(order.id)

        # Pull extra from Augges (28 keys)
        aug = self._fetch_augges_order_extra(order) or {}

        if aug.get("order_code"):
            order_code = aug.get("order_code")

        # Build order line items:
        items = aug.get("order_data_item") or []
        if not items:
            for li in order.lines:
                items.append({
                    "item_id": str(li.product_id.default_code or li.product_id.display_name or ""),
                    "item_name": str(li.product_id.display_name or ""),
                    "quantity": float(li.qty or 0.0),
                    "price": float(li.price_unit or 0.0),
                    # "don_vi": li.product_id.uom_id.name if li.product_id.uom_id else "",
                    "don_vi": "",
                    "vat": float(self._tax_percent(li) or 0.0),
                    "discount_percent": float(getattr(li, "discount", 0.0) or 0.0),
                    "discount_value": 0.0,
                    "amount": float(getattr(li, "price_subtotal_incl", 0.0) or getattr(li, "price_subtotal", 0.0) or 0.0),
                })

        amount_total = float(aug.get("order_amount") if aug.get("order_amount") is not None else (getattr(order, "amount_total", 0.0) or 0.0))
        amount_tax = float(aug.get("total_vat") if aug.get("total_vat") is not None else (getattr(order, "amount_tax", 0.0) or 0.0))
        amount_paid = float(getattr(order, "amount_paid", 0.0) or 0.0)
        amount_left = amount_total - amount_paid

        # phones/emails: BizCRM expects array-object
        phone_val = ""
        if aug.get("phones"):
            phone_val = self._normalize_phone(aug.get("phones"))
        else:
            # fallback: partner phone
            partner = order.partner_id
            if partner and (partner.mobile or partner.phone):
                phone_val = self._normalize_phone(partner.mobile or partner.phone)

        email_val = (aug.get("emails") or "").strip()

        customer_link = [{"id": bizcrm_customer_id}]

        # chi_nhanh / vung: per your note "không tạo mới chi nhánh" -> only map "gần đúng"
        # Because we cannot query BizCRM select options here (you asked NOT to filter struct),
        # we send as "chon-mot" format: [{"value": "..."}] if have text, else [].
        chi_nhanh_val = (aug.get("chi_nhanh") or "").strip()
        vung_val = (aug.get("vung") or "").strip()

        # created_at / order_created_on: BizCRM expects date type_view ngay-gio -> send ISO Z if possible
        # order_created_on = aug.get("order_created_on") or order.date_order
        # created_at =  aug.get("created_at") or order.date_order

        fields_dict = {
            # Required keys
            "order_code": order_code,
            "order_name": {"value": (aug.get("order_name") or order_code), "key": (aug.get("order_name") or order_code)},
            "customer": customer_link,

            # Contacts
            "phones": ([{"value": phone_val}] if phone_val else []),
            "emails": ([{"value": email_val}] if email_val else []),

            # Detail lines (table)
            "order_data_item": items,

            # Totals
            "tong_tien_hang": aug.get("tong_tien_hang"),
            "total_discounts": aug.get("total_discounts"),
            "total_vat": amount_tax,
            "order_amount": amount_total,
            "order_paid_amount": amount_paid,
            "order_left_amount": amount_left,
            "order_tax": aug.get("order_tax"),
            "order_discount": aug.get("order_discount"),
            "order_pretax": aug.get("order_pretax"),

            # Dates
            "order_created_on": self._to_bizcrm_iso(fields.Datetime.now()),
            "created_at": fields.Datetime.to_string(fields.Datetime.context_timestamp(
                            self.with_context(tz="Asia/Ho_Chi_Minh"),
                            order.date_order
                        )) if order.date_order else None,

            # Other fields (28-key set)
            "note": aug.get("note") or "VE",
            "_total_data_item": aug.get("_total_data_item"),
            "store_name": aug.get("store_name"),
            "chi_nhanh": ([{"value": chi_nhanh_val}] if chi_nhanh_val else []) or order.ttb_branch_id.name,
            "vung": ([{"value": vung_val}] if vung_val else []) or order.ttb_branch_id.ttb_region_id.name,
            "source": aug.get("source") or "VE",
            "tai_khoan_thu_ngan": aug.get("tai_khoan_thu_ngan") or order.user_id.login,
            "thu_ngan": tcvn3_to_unicode(aug.get("thu_ngan")) or order.user_id.name,
            "order_created_account": tcvn3_to_unicode(aug.get("order_created_account")),
            "order_payment_account": tcvn3_to_unicode(aug.get("order_payment_account")),
            "quay": aug.get("quay") or order.id_quay_augges,
            "ma_kho": aug.get("ma_kho"),
            "ten_kho": aug.get("ten_kho"),
            "sp": aug.get("sp") or order.sp_augges,
        }

        # Remove None keys
        fields_dict = {k: v for k, v in fields_dict.items() if v is not None}

        data_item = {"fields": self._fields_dict_to_list(fields_dict)}

        # If we already stored bizcrm id, use it. otherwise try find by order_code.
        bizcrm_order_id = self._bizcrm_find_order_by_code(order_code)
        if bizcrm_order_id:
            data_item["id"] = bizcrm_order_id

        payload = {"table": self.TABLE_ORDER, "data": [data_item]}
        res = self._request("/base-table/update", payload)

        # BizCRM returns data[0].__id
        new_id = bizcrm_order_id
        rows = res.get("data") or []
        if isinstance(rows, list) and rows:
            new_id = rows[0].get("__id") or rows[0].get("id") or new_id
        if not new_id:
            raise UserError("BizCRM update did not return order id: %s" % (res,))
        return new_id, res

    @api.model
    def cron_sync_kvc_orders_to_bizcrm(self, limit=50):
        """
        Push KVC ticket POS orders to BizCRM.

        Rules:
        - Only push orders flagged ttb_is_ve_order=True
        - Only push orders with date_order in *today* (user timezone)
        - Only push orders not yet synced successfully (ttb_bizcrm_sync_state != 'done')
        - Store payload hash to prevent re-sending identical payload on retries
        """
        if not (self.BASE_URL and self.ACCESS_KEY and self.SECRET_KEY and self.PROJECT_TOKEN):
            _logger.warning("[BizCRM] Missing credentials. Skip cron.")
            return


        tz = pytz.timezone(self.env.user.tz or "UTC")
        now_utc = fields.Datetime.now().replace(tzinfo=pytz.UTC)
        now_local = now_utc.astimezone(tz)
        start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        end_local = start_local + timedelta(days=1)

        start_utc = start_local.astimezone(pytz.UTC).replace(tzinfo=None)
        end_utc = end_local.astimezone(pytz.UTC).replace(tzinfo=None)

        domain = [
            ("ttb_is_ve_order", "=", True),
            ("date_order", ">=", start_utc),
            ("date_order", "<", end_utc),
            ("ttb_bizcrm_sync_state", "!=", "done"),
        ]

        orders = self.env["pos.order"].search(domain, order="date_order asc, id asc", limit=limit)
        _logger.info("[BizCRM] Sync KVC orders: found %s candidate(s)", len(orders))

        for order in orders:
            try:
                partner = order.partner_id
                phone = (partner.mobile or partner.phone or "").strip() if partner else ""
                if not phone:
                    raise UserError("POS order %s: customer has no phone" % (order.display_name,))

                bizcrm_customer_id, _ = self._bizcrm_create_or_update_customer(partner, phone)
                bizcrm_order_id, _ = self._bizcrm_create_or_update_order(order, bizcrm_customer_id)

                order.write({
                    "ttb_bizcrm_last_sync_at": fields.Datetime.now(),
                    "ttb_bizcrm_sync_state": "done",
                })

                _logger.info(
                    "[BizCRM] Synced POS order %s (id=%s) -> bizcrm_order_id=%s, bizcrm_customer_id=%s",
                    order.name, order.id, bizcrm_order_id, bizcrm_customer_id,
                )

            except Exception as exc:
                _logger.exception("[BizCRM] Failed to sync POS order %s (id=%s)", order.name, order.id)
                order.write({
                    "ttb_bizcrm_last_sync_at": fields.Datetime.now(),
                    "ttb_bizcrm_sync_state": "error",
                })

    @api.model
    def cron_push_kvc_orders_to_bizcrm(self, limit=None):
        """Backward compatible alias."""
        return self.cron_sync_kvc_orders_to_bizcrm(limit=limit)
