from odoo import models, fields, _, api
from odoo.exceptions import ValidationError
import logging
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class PeriodCampaign(models.Model):
    _name = 'period.campaign'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'ttb.approval.mixin']
    _description = 'Chiến dịch theo kỳ'

    name = fields.Char(string='Tên chiến dịch', required=True)
    start_date = fields.Datetime(string='Ngày bắt đầu', required=True)
    end_date = fields.Datetime(string='Ngày kết thúc', required=True)
    description = fields.Text(string='Mô tả chiến dịch')
    template_id = fields.Many2one('zalo.template', string='Mẫu template', tracking=True)
    manager_campaign = fields.Many2one('res.users', string='Quản lý chiến dịch', tracking=True)
    users_follow_campaign = fields.Many2many('res.users', 'res_users_period_campaign_rel', string='Người tham gia chiến dịch', tracking=True)
    state = fields.Selection(
        selection=[
            ('draft', 'Nháp'),
            ('wait_approve', 'Chờ duyệt'),
            ('approved', 'Đã duyệt'),
            ('running', 'Đang chạy'),
            ('pause', 'Tạm dừng'),
            ('completed', 'Kết thúc'),
            ('cancelled', 'Đã hủy'),

        ],
        string='Trạng thái',
        default='draft'
    )
    time_send = fields.Integer(string='Thời gian gửi tin ZNS sau mua hàng (phút)', default=60)
    product_ids = fields.Many2many('product.product', 'period_campaign_product_product_rel', string='Danh sách sản phẩm áp dụng')
    condition_run_campaign = fields.One2many('condition.to.send.zns', 'campaign_id', string='Danh sách cơ sở chạy chiến dịch')
    zns_send_ids = fields.One2many('zns.send', 'campaign_id', string='Danh sách tin ZNS')
    model_id = fields.Many2one(
        comodel_name='ir.model',
        string='Loại chứng từ',
        default=lambda self: self.env['ir.model'].sudo().search(
            [('model', '=', 'res.partner')],
            limit=1
        ), readonly=True
    )
    model = fields.Char(string='Model', related='model_id.model')
    domain = fields.Char(string='Điều kiện', default='[]')

    @api.model_create_multi
    def create(self, vals):
        record = super().create(vals)

        partners = []

        if record.manager_campaign:
            partners.append(record.manager_campaign.partner_id.id)

        if record.users_follow_campaign:
            partners += record.users_follow_campaign.mapped('partner_id').ids

        if partners:
            record.message_post(
                body="🆕 Chiến dịch mới đã được tạo",
                partner_ids=list(set(partners)),
            )

        return record

    def write(self, vals):
        for rec in self:
            old_manager = rec.manager_campaign
            old_followers = rec.users_follow_campaign

            res = super().write(vals)

            # 1. Thay đổi quản lý chiến dịch
            if 'manager_campaign' in vals:
                new_manager = rec.manager_campaign
                if new_manager and new_manager != old_manager:
                    rec.message_post(
                        body=f"👤 Quản lý chiến dịch đã được thay đổi: <b>{new_manager.name}</b>",
                        partner_ids=[new_manager.partner_id.id],
                    )

            # 2. Thêm người follow chiến dịch
            if 'users_follow_campaign' in vals:
                new_followers = rec.users_follow_campaign - old_followers
                if new_followers:
                    rec.message_post(
                        body="➕ Bạn đã được thêm vào chiến dịch",
                        partner_ids=new_followers.mapped('partner_id').ids,
                    )

        return res

    @api.constrains('start_date', 'end_date')
    def _check_date_range(self):
        for record in self:
            if record.start_date >= record.end_date:
                raise ValidationError(_("Ngày bắt đầu phải nhỏ hơn ngày kết thúc."))

    def get_approve_user_ids(self, rule):
        if rule.method not in ['manager', 'title_manager', 'mch_manager']:
            return super().get_approve_user_ids(rule)
        user_ids = self.env['res.users']
        company_domain = []
        if self.fields_get(['company_id']).get('company_id') and self.company_id:
            self = self.with_company(self.company_id)
            company_domain = ['|', ('company_id', '=', self.company_id.id), ('company_id', '=', False)]
        if rule.method == 'manager':
            user_ids = self.manager_campaign
        elif rule.method == 'title_manager':
            parent = self.manager_campaign.employee_id.parent_id
            while parent:
                if parent.job_id.id == rule.job_id.id:
                    user_ids |= parent.user_id
                parent = parent.parent_id
        return user_ids


    def action_submit_for_approval(self):
        """Hành động gửi duyệt chiến dịch"""
        self.ensure_one()
        process_id, approval_line_ids = self.get_approval_line_ids()
        self.write({'process_id': process_id.id,
                    'date_sent': fields.Datetime.now(),
                    'state': 'wait_approve',
                    'approval_line_ids': [(5, 0, 0)] + approval_line_ids})
        if self.env.user.id not in self.current_approve_user_ids.ids:
            self.send_notify(message='Bạn cần duyệt chiến dịch', users=self.manager_campaign,
                             subject='Chiến dịch duyệt giá cần duyệt')
        partners = []
        if self.manager_campaign:
            partners.append(self.manager_campaign.partner_id.id)

        if partners:
            self.message_post(
                body="📤 Chiến dịch đã được <b>gửi duyệt</b>.",
                partner_ids=partners,
            )
    def action_pause_campaign(self):
        """Hành động tạm dừng chiến dịch"""
        self.ensure_one()
        if self.state in ['draft', 'cancelled']:
            raise ValidationError(_("Chỉ có thể tạm dừng ở trạng thái khác Nháp và Hủy."))

        self.state = 'pause'

        partners = []
        if self.manager_campaign:
            partners.append(self.manager_campaign.partner_id.id)

        if partners:
            self.message_post(
                body="📤 Chiến dịch đã được <b>gửi duyệt</b>.",
                partner_ids=partners,
            )

    def action_approve_campaign(self):
        """Hành động duyệt chiến dịch"""
        self.ensure_one()
        self.state_change('approved')

        if self.state != 'wait_approve':
            raise ValidationError(_("Chỉ có thể duyệt chiến dịch đang chờ duyệt."))

        self.state = 'approved'

        partners = []

        if self.create_uid:
            partners.append(self.create_uid.partner_id.id)

        partners += self.users_follow_campaign.mapped('partner_id').ids

        if partners:
            self.message_post(
                body="✅ Chiến dịch đã được <b>phê duyệt</b>.",
                partner_ids=list(set(partners)),
            )

    def action_cancel_campaign(self):
        """Hành động hủy chiến dịch"""
        self.ensure_one()
        if self.state not in ['draft', 'wait_approve', 'approved', 'pause']:
            raise ValidationError(_("Chỉ có thể hủy chiến dịch ở trạng thái Nháp, Chờ duyệt hoặc Đã duyệt."))

        self.state = 'cancelled'

        partners = []

        if self.create_uid:
            partners.append(self.create_uid.partner_id.id)

        partners += self.users_follow_campaign.mapped('partner_id').ids

        if partners:
            self.message_post(
                body="⛔ Chiến dịch đã bị <b>hủy</b>.",
                partner_ids=list(set(partners)),
            )

    def action_refuse_campaign(self):
        """Hành động từ chối chiến dịch"""
        self.ensure_one()
        self.state_change('rejected')
        if self.rule_line_ids.search([('notif_only', '=', False), ('res_id', 'in', self.ids), ('res_model', '=', self._name)], order='sequence asc', limit=1).state == 'rejected':
            self.sudo().write({'state': 'draft'})

        if self.create_uid:
            self.message_post(
                body="❌ Chiến dịch đã bị <b>từ chối</b> và quay về trạng thái Nháp.",
                partner_ids=[self.create_uid.partner_id.id],
            )

    def action_start_campaign(self):
        """Hành động bắt đầu chiến dịch"""
        self.ensure_one()
        partners = []
        if self.manager_campaign:
            partners.append(self.manager_campaign.partner_id.id)

        partners += self.users_follow_campaign.mapped('partner_id').ids

        self.message_post(
            body="🚀 Chiến dịch đã được khởi động",
            partner_ids=list(set(partners)),
        )
        self.state = 'running'

    def cron_job_auto_start_campaign(self):
        """Tự động start Chiến dịch khi đến ngày bắt đầu và chiến dịch ở trạng thái đã duyệt"""
        now = fields.Datetime.now()

        campaigns = self.search([
            ('state', '=', 'approved'),
            ('start_date', '<=', now),
        ])

        for campaign in campaigns:
            campaign.write({
                'state': 'running'
            })

    def cron_job_auto_finish_campaign(self):
        """
        Tự động hoàn thành Chiến dịch khi:
        - Đến ngày kết thúc (date_end)
        - Chiến dịch đang ở trạng thái running
        """
        now = fields.Datetime.now()

        campaigns = self.search([
            ('state', '=', 'running'),
            ('end_date', '!=', False),
            ('end_date', '<=', now),
        ])

        for campaign in campaigns:
            campaign.write({
                'state': 'completed'
            })

        if campaigns:
            _logger.info(
                "[CRON] Auto finished %s campaign(s)",
                len(campaigns)
            )