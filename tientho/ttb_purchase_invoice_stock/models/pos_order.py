from odoo import models, fields, api
from datetime import datetime, time, date, timedelta
import logging
_logger = logging.getLogger(__name__)

# Cheat tạm để không bị báo lỗi ko có trường trong model
class AccountMove(models.Model):
    _inherit = 'account.move'

    ttb_einvoice_state = fields.Selection(string='Trạng thái HĐĐT', selection=[('new', 'Chưa tạo'), ('created', 'Đã tạo hóa đơn'), ('published', 'Đã phát hành')], default='new', tracking=True)
    

class PosOrder(models.Model):
    _inherit = 'pos.order'

    ttb_einvoice_state = fields.Selection(string='Trạng thái HĐĐT', selection=[
        ('new', 'Chưa tạo'), 
        ('created', 'Đã tạo hóa đơn'), 
        ('published', 'Đã phát hành')
    ], related='account_move.ttb_einvoice_state', store=True)

    ttb_einvoice_message = fields.Text('Lỗi HĐĐT')
    reserve_picking_ids = fields.One2many('stock.picking', 'reserve_pos_order_id')

    einvoice_tracking_state = fields.Selection([
        ('on_time', 'Đúng lịch'),
        ('late', 'Xuất trễ'),  # Chưa phát hành & > 1.5h
        ('missing', 'Chưa xuất')  # Chưa phát hành & < 1.5h
    ], string='Theo dõi HĐĐT', default=False, index=True)

    einvoice_published_at = fields.Datetime(
        string='Thời điểm phát hành HĐĐT',
        compute='_compute_einvoice_published_at',
        store=True,
        readonly=True
    )

    @api.depends('ttb_einvoice_state')
    def _compute_einvoice_published_at(self):
        for order in self:
            if order.ttb_einvoice_state == 'published':
                if not order.einvoice_published_at:
                    order.einvoice_published_at = fields.Datetime.now()

    def _cron_update_einvoice_tracking(self):
        """
        Job chạy định kỳ (10 phút/lần)
        """
        now = fields.Datetime.now()
        sla_duration = timedelta(hours=1.5)

        orders = self.search([
            ('is_personalized_invoice', '=', True),
            ('state', 'not in', ['draft', 'cancel']),
            ('einvoice_tracking_state', 'in', [False, 'missing']),

        ])

        for order in orders:
            deadline = order.date_order + sla_duration
            new_state = False

            if order.ttb_einvoice_state == 'published':

                published_time = order.einvoice_published_at

                if published_time <= deadline:
                    new_state = 'on_time' # đúng lịch
                else:
                    new_state = 'late'  # Xong nhưng bị trễ
            else:
                if now > deadline:
                    new_state = 'late'  # Đã quá hạn mà vẫn chưa xong
                else:
                    new_state = 'missing'  # Chưa xong, nhưng chưa quá hạn

            if order.einvoice_tracking_state != new_state:
                order.einvoice_tracking_state = new_state

    def create_payment_auto(self, payment_methods={}, amount=None):
        # Thanh toán đơn pos. Học từ Button thanh toán trong đơn pos.
        # Button này sau đó có hàm check của model pos.make.payment
        if self.state != 'draft': return

        amount = amount or self.amount_total
        session_id = self.session_id.id
        # Lấy phương thức thanh toán
        if session_id not in payment_methods:
            payment_methods[session_id] = self.session_id.payment_method_ids.sorted(lambda pm: pm.is_cash_count, reverse=True)[:1]
        payment_method = payment_methods[session_id]

        self.add_payment({
            'pos_order_id': self.id,
            'amount': self._get_rounded_amount(amount, payment_method.is_cash_count or not self.session_id.config_id.only_round_cash_method),
            'name': 'Tự động thanh toán - xuất hoá đơn',
            'payment_method_id': payment_method.id,
        })
        self.action_pos_order_paid()

    def _cron_ttb_einvoice_state(self):
        """
        Cron job kiểm tra và gửi cảnh báo các đơn chuyển khoản quá 4h chưa xuất hóa đơn
        """
        orders = self.search([
            ('augges_no_tk', '=', '112120'),
            ('ttb_einvoice_state', '!=', 'published'),
        ])
        if not orders:
            _logger.info('Không có đơn hàng nào cần kiểm tra trạng thái HĐĐT.')
            return

        now = fields.Datetime.now()

        params = self.env['ir.config_parameter'].sudo()
        list_account_accounting = params.get_param('ttb_purchase_invoice_stock.list_account_accounting', '')
        list_account_it = params.get_param('ttb_purchase_invoice_stock.list_account_it', '')

        user_ids = []
        if list_account_accounting:
            try:
                user_ids.extend([int(uid.strip()) for uid in list_account_accounting.split(',') if uid.strip()])
            except ValueError:
                _logger.warning(f'Không thể parse list_account_accounting: {list_account_accounting}')

        if list_account_it:
            try:
                user_ids.extend([int(uid.strip()) for uid in list_account_it.split(',') if uid.strip()])
            except ValueError:
                _logger.warning(f'Không thể parse list_account_it: {list_account_it}')
        user_ids = list(set(user_ids))

        if not user_ids:
            _logger.warning('Chưa thiết lập người dùng nhận cảnh báo.')
            return

        late_order_names = []
        for order in orders:
            if now - order.create_date > timedelta(hours=4):
                late_order_names.append(order.name)

        if not late_order_names:
            _logger.info('Không có đơn chuyển khoản nào quá 4h chưa xuất hóa đơn.')
            return

        order_list_text = ', '.join(late_order_names)
        _logger.info(f'Các đơn chuyển khoản quá 4h chưa xuất hóa đơn: ({order_list_text})')

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        action_id = self.env.ref('point_of_sale.action_pos_pos_form').id
        url = f"{base_url}/web#action={action_id}&model=pos.order"

        email_body = f'''
        <div style="font-family: Arial, sans-serif; padding: 20px; background-color: #f9f9f9;">
            <div style="background-color: #fff; padding: 20px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h2 style="color: #d9534f; margin-top: 0;">
                    Cảnh báo HĐĐT: Đơn chuyển khoản quá hạn
                </h2>
                <p style="font-size: 16px; color: #333;">
                    Có <strong style="color: #d9534f;">{len(late_order_names)} đơn chuyển khoản</strong> quá 4 giờ chưa xuất hóa đơn điện tử.
                </p>
                <div style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 12px; margin: 15px 0;">
                    <strong>Danh sách đơn hàng:</strong><br/>
                    <span style="color: #856404;">{order_list_text}</span>
                </div>
                <p style="margin: 20px 0;">
                    <a href="{url}" style="display: inline-block; padding: 12px 24px; background-color: #007bff; color: #fff; text-decoration: none; border-radius: 4px; font-weight: bold;">
                        Xem danh sách đơn hàng
                    </a>
                </p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;"/>
                <p style="font-size: 12px; color: #999;">
                    Đây là email tự động từ hệ thống Odoo. Vui lòng không trả lời email này.
                </p>
            </div>
        </div>
        '''

        notification_body = f'''Cảnh báo: Có {len(late_order_names)} đơn chuyển khoản quá 4h chưa xuất hóa đơn.
Danh sách đơn hàng: <strong>{order_list_text}'''

        users = self.env['res.users'].browse(user_ids)
        partner_ids = users.mapped('partner_id').ids

        if not partner_ids:
            _logger.warning('Không tìm thấy partner nào từ danh sách user_ids.')
            return

        first_order = orders[0]

        try:
            first_order.message_post(
                body=notification_body,
                subject='Cảnh báo HĐĐT: Đơn chuyển khoản quá hạn',
                partner_ids=partner_ids,
                message_type='notification',
                subtype_xmlid='mail.mt_note'
            )
            _logger.info(f'Đã gửi thông báo trong hệ thống cho {len(partner_ids)} người dùng.')

            mail_from = self.env.user.email_formatted or self.env.user.company_id.email or 'noreply@odoo.local'

            for user in users:
                if not user.partner_id.email:
                    _logger.warning(f'User {user.name} (ID: {user.id}) không có email, bỏ qua.')
                    continue

                mail_values = {
                    'subject': f'⚠️ Cảnh báo HĐĐT: {len(late_order_names)} đơn chuyển khoản quá hạn',
                    'body_html': email_body,
                    'email_from': mail_from,
                    'email_to': user.partner_id.email,
                    'auto_delete': False,  # Không tự động xóa để có thể kiểm tra log
                }

                mail = self.env['mail.mail'].sudo().create(mail_values)
                mail.send()

            _logger.info(f'Đã gửi email cho {len([u for u in users if u.partner_id.email])} người dùng về {len(late_order_names)} đơn hàng quá hạn.')

        except Exception as e:
            _logger.error(f'Lỗi khi gửi thông báo/email: {str(e)}')
