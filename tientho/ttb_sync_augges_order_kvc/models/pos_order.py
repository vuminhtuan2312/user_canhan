# -*- coding: utf-8 -*-
import hashlib
import json
from odoo import api, fields, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    # Flag: order contains ticket items (Augges DmH.Ma_Tong = 'VE')
    ttb_is_ve_order = fields.Boolean(string='Đơn vé (Ma_Tong=VE)', index=True, tracking=True)

    # BizCRM sync state (for pushing orders)
    ttb_bizcrm_sync_state = fields.Selection([
        ('draft', 'Chưa đồng bộ'),
        ('done', 'Đã đồng bộ'),
        ('error', 'Lỗi'),
    ], default='draft', index=True, tracking=True)

    ttb_bizcrm_last_sync_at = fields.Datetime(string='Lần đồng bộ BizCRM gần nhất', index=True)
    ttb_bizcrm_error = fields.Text(string='Lỗi BizCRM')

    def _ttb_bizcrm_payload_hash(self, payload: dict) -> str:
        """Stable hash to avoid resending identical payload."""
        data = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(data.encode('utf-8')).hexdigest()
