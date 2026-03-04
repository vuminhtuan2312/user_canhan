import json
import requests
from odoo import models, fields
from datetime import datetime

class WebhookService(models.AbstractModel):
    _name = 'webhook.service'
    _description = 'Webhook Service'

    def send_event(self, event, obj):
        webhooks = self.env['webhook.config'].search([
            ('active', '=', True),
            ('event', '=', event)
        ])

        for webhook in webhooks:
            headers = {}
            if webhook.headers:
                headers.update(json.loads(webhook.headers))

            if webhook.token:
                headers['X-Webhook-Token'] = webhook.token

            payload = {
                'id': obj.id,
                'model': obj._name,
            }

            try:
                resp = requests.request(
                    webhook.method,
                    webhook.url,
                    json=payload,
                    headers=headers,
                    timeout=10
                )

                webhook.write({
                    'last_call_at': fields.Datetime.now(),
                    'last_status': resp.status_code,
                    'last_response': resp.text,
                })

            except Exception as e:
                webhook.write({
                    'last_call_at': fields.Datetime.now(),
                    'last_status': 0,
                    'last_response': str(e),
                })
