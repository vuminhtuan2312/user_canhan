from odoo import models, fields
import requests
import logging
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)

class CreateTemplateWizard(models.TransientModel):
    _name = 'create.template.wizard'
    _description = 'Wizard tạo template Zalo OA/ZNS'

    oa_id = fields.Char(string='Zalo OA ID', required=True)
    template_id = fields.Integer(string='Template ID', required=True)
    template_type = fields.Selection(
    selection=[
        ('text', 'Tin dạng văn bản'),
        ('otp', 'Tin xác thực'),
        ('table', 'Tin dạng bảng'),
        ('rating', 'Tin đánh giá'),
        ('response_button', 'Tin response button'),
        ('payment_request', 'Tin yêu cầu thanh toán'),
        ('voucher', 'Tin voucher'),
        ('custom', 'Tin tinh chỉnh'),
    ],
    string='Loại tin',
    required=True
    )
    def action_create_template(self):
        """Tạo template mới trên Zalo OA/ZNS"""
        shop_config = self.env['zalo.shop.config'].search([('active', '=', True)], limit=1)
        if not shop_config:
            raise UserError("Chưa có cấu hình Zalo Shop được kích hoạt.")

        base_url = self.env['ir.config_parameter'].sudo().get_param('zns.create_template_url')

        headers = {
            "Authorization": f"Bearer {shop_config.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        payload = {
            "oa_id": shop_config.oa_id,
            "template_id": self.template_id,
            "type": self.template_type,
        }
        try:
            _logger.info("Tạo template Zalo OA/ZNS với payload: %s", payload)
            response = requests.post(
                base_url,
                headers=headers,
                json=payload,
                timeout=15
            )
            _logger.info("Phản hồi từ Zalo OA/ZNS khi tạo template: %s - %s", response.status_code, response.text)
            response_data = response.json()
            if response.status_code == 200 and not response_data.get('error'):
                self.env['zalo.template'].save_template(response_data)
                return True
            else:
                raise ValueError(f"Lỗi khi tạo template: {response_data.get('msg')}")
        except Exception as e:
            _logger.error("Lỗi khi tạo template Zalo OA/ZNS: %s", str(e))
            raise e
