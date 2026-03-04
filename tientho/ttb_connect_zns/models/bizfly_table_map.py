from os.path import exists

from odoo import models, fields, _
from odoo.exceptions import UserError
import hashlib
import hmac
import json
import logging
import re
import time
import pytz
import requests

_logger = logging.getLogger(__name__)

class BizFlyTableMap(models.Model):
    _name = 'bizfly.table.map'
    _inherit = 'api_call.base'
    _description = 'Bizfly table map'
    _rec_name = 'table_code'

    model_id = fields.Many2one('ir.model', string='Model', help="Model dùng để check mapping trường")
    table_code = fields.Char(
        string='Mã bảng bizfly',
        required=True,
    )
    mapping_by = fields.Many2many('param.mapping',
        string='Mapping by',
        help='Trường dùng để mapping bản ghi',
        domain = "[('id', 'in', table_param_ids)]"
    )
    table_param_ids = fields.One2many(
        'param.mapping',
        'table_param_id',
        string='Template Params',
        readonly=False

    )
    updated_at = fields.Datetime(
        string='Ngày cập nhật',
        readonly=True

    )
    _sql_constraints = [
        ('table_code_unique',
         'unique(table_code)',
         'Table code must be unique!')
    ]

    def update_table(self, response_json):
        fields_data = response_json.get('data', {}).get('fields', [])
        if not fields_data:
            return
        now = fields.Datetime.now()
        TemplateParam = self.env['param.mapping'].sudo()

        for p in fields_data:
            key = p.get('key')
            if not key:
                continue

            vals = {
                'name': p.get('label'),
                'key': key,
                'type': p.get('type'),
                'require': p.get('prop_require') in (True, 1),
                'accept_null': not bool(p.get('field_default')),
                'table_param_id': self.id,
            }

            param = TemplateParam.search([
                ('table_param_id', '=', self.id),
                ('key', '=', key),
            ], limit=1)
            self.write({
                'updated_at': now,
            })
            if param:
                param.write(vals)
            else:
                TemplateParam.create(vals)

        if any(line.is_selection_field for line in self.table_param_ids):
            keys = self.table_param_ids.filtered(lambda l: l.is_selection_field)
            url = 'https://api.bizfly.vn/crm/_api/base-table/find'
            headers = self.generate_bizfly_headers()
            MappingLine = self.env['param.mapping.line']
            for key in keys:
                payload = {
                    "table": "crm_option",
                    "limit": 10000,
                    "skip": 0,
                    "select": ["collection_key", "value", "field_target"],
                    "query": {"collection_key": self.table_code,
                              "field_target": key.key},
                    "output": "by-key"
                }
                response = self.env['zalo.shop.config'].call_api(url, headers, payload)
                records = response.get('data', {})
                if records:
                    for record in records:
                        exists = MappingLine.search([
                            ('key', '=', record.get('id')),
                        ])
                        if exists:
                            continue
                        MappingLine.create({
                            'key': record.get('id'),  # ví dụ: '668baf5c90de4a93e303801d'
                            'value': record.get('value'), # ví dụ: 'rất hài lòng'
                            'param_id': key.id,  # nếu có many2one
                        })

    def call_bizfly_base_table_struct(self, table_code):
        """
        Call Bizfly CRM base-table struct API
        """
        headers = self.generate_bizfly_headers()
        # 2. Payload
        payload = {
            "table": table_code
        }
        # 3. Call API
        url = 'https://api.bizfly.vn/crm/_api/base-table/struct'
        response = self.env['zalo.shop.config'].call_api(url, headers, payload)
        try:
            if response.get('status') == -1:
                raise UserError(response.get('msg'))
            if response:
                self.update_table(response)
        except Exception as e:
            _logger.error(f"Exception while updating webhook URL: {str(e)}")
            raise

    def _get_value_from_mapping(self, record, mapping_key):
        value = record
        for attr in mapping_key.split('.'):
            if not value:
                return False
            if not hasattr(value, attr):
                raise AttributeError(attr)
            value = getattr(value, attr)
        return value

    def generate_bizfly_headers(self):
        # 1. Timestamp hiện tại (milliseconds)
        zalo_shop = self.env['zalo.shop.config'].search([('active', '=', True)], limit=1)
        api_key = zalo_shop.api_key_bizfly
        api_secret = zalo_shop.api_secret_key_bizfly
        project_token = zalo_shop.project_key_bizfly
        timestamp = str(int(time.time() * 1000))
        message = f"{timestamp}{project_token}"
        signature = hmac.new(
            api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()
        # # 2. Chuỗi cần ký
        # sign_string = f"{api_key}{api_secret}{timestamp}"
        #
        # # 3. SHA-512
        # access_sign = hashlib.sha512(sign_string.encode("utf-8")).hexdigest()

        # 4. Headers
        headers = {
            "cb-access-key": api_key,
            "cb-project-token": project_token,
            "cb-access-timestamp": timestamp,
            "cb-access-sign": signature,
            "Content-Type": "application/json",
        }

        return headers

    def action_update_table(self):
        if not self.table_code:
            raise UserError('Bạn cần điền table code')
        self.call_bizfly_base_table_struct(self.table_code)

    def action_check_mapping_key(self):
        model_id = self.model_id
        if not model_id:
            raise UserError('Bạn chưa điền model để mapping trường!')

        model = self.env[model_id.model]

        # Lấy 1 mẫu để test
        record = model.search([], limit=1)
        if not record:
            raise UserError(_(
                "Không có bản ghi nào của model '%s' (%s) để kiểm tra"
            ) % (model_id.name, model_id.model))

        for table in self:
            errors = []

            for param in table.table_param_ids:
                if not param.mapping_key:
                    continue

                mapping_key = param.mapping_key.strip()
                # Thử lấy giá trị từ order
                try:
                    value = table._get_value_from_mapping(record, mapping_key)
                except AttributeError as e:
                    errors.append(
                        _("mapping_key '%s' không truy cập được field '%s'")
                        % (mapping_key, e.args[0])
                    )
                    continue
                if param.accept_null:
                    continue
                # Không có giá trị
                if value in (False, None, ''):
                    errors.append(
                        _("mapping_key '%s' truy cập được nhưng không có giá trị")
                        % mapping_key
                    )
            if errors:
                raise UserError("\n".join(errors))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('OK'),
                'message': _('Tất cả mapping_key đều hợp lệ'),
                'type': 'success',
                'sticky': False,
            }
        }
