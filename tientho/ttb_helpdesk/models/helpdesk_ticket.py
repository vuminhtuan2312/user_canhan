from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError

from email.policy import default


class Helpdesk(models.Model):
    _inherit = "helpdesk.ticket"

    source_channel = fields.Selection([
        ('Happy call', 'Happy call'),
        ('Facebook', 'Facebook'),
        ('Google map', 'Google map'),
        ('Hotline', 'Hotline'),
        ('Nhỡ gọi lại', 'Nhỡ gọi lại'),
        ('QR CODE', 'QR CODE'),
        ('Zalo OA', 'Zalo OA')
    ], string='Nguồn ticket', tracking=True, help="Nguồn tiếp nhận yêu cầu hỗ trợ", readonly=False)
    ticket_type = fields.Selection([
        ('Xử lý khiếu nại', 'Xử lý khiếu nại')
    ], string='Loại ticket', tracking=True, help="Loại yêu cầu hỗ trợ", default='Xử lý khiếu nại')
    user_ids = fields.Many2many('res.users', string='Người xử lý', relation='helpdesk_ticket_user_rel', default=lambda self: self.env.user)
    ttb_branch_id = fields.Many2one('ttb.branch', string='Cơ sở')
    ttb_region_id = fields.Many2one('ttb.region', string='Vùng', related='ttb_branch_id.ttb_region_id')
    ttb_description = fields.Selection([
        ('Khách hàng chưa hài lòng trong tầm kiểm soát của chi nhánh', 'Khách hàng chưa hài lòng trong tầm kiểm soát của chi nhánh'),
        ('Khách hàng chưa hài lòng ngoài tầm kiểm soát của chi nhánh', 'Khách hàng chưa hài lòng ngoài tầm kiểm soát của chi nhánh'),
        ('Tư vấn thông tin', 'Tư vấn thông tin'),
        ('Khác', 'Khác')
    ], string='Chủ đề')

    ttb_description_ids = fields.Many2many('ttb.description', string='Chủ đề', readonly=False, default=lambda self: self._default_description())
    under_control_content_ids = fields.Many2many('ttb.related.content', string='Nội dung liên quan trong tầm', domain=[('type', '=', 'under_control')], relation='ttb_ticket_under_control_content_rel')
    out_control_content_ids = fields.Many2many('ttb.related.content', string='Nội dung liên quan ngoài tầm', domain=[('type', '=', 'out_control')], relation='ttb_ticket_out_control_content_rel')
    other_control_content_ids = fields.Many2many('ttb.related.content', string='Nội dung liên quan', domain=[('type', 'in', ['other', 'consulting'])], relation='ttb_ticket_other_control_content_rel')

    show_under_control_content = fields.Boolean(compute='_show_control_description')
    show_out_control_content = fields.Boolean(compute='_show_control_description')
    show_other_control_content = fields.Boolean(compute='_show_control_description')
    order_ids = fields.Many2many('pos.order', string='Đơn hàng liên quan', compute='_compute_order_ids', store=False)

    @api.depends('partner_id')
    def _compute_order_ids(self):
        for record in self:
            if record.partner_id:
                record.order_ids = self.env['pos.order'].sudo().search([('partner_id', '=', record.partner_id.id)], limit=100)
            else:
                record.order_ids = self.env['pos.order'].sudo()

    def _default_description(self):
        under_control = self.env.ref('ttb_helpdesk.ttb_description_under_control_data', raise_if_not_found=False)
        return under_control and [under_control.id] or []
    @api.depends('ttb_description_ids')
    def _show_control_description(self):
        for record in self:
            record.show_under_control_content = 'under_control' in record.ttb_description_ids.mapped('type')
            record.show_out_control_content = 'out_control' in record.ttb_description_ids.mapped('type')
            record.show_other_control_content = 'other' in record.ttb_description_ids.mapped('type') or 'consulting' in record.ttb_description_ids.mapped('type')

    customer_description = fields.Text(string='Nội dung khách hàng phản ánh', help="Mô tả của khách hàng về vấn đề gặp phải")
    related_department_ids = fields.Many2many('hr.department', string='Bộ phận liên quan', relation='helpdesk_ticket_department_rel', domain="[('show_in_crm', '=', True)]")
    has_related_user = fields.Selection([
        ('yes', 'Có nhân viên liên quan'),
        ('no', 'Không có nhân viên liên quan')
    ], string='Nhân viên liên quan')
    related_employee_ids = fields.Many2many(
        'res.users',
        string='Nhân viên vi phạm',
        domain="[('employee_id.department_id', 'in', user_department_ids)]"
    )
    support_description = fields.Text(string='Nội dung CSKH xử lý cho khách hàng')
    attachment_ids = fields.Many2many('ir.attachment', string='Link ghi âm/ camera', relation='helpdesk_ticket_attachment_rel')

    process_ttb_branch_id = fields.Many2one('ttb.branch', string='Chi nhánh xử lý')
    branch_response = fields.Selection([
        ('Đồng thuận', 'Đồng thuận'),
        ('Không đồng thuận', 'Không đồng thuận')
    ], string='Phản hồi của chi nhánh')
    branch_attchment_ids = fields.Many2many('ir.attachment', string='Bằng chứng', relation='helpdesk_ticket_branch_attachment_rel')
    user_department_ids = fields.Many2many('hr.department', string='Bộ phận liên quan của nhân viên', relation='helpdesk_ticket_user_department_rel')
    branch_response_description = fields.Text(string='Nội dung chi nhánh phản hồi')
    cs_response = fields.Selection([
        ('Ghi nhận than phiền', 'Ghi nhận than phiền'),
        ('Loại bỏ', 'Loại bỏ')
    ], string='Phản hồi CS')
    cs_response_attachment = fields.Selection([
        ('Đủ điều kiện', 'Đủ điều kiện'),
        ('Không đủ điều kiện', 'Không đủ điều kiện'),
    ], string='CS kiểm tra bằng chứng')
    priority = fields.Selection(default='3')
    use_for = fields.Selection(related='stage_id.use_for', string='Loại giai đoạn')

    @api.onchange('ttb_branch_id')
    def _onchange_ttb_branch_id(self):
        self.process_ttb_branch_id = self.ttb_branch_id

    @api.onchange('partner_phone')
    def _onchange_partner_phone(self):
        if self.partner_phone and not self.partner_id:
            partner = self.env['res.partner'].search([('phone', '=', self.partner_phone)], limit=1)
            if partner:
                self.partner_id = partner.id

    @tools.ormcache('self.env.uid', 'self.env.su')
    def _track_get_fields(self):
        """ Return the set of tracked fields names for the current model. """
        exp_fields = ['__last_update', 'write_date', 'write_uid', 'create_date', 'create_uid', 'display_name',
                      'message_ids', 'message_main_attachment_id', 'website_message_ids', 'message_bounce', 'activity_ids',
                      'is_locked', 'noti_before_overdue', 'overdue_time',
                      ]
        model_fields = {
            name
            for name, field in self._fields.items()
            if (getattr(field, 'type', None) != 'one2many' and getattr(field, 'name', None) not in exp_fields and getattr(field, 'store', None)) or getattr(field, 'tracking', None) or getattr(field, 'track_visibility', None)
        }

        return model_fields and set(self.fields_get(model_fields))

    def default_get(self, fields):
        """ Override default_get to set default values for specific fields. """
        res = super(Helpdesk, self).default_get(fields)
        if 'name' in fields:
            res['name'] = '[TNKH-GQKN] Khách hàng phản ánh về vấn đề '
        return res

    # def _get_view(self, view_id=None, view_type='form', **options):
    #     arch, view = super()._get_view(view_id, view_type, **options)
    #     fields_data = self.fields_get(attributes=['readonly'])
    #     if view_type == 'form':
    #         for name_node in arch.xpath("//div/field"):
    #             if name_node.get('name') in fields_data and fields_data[name_node.get('name')].get('readonly'):
    #                 continue
    #             name_node.set('readonly', "not can_edit_ticket")
    #             name_node.set('force_save', "1")
    #         for name_node in arch.xpath("//group/field"):
    #             if name_node.get('name') in ['ttb_description_ids', 'source_channel']:
    #                 continue
    #             if name_node.get('name') in fields_data and fields_data[name_node.get('name')].get('readonly'):
    #                 continue
    #             name_node.set('readonly', "not can_edit_ticket")
    #             name_node.set('force_save', "1")
    #         for name_node in arch.xpath("//header/field"):
    #             if name_node.get('name') in fields_data and fields_data[name_node.get('name')].get('readonly'):
    #                 continue
    #             name_node.set('readonly', "not can_edit_ticket")
    #             name_node.set('force_save', "1")
    #     return arch, view

    happy_call_id = fields.Many2one('ttb.happy.call', string='Happy call ID', readonly=True)
    transaction_id = fields.Many2one('ttb.transaction', string='Transaction ID', readonly=True)
    internal_exchange_time = fields.Datetime(string='Thời gian trao đổi nội bộ', readonly=True)
    last_order_id = fields.Many2one('pos.order', string='Đơn hàng liên quan')
    is_locked = fields.Boolean('Khóa', default=False, readonly=True, copy=False)
    noti_before_overdue = fields.Datetime(string='Thời gian thông báo sắp trễ hạn', readonly=True, copy=False)
    overdue_time = fields.Datetime(string='Thời gian trễ hạn', readonly=True, copy=False)
    noti_overdue = fields.Datetime(string='Thời gian thông báo trễ hạn', readonly=True, copy=False)
    ticket_deadline = fields.Datetime(string='Thời gian hết hạn ticket', compute='_compute_ticket_deadline', store=True, readonly=True)

    ttb_transaction_ids = fields.One2many('ttb.transaction', compute="compute_ttb_infor_partner", string='Tuơng tác')
    ticket_ids = fields.One2many('helpdesk.ticket', compute="compute_ttb_infor_partner", string='Ticket')
    ttb_hpc_ids = fields.One2many('ttb.happy.call', compute="compute_ttb_infor_partner", string='Happycall')
    can_edit_ticket = fields.Boolean(
        compute='_compute_can_edit_ticket',
        string='Có thể chỉnh sửa',
        store=False
    )

    can_use_branch_fields = fields.Boolean(
        compute='_compute_can_use_branch_fields',
        string='Có thể dùng chi nhánh đánh giá',
        store=False
    )

    can_change_stage = fields.Boolean(
        compute="_compute_can_change_stage", store=False
    )

    @api.depends_context('uid')
    def _compute_can_change_stage(self):
        for rec in self:
            user = self.env.user
            if user.has_group('ttb_kpi.group_ttb_kpi_warehouse_manager') or user.has_group('ttb_kpi.group_ttb_kpi_warehouse_director') or user.has_group('ttb_kpi.group_ttb_kpi_warehouse_user'):
                rec.can_change_stage = False
            else:
                rec.can_change_stage = True

    @api.depends('stage_id.name')
    @api.depends_context('uid')
    def _compute_can_edit_ticket(self):
        for record in self:
            user = self.env.user

            if user.has_group('ttb_kpi.group_ttb_kpi_tnkh_manager') or user.has_group('ttb_kpi.group_ttb_kpi_tn_cskh') or user.has_group('base.group_system'):
                record.can_edit_ticket = True

            elif record.stage_id.name not in ['Hoàn thành', 'Loại bỏ', 'Đồng thuận'] and user.has_group('ttb_kpi.group_ttb_kpi_nv_cskh'):
                record.can_edit_ticket = True

            elif user.has_group('ttb_kpi.group_ttb_kpi_warehouse_manager') or user.has_group('ttb_kpi.group_ttb_kpi_warehouse_director') or user.has_group('ttb_kpi.group_ttb_kpi_warehouse_user'):
                record.can_edit_ticket = False
            else:
                record.can_edit_ticket = False

    @api.depends('stage_id.name')
    @api.depends_context('uid')
    def _compute_can_use_branch_fields(self):
        for record in self:
            user = self.env.user

            if user.has_group('ttb_kpi.group_ttb_kpi_tnkh_manager') or user.has_group('ttb_kpi.group_ttb_kpi_tn_cskh') or user.has_group('base.group_system'):
                record.can_use_branch_fields = True

            elif record.stage_id.name not in ['Hoàn thành', 'Loại bỏ', 'Đồng thuận'] and  user.has_group('ttb_kpi.group_ttb_kpi_nv_cskh'):
                record.can_use_branch_fields = True

            elif record.stage_id.name == 'Trao đổi nội bộ' and (user.has_group('ttb_kpi.group_ttb_kpi_warehouse_manager') or user.has_group('ttb_kpi.group_ttb_kpi_warehouse_director') or user.has_group('ttb_kpi.group_ttb_kpi_warehouse_user')):
                record.can_use_branch_fields = True
            else:
                record.can_use_branch_fields = False

    def action_confirm_branch_response(self):
        self.ensure_one()
        if not self.env.user.has_group('ttb_kpi.group_ttb_kpi_warehouse_user') and not self.env.user.has_group('ttb_kpi.group_ttb_kpi_warehouse_manager') and not self.env.user.has_group('ttb_kpi.group_ttb_kpi_warehouse_director'):
            raise UserError("Bạn không có quyền thực hiện hành động này.")

        if not self.branch_response:
            raise UserError("Vui lòng chọn Phản hồi của chi nhánh trước khi xác nhận.")

        stage_yes = self.env['helpdesk.stage'].search([('use_for', '=', 'Đồng thuận')], limit=1)
        stage_internal = self.env['helpdesk.stage'].search([('use_for', '=', 'Trao đổi nội bộ')], limit=1)
        if self.branch_response == 'Đồng thuận' and stage_yes:
            self.write({
                'stage_id': stage_yes.id,
                'is_locked': True
            })
            self.message_notify(
                subject=f"Chi nhánh đã xác nhận Đồng thuận",
                body=f"Chi nhánh đã xác nhận Đồng thuận đối với phiếu hỗ trợ. Vui lòng CSKH kiểm tra và tiếp tục xử lý. ",
                partner_ids=self.user_ids.mapped('partner_id').ids,
                subtype_xmlid="mail.mt_comment",
                email_layout_xmlid=False,
                email_add_signature=False
            )

        elif self.branch_response == 'Không đồng thuận' and stage_internal:
            self.write({
                'stage_id': stage_internal.id,
                'is_locked': True
            })
            self.message_notify(
                subject=f"Chi nhánh đã xác nhận Không đồng thuận",
                body=f"Chi nhánh đã xác nhận Không đồng thuận đối với phiếu hỗ trợ. Vui lòng CSKH kiểm tra và tiếp tục xử lý. ",
                partner_ids=self.user_ids.mapped('partner_id').ids,
                subtype_xmlid="mail.mt_comment",
                email_layout_xmlid=False,
                email_add_signature=False
            )
    @api.depends('partner_id')
    def compute_ttb_infor_partner(self):
        for rec in self:
            rec.ttb_transaction_ids = self.env['ttb.transaction'].search([('partner_id', '=', rec.partner_id.id)])
            rec.ticket_ids = self.env['helpdesk.ticket'].search([('partner_id', '=', rec.partner_id.id)])
            rec.ttb_hpc_ids = self.env['ttb.happy.call'].search([('partner_id', '=', rec.partner_id.id)])

    def write(self, vals):
        stage_yes = self.env['helpdesk.stage'].search([('use_for', '=', 'Đồng thuận')], limit=1)
        stage_cancel = self.env['helpdesk.stage'].search([('use_for', '=', 'Loại bỏ')], limit=1)
        stage_done = self.env['helpdesk.stage'].search([('use_for', '=', 'Hoàn thành')], limit=1)
        stage_internal = self.env['helpdesk.stage'].search([('use_for', '=', 'Trao đổi nội bộ')], limit=1)
        stage_new = self.env['helpdesk.stage'].search([('use_for', '=', 'Mới')], limit=1)
        stage_overdue = self.env['helpdesk.stage'].search([('use_for', '=', 'Trễ hạn')], limit=1)
        if 'stage_id' not in vals:
            if vals.get('branch_response') == 'Đồng thuận' and stage_yes:
                vals['stage_id'] = stage_yes.id
            if vals.get('cs_response') == 'Loại bỏ' and stage_cancel:
                vals['stage_id'] = stage_cancel.id
            if vals.get('cs_response') == 'Ghi nhận than phiền' and stage_done:
                vals['stage_id'] = stage_done.id
        is_internal_exchange = False
        is_overdue = False
        if vals.get('stage_id') and vals.get('stage_id') == stage_internal.id:
            vals['internal_exchange_time'] = fields.Datetime.now()
            is_internal_exchange = True
        if vals.get('stage_id') and vals.get('stage_id') == stage_overdue.id:
            vals['overdue_time'] = fields.Datetime.now()
            vals['noti_overdue'] = fields.Datetime.now()
            is_overdue = True
        is_done_ticket = False
        if vals.get('stage_id') and vals.get('stage_id') == stage_done.id:
            is_done_ticket = True
        if vals.get('stage_id'):
            if vals.get('stage_id') in [stage_new.id, stage_internal.id, stage_overdue.id]:
                vals['is_locked'] = False
            else:
                vals['is_locked'] = True
        res = super(Helpdesk, self).write(vals)
        if (not self._context.get('igone_check_branch')
                and not self._context.get('mail_post_autofollow')
                and not self._context.get('mail_create_nolog')
                and self.env.user.has_groups(
                    'ttb_kpi.group_ttb_kpi_warehouse_director,'
                    'ttb_kpi.group_ttb_kpi_warehouse_manager,'
                    'ttb_kpi.group_ttb_kpi_warehouse_user'
                )
                and not self.env.context.get('import_file')):

            for rec in self:
                if not rec.branch_response:
                    raise UserError('Bạn vui lòng chọn trạng thái đồng thuận/ không đồng thuận')

        if is_internal_exchange:
            self.send_notify_internal_exchange()
        if is_done_ticket:
            self.send_notify_done()
        return res

    def create(self, vals_list):
        res = super().create(vals_list)
        for rec in res:
            rec.send_notify_create()
        return res

    def cron_mark_overdue_tickets(self):
        overdue_stage = self.env['helpdesk.stage'].search([('use_for', '=', 'Trễ hạn')], limit=1)
        if not overdue_stage:
            raise UserError("Vui lòng cấu hình giai đoạn 'Trễ hạn' trong hệ thống.")

        overdue_tickets = self.search([('stage_id.use_for', '=', 'Trao đổi nội bộ'), ('internal_exchange_time', '<', fields.Datetime.now() - relativedelta(days=1))])
        if overdue_tickets:
            overdue_tickets.write({'stage_id': overdue_stage.id})

    def cron_noti_before_overdue_tickets(self):
        before_overdue_tickets = self.search([('stage_id.use_for', '=', 'Trao đổi nội bộ'), ('noti_before_overdue', '=', False), ('internal_exchange_time', '<', fields.Datetime.now() + relativedelta(days=-1, hours=3)), ('internal_exchange_time', '>', fields.Datetime.now() + relativedelta(days=-1, hours=2))])
        for ticket in before_overdue_tickets:
            noti_users = ticket.create_uid | ticket.ttb_branch_id.director_id | ticket.ttb_branch_id.manager_id
            message = f"Bạn còn 3h để xử lý ticket #{ticket.ticket_ref} {ticket.name}"
            ticket.send_notify(message, noti_users)
        before_overdue_tickets.write({'noti_before_overdue': fields.Datetime.now()})

    def cron_noti_overdue_tickets(self):
        overdue_tickets = self.search([('stage_id.use_for', '=', 'Trễ hạn'), ('noti_overdue', '<', fields.Datetime.now() - relativedelta(hours=3))])
        for ticket in overdue_tickets:
            noti_users = ticket.ttb_branch_id.director_id | ticket.ttb_branch_id.manager_id
            message = f"Ticket #{ticket.ticket_ref} {ticket.name} đã quá hạn"
            ticket.send_notify(message, noti_users)
        overdue_tickets.write({'noti_overdue': fields.Datetime.now()})

    def send_notify_internal_exchange(self):
        if not self.ttb_branch_id:
            return
        noti_users = self.ttb_region_id.director_id | self.ttb_branch_id.director_id | self.ttb_branch_id.manager_id
        message = f"Bạn có ticket cần xử lý #{self.ticket_ref} {self.name}"
        self.send_notify(message, noti_users)

    def send_notify_create(self):
        if not self.ttb_branch_id:
            return
        noti_users = self.ttb_region_id.director_id | self.ttb_branch_id.director_id | self.ttb_branch_id.manager_id
        message = f"Cơ sở bạn quản lý có 1 ticket mới #{self.ticket_ref} {self.name}"
        self.send_notify(message, noti_users)

    def send_notify_done(self):
        noti_users = self.create_uid | self.ttb_branch_id.director_id | self.ttb_branch_id.manager_id
        message = f"Ticket của bạn đã được xử lý #{self.ticket_ref} {self.name}"
        self.send_notify(message, noti_users)

    def send_notify(self, message, users, subject=''):
        if not users:
            return
        mail_template_id = 'ttb_approval.notify_record_message_template'
        for record in self:
            if not record.exists():
                continue

            rec_ctx = record.with_context(ttb_skip_comment_notify=True)
            # self.message_subscribe(partner_ids=users.mapped('partner_id').ids)
            rec_ctx.message_subscribe(partner_ids=users.mapped('partner_id').ids)
            model_description = self.env['ir.model']._get(record._name).with_context(lang=self.env.user.lang or 'vi_VN').display_name
            values = {
                'object': record,
                'model_description': model_description,
                'message': message,
                'access_link': self.env[self._name]._notify_get_action_link('view', model=record._name, res_id=record.id),
            }
            rendered_body = self.env['ir.qweb']._render(mail_template_id, values)
            if not subject:
                subject = record.display_name
            rec_ctx.message_notify(
                subject=subject,
                body=rendered_body,
                partner_ids=users.mapped('partner_id').ids,
                record_name=subject,
                subtype_xmlid='mail.mt_comment',
                email_layout_xmlid='mail.mail_notification_light',
                model_description=model_description,
                mail_auto_delete=False,
            )
            rec_ctx.message_post(
                subject=subject,
                body=rendered_body,
            )

    last_order_name = fields.Char(string='Mã đơn hàng')
    last_order_date = fields.Datetime(string='Ngày mua')
    last_order_cashier = fields.Char(string='Tên thu ngân')
    total_accumulated_points = fields.Float(related='last_order_id.total_accumulated_points')
    redeemed_accumulated_points = fields.Float(related='last_order_id.redeemed_accumulated_points')
    remaining_accumulated_points = fields.Float(related='last_order_id.remaining_accumulated_points')
    # Đè trường create_date để import migrate
    create_date = fields.Datetime(readonly=False)
    report_date = fields.Datetime('Ngày gọi', default=fields.Datetime.now)

    def action_view_partner(self):
        partner_id = self._context.get('partner_id_on_view') or self.partner_id.id
        partner = self.env['res.partner'].search([('id', '=', partner_id)])
        return {
            'type': 'ir.actions.act_window',
            'name': 'Khách hàng',
            'res_model': 'res.partner',
            'view_mode': 'form',
            'res_id': partner.id,
            'target': 'new',
        }

    ngay_phieu = fields.Date(string='Ngày phiếu', compute='_compute_ngay_phieu', store=True)

    @api.depends('create_date')
    def _compute_ngay_phieu(self):
        for rec in self:
            rec.ngay_phieu = rec.create_date.date() if rec.create_date else False

    @api.depends('internal_exchange_time')
    def _compute_ticket_deadline(self):
        for rec in self:
            if rec.internal_exchange_time:
                rec.ticket_deadline = rec.internal_exchange_time + relativedelta(days=1)
            else:
                rec.ticket_deadline = False


    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super(Helpdesk, self).fields_get(allfields=allfields, attributes=attributes)
        if 'string' in res.get('create_uid', {}):
            res['create_uid']["string"] = "Người tạo"
        if 'string' in res.get('create_date', {}):
            res['create_date']["string"] = "Ngày tạo"
        if 'string' in res.get('write_uid', {}):
            res['write_uid']["string"] = "Người cập nhật"
        if 'string' in res.get('write_date', {}):
            res['write_date']["string"] = "Ngày cập nhật"
        return res
