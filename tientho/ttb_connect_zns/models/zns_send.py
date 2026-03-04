from odoo import models, fields, _, api
from odoo.exceptions import ValidationError, UserError

import logging
import re
_logger = logging.getLogger(__name__)
TABLE_CUSTOMER = "data_customer"
TABLE_rating = "data_rating"


class ZNSSend(models.Model):
    _name = 'zns.send'
    _description = 'ZNS Send SMS'

    name = fields.Char(string='Tên cơ sở', required=True)
    ttb_branch_id = fields.Many2one('ttb.branch', string='Cơ sở', required=True, readonly=True)
    store_code = fields.Char(string='Mã cơ sở', required=False, unique=True)
    order_id = fields.Many2one('pos.order', string='Đơn hàng liên kết')
    partner_id = fields.Many2one('res.partner', string='Khách hàng liên kết')
    phone = fields.Char(string='Số điện thoại nhận SMS')
    order_code = fields.Char(string='Mã đơn hàng')
    template_id = fields.Many2one('zalo.template', string='ZNS Template ID')
    msg_id = fields.Char('msg ID', readonly=True)
    template_data = fields.Text(string='Dữ liệu template')
    status = fields.Selection(
        selection=[
            ('pending', 'Chờ gửi'),
            ('user_received_message', 'Người dùng đã nhận tin'),
            ('sent', 'Người dùng phản hồi template'),
            ('failed', 'Gửi thất bại'),
            ('failed_zalo', 'Gửi đến zalo không thành công'),
        ],
        string='Trạng thái gửi',
        default='pending'
    )
    sent_at = fields.Datetime(string='Thời gian gửi', required=False)
    note = fields.Char('Ghi chú')
    response_message = fields.Text(string='Câu trả lời')
    response_json = fields.Text(string='Message lỗi')


    purchase_datetime = fields.Datetime(
        string='Thời gian mua hàng',
        tracking=True
    )

    zalo_request_datetime = fields.Datetime(
        string='Thời gian đã yêu cầu Zalo gửi',
        tracking=True
    )

    zalo_sent_datetime = fields.Datetime(
        string='Thời gian Zalo đã gửi',
        tracking=True
    )

    device_received_datetime = fields.Datetime(
        string='Thời gian thiết bị nhận được tin',
        tracking=True
    )

    first_click_datetime = fields.Datetime(
        string='Thời gian click đầu tiên',
        tracking=True
    )

    completed_datetime = fields.Datetime(
        string='Thời gian hoàn thành',
        tracking=True
    )
    day_in_week = fields.Selection(
        [
            ('0', 'Thứ Hai'),
            ('1', 'Thứ Ba'),
            ('2', 'Thứ Tư'),
            ('3', 'Thứ Năm'),
            ('4', 'Thứ Sáu'),
            ('5', 'Thứ Bảy'),
            ('6', 'Chủ Nhật'),
        ],
        string='Ngày trong tuần')
    campaign_id = fields.Many2one('period.campaign')
    time_range_text = fields.Char(
        string='Khoảng thời gian',
    )
    sender_id = fields.Char('ID sender')
    rate = fields.Char('Điểm đánh giá')
    is_upload_bizfly = fields.Boolean('Đã đẩy rating', default=False)
