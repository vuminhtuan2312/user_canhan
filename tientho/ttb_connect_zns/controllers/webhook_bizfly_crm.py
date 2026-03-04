from odoo import http, fields
from odoo.http import request
from datetime import datetime
import json
import logging

_logger = logging.getLogger(__name__)

class WebhookBizflyController(http.Controller):

    @http.route(
        '/webhook/bizfly',
        type='json',
        auth='public',
        methods=['POST'],
        csrf=False
    )
    def webhook_order(self, **payload):
        _logger.info("Webhook received: %s", payload)
        raw = getattr(getattr(request, 'httprequest', None), 'get_data', lambda as_text=True: "")(as_text=True) or ""
        if not payload:
            # prefer Odoo parsed JSON if available
            payload = json.loads(raw)