from odoo import models, fields, _
import requests
import logging
from datetime import datetime
from odoo.exceptions import UserError
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ZaloTemplate(models.Model):
    _name = 'zalo.template'
    _description = 'Zalo OA Template'
    _rec_name = 'template_name'
    _order = 'updated_at desc'

    template_id = fields.Integer(
        string='Mã Template Zalo',
        required=True,
        index=True,
        readonly=True
    )

    template_name = fields.Char(
        string='Tên Template',
        required=True,
        readonly=True

    )

    type = fields.Selection(
        selection=[
            ('text', 'Tin dạng văn bản'),
            ('otp', 'Tin xác thực'),
            ('table', 'Tin dạng bảng'),
            ('rating', 'Tin đánh giá'),
            ('response_button', 'Tin phản hồi (Response Button)'),
            ('payment_request', 'Tin yêu cầu thanh toán'),
            ('voucher', 'Tin voucher'),
            ('custom', 'Tin tuỳ chỉnh'),
        ],
        string='Loại Template',
        readonly=True

    )

    timeout = fields.Integer(
        string='Thời gian hiệu lực (giây)',
        readonly=True

    )

    price = fields.Integer(
        string='Giá gửi tin',
        readonly=True

    )

    price_exceeded = fields.Integer(
        string='Giá vượt hạn mức',
        readonly=True

    )

    retail_price = fields.Integer(
        string='Giá bán lẻ',
        readonly=True

    )

    preview_url = fields.Char(
        string='Link xem trước Template',
        readonly=True

    )

    template_status = fields.Selection(
        selection=[
            ('ENABLE', 'Đang hoạt động'),
            ('DISABLE', 'Ngừng hoạt động'),
            ('PENDING', 'Chờ duyệt'),
            ('REJECT', 'Bị từ chối'),
        ],
        string='Trạng thái Template',
        readonly=True

    )

    template_quality = fields.Selection(
        selection=[
            ('unknown', 'Chưa đánh giá'),
            ('good', 'Tốt'),
            ('normal', 'Trung bình'),
            ('bad', 'Kém'),
        ],
        string='Chất lượng Template',
        readonly=True

    )

    template_tag = fields.Selection(
        selection=[
            ('unknown', 'Không xác định'),
            ('utility', 'Thông báo'),
            ('promotion', 'Khuyến mãi'),
            ('care', 'Chăm sóc khách hàng'),
        ],
        string='Nhóm Template',
        readonly=True

    )

    apply_template_quota = fields.Boolean(
        string='Áp dụng hạn mức gửi',
        readonly=True

    )

    template_daily_quota = fields.Integer(
        string='Hạn mức gửi mỗi ngày',
        readonly=True

    )

    template_remaining_quota = fields.Integer(
        string='Số lượt gửi còn lại',
        readonly=True

    )

    is_journey = fields.Boolean(
        string='Thuộc hành trình (Journey)',
        readonly=True

    )

    token_type = fields.Char(
        string='Loại Token',
        readonly=True

    )

    ref_param = fields.Char(
        string='Tham số tham chiếu',
        readonly=True

    )

    created_at = fields.Datetime(
        string='Ngày tạo trên Zalo',
        readonly=True

    )

    updated_at = fields.Datetime(
        string='Ngày cập nhật trên Zalo',
        readonly=True

    )
    template_param_ids = fields.One2many(
        'param.mapping',
        'template_id_ref',
        string='Template Params',
        readonly=False

    )
    default_template = fields.Boolean(
        string='Mặc định',
        default=False,
    help='Khi gửi tin nhắn ZNS, nếu không chọn template thì sẽ sử dụng template này.'
    )
    oa_id = fields.Char(
        string='Zalo OA ID',
        required=False,
        readonly=True

    )
    shop_id = fields.Char(
        string='Zalo Shop ID',
        required=False,
        readonly=True

    )
    _sql_constraints = [
        ('template_id_unique',
         'unique(template_id)',
         'Template ID must be unique!')
    ]
    def save_templates(self, response_json):
        TemplateParam = self.env['param.mapping'].sudo()

        templates = response_json.get('templates', [])
        if not templates:
            return

        for tpl in templates:
            record = self.search([
                ('template_id', '=', tpl.get('template_id'))
            ], limit=1)

            vals = {
                # ===== IDENTIFIER =====
                'template_id': tpl.get('template_id'),
                'template_name': tpl.get('template_name'),
                'oa_id': tpl.get('oa_id'),
                'shop_id': tpl.get('shop_id'),

                # ===== TYPE & STATUS =====
                'type': tpl.get('type'),
                'template_status': tpl.get('template_status'),
                'template_quality': tpl.get('template_quality'),
                'template_tag': tpl.get('template_tag'),

                # ===== PRICE =====
                'price': tpl.get('price'),
                'price_exceeded': tpl.get('price_exceeded'),
                'retail_price': tpl.get('retail_price'),

                # ===== QUOTA =====
                'apply_template_quota': tpl.get('apply_template_quota'),
                'template_daily_quota': tpl.get('template_daily_quota'),
                'template_remaining_quota': tpl.get('template_remaining_quota'),

                # ===== OTHER INFO =====
                'timeout': tpl.get('timeout'),
                'preview_url': tpl.get('preview_url'),
                'is_journey': tpl.get('is_journey'),
                'token_type': tpl.get('token_type'),
                'ref_param': tpl.get('ref_param'),

                # ===== TIME =====
                'created_at': tpl.get('created_at'),
                'updated_at': tpl.get('updated_at'),
            }
            updated_at = tpl.get('updated_at')
            created_at = tpl.get('created_at')
            if created_at:
                raw = created_at
                dt = datetime.strptime(raw, '%Y-%m-%dT%H:%M:%S.%fZ')
                vals['created_at'] = fields.Datetime.to_string(dt)
            if updated_at:
                raw = updated_at
                dt = datetime.strptime(raw, '%Y-%m-%dT%H:%M:%S.%fZ')
                vals['updated_at'] = fields.Datetime.to_string(dt)
            if record:
                record.write(vals)
                record.template_param_ids.unlink()
            else:
                record = self.create(vals)
            # xử lý template_params (list)
            for p in tpl.get('template_params', []):
                TemplateParam.create({
                    'template_id_ref': record.id,
                    'name': p.get('name'),
                    'type': p.get('type'),
                    'require': bool(p.get('require')),
                    'accept_null': bool(p.get('accept_null')),
                })

    def save_template(self, response_json):
        TemplateParam = self.env['param.mapping'].sudo()


        record = self.search([
            ('template_id', '=', response_json.get('template_id'))
        ], limit=1)

        vals = {
            # ===== IDENTIFIER =====
            'template_id': response_json.get('template_id'),
            'template_name': response_json.get('template_name'),
            'oa_id': response_json.get('oa_id'),
            'shop_id': response_json.get('shop_id'),

            # ===== TYPE & STATUS =====
            'type': response_json.get('type'),
            'template_status': response_json.get('template_status'),
            'template_quality': response_json.get('template_quality'),
            'template_tag': response_json.get('template_tag'),

            # ===== PRICE =====
            'price': response_json.get('price'),
            'price_exceeded': response_json.get('price_exceeded'),
            'retail_price': response_json.get('retail_price'),

            # ===== QUOTA =====
            'apply_template_quota': response_json.get('apply_template_quota'),
            'template_daily_quota': response_json.get('template_daily_quota'),
            'template_remaining_quota': response_json.get('template_remaining_quota'),

            # ===== OTHER INFO =====
            'timeout': response_json.get('timeout'),
            'preview_url': response_json.get('preview_url'),
            'is_journey': response_json.get('is_journey'),
            'token_type': response_json.get('token_type'),
            'ref_param': response_json.get('ref_param'),

            # ===== TIME =====
            'created_at': response_json.get('created_at'),
            'updated_at': response_json.get('updated_at'),
        }
        updated_at = response_json.get('updated_at')
        created_at = response_json.get('created_at')
        if created_at:
            raw = created_at
            dt = datetime.strptime(raw, '%Y-%m-%dT%H:%M:%S.%fZ')
            vals['created_at'] = fields.Datetime.to_string(dt)
        if updated_at:
            raw = updated_at
            dt = datetime.strptime(raw, '%Y-%m-%dT%H:%M:%S.%fZ')
            vals['updated_at'] = fields.Datetime.to_string(dt)
        if record:
            record.write(vals)
            record.template_param_ids.unlink()
        else:
            record = self.create(vals)
        # xử lý template_params (list)
        for p in response_json.get('template_params', []):
            TemplateParam.create({
                'template_id_ref': record.id,
                'name': p.get('name'),
                'type': p.get('type'),
                'require': bool(p.get('require')),
                'accept_null': bool(p.get('accept_null')),
            })

    def update_template(self):
        """Cập nhật thông tin template từ Zalo OA/ZNS"""
        shop_config = self.env['zalo.shop.config'].search([('active', '=', True)], limit=1)
        if not shop_config:
            raise UserError("Chưa có cấu hình Zalo Shop được kích hoạt.")

        base_url = self.env['ir.config_parameter'].sudo().get_param('zns.get_template_detail_url')

        headers = {
            "Authorization": f"Bearer {shop_config.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        payload = {
            "oa_id": shop_config.oa_id,
            "template_id": self.template_id,
        }
        try:
            _logger.info("Cập nhật template Zalo OA/ZNS với payload: %s", payload)
            response = requests.post(
                base_url,
                headers=headers,
                json=payload,
                timeout=15
            )
            _logger.info("Phản hồi từ Zalo OA/ZNS khi cập nhật template: %s - %s", response.status_code, response.text)
            response_data = response.json()
            if response.status_code == 200 and not response_data.get('error'):
                self.env['zalo.template'].save_templates(response_data)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Thành công',
                        'message': 'Cập nhật template thành công.',
                        'sticky': False,
                    }
                }
            else:
                raise ValueError(f"Lỗi khi cập nhật template: {response_data.get('message')}")
        except Exception as e:
            _logger.error("Lỗi khi cập nhật template Zalo OA/ZNS: %s", str(e))
            raise e

    def action_get_templates(self):
        zalo_config = self.env['zalo.shop.config'].search([('active', '=', True)], limit=1).action_get_templates()

    def action_create_template_wizard(self):
        """Mở wizard tạo template Zalo OA/ZNS"""
        return {
            'name': _('Tạo Template Zalo OA/ZNS'),
            'type': 'ir.actions.act_window',
            'res_model': 'create.template.wizard',
            'view_mode': 'form',
            'target': 'new',
        }

    def _get_value_from_mapping(self, record, mapping_key):
        value = record
        for attr in mapping_key.split('.'):
            if not value:
                return False
            if not hasattr(value, attr):
                raise AttributeError(attr)
            value = getattr(value, attr)
        return value

    def action_check_mapping_key(self):
        PosOrder = self.env['pos.order']

        # Lấy 1 order mẫu để test
        order = PosOrder.search([], limit=1)
        if not order:
            raise UserError(_("Không có pos.order nào để kiểm tra"))

        for template in self:
            errors = []

            for param in template.template_param_ids:
                if not param.mapping_key:
                    continue

                mapping_key = param.mapping_key.strip()
                # Thử lấy giá trị từ order
                try:
                    value = template._get_value_from_mapping(order, mapping_key)
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
