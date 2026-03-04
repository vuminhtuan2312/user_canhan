from odoo import models, fields, _, api
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, time, timedelta
from dateutil.relativedelta import relativedelta
from odoo.addons.ttb_tools.models.ttb_tcvn3 import tcvn3_to_unicode

import shlex
import re
import json
import logging
import unicodedata


_logger = logging.getLogger(__name__)

class ZaloShopConfig(models.Model):
    _name = 'zalo.shop.config'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'api_call.base']
    _description = 'Zalo Shop Connect Configuration'

    name = fields.Char(string='Tên cấu hình', required=True)
    zalo_shop_id = fields.Char(string='Zalo Shop ID', required=True)
    api_key = fields.Char(string='API Key', required=True)
    access_token = fields.Char(string='Access Token', required=True)
    active = fields.Boolean(string='Kích hoạt', default=True)
    oa_id = fields.Char(string='Zalo OA ID', required=True)
    date_start = fields.Datetime(string='Ngày bắt đầu lấy template', default=fields.Datetime.now, required=True)
    date_end = fields.Datetime(string='Ngày kết thúc lấy template', required=False)
    zns_api_code_error_ids = fields.One2many(
        'zns.api.code.error',
        'zalo_shop_config_id',
        string='Bảng mã lỗi API ZNS'
    )
    # Cấu hình chạy job gửi zns tự động
    type_run = fields.Selection(
        selection=[
            ('cron', 'Chạy theo lịch định kỳ'),
            ('manual', 'Chạy thủ công'),
        ],
        string='Loại chạy gửi ZNS tự động',
        default='cron'
    )

    auto_send_zns_interval = fields.Selection(
        selection=[
            ('every_1_hour', 'Mỗi 1 giờ'),
            ('every_3_hours', 'Mỗi 3 giờ'),
            ('every_6_hours', 'Mỗi 6 giờ'),
            ('every_12_hours', 'Mỗi 12 giờ'),
            ('custom_time', 'Thời gian tự chọn'),
        ],
        string='Khoảng thời gian gửi ZNS tự động',
        default='every_6_hours'
    )
    partner_ids = fields.Many2many(
        'res.partner',
        string='Danh sách khách hàng đã nhận ZNS',
        help='Danh sách các khách hàng đã nhận tin nhắn ZNS qua Zalo OA/ZNS trong ngày.'
             'Danh sách này sẽ được làm mới hàng ngày.',
        tracking=True
    )

    webhook_url = fields.Text()
    oa_app_id = fields.Text()

    condition_to_send_zns_ids = fields.One2many(
        'condition.to.send.zns',
        'zalo_shop_config_id',
        string='Điều kiện gửi ZNS'
    )

    #### BIZFLY FIELDS


    project_key_bizfly = fields.Char(string='Key project của Bizfly')
    api_key_bizfly = fields.Char(string='API key Bizfly')
    api_secret_key_bizfly = fields.Char(string='API secret key Bizfly')
    api_embed_key_bizfly = fields.Char(string='API embed key Bizfly')


    def parse_zalo_datetime(self, val):
        if not val:
            return False

        if isinstance(val, str):
            # Zalo ISO 8601 UTC với milliseconds
            dt = datetime.strptime(val, "%Y-%m-%dT%H:%M:%S.%fZ")
            return dt.replace(tzinfo=None)

        if isinstance(val, datetime):
            return val.replace(tzinfo=None)

        return False

    @api.constrains('active')
    def _check_only_one_active(self):
        for record in self:
            if record.active:
                count = self.search_count([
                    ('active', '=', True),
                    ('id', '!=', record.id),
                ])
                if count:
                    raise ValidationError(
                        "Chỉ được phép tồn tại duy nhất 1 bản ghi được kích hoạt."
                    )

    def action_update_webhook_url(self):
        self.ensure_one()
        """Cập nhật webhook URL cho Zalo Shop Connect"""
        base_url = self.env['ir.config_parameter'].sudo().get_param('zns.get_update_shop_oa_url')
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        payload = {
            "oa_id": self.zalo_shop_id,
            "webhook_url": self.webhook_url,
        }
        try:
            response = self.call_api(base_url, headers, payload)
            _logger.info("Webhook URL updated successfully for shop %s", self.zalo_shop_id)
        except Exception as e:
            _logger.error(f"Exception while updating webhook URL: {str(e)}")
            raise


    @api.model
    def action_get_access_token(self):
        """Lấy access token từ Zalo Shop Connect"""
        access_token = self.env['ir.config_parameter'].sudo().get_param(
            'zalo.oa.access_token'
        )
        for record in self:
            record.access_token = access_token

    def action_get_templates(self):
        """Lấy danh sách template từ ZNS"""
        api_key = self.api_key
        base_url = self.env['ir.config_parameter'].sudo().get_param('zns.get_templates_url')
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        payload = {
            "filter": {
                "date_from": self.date_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "date_to": self.date_end.strftime("%Y-%m-%dT%H:%M:%SZ") if self.date_end else fields.Datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
            "paging": {
                "limit": 50,
            }
        }
        response = self.call_api(base_url, headers, payload)

        self.env['zalo.template'].sudo().save_templates(response)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Thành công'),
                'message': _('Đã lấy danh sách template từ ZNS thành công.'),
                'type': 'success',
                'sticky': False,
            }
        }
    def action_create_template_wizard(self):
        """Mở wizard tạo template Zalo OA/ZNS"""
        return {
            'name': _('Tạo Template Zalo OA/ZNS'),
            'type': 'ir.actions.act_window',
            'res_model': 'create.template.wizard',
            'view_mode': 'form',
            'target': 'new',
        }
    @api.model
    def clear_partner_ids_daily(self):
        shops = self.search([('active', '=', True)])
        for shop in shops:
            _logger.info("Clear partner_ids cho shop %s", shop.id)
            shop.partner_ids = [(5, 0, 0)]
        campaigns = self.env['period.campaign'].search([('state', '=', 'running')])
        for campaign in campaigns:
            for line in campaign.condition_run_campaign:
                line.count_sent = 0

    def write(self, vals):
        if 'partner_ids' in vals:
            for record in self:
                old_partners = record.partner_ids
                res = super().write(vals)
                new_partners = record.partner_ids

                added = new_partners - old_partners
                removed = old_partners - new_partners

                messages = []
                if added:
                    messages.append(
                        "➕ Thêm: %s" % ", ".join(added.mapped('name'))
                    )
                if removed:
                    messages.append(
                        "➖ Xoá: %s" % ", ".join(removed.mapped('name'))
                    )

                if messages:
                    record.message_post(body="<br/>".join(messages))
                return res
        return super().write(vals)

    def _build_auth_headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def call_api(self, url_path, headers, payload, method='POST', type='json'):
        url = url_path
        if url != 'https://api.bizfly.vn/crm/_api/base-table/update':
            payload = json.dumps(payload, ensure_ascii=False)
        return self.env['api_call.base']._call_api(
            url,
            params=payload,
            headers=headers,
            method=method,
            type=type
        )

    def to_curl(self, method, url, headers=None, data=None):
        cmd = ["curl", "-X", method]

        if headers:
            for k, v in headers.items():
                cmd.extend(["-H", f"{k}: {v}"])

        if data:
            cmd.extend(["--data-raw", data if isinstance(data, str) else str(data)])

        cmd.append(url)
        return " ".join(shlex.quote(c) for c in cmd)



    def _send_zns(self, order, condition, template, after_sent_callback=None):
        zns_send = self.env['zns.send'].sudo()

        today = fields.Date.context_today(self)

        start_of_day = fields.Datetime.to_string(
            datetime.combine(today, time.min)
        )

        end_of_day = fields.Datetime.to_string(
            datetime.combine(today, time.max)
        )
        daily_limit = int(
            self.env['ir.config_parameter']
            .sudo()
            .get_param('zns.daily_limit_zalo_oa_zns', 0)
        )

        sent_today = zns_send.search_count([
            ('status', '=', 'sent'),
            ('sent_at', '>=', start_of_day),
            ('sent_at', '<=', end_of_day),
        ])

        remain_quota = max(daily_limit - sent_today, 0)

        if daily_limit and remain_quota <= 0:
            _logger.info("Đã đạt giới hạn ZNS/ngày (%s)", daily_limit)
            return True

        if remain_quota <= 0:
            return False
        sent_partner_ids = set()

        if order.partner_id.id in sent_partner_ids:
            return False

        shop = self.env['zalo.shop.config'].search(
            [('active', '=', True)], limit=1
        )
        phone_default = self.env['ir.config_parameter'].sudo().get_param('phone.test_zns', '0327865111')
        template_data = {}

        for p in template.template_param_ids:
            value = self._get_value_from_mapping(order, p.mapping_key)

            # Format DATE
            if p.type == 'DATE' and value:
                if isinstance(value, str):
                    value = fields.Date.from_string(value)
                value = value.strftime("%d/%m/%Y")

            if value is None or value is False:
                value = ""
            elif isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            else:
                if p.mapping_key == 'date_order':
                    try:
                        dt = fields.Datetime.from_string(value)
                        dt = dt + timedelta(hours=7)
                        value = dt
                    except Exception:
                        pass
                value = str(value)

            template_data[p.name] = value

        payload = {
            "oa_id": shop.oa_id,
            "template_id": template.template_id,
            "phone": phone_default or order.partner_id.phone,
            "template_data": template_data,
            "tracking_id": str(order.id),
            "sending_mode": "default",
        }
        shop = self.env['zalo.shop.config'].search(
            [('active', '=', True)], limit=1
        )
        base_url = self.env['ir.config_parameter'].sudo().get_param(
            'zns.send_sms_zalo_oa_zns'
        )
        headers = self._build_auth_headers()
        try:
            _logger.info("Gửi ZNS đơn %s", order.name)
            response = self.call_api(base_url, headers, payload)
            curl_cmd = self.to_curl('POST', base_url, headers, payload)
            _logger.error("CURL DEBUG SendZNS:\n%s", curl_cmd)
        except Exception as e:
            _logger.error("Lỗi gửi ZNS %s: %s", order.name, e)
            return False
        result = response
        msg_id = result.get("msg_id")

        time_range_text = "%02d:%02d - %02d:%02d" % (
            int(condition.time_from),
            int((condition.time_from % 1) * 60),
            int(condition.time_to),
            int((condition.time_to % 1) * 60),
        )
        branch_name = order.ttb_branch_id.name or ""
        order_name = order.name or ""
        response_json = False
        error_code = response.get('error_code')
        if error_code is not None:
            try:
                error_code_int = int(error_code or 0)
            except (TypeError, ValueError):
                error_code_int = 0
            if error_code_int != 0:
                error_record = self.env['zns.api.code.error'].search([('code', '=', str(error_code))], limit=1)
                if error_record:
                    response_json = f"{error_record.code}: {error_record.message}"
                else:
                    response_json = "Lỗi không xác định: %s" % (response.get('message') or 'Unknown error',)
        elif response.get('code'):
            response_json = "Lỗi không xác định: %s" % (response.get('msg') or 'Unknown error',)

        result = f"{branch_name} - {order_name}".strip(" -")
        zns = self.env['zns.send'].create({
            'order_id': order.id,
            'order_code': order.id_augges,
            'partner_id': order.partner_id.id,
            'phone': order.partner_id.phone,
            'purchase_datetime': order.date_order,
            'template_id': template.id,
            'response_json': response_json,
            'sent_at': fields.Datetime.now(),
            'msg_id': msg_id,
            'ttb_branch_id': order.ttb_branch_id.id,
            'name': result,
            'status': 'failed' if response.get('code') else 'failed_zalo' if response.get('error_code') != 0 else 'pending',
            'campaign_id': condition.campaign_id.id,
            'day_in_week': condition.date_in_week,
            'time_range_text': time_range_text,
        })

        result = response
        order.is_send_sms_zalo_oa_zns = True
        sent_partner_ids.add(order.partner_id.id)
        if sent_partner_ids:
            shop.partner_ids = [(4, pid) for pid in sent_partner_ids]
        remain_quota -= 1
        if after_sent_callback:
            after_sent_callback()
        return True

    @staticmethod
    def _fields_dict_to_list(fields_dict):
        return [{"key": k, "value": v} for k, v in fields_dict.items()]

    def _to_bizcrm_iso(self, dt):
        if not dt:
            return None
        dt = fields.Datetime.to_datetime(dt)
        dt_local = fields.Datetime.context_timestamp(self.with_context(tz="Asia/Ho_Chi_Minh"), dt)
        dt_local = dt_local - relativedelta(hours=7)
        return dt_local.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    def _bizcrm_find_rating_by_msg_id(self, msg_id):
        if not msg_id:
            return None

    def ir_cron_upload_data_rating_crm(self, table_code=None):
        if table_code is None:
            table_code = []
        self.bizfly_update_base_table(table_code=table_code)

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

    def _tax_percent(self, pos_line):
        pct = 0.0
        taxes = getattr(pos_line, "tax_ids", False)
        if taxes:
            for t in taxes:
                if getattr(t, "amount_type", "") == "percent":
                    pct += float(t.amount or 0.0)
        return pct

    def remove_accents(self, text):
        if not text:
            return text
        text = unicodedata.normalize('NFD', text)
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
        return text.replace('đ', 'd').replace('Đ', 'D')
    def _bizcrm_create_or_update_customer(self, partner, phone, table=None, mapping_by=None):
        if not partner:
            raise UserError("Missing partner for BizCRM customer sync")
        zalo_shop_config = self.search([('active', '=', True)], limit=1)
        headers = self.env['bizfly.table.map'].generate_bizfly_headers()
        phone_norm = self._normalize_phone(phone)
        if not phone_norm:
            raise UserError("Partner %s: missing phone/mobile" % (partner.id,))

        # attach logs to the partner
        ctx = self.with_context(api_call_res_model="res.partner", api_call_res_id=partner.id)

        existing = ctx._bizcrm_find_customer_by_phone(phone_norm, table, mapping_by)
        partner_name = self.remove_accents(partner.name)
        fields_dict = {
            "name": {"value": partner_name or phone_norm, "key": partner_name or phone_norm},
            "phones": [{"value": phone_norm}],
        }

        data_item = {"fields": self._fields_dict_to_list(fields_dict)}

        # UPDATE
        url = 'https://api.bizfly.vn/crm/_api//base-table/update'
        if existing and existing.get("__id"):
            data_item["id"] = existing["__id"]
            payload = {"table": 'data_customer', "data": [data_item]}
            response = zalo_shop_config.call_api(url, headers, payload)
            return existing["__id"], response
        # CREATE
        payload = {"table": "data_customer", "data": [data_item]}
        response = zalo_shop_config.call_api(url, headers, payload)
        res = response
        created_id = None
        rows = res.get("data") or []
        if isinstance(rows, list) and rows:
            created_id = rows[0].get("__id") or rows[0].get("id")
        if not created_id:
            raise UserError("BizCRM create customer did not return id: %s" % (res,))
        return created_id, res

    def _bizcrm_find_customer_by_phone(self, phone, table=None, mapping_by=None):
        if not phone:
            return None
        zalo_shop_config = self.search([('active', '=', True)], limit=1)
        for p in self._phone_variants(phone):
            payload = {
                "table": 'data_customer',
                "limit": 1,
                "skip": 0,
                "select": ["__id", "name", "created_at", "phones"],
                "query": {"phones.value": p},
                "output": "by-key",
            }

            headers = self.env['bizfly.table.map'].generate_bizfly_headers()
            url = 'https://api.bizfly.vn/crm/_api/base-table/find'
            response = self.call_api(url, headers, payload)
            rows = response.get("data") or []
            if rows:
                return rows[0]
        return None
    def _bizcrm_find_order_by_code(self, order_code):
        zalo_shop_config = self.search([('active', '=', True)], limit=1)
        url = 'https://api.bizfly.vn/crm/_api/base-table/find'
        if not order_code:
            return None
        headers = self.env['bizfly.table.map'].generate_bizfly_headers()
        payload = {
              "table": "data_order",
              "limit": 1,
              "skip": 0,
              "select": ["__id", "order_code", "created_at"],
              "query": {
                "order_code": str(order_code)
              }
            }

        response = zalo_shop_config.call_api(url, headers, payload)
        rows = response.get("data") or []
        if rows:
            return rows[0][0]['value'] or rows[0].get("id")
        return None
    def _bizcrm_create_or_update_order(self, order, bizcrm_customer_id, msg_id=None):
        if not order:
            raise UserError("Missing POS order for BizCRM sync")
        if not bizcrm_customer_id:
            raise UserError("Missing BizCRM customer id for order sync")

        # attach logs to the POS order
        self = self.with_context(api_call_res_model="pos.order", api_call_res_id=order.id)

        # Base code/name
        order_code = order.id_augges or order.name or str(order.id)

        # Pull extra from Augges (28 keys)
        aug = order._fetch_augges_order_extra() or {}

        if aug.get("order_code"):
            order_code = aug.get("order_code")

        # Build order line items:
        items = aug.get("order_data_item") or []
        if not items:
            for li in order.lines:
                items.append({
                    "item_id": str(self.get_stt_product_order_line(li) or ""),
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
            "order_name": {"value": ""},
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
            # "chi_nhanh": ([{"value": chi_nhanh_val}] if chi_nhanh_val else []) or order.ttb_branch_id.name,
            "vung": ([{"value": vung_val}] if vung_val else []) or order.ttb_branch_id.ttb_region_id.name or '',
            "source": aug.get("source") or "VE",
            "tai_khoan_thu_ngan": aug.get("tai_khoan_thu_ngan") or order.user_id.login,
            "thu_ngan": tcvn3_to_unicode(aug.get("thu_ngan")) or order.user_id.name,
            "order_created_account": tcvn3_to_unicode(aug.get("order_created_account")),
            "order_payment_account": tcvn3_to_unicode(aug.get("order_payment_account")),
            "quay": aug.get("quay") or order.id_quay_augges,
            "ma_kho": aug.get("ma_kho"),
            "ten_kho": aug.get("ten_kho"),
            "sp": aug.get("sp") or order.sp_augges,
            "msg_id": msg_id or "",
        }

        # Remove None keys
        fields_dict = {k: v for k, v in fields_dict.items() if v is not None}

        data_item = {"fields": self._fields_dict_to_list(fields_dict)}

        # If we already stored bizcrm id, use it. otherwise try find by order_code.
        bizcrm_order_id = self._bizcrm_find_order_by_code(order_code)
        if bizcrm_order_id:
            data_item["id"] = bizcrm_order_id
        zalo_shop_config = self.search([('active', '=', True)], limit=1)
        url = "https://api.bizfly.vn/crm/_api/base-table/update"
        headers = self.env['bizfly.table.map'].generate_bizfly_headers()

        payload = {"table": "data_order", "data": [data_item]}
        res = zalo_shop_config.call_api(url, headers, payload)

        # BizCRM returns data[0].__id
        new_id = bizcrm_order_id
        rows = res.get("data") or []
        if isinstance(rows, list) and rows:
            new_id = rows[0].get("__id") or rows[0].get("id") or new_id
        if not new_id:
            raise UserError("BizCRM update did not return order id: %s" % (res,))
        return new_id



    def bizfly_update_base_table(self, table_code=None):
        """
        Gọi API BizFly CRM base-table/update
        """
        zalo_shop_config = self.search([('active', '=', True)], limit=1)
        if not zalo_shop_config:
            _logger.warning("No active zalo_shop_config found for BizFly upload")
            return False

        zns_sends = self.env['zns.send'].search([('is_upload_bizfly', '=', False), ('status', '=', 'sent')])
        if not zns_sends:
            _logger.info("No ZNS sends to upload to BizFly")
            return True

        bizfly_table_maps = self.env['bizfly.table.map'].search([])
        if table_code:
            bizfly_table_maps = bizfly_table_maps.filtered(lambda l: l.table_code in (table_code if isinstance(table_code, (list, tuple)) else [table_code]))
        if not bizfly_table_maps:
            _logger.info("No BizFly table mappings to process")
            return True

        url = "https://api.bizfly.vn/crm/_api/base-table/update"

        for table_map in bizfly_table_maps:
            headers = table_map.generate_bizfly_headers()
            table = table_map.table_code
            mapping_by = table_map.mapping_by
            mapping_by_list = mapping_by.mapped('key') if mapping_by else []

            for zns in zns_sends:
                try:
                    order = zns.order_id
                    order_code = (order.id_augges or order.name or str(order.id)) if order else ""

                    partner = zns.partner_id
                    phone = (partner.mobile or partner.phone or "").strip() if partner else ""
                    # Ensure customer exists in BizCRM and get id
                    bizcrm_customer_id = None
                    try:
                        bizcrm_customer_id, _ = self._bizcrm_create_or_update_customer(partner, phone, table, mapping_by)
                    except Exception as e:
                        _logger.exception("Failed to create/update BizCRM customer for ZNS %s: %s", zns.id, e)
                        # Continue processing other records (no customer link)

                    bizcrm_order_id = None
                    try:
                        bizcrm_order_id = self._bizcrm_find_order_by_code(order_code)
                        if not bizcrm_order_id:
                            bizcrm_order_id = self._bizcrm_create_or_update_order(order, bizcrm_customer_id, zns.msg_id)
                    except Exception:
                        _logger.exception("Failed to find BizCRM order for order_code=%s (ZNS %s)", order_code, zns.id)

                    customer_link = [{"id": bizcrm_customer_id}] if bizcrm_customer_id else []

                    # Build record data from mappings
                    record_data = {}
                    now = fields.Datetime.now()
                    for field_map in table_map.table_param_ids:
                        if field_map.require and not field_map.mapping_key:
                            raise ValidationError(
                                f"Thiếu mapping key cho trường bắt buộc '{field_map.key}' "
                                f"trong bảng '{table_map.table_code}'"
                            )

                        # Use helper to extract value; allow falsy values like 0
                        value = None
                        if field_map.mapping_key:
                            value = self._get_value_from_mapping(zns, field_map.mapping_key)
                            # _get_value_from_mapping returns False for empty; treat as None
                            if value is False:
                                value = None

                        # Special handling
                        if field_map.type == 'date' and value:
                            value = self._to_bizcrm_iso(value)

                        if field_map.is_selection_field and value is not None:
                            for line in field_map.param_mapping_line_ids:
                                if str(value) in (line.mapping_value or '').split(','):
                                    value = line.value
                                    break

                        # Fallback to empty string for None when building fields later
                        record_data[field_map.key] = value

                    # Build fields array: start with customer/order/note/ks_cau6 then record_data
                    fields_list = []
                    fields_list.extend([
                        {"key": "customer", "value": customer_link},
                        {"key": "order", "value": [{"id": bizcrm_order_id}] if bizcrm_order_id else []},
                        {"key": "note", "value": getattr(zns, "response_message", "") or ""},
                        {"key": "ks_cau6", "value": getattr(zns, "note", "") or ""},
                        {"key": "loai_hpc", "value": zns.time_range_text},
                    ])

                    # Append mapped fields
                    for k, v in record_data.items():
                        fields_list.append({"key": k, "value": v if v is not None else ""})

                    payload = {
                        "table": table,
                        "mappingBy": mapping_by_list,
                        "data": [
                            {
                                "fields": fields_list,
                            }
                        ]
                    }

                    _logger.info("[BIZFLY] POST %s", url)
                    _logger.debug("[BIZFLY] Headers: %s", headers)
                    _logger.debug("[BIZFLY] Payload: %s", json.dumps(payload, ensure_ascii=False))

                    response = zalo_shop_config.call_api(url, headers, payload)

                    # Interpret response
                    status = response.get('status') if isinstance(response, dict) else None
                    if status == -1:
                        # API-level error
                        _logger.error("BizFly responded with error for ZNS %s: %s", zns.id, response.get('msg'))
                        # mark failed sync info on zns (optional)
                        zns.write({'is_upload_bizfly': False})
                    elif status == 1:
                        # Success for this record
                        zns.write({'is_upload_bizfly': True})
                        _logger.info("Uploaded ZNS %s to BizFly table %s successfully", zns.id, table)
                    else:
                        # Unknown/malformed response: log and continue
                        _logger.warning("Unexpected BizFly response for ZNS %s: %s", zns.id, response)

                except Exception as e:
                    _logger.exception("Exception while uploading ZNS %s to BizFly: %s", getattr(zns, 'id', 'n/a'), e)
                    # continue with next zns
        return True
    def _get_value_from_mapping(self, record, mapping_key):
        if not mapping_key or not isinstance(mapping_key, str):
            return False

        value = record
        for key in mapping_key.split('.'):
            value = getattr(value, key, False)
            if not value:
                return False
        return value
    def get_stt_product_order_line(self, line):
        if not line:
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
        SELECT TOP 1
            stt
        FROM slbld 
        WHERE id_hang = ? and id = ?
        """
        try:
            cursor.execute(sql, (line.product_id.augges_id, line.order_id.id_augges))
            row = cursor.fetchone()
            if not row:
                return {}

            cols = [d[0] for d in cursor.description]
            rec = dict(zip(cols, row))

        except Exception as exc:
            _logger.exception("[Augges] CTE header+totals SQL failed for order_id=%s: %s", line, exc)
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
        if rec:
            return rec.get('stt')
        return None