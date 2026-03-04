from odoo import http, fields
from odoo.http import request
from datetime import datetime
import json
import logging

_logger = logging.getLogger(__name__)

class WebhookZNSController(http.Controller):

    def _timestamp_to_datetime(self, ts):
        """
        Convert timestamp (seconds or milliseconds) to Odoo datetime string (UTC)
        :param ts: int | float | None
        :return: str | False
        """
        if not ts:
            return False

        try:
            ts = float(ts)

            # Detect milliseconds
            if ts > 10 ** 12:
                ts = ts / 1000

            dt = datetime.utcfromtimestamp(ts)
            return fields.Datetime.to_string(dt)

        except Exception:
            _logger.exception("Invalid timestamp: %s", ts)
            return False


    def _handle_user_received_message(self, payload):
        webhook_response = request.env['webhook.response'].sudo()

        if not payload:
            _logger.info("[EVENT] user_received_message - empty payload")
            return

        app_id = payload.get('app_id')
        timestamp = self._timestamp_to_datetime(payload.get('timestamp'))
        sender_id = payload.get('sender', {}).get('id')
        recipient_id = payload.get('recipient', {}).get('id')

        msg = payload.get('message', {}) or {}
        msg_id = msg.get('msg_id')
        tracking_id = msg.get('tracking_id')
        text = msg.get('text', '') or ''
        receiver_device = msg.get('receiver_device')
        # ===== convert delivery_time =====
        delivery_datetime = self._timestamp_to_datetime(
            msg.get('delivery_time')
        )

        if not text:
            parts = []
            if msg_id:
                parts.append(f"msg_id={msg_id}")
            if tracking_id:
                parts.append(f"tracking_id={tracking_id}")
            if delivery_datetime:
                parts.append(f"delivery_time={delivery_datetime}")
            text = "; ".join(parts) if parts else ""
        zns_send = request.env['zns.send'].search([('msg_id', '=', msg_id)], limit=1)

        vals = {
            'name': 'Người dùng nhận tin nhắn',
            'event_name': 'user_received_message',
            'app_id': app_id,
            'timestamp': timestamp,
            'message_text': text,
            'msg_id': msg_id,
            'delivery_time': delivery_datetime,
            'tracking_id': tracking_id,
            'sender_id': sender_id,
            'recipient_id': recipient_id,
            'receiver_device': receiver_device,
            'raw_payload': json.dumps(payload, ensure_ascii=False),
            'zns_id': zns_send.id,
        }
        val_update = {
            'sender_id': sender_id,
            'status': 'user_received_message',
        }
        if payload.get('receiver_device'):
            pass
            # Thiết bị đã nhận được tin
        else:
            # Đã gửi yêu cầu sang Zalo
            if not zns_send.zalo_request_datetime:
                val_update['zalo_request_datetime'] = timestamp

            # Zalo xác nhận đã gửi
            if delivery_datetime and not zns_send.zalo_sent_datetime:
                val_update['zalo_sent_datetime'] = delivery_datetime
                val_update['device_received_datetime'] = delivery_datetime

        zns_send.write(val_update)
        try:
            webhook_response.create(vals)
            _logger.info(
                "[EVENT] user_received_message - created webhook.response "
                "(app_id=%s, msg_id=%s, tracking_id=%s)",
                app_id, msg_id, tracking_id
            )
        except Exception as e:
            _logger.exception(
                "Failed to create webhook.response for user_received_message"
            )
            return {
                'status': 'error',
                'message': str(e)
            }
    def _handle_user_feedback(self, payload):
        webhook_response = request.env['webhook.response'].sudo()
        zalo_shop_config = request.env['zalo.shop.config'].search([('active', '=', True)], limit=1)
        if not payload:
            _logger.info("[EVENT] user_feedback - empty payload")
            return
        msg = payload.get('message', {}) or {}
        zns_send = request.env['zns.send'].search([('msg_id', '=', msg.get('msg_id'))], limit=1)
        # Prefer explicit note, otherwise join feedbacks into a single text
        note = msg.get('note') or ''
        feedbacks = msg.get('feedbacks')
        if isinstance(feedbacks, (list, tuple)):
            feedbacks_text = "; ".join(str(f) for f in feedbacks)
        else:
            feedbacks_text = str(feedbacks) if feedbacks is not None else ''

        message_text = note if note else feedbacks_text
        timestamp = self._timestamp_to_datetime(payload.get('timestamp'))
        submit_time = self._timestamp_to_datetime(payload.get('message').get('submit_time'))
        vals = {
            'name': 'User Feedback',
            'event_name': 'user_feedback',
            'app_id': payload.get('app_id'),
            'timestamp': timestamp,
            'rate': str(msg.get('rate')) if msg.get('rate') is not None else False,
            'message_text': message_text,
            'msg_id': msg.get('msg_id') or payload.get('msg_id'),
            # store entire payload as text
            'raw_payload': json.dumps(payload, ensure_ascii=False),
            'zns_id': zns_send.id if zns_send.msg_id else False,
        }
        feedbacks = payload.get('message', {}).get('feedbacks', []) or []
        feedbacks_str = ' | '.join(feedbacks) if feedbacks else ''
        zns_send.write({
            'rate': str(msg.get('rate')) if msg.get('rate') is not None else False,
            'completed_datetime': submit_time,
            'note': msg.get('note'),
            'response_message': feedbacks_str,
            'status': 'sent',
        })
        try:
            if not zns_send.zalo_sent_datetime:
                url_path = request.env['ir.config_parameter'].sudo().get_param('zns.get_message_url')
                header = zalo_shop_config._build_auth_headers()
                payload = {
                    "oa_id": zalo_shop_config.oa_id,
                    "msg_id": msg.get('msg_id') or payload.get('msg_id'),
                }
                response_detail_msg = request.env['zalo.shop.config'].call_api(url_path, header, payload)
                if response_detail_msg:
                    zns_send.write({
                        'zalo_request_datetime': zalo_shop_config.parse_zalo_datetime(response_detail_msg.get('sent_time')),
                        'zalo_sent_datetime': zalo_shop_config.parse_zalo_datetime(response_detail_msg.get('delivery_time')),
                    })
            webhook_response.create(vals)
            _logger.info("[EVENT] user_feedback - created webhook.response: %s", {
                'app_id': vals['app_id'],
                'msg_id': vals['msg_id'],
                'rate': vals['rate']
            })
        except Exception as e:
            _logger.exception("Failed to create webhook.response for user_feedback")
            return {
                'status': 'error',
                'message': str(e)
            }
    def _handle_user_click_response_button(self, payload):
        webhook_response = request.env['webhook.response'].sudo()

        if not payload:
            _logger.info("[EVENT] user_click_response_button - empty payload")
            return

        # ===== Basic metadata =====
        oa_id = payload.get('oa_id')
        app_id = payload.get('app_id')
        event_name = payload.get('event_name')
        timestamp = payload.get('timestamp')

        timestamp_dt = self._timestamp_to_datetime(timestamp)

        # ===== Message data =====
        msg_id = payload.get('msg_id')
        message = payload.get('message', {}) or {}

        data = message.get('data')  # "Dịch vụ ZNS"
        button_type = message.get('button_type')  # response
        tracking_id = message.get('tracking_id')
        submit_time = message.get('submit_time')

        submit_time_dt = self._timestamp_to_datetime(submit_time)

        # Fallback message text
        text = data or f"button_type={button_type}"

        vals = {
            'name': 'Người dùng bấm nút phản hồi',
            'event_name': event_name,
            'app_id': app_id,
            'oa_id': oa_id,
            'timestamp': timestamp_dt,
            'message_text': text,
            'msg_id': msg_id,
            'tracking_id': tracking_id,
            'submit_time': submit_time_dt,
            'button_type': button_type,
            'raw_payload': json.dumps(payload, ensure_ascii=False),
        }

        try:
            webhook_response.create(vals)
            _logger.info(
                "[EVENT] user_click_response_button - created webhook.response "
                "(msg_id=%s, tracking_id=%s)",
                msg_id, tracking_id
            )
        except Exception as e:
            _logger.exception(
                "Failed to create webhook.response for user_click_response_button"
            )
            return {
                'status': 'error',
                'message': str(e)
            }
    def _handle_oa_send_text(self, payload):
        webhook_response = request.env['webhook.response'].sudo()

        if not payload:
            _logger.info("[EVENT] oa_send_text - empty payload")
            return

        # ===== Basic metadata =====
        app_id = payload.get('app_id')
        event_name = payload.get('event_name')
        timestamp = payload.get('timestamp')
        timestamp_dt = self._timestamp_to_datetime(timestamp)

        sender = payload.get('sender', {}) or {}
        recipient = payload.get('recipient', {}) or {}

        sender_id = sender.get('id')
        sender_admin_id = sender.get('admin_id')
        recipient_id = recipient.get('id')

        user_id_by_app = payload.get('user_id_by_app')

        # ===== Message =====
        message = payload.get('message', {}) or {}
        text = message.get('text', '') or ''
        msg_id = message.get('msg_id')

        # Fallback text
        if not text:
            text = f"msg_id={msg_id}" if msg_id else ""

        vals = {
            'name': 'OA gửi tin nhắn văn bản',
            'event_name': event_name,
            'app_id': app_id,
            'timestamp': timestamp_dt,
            'message_text': text,
            'msg_id': msg_id,
            'sender_id': sender_id,
            'sender_admin_id': sender_admin_id,
            'recipient_id': recipient_id,
            'user_id_by_app': user_id_by_app,
            'raw_payload': json.dumps(payload, ensure_ascii=False),
        }

        try:
            webhook_response.create(vals)
            _logger.info(
                "[EVENT] oa_send_text - created webhook.response "
                "(msg_id=%s, sender_id=%s)",
                msg_id, sender_id
            )
        except Exception as e:
            _logger.exception("Failed to create webhook.response for oa_send_text")
            return {
                'status': 'error',
                'message': str(e)
            }
    def _handle_oa_send_sticker(self, payload):
        webhook_response = request.env['webhook.response'].sudo()

        if not payload:
            _logger.info("[EVENT] oa_send_sticker - empty payload")
            return

        # ===== Basic metadata =====
        event_name = payload.get('event_name')
        app_id = payload.get('app_id')
        timestamp = payload.get('timestamp')
        timestamp_dt = self._timestamp_to_datetime(timestamp)

        sender = payload.get('sender', {}) or {}
        recipient = payload.get('recipient', {}) or {}

        sender_id = sender.get('id')
        recipient_id = recipient.get('id')

        # ===== Message =====
        message = payload.get('message', {}) or {}
        msg_id = message.get('msg_id')

        attachments = message.get('attachments', []) or []

        sticker_id = False
        sticker_url = False

        # Zalo hiện chỉ có 1 sticker trong attachments
        if attachments:
            attachment = attachments[0]
            payload_attach = attachment.get('payload', {}) or {}
            sticker_id = payload_attach.get('id')
            sticker_url = payload_attach.get('url')

        # Fallback message text
        text = sticker_id or 'OA gửi sticker'

        vals = {
            'name': 'OA gửi sticker',
            'event_name': event_name,
            'app_id': app_id,
            'timestamp': timestamp_dt,
            'message_text': text,
            'msg_id': msg_id,
            'sender_id': sender_id,
            'recipient_id': recipient_id,
            'sticker_id': sticker_id,
            'sticker_url': sticker_url,
            'raw_payload': json.dumps(payload, ensure_ascii=False),
        }

        try:
            webhook_response.create(vals)
            _logger.info(
                "[EVENT] oa_send_sticker - created webhook.response "
                "(msg_id=%s, sticker_id=%s)",
                msg_id, sticker_id
            )
        except Exception as e:
            _logger.exception("Failed to create webhook.response for oa_send_sticker")
            return {
                'status': 'error',
                'message': str(e)
            }
    def _handle_oa_send_file(self, payload):
        webhook_response = request.env['webhook.response'].sudo()

        if not payload:
            _logger.info("[EVENT] oa_send_file - empty payload")
            return

        # ===== Basic metadata =====
        event_name = payload.get('event_name')
        app_id = payload.get('app_id')
        timestamp = payload.get('timestamp')
        timestamp_dt = self._timestamp_to_datetime(timestamp)

        sender = payload.get('sender', {}) or {}
        recipient = payload.get('recipient', {}) or {}

        sender_id = sender.get('id')
        recipient_id = recipient.get('id')

        # ===== Message =====
        message = payload.get('message', {}) or {}
        msg_id = message.get('msg_id')

        attachments = message.get('attachments', []) or []

        file_name = False
        file_url = False
        file_type = False
        file_size = False
        file_checksum = False

        if attachments:
            attachment = attachments[0]
            payload_attach = attachment.get('payload', {}) or {}

            file_name = payload_attach.get('name')
            file_url = payload_attach.get('url')
            file_type = payload_attach.get('type')
            file_size = payload_attach.get('size')
            file_checksum = payload_attach.get('checksum')

        # Fallback message text
        text = file_name or 'OA gửi tệp tin'

        vals = {
            'name': 'OA gửi tệp tin',
            'event_name': event_name,
            'app_id': app_id,
            'timestamp': timestamp_dt,
            'message_text': text,
            'msg_id': msg_id,
            'sender_id': sender_id,
            'recipient_id': recipient_id,
            'file_name': file_name,
            'file_url': file_url,
            'file_type': file_type,
            'file_size': file_size,
            'file_checksum': file_checksum,
            'raw_payload': json.dumps(payload, ensure_ascii=False),
        }

        try:
            webhook_response.create(vals)
            _logger.info(
                "[EVENT] oa_send_file - created webhook.response "
                "(msg_id=%s, file_name=%s)",
                msg_id, file_name
            )
        except Exception as e:
            _logger.exception("Failed to create webhook.response for oa_send_file")
            return {
                'status': 'error',
                'message': str(e)
            }
    def _handle_oa_send_image(self, payload):
        webhook_response = request.env['webhook.response'].sudo()

        if not payload:
            _logger.info("[EVENT] oa_send_image - empty payload")
            return

        # ===== Basic metadata =====
        event_name = payload.get('event_name')
        app_id = payload.get('app_id')
        timestamp = payload.get('timestamp')
        timestamp_dt = self._timestamp_to_datetime(timestamp)

        sender = payload.get('sender', {}) or {}
        recipient = payload.get('recipient', {}) or {}

        sender_id = sender.get('id')
        recipient_id = recipient.get('id')

        # ===== Message =====
        message = payload.get('message', {}) or {}
        msg_id = message.get('msg_id')

        attachments = message.get('attachments', []) or []

        image_url = False
        image_thumbnail = False

        if attachments:
            attachment = attachments[0]
            payload_attach = attachment.get('payload', {}) or {}
            image_url = payload_attach.get('url')
            image_thumbnail = payload_attach.get('thumbnail')

        # Fallback message text
        text = image_url or 'OA gửi hình ảnh'

        vals = {
            'name': 'OA gửi hình ảnh',
            'event_name': event_name,
            'app_id': app_id,
            'timestamp': timestamp_dt,
            'message_text': text,
            'msg_id': msg_id,
            'sender_id': sender_id,
            'recipient_id': recipient_id,
            'image_url': image_url,
            'image_thumbnail': image_thumbnail,
            'raw_payload': json.dumps(payload, ensure_ascii=False),
        }

        try:
            webhook_response.create(vals)
            _logger.info(
                "[EVENT] oa_send_image - created webhook.response "
                "(msg_id=%s)",
                msg_id
            )
        except Exception as e:
            _logger.exception("Failed to create webhook.response for oa_send_image")
            return {
                'status': 'error',
                'message': str(e)
            }
    def _handle_oa_send_list(self, payload):
        webhook_response = request.env['webhook.response'].sudo()

        if not payload:
            _logger.info("[EVENT] oa_send_list - empty payload")
            return

        # ===== Basic metadata =====
        event_name = payload.get('event_name')
        app_id = payload.get('app_id')
        timestamp = payload.get('timestamp')
        timestamp_dt = self._timestamp_to_datetime(timestamp)

        sender = payload.get('sender', {}) or {}
        recipient = payload.get('recipient', {}) or {}

        sender_id = sender.get('id')
        recipient_id = recipient.get('id')

        # ===== Message =====
        message = payload.get('message', {}) or {}
        msg_id = message.get('msg_id')
        text = message.get('text', '') or ''

        attachments = message.get('attachments', []) or []

        link_title = False
        link_description = False
        link_url = False
        link_thumbnail = False

        if attachments:
            attachment = attachments[0]
            payload_attach = attachment.get('payload', {}) or {}

            link_title = payload_attach.get('title')
            link_description = payload_attach.get('description')
            link_url = payload_attach.get('url')
            link_thumbnail = payload_attach.get('thumbnail')

        # Fallback message text
        display_text = text or link_title or 'OA gửi danh sách'

        vals = {
            'name': 'OA gửi danh sách',
            'event_name': event_name,
            'app_id': app_id,
            'timestamp': timestamp_dt,
            'message_text': display_text,
            'msg_id': msg_id,
            'sender_id': sender_id,
            'recipient_id': recipient_id,
            'link_title': link_title,
            'link_description': link_description,
            'link_url': link_url,
            'link_thumbnail': link_thumbnail,
            'raw_payload': json.dumps(payload, ensure_ascii=False),
        }

        try:
            webhook_response.create(vals)
            _logger.info(
                "[EVENT] oa_send_list - created webhook.response "
                "(msg_id=%s, link_title=%s)",
                msg_id, link_title
            )
        except Exception as e:
            _logger.exception("Failed to create webhook.response for oa_send_list")
            return {
                'status': 'error',
                'message': str(e)
            }
    def _handle_user_send_text(self, payload):
        _logger.info("[EVENT] user_send_text")

        webhook_response = request.env['webhook.response'].sudo()

        if not payload:
            _logger.info("[EVENT] user_send_text - empty payload")
            return

        # ===== Basic metadata =====
        event_name = payload.get('event_name')
        app_id = payload.get('app_id')
        timestamp = payload.get('timestamp')
        timestamp_dt = self._timestamp_to_datetime(timestamp)

        sender = payload.get('sender', {}) or {}
        recipient = payload.get('recipient', {}) or {}

        sender_id = sender.get('id')
        recipient_id = recipient.get('id')

        # ===== Message =====
        message_data = payload.get('message', {}) or {}
        message_text = message_data.get('text')
        msg_id = message_data.get('msg_id')

        vals = {
            'name': 'Người dùng gửi tin nhắn văn bản',
            'event_name': event_name,
            'app_id': app_id,
            'timestamp': timestamp_dt,
            'sender_id': sender_id,
            'recipient_id': recipient_id,
            'msg_id': msg_id,
            'message_text': message_text,
            'raw_payload': json.dumps(payload, ensure_ascii=False),
        }

        try:
            webhook_response.create(vals)
            _logger.info(
                "[EVENT] user_send_text - created webhook.response "
                "(msg_id=%s, sender_id=%s)",
                msg_id, sender_id
            )
        except Exception as e:
            _logger.exception("Failed to create webhook.response for user_send_text")
            return {
                'status': 'error',
                'message': str(e)
            }

    def _handle_user_send_sticker(self, payload):
        _logger.info("[EVENT] user_send_sticker")

        webhook_response = request.env['webhook.response'].sudo()

        if not payload:
            _logger.info("[EVENT] user_send_sticker - empty payload")
            return

        # ===== Basic metadata =====
        event_name = payload.get('event_name')
        app_id = payload.get('app_id')
        timestamp = payload.get('timestamp')
        timestamp_dt = self._timestamp_to_datetime(timestamp)

        sender = payload.get('sender', {}) or {}
        recipient = payload.get('recipient', {}) or {}

        sender_id = sender.get('id')
        recipient_id = recipient.get('id')

        # ===== Message =====
        msg = payload.get('message', {}) or {}
        msg_id = msg.get('msg_id')

        attachments = msg.get('attachments', []) or []

        sticker_id = None
        sticker_url = None

        if attachments:
            attachment = attachments[0]
            payload_attach = attachment.get('payload', {}) or {}
            sticker_id = payload_attach.get('id')
            sticker_url = payload_attach.get('url')

        # Fallback message text
        message_text = f"Sticker: {sticker_id}" if sticker_id else "Sticker"

        vals = {
            'name': 'Người dùng gửi sticker',
            'event_name': event_name,
            'app_id': app_id,
            'timestamp': timestamp_dt,
            'sender_id': sender_id,
            'recipient_id': recipient_id,
            'msg_id': msg_id,
            'message_text': message_text,
            'raw_payload': json.dumps(payload, ensure_ascii=False),
        }

        try:
            webhook_response.create(vals)
            _logger.info(
                "[EVENT] user_send_sticker - created webhook.response "
                "(msg_id=%s, sticker_id=%s)",
                msg_id, sticker_id
            )
        except Exception as e:
            _logger.exception("Failed to create webhook.response for user_send_sticker")
            return {
                'status': 'error',
                'message': str(e)
            }
    def _handle_user_send_file(self, payload):
        _logger.info("[EVENT] user_send_file")

        webhook_response = request.env['webhook.response'].sudo()

        if not payload:
            _logger.info("[EVENT] user_send_file - empty payload")
            return

        # ===== Basic metadata =====
        event_name = payload.get('event_name')
        app_id = payload.get('app_id')
        timestamp = payload.get('timestamp')
        timestamp_dt = self._timestamp_to_datetime(timestamp)

        sender = payload.get('sender', {}) or {}
        recipient = payload.get('recipient', {}) or {}

        sender_id = sender.get('id')
        recipient_id = recipient.get('id')

        # ===== Message =====
        msg = payload.get('message', {}) or {}
        msg_id = msg.get('msg_id')

        attachments = msg.get('attachments', []) or []

        file_name = None
        file_type = None
        file_size = None
        file_url = None
        checksum = None

        if attachments:
            attachment = attachments[0]
            payload_attach = attachment.get('payload', {}) or {}

            file_name = payload_attach.get('name')
            file_type = payload_attach.get('type')
            file_size = payload_attach.get('size')
            file_url = payload_attach.get('url')
            checksum = payload_attach.get('checksum')

        # Fallback message text
        parts = []
        if file_name:
            parts.append(file_name)
        if file_type:
            parts.append(f"type={file_type}")
        if file_size:
            parts.append(f"size={file_size}")

        message_text = " | ".join(parts) if parts else "User gửi file"

        vals = {
            'name': 'Người dùng gửi file',
            'event_name': event_name,
            'app_id': app_id,
            'timestamp': timestamp_dt,
            'sender_id': sender_id,
            'recipient_id': recipient_id,
            'msg_id': msg_id,
            'message_text': message_text,
            'raw_payload': json.dumps(payload, ensure_ascii=False),
        }

        try:
            webhook_response.create(vals)
            _logger.info(
                "[EVENT] user_send_file - created webhook.response "
                "(msg_id=%s, file=%s)",
                msg_id, file_name
            )
        except Exception as e:
            _logger.exception("Failed to create webhook.response for user_send_file")
            return {
                'status': 'error',
                'message': str(e)
            }
    def _handle_user_send_image(self, payload):
        _logger.info("[EVENT] user_send_image")

        webhook_response = request.env['webhook.response'].sudo()

        if not payload:
            _logger.info("[EVENT] user_send_image - empty payload")
            return

        # ===== Basic metadata =====
        event_name = payload.get('event_name')
        app_id = payload.get('app_id')
        timestamp = payload.get('timestamp')
        timestamp_dt = self._timestamp_to_datetime(timestamp)

        sender = payload.get('sender', {}) or {}
        recipient = payload.get('recipient', {}) or {}

        sender_id = sender.get('id')
        recipient_id = recipient.get('id')

        # ===== Message =====
        msg = payload.get('message', {}) or {}
        msg_id = msg.get('msg_id')

        attachments = msg.get('attachments', []) or []

        image_url = None
        thumbnail_url = None

        if attachments:
            attachment = attachments[0]
            payload_attach = attachment.get('payload', {}) or {}
            image_url = payload_attach.get('url')
            thumbnail_url = payload_attach.get('thumbnail')

        # Fallback message text
        if image_url:
            message_text = "User gửi hình ảnh"
        else:
            message_text = "User gửi image"

        vals = {
            'name': 'Người dùng gửi hình ảnh',
            'event_name': event_name,
            'app_id': app_id,
            'timestamp': timestamp_dt,
            'sender_id': sender_id,
            'recipient_id': recipient_id,
            'msg_id': msg_id,
            'message_text': message_text,
            'raw_payload': json.dumps(payload, ensure_ascii=False),
        }

        try:
            webhook_response.create(vals)
            _logger.info(
                "[EVENT] user_send_image - created webhook.response "
                "(msg_id=%s)",
                msg_id
            )
        except Exception as e:
            _logger.exception("Failed to create webhook.response for user_send_image")
            return {
                'status': 'error',
                'message': str(e)
            }
    def _handle_user_send_business_card(self, payload):
        _logger.info("[EVENT] user_send_business_card")

        webhook_response = request.env['webhook.response'].sudo()

        if not payload:
            _logger.info("[EVENT] user_send_business_card - empty payload")
            return

        # ===== Basic metadata =====
        event_name = payload.get('event_name')
        app_id = payload.get('app_id')
        timestamp = payload.get('timestamp')
        timestamp_dt = self._timestamp_to_datetime(timestamp)

        sender = payload.get('sender', {}) or {}
        recipient = payload.get('recipient', {}) or {}

        sender_id = sender.get('id')
        recipient_id = recipient.get('id')

        # ===== Message =====
        msg = payload.get('message', {}) or {}
        msg_id = msg.get('msg_id')
        text = msg.get('text') or ''

        attachments = msg.get('attachments', []) or []

        thumbnail = None
        card_url = None
        description_raw = None
        qr_code_url = None

        if attachments:
            attachment = attachments[0]
            payload_attach = attachment.get('payload', {}) or {}

            thumbnail = payload_attach.get('thumbnail')
            card_url = payload_attach.get('url')
            description_raw = payload_attach.get('description')

            # description là JSON string
            if description_raw:
                try:
                    description_json = json.loads(description_raw)
                    qr_code_url = description_json.get('qrCodeUrl')
                except Exception:
                    _logger.warning("Invalid description JSON in business_card")

        # Fallback message text
        parts = []
        if text:
            parts.append(text)
        if qr_code_url:
            parts.append("QR Card")

        message_text = " | ".join(parts) if parts else "User gửi danh thiếp"

        vals = {
            'name': 'Người dùng gửi danh thiếp',
            'event_name': event_name,
            'app_id': app_id,
            'timestamp': timestamp_dt,
            'sender_id': sender_id,
            'recipient_id': recipient_id,
            'msg_id': msg_id,
            'message_text': message_text,
            'raw_payload': json.dumps(payload, ensure_ascii=False),
        }

        try:
            webhook_response.create(vals)
            _logger.info(
                "[EVENT] user_send_business_card - created webhook.response "
                "(msg_id=%s)",
                msg_id
            )
        except Exception as e:
            _logger.exception("Failed to create webhook.response for user_send_business_card")
            return {
                'status': 'error',
                'message': str(e)
            }
    def _handle_user_submit_info(self, payload):
        _logger.info("[EVENT] user_submit_info")

        webhook_response = request.env['webhook.response'].sudo()

        if not payload:
            _logger.info("[EVENT] user_submit_info - empty payload")
            return

        # ===== Basic metadata =====
        event_name = payload.get('event_name')
        app_id = payload.get('app_id')
        timestamp = payload.get('timestamp')
        timestamp_dt = self._timestamp_to_datetime(timestamp)

        sender = payload.get('sender', {}) or {}
        recipient = payload.get('recipient', {}) or {}

        sender_id = sender.get('id')
        recipient_id = recipient.get('id')

        # ===== Submitted info =====
        info = payload.get('info', {}) or {}

        name = info.get('name')
        phone = info.get('phone')
        address = info.get('address')
        city = info.get('city')
        district = info.get('district')

        # Build readable message
        parts = []
        if name:
            parts.append(f"Tên: {name}")
        if phone:
            parts.append(f"SĐT: {phone}")
        if city:
            parts.append(f"Tỉnh/TP: {city}")
        if district:
            parts.append(f"Quận/Huyện: {district}")
        if address:
            parts.append(f"Địa chỉ: {address}")

        message_text = " | ".join(parts) if parts else "User submit info"

        vals = {
            'name': 'Người dùng gửi thông tin',
            'event_name': event_name,
            'app_id': app_id,
            'timestamp': timestamp_dt,
            'sender_id': sender_id,
            'recipient_id': recipient_id,
            'message_text': message_text,
            'raw_payload': json.dumps(payload, ensure_ascii=False),
        }

        try:
            webhook_response.create(vals)
            _logger.info(
                "[EVENT] user_submit_info - created webhook.response "
                "(sender_id=%s)",
                sender_id
            )
        except Exception as e:
            _logger.exception("Failed to create webhook.response for user_submit_info")
            return {
                'status': 'error',
                'message': str(e)
            }
    def _handle_oa_send_consent(self, payload):
        _logger.info("[EVENT] oa_send_consent")

        webhook_response = request.env['webhook.response'].sudo()

        if not payload:
            _logger.info("[EVENT] oa_send_consent - empty payload")
            return

        # ===== Basic metadata =====
        event_name = payload.get('event_name')
        app_id = payload.get('app_id')
        oa_id = payload.get('oa_id')

        timestamp = payload.get('timestamp')
        timestamp_dt = self._timestamp_to_datetime(timestamp)

        create_time = payload.get('create_time')
        create_time_dt = self._timestamp_to_datetime(create_time)

        expired_time = payload.get('expired_time')
        expired_time_dt = self._timestamp_to_datetime(expired_time)

        request_type = payload.get('request_type')
        phone = payload.get('phone')

        # Build readable message
        parts = []
        if phone:
            parts.append(f"SĐT: {phone}")
        if request_type:
            parts.append(f"Loại yêu cầu: {request_type}")
        if expired_time_dt:
            parts.append(f"Hết hạn: {expired_time_dt}")

        message_text = " | ".join(parts) if parts else "OA gửi yêu cầu đồng ý"

        vals = {
            'name': 'OA gửi yêu cầu đồng ý',
            'event_name': event_name,
            'app_id': app_id,
            'sender_id': oa_id,  # OA là bên gửi
            'timestamp': timestamp_dt,
            'message_text': message_text,
            'raw_payload': json.dumps(payload, ensure_ascii=False),
        }

        try:
            webhook_response.create(vals)
            _logger.info(
                "[EVENT] oa_send_consent - created webhook.response "
                "(phone=%s, request_type=%s)",
                phone, request_type
            )
        except Exception as e:
            _logger.exception("Failed to create webhook.response for oa_send_consent")
            return {
                'status': 'error',
                'message': str(e)
            }
    def _handle_user_reply_consent(self, payload):
        _logger.info("[EVENT] user_reply_consent")

        webhook_response = request.env['webhook.response'].sudo()

        if not payload:
            _logger.info("[EVENT] user_reply_consent - empty payload")
            return

        # ===== Basic metadata =====
        event_name = payload.get('event_name')
        app_id = payload.get('app_id')
        oa_id = payload.get('oa_id')

        timestamp = payload.get('timestamp')
        timestamp_dt = self._timestamp_to_datetime(timestamp)

        confirmed_time = payload.get('confirmed_time')
        confirmed_time_dt = self._timestamp_to_datetime(confirmed_time)

        expired_time = payload.get('expired_time')
        expired_time_dt = self._timestamp_to_datetime(expired_time)

        phone = payload.get('phone')
        user_consent = payload.get('user_consent')  # ALLOW / DENY

        # Build readable message
        consent_map = {
            'ALLOW': 'Đồng ý',
            'DENY': 'Từ chối',
        }
        consent_text = consent_map.get(user_consent, user_consent)

        parts = []
        if phone:
            parts.append(f"SĐT: {phone}")
        if consent_text:
            parts.append(f"Phản hồi: {consent_text}")
        if confirmed_time_dt:
            parts.append(f"Xác nhận lúc: {confirmed_time_dt}")

        message_text = " | ".join(parts) if parts else "Người dùng phản hồi đồng ý"

        vals = {
            'name': 'Người dùng phản hồi đồng ý',
            'event_name': event_name,
            'app_id': app_id,
            'sender_id': oa_id,
            'timestamp': timestamp_dt,

            'phone': phone,
            'request_type': user_consent,
            'consent_create_time': confirmed_time_dt,
            'consent_expired_time': expired_time_dt,

            'message_text': message_text,
            'raw_payload': json.dumps(payload, ensure_ascii=False),
        }

        try:
            webhook_response.create(vals)
            _logger.info(
                "[EVENT] user_reply_consent - created webhook.response "
                "(phone=%s, consent=%s)",
                phone, user_consent
            )
        except Exception as e:
            _logger.exception("Failed to create webhook.response for user_reply_consent")
            return {
                'status': 'error',
                'message': str(e)
            }
    def _handle_follow(self, payload):
        _logger.info("[EVENT] follow")

        webhook_response = request.env['webhook.response'].sudo()

        if not payload:
            _logger.info("[EVENT] follow - empty payload")
            return

        # ===== Basic metadata =====
        event_name = payload.get('event_name')
        app_id = payload.get('app_id')
        oa_id = payload.get('oa_id')

        timestamp = payload.get('timestamp')
        timestamp_dt = self._timestamp_to_datetime(timestamp)

        follower = payload.get('follower', {}) or {}
        follower_id = follower.get('id')

        source = payload.get('source')  # oa_profile / chat / search ...

        # Build readable message
        parts = []
        if follower_id:
            parts.append(f"Follower ID: {follower_id}")
        if source:
            parts.append(f"Nguồn: {source}")

        message_text = " | ".join(parts) if parts else "Người dùng theo dõi OA"

        vals = {
            'name': 'Người dùng theo dõi OA',
            'event_name': event_name,
            'app_id': app_id,
            'sender_id': follower_id,  # user
            'recipient_id': oa_id,  # OA
            'timestamp': timestamp_dt,
            'message_text': message_text,
            'raw_payload': json.dumps(payload, ensure_ascii=False),
        }

        try:
            webhook_response.create(vals)
            _logger.info(
                "[EVENT] follow - created webhook.response "
                "(follower_id=%s, source=%s)",
                follower_id, source
            )
        except Exception as e:
            _logger.exception("Failed to create webhook.response for follow")
            return {
                'status': 'error',
                'message': str(e)
            }
    def _handle_unfollow(self, payload):
        _logger.info("[EVENT] unfollow")

        webhook_response = request.env['webhook.response'].sudo()

        if not payload:
            _logger.info("[EVENT] unfollow - empty payload")
            return

        # ===== Basic metadata =====
        event_name = payload.get('event_name')
        app_id = payload.get('app_id')
        oa_id = payload.get('oa_id')

        timestamp = payload.get('timestamp')
        timestamp_dt = self._timestamp_to_datetime(timestamp)

        follower = payload.get('follower', {}) or {}
        follower_id = follower.get('id')

        source = payload.get('source')  # usually 'unfollow'

        # Build readable message
        parts = []
        if follower_id:
            parts.append(f"Follower ID: {follower_id}")
        if source:
            parts.append(f"Lý do: {source}")

        message_text = " | ".join(parts) if parts else "Người dùng hủy theo dõi OA"

        vals = {
            'name': 'Người dùng hủy theo dõi OA',
            'event_name': event_name,
            'app_id': app_id,
            'sender_id': follower_id,  # user
            'recipient_id': oa_id,  # OA
            'timestamp': timestamp_dt,
            'message_text': message_text,
            'raw_payload': json.dumps(payload, ensure_ascii=False),
        }

        try:
            webhook_response.create(vals)
            _logger.info(
                "[EVENT] unfollow - created webhook.response "
                "(follower_id=%s)",
                follower_id
            )
        except Exception as e:
            _logger.exception("Failed to create webhook.response for unfollow")
            return {
                'status': 'error',
                'message': str(e)
            }
    def _handle_change_template_status(self, payload):
        _logger.info("[EVENT] change_template_status")

        webhook_response = request.env['webhook.response'].sudo()

        if not payload:
            _logger.info("[EVENT] change_template_status - empty payload")
            return

        # ===== Basic metadata =====
        event_name = payload.get('event_name')
        app_id = payload.get('app_id')
        oa_id = payload.get('oa_id')

        timestamp = payload.get('timestamp')
        timestamp_dt = self._timestamp_to_datetime(timestamp)

        template_id = payload.get('template_id')
        reason = payload.get('reason')

        status = payload.get('status', {}) or {}
        prev_status = status.get('prev_status')
        new_status = status.get('new_status')

        # Build readable message
        parts = []
        if template_id:
            parts.append(f"Template ID: {template_id}")
        if prev_status and new_status:
            parts.append(f"Trạng thái: {prev_status} → {new_status}")
        if reason:
            parts.append(f"Lý do: {reason}")

        message_text = " | ".join(parts) if parts else "Thay đổi trạng thái template"

        vals = {
            'name': 'Thay đổi trạng thái template',
            'event_name': event_name,
            'app_id': app_id,
            'sender_id': oa_id,  # OA
            'timestamp': timestamp_dt,
            'message_text': message_text,
            'raw_payload': json.dumps(payload, ensure_ascii=False),
        }

        try:
            webhook_response.create(vals)
            _logger.info(
                "[EVENT] change_template_status - created webhook.response "
                "(template_id=%s, %s→%s)",
                template_id, prev_status, new_status
            )
        except Exception as e:
            _logger.exception("Failed to create webhook.response for change_template_status")
            return {
                'status': 'error',
                'message': str(e)
            }
    def _handle_user_seen_message(self, payload):
        _logger.info("[EVENT] user_seen_message")
        webhook_response = request.env['webhook.response'].sudo()

        if not payload:
            _logger.info("[EVENT] user_seen_message - empty payload")
            return

        # ===== Basic metadata =====
        event_name = payload.get('event_name')
        app_id = payload.get('app_id')

        timestamp = payload.get('timestamp')
        timestamp_dt = self._timestamp_to_datetime(timestamp)

        sender = payload.get('sender', {}) or {}
        recipient = payload.get('recipient', {}) or {}

        sender_id = sender.get('id')  # user
        recipient_id = recipient.get('id')  # OA

        user_id_by_app = payload.get('user_id_by_app')

        # ===== Message =====
        message_data = payload.get('message', {}) or {}
        msg_ids = message_data.get('msg_ids', []) or []

        msg_ids_str = ", ".join(msg_ids) if msg_ids else None
        zns_send = request.env['zns.send'].search([('msg_id', 'in', msg_ids)], limit=1)

        # Build readable message
        parts = []
        if msg_ids_str:
            parts.append(f"Đã xem msg_id: {msg_ids_str}")
        if user_id_by_app:
            parts.append(f"user_id_by_app: {user_id_by_app}")

        message_text = " | ".join(parts) if parts else "Người dùng đã xem tin nhắn"

        vals = {
            'name': 'Người dùng đã xem tin nhắn',
            'event_name': event_name,
            'app_id': app_id,
            'sender_id': sender_id,
            'recipient_id': recipient_id,
            'timestamp': timestamp_dt,
            'message_text': message_text,
            'raw_payload': json.dumps(payload, ensure_ascii=False),
        }
        zns_send.write({
            'first_click_datetime': timestamp_dt
        })
        try:
            webhook_response.create(vals)
            _logger.info(
                "[EVENT] user_seen_message - created webhook.response "
                "(sender_id=%s, msg_ids=%s)",
                sender_id, msg_ids_str
            )
        except Exception as e:
            _logger.exception("Failed to create webhook.response for user_seen_message")
            return {
                'status': 'error',
                'message': str(e)
            }
    @http.route(
        '/webhook/order',
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
        _logger.info("Payload parsed: %s", payload)
        event_name = payload.get('event_name')
        try:
            result = None
            if event_name == "user_received_message":
                result = self._handle_user_received_message(payload)
            elif event_name == "user_feedback":
                result = self._handle_user_feedback(payload)
            elif event_name == "user_click_response_button":
                result = self._handle_user_click_response_button(payload)
            elif event_name == "oa_send_text":
                result = self._handle_oa_send_text(payload)
            elif event_name == "oa_send_sticker":
                result = self._handle_oa_send_sticker(payload)
            elif event_name == "oa_send_file":
                result = self._handle_oa_send_file(payload)
            elif event_name == "oa_send_image":
                result = self._handle_oa_send_image(payload)
            elif event_name == "oa_send_list":
                result = self._handle_oa_send_list(payload)
            elif event_name == "user_send_text":
                result = self._handle_user_send_text(payload)
            elif event_name == "user_send_sticker":
                result = self._handle_user_send_sticker(payload)
            elif event_name == "user_send_file":
                result = self._handle_user_send_file(payload)
            elif event_name == "user_send_image":
                result = self._handle_user_send_image(payload)
            elif event_name == "user_send_business_card":
                result = self._handle_user_send_business_card(payload)
            elif event_name == "user_submit_info":
                result = self._handle_user_submit_info(payload)
            elif event_name == "oa_send_consent":
                result = self._handle_oa_send_consent(payload)
            elif event_name == "user_reply_consent":
                result = self._handle_user_reply_consent(payload)
            elif event_name == "follow":
                result = self._handle_follow(payload)
            elif event_name == "unfollow":
                result = self._handle_unfollow(payload)
            elif event_name == "change_template_status":
                result = self._handle_change_template_status(payload)
            elif event_name == "user_seen_message":
                result = self._handle_user_seen_message(payload)
            else:
                _logger.info("Unhandled event: %s", event_name)
            if isinstance(result, dict):
                return result
            else:
                return {
                    'status': 'success',
                    'message': 'Webhook processed'
                }
        except Exception as e:
            _logger.exception("Webhook error")
            return {
                'status': 'error',
                'message': str(e)
            }
