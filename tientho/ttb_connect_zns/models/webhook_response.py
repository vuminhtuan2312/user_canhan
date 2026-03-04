from odoo import models, fields, api
import hashlib


class WebhookResponse(models.Model):
    _name = 'webhook.response'
    _description = 'Webhook phản hồi từ Zalo'
    _order = 'timestamp desc, id desc'

    # =====================================================
    # THÔNG TIN ĐỊNH DANH
    # =====================================================
    unique_key = fields.Char(
        string='Khóa duy nhất',
        required=True,
        index=True,
        readonly=True
    )

    name = fields.Char(
        string='Tên sự kiện',
        required=True,
        index=True
    )

    event_name = fields.Char(
        string='Mã sự kiện',
        required=True,
        index=True
    )

    app_id = fields.Char(
        string='App ID',
        index=True
    )

    oa_id = fields.Char(
        string='OA ID',
        index=True
    )

    # =====================================================
    # THỜI GIAN
    # =====================================================
    timestamp = fields.Datetime(
        string='Thời gian sự kiện',
        index=True
    )

    delivery_time = fields.Datetime(
        string='Thời gian giao tin'
    )

    submit_time = fields.Datetime(
        string='Thời gian gửi phản hồi'
    )

    consent_create_time = fields.Datetime(
        string='Thời gian xác nhận đồng ý'
    )

    consent_expired_time = fields.Datetime(
        string='Thời gian hết hạn đồng ý'
    )

    # =====================================================
    # ĐỐI TƯỢNG GỬI / NHẬN
    # =====================================================
    sender_id = fields.Char(
        string='ID người gửi',
        index=True
    )

    sender_admin_id = fields.Char(
        string='Admin OA gửi'
    )

    recipient_id = fields.Char(
        string='ID người nhận',
        index=True
    )

    user_id_by_app = fields.Char(
        string='User ID theo App'
    )

    receiver_device = fields.Char(
        string='Thiết bị nhận'
    )

    phone = fields.Char(
        string='Số điện thoại'
    )

    # =====================================================
    # THÔNG TIN MESSAGE
    # =====================================================
    msg_id = fields.Char(
        string='Message ID',
        index=True
    )

    tracking_id = fields.Char(
        string='Tracking ID',
        index=True
    )

    message_text = fields.Text(
        string='Nội dung hiển thị'
    )

    rate = fields.Char('Điểm đánh giá')


    button_type = fields.Char(
        string='Loại nút bấm'
    )

    request_type = fields.Char(
        string='Loại yêu cầu'
    )

    # =====================================================
    # FILE / IMAGE / STICKER / LINK
    # =====================================================
    file_name = fields.Char(string='Tên file')
    file_type = fields.Char(string='Loại file')
    file_size = fields.Char(string='Dung lượng file')
    file_url = fields.Char(string='Link file')
    file_checksum = fields.Char(string='Checksum file')

    image_url = fields.Char(string='Link hình ảnh')
    image_thumbnail = fields.Char(string='Thumbnail hình ảnh')

    sticker_id = fields.Char(string='Sticker ID')
    sticker_url = fields.Char(string='Link sticker')

    link_title = fields.Char(string='Tiêu đề link')
    link_description = fields.Text(string='Mô tả link')
    link_url = fields.Char(string='Link')
    link_thumbnail = fields.Char(string='Ảnh đại diện link')
    zns_id = fields.Many2one('zns.send', string='ZNS send')
    zns_send = fields.Many2one('zns.send', string='Mã gửi ZNS')
    # =====================================================
    # RAW PAYLOAD
    # =====================================================
    raw_payload = fields.Text(
        string='Payload gốc (JSON)'
    )
    # =====================================================
    # SQL CONSTRAINT
    # =====================================================
    _sql_constraints = [
        (
            'uniq_webhook_unique_key',
            'unique(unique_key)',
            'Webhook đã tồn tại!'
        )
    ]

    # =====================================================
    # AUTO GENERATE UNIQUE KEY
    # =====================================================
    @api.model
    def create(self, vals):
        if not vals.get('unique_key'):
            vals['unique_key'] = self._generate_unique_key(vals)
        return super().create(vals)

    def _generate_unique_key(self, vals):
        """
        Sinh khóa duy nhất cho webhook
        Ưu tiên: event_name + msg_id + tracking_id + timestamp
        """
        raw = "|".join([
            vals.get('event_name') or '',
            vals.get('msg_id') or '',
            vals.get('tracking_id') or '',
            str(vals.get('timestamp') or ''),
        ])
        return hashlib.sha1(raw.encode('utf-8')).hexdigest()
