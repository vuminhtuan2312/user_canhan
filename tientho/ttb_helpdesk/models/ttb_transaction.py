from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError


class TTBTransaction(models.Model):
    _name = 'ttb.transaction'
    _description = 'Tương tác'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Tên Tương tác', required=True, copy=False, default=lambda self: self.env['ir.sequence'].next_by_code('seq.ttb.transaction'))
    state = fields.Selection([
        ('draft', 'Mới'),
        ('follow', 'Theo dõi'),
        ('done', 'Hoàn thành'),
    ], string='Trạng thái', default='draft', required=True)
    partner_phone = fields.Char(string='Số điện thoại')
    partner_name = fields.Char(string='Tên khách hàng', required=True)
    partner_id = fields.Many2one('res.partner', string='Khách hàng', required=False)
    ttb_branch_id = fields.Many2one('ttb.branch', string='Cơ sở', required=True)
    order_ids = fields.Many2many('pos.order', string='Đơn hàng liên quan', compute='_compute_order_ids', store=False)
    last_order_id = fields.Many2one('pos.order', string='Đơn hàng gần nhất', compute='_compute_last_order_id', store=True)
    last_order_line_ids = fields.Many2many('pos.order.line', string='Chi tiết Đơn hàng gần nhất', compute='_compute_last_order_line_ids')
    last_order_name = fields.Char(string='Mã đơn hàng', related='last_order_id.name')
    last_order_date = fields.Datetime(string='Ngày mua', related='last_order_id.date_order')
    last_order_account_move = fields.Many2one('account.move', string='Số hóa đơn', related='last_order_id.account_move')
    last_order_cashier = fields.Char(string='Tên thu ngân', related='last_order_id.cashier')
    last_order_amount_total = fields.Float(string='Tổng tiền', related=False, compute='_compute_last_order', currency_field='last_order_currency_id', store=True)
    last_order_currency_id = fields.Many2one(related='last_order_id.currency_id')
    # Đè trường create_date để migrate
    create_date = fields.Datetime(readonly=False)
    report_date = fields.Datetime('Ngày gọi', default=fields.Datetime.now)
    voip_call_id = fields.Many2one('voip.call', string='Lịch sử cuộc gọi', readonly=1)
    recording_link = fields.Char(string="File ghi âm", related='voip_call_id.recording_link')

    def get_recording_link(self):
        for rec in self:
            rec.voip_call_id.get_recording_link()

    @api.depends('last_order_id')
    def _compute_last_order(self):
        for rec in self:
            rec.last_order_amount_total = rec.last_order_id.amount_total

    @api.depends('partner_id')
    def _compute_last_order_id(self):
        for rec in self:
            if rec.partner_id:
                rec.last_order_id = self.env['pos.order'].search(
                    [('partner_id', '=', rec.partner_id.id), ('state', 'in', ['paid', 'done'])],
                    order='date_order desc', limit=1)
            else:
                rec.last_order_id = False

    @api.depends('last_order_id')
    def _compute_last_order_line_ids(self):
        for rec in self:
            rec.last_order_line_ids = rec.last_order_id.lines

    @api.depends('partner_id')
    def _compute_order_ids(self):
        for record in self:
            if record.partner_id:
                record.order_ids = self.env['pos.order'].search([('partner_id', '=', record.partner_id.id)], limit=100)
            else:
                record.order_ids = self.env['pos.order']

    @api.onchange('partner_phone')
    def _onchange_partner_phone(self):
        if self.partner_phone and not self.partner_id:
            partner = self.env['res.partner'].search([('phone', '=', self.partner_phone)], limit=1)
            if partner:
                self.partner_id = partner.id

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.partner_phone = self.partner_id.phone
            self.partner_name = self.partner_id.name

    user_id = fields.Many2one('res.users', string='Nhân viên', default=lambda self: self.env.user)
    department_id = fields.Many2one('hr.department', string='Bộ phận')

    @api.onchange('user_id')
    def _onchange_user_id(self):
        if self.user_id:
            self.department_id = self.user_id.employee_id.department_id

    source_channel = fields.Selection([
        ('Facebook', 'Facebook'),
        ('Google map', 'Google map'),
        ('Hotline', 'Hotline'),
        ('Nhỡ gọi lại', 'Nhỡ gọi lại'),
        ('QR CODE', 'QR CODE'),
        ('Zalo OA', 'Zalo OA')
    ], string='Nguồn call', required=True)
    ttb_description = fields.Selection([
        ('Khách hàng chưa hài lòng trong tầm kiểm soát của chi nhánh', 'Khách hàng chưa hài lòng trong tầm kiểm soát của chi nhánh'),
        ('Khách hàng chưa hài lòng ngoài tầm kiểm soát của chi nhánh', 'Khách hàng chưa hài lòng ngoài tầm kiểm soát của chi nhánh'),
        ('Tư vấn thông tin', 'Tư vấn thông tin'),
        ('Khác', 'Khác')
    ], string='Chủ đề')
    ttb_description_ids = fields.Many2many('ttb.description', string='Chủ đề', required=True)
    under_control_content_ids = fields.Many2many('ttb.related.content', string='Nội dung liên quan trong tầm', domain=[('type', '=', 'under_control')], relation='ttb_transaction_under_control_content_rel')
    out_control_content_ids = fields.Many2many('ttb.related.content', string='Nội dung liên quan ngoài tầm', domain=[('type', '=', 'out_control')], relation='ttb_transaction_out_control_content_rel')
    other_control_content_ids = fields.Many2many('ttb.related.content', string='Nội dung liên quan', domain=[('type', 'in', ['other', 'consulting'])], relation='ttb_transaction_other_control_content_rel')

    show_under_control_content = fields.Boolean(compute='_show_control_description')
    show_out_control_content = fields.Boolean(compute='_show_control_description')
    show_other_control_content = fields.Boolean(compute='_show_control_description')

    @api.depends('ttb_description_ids')
    def _show_control_description(self):
        for record in self:
            record.show_under_control_content = 'under_control' in record.ttb_description_ids.mapped('type')
            record.show_out_control_content = 'out_control' in record.ttb_description_ids.mapped('type')
            record.show_other_control_content = 'other' in record.ttb_description_ids.mapped('type') or 'consulting' in record.ttb_description_ids.mapped('type')

    partner_comment = fields.Text(string='Khách hàng chia sẻ', required=True)
    user_comment = fields.Text(string='Hướng xử lý cho khách hàng', required=True)

    has_related_user = fields.Selection([
        ('yes', 'Có nhân viên liên quan'),
        ('no', 'Không có nhân viên liên quan')
    ], string='Nhân viên liên quan')
    related_department_ids = fields.Many2many('hr.department', string='Bộ phận liên quan', required=True, domain="[('show_in_crm', '=', True)]")
    ttb_transaction_ids = fields.Many2many('ttb.transaction', string='Lịch sử tuơng tác', compute='_get_ttb_transaction_ids')

    @api.depends('partner_id')
    def _get_ttb_transaction_ids(self):
        for rec in self:
            rec.ttb_transaction_ids = rec.partner_id.ttb_transaction_ids - rec

    @api.onchange('partner_phone')
    def _onchange_partner_phone(self):
        for rec in self:
            if rec.partner_phone:
                phone = rec.partner_phone.replace(' ', '').replace('+', '').replace('-', '')
                if phone.startswith('84') and len(phone) >= 10:
                    phone = '0' + phone[2:]
                rec.partner_phone = phone

    @api.constrains('partner_phone')
    def _check_partner_phone(self):
        for rec in self:
            phone = rec.partner_phone
            if phone:
                phone = phone.replace(' ', '').replace('+', '').replace('-', '')
                if phone.startswith('84') and len(phone) >= 10:
                    phone = '0' + phone[2:]
                if not phone.isdigit():
                    raise UserError(_('Số điện thoại chỉ được chứa các chữ số.'))
                if len(phone) != 10:
                    raise UserError(_('Số điện thoại phải gồm đúng 10 chữ số.'))
                if not phone.startswith('0'):
                    raise UserError(_('Số điện thoại phải bắt đầu bằng số 0.'))

    @tools.ormcache('self.env.uid', 'self.env.su')
    def _track_get_fields(self):
        """ Return the set of tracked fields names for the current model. """
        exp_fields = ['__last_update', 'write_date', 'write_uid', 'create_date', 'create_uid', 'display_name',
                      'message_ids', 'message_main_attachment_id', 'website_message_ids', 'message_bounce', 'activity_ids']
        model_fields = {
            name
            for name, field in self._fields.items()
            if (getattr(field, 'type', None) != 'one2many' and getattr(field, 'name', None) not in exp_fields and getattr(field, 'store', None)) or getattr(field, 'tracking', None) or getattr(field, 'track_visibility', None)
        }

        return model_fields and set(self.fields_get(model_fields))

    def action_create_ticket(self):
        self.ensure_one()
        ticket = self.env['helpdesk.ticket'].search([('transaction_id', '=', self.id)], limit=1)
        if not ticket:
            under_control_desc = self.ttb_description_ids.filtered(lambda d: d.type == 'under_control')
            under_control_content = self.under_control_content_ids
            vals = {
                'transaction_id': self.id,
                'partner_id': self.partner_id.id,
                'source_channel': self.source_channel,
                'ttb_branch_id': self.ttb_branch_id.id,
                'ttb_description_ids': [(6, 0, under_control_desc.ids)],
                'under_control_content_ids': [(6, 0, under_control_content.ids)],
                'customer_description': self.partner_comment,
                'related_department_ids': [(6, 0, self.related_department_ids.ids)],
                'has_related_user': self.has_related_user,
                'related_employee_ids': False,
                'support_description': self.user_comment,
            }
            ticket = self.env['helpdesk.ticket'].with_context(igone_check_branch=True).create(vals)
        return ticket

    @api.model_create_multi
    def create(self, vals_list):
        records = super(TTBTransaction, self).create(vals_list)
        for rec in records:
            if not rec.partner_id:
                rec.partner_id = self.env['res.partner'].sudo().create({
                    'name': rec.partner_name,
                    'phone': rec.partner_phone,
                })
            if rec.show_under_control_content:
                rec.action_create_ticket()
        return records

    def write(self, vals):
        check_show_under_control_content = False
        if vals.get('ttb_description_ids'):
            check_show_under_control_content = True
        res = super(TTBTransaction, self).write(vals)
        if check_show_under_control_content:
            for rec in self:
                if rec.show_under_control_content:
                    rec.action_create_ticket()
        return res

    def action_view_partner(self):
        partner_id = self._context.get('partner_id_on_view') or self.partner_id.id
        partner = self.env['res.partner'].search([('id', '=', partner_id)])
        return {
            'type': 'ir.actions.act_window',
            'name': 'Khách hàng',
            'res_model': 'res.partner',
            'view_mode': 'form',
            'res_id': partner.id,
            'target': 'target',
        }

    ngay_phieu = fields.Date(string='Ngày phiếu', compute='_compute_ngay_phieu', store=True)

    @api.depends('create_date')
    def _compute_ngay_phieu(self):
        for rec in self:
            rec.ngay_phieu = rec.create_date.date() if rec.create_date else False

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super(TTBTransaction, self).fields_get(allfields=allfields, attributes=attributes)
        if 'string' in res.get('create_uid', {}):
            res['create_uid']["string"] = "Người tạo"
        if 'string' in res.get('create_date', {}):
            res['create_date']["string"] = "Ngày tạo"
        if 'string' in res.get('write_uid', {}):
            res['write_uid']["string"] = "Người cập nhật"
        if 'string' in res.get('write_date', {}):
            res['write_date']["string"] = "Ngày cập nhật"
        return res
