from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
import re

class TTBHappyCall(models.Model):
    _name = 'ttb.happy.call'
    _description = 'Happy Call'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Tên Happy Call', required=True)

    state = fields.Selection([
        ('to_call', 'Cần gọi'),
        ('success', 'HPC thành công'),
        ('refuse', 'Từ chối phỏng vấn'),
        ('wrong_number', 'Sai số khách hàng báo'),
        ('follow_up', 'Theo dõi'),
        ('no_contact', 'Không liên lạc được'),
        ('no_answer', 'Không nghe máy'),
    ], string='Trạng thái', default='to_call', required=True)

    partner_phone = fields.Char(string='Số điện thoại', required=True)
    partner_id = fields.Many2one('res.partner', string='Khách hàng')
    ttb_branch_id = fields.Many2one('ttb.branch', string='Cơ sở', compute='_compute_branch_id', store=True, readonly=False)
    is_partner_phone_update = fields.Boolean(compute='_compute_is_partner_phone_update', export_string_translation=False)
    # Thiện bỏ readonly để import được. Cho readonly ở xml
    execution_date = fields.Datetime(string='Ngày thực hiện', readonly=False, copy=False)
    last_happy_call_id = fields.Many2one(
        comodel_name='ttb.happy.call',
        string="Happy call gần nhất",
        compute='_compute_last_happy_call_info',
        store=False
    )
    last_happy_call_state = fields.Char(
        string="Trạng thái cuộc gọi gần nhất",
        compute="_compute_last_happy_call_info"
    )
    last_happy_call_date = fields.Datetime(
        string="Ngày gọi gần nhất",
        compute="_compute_last_happy_call_info"
    )
    phone_masked = fields.Char(compute="_compute_phone_masked")

    @api.depends('partner_phone')
    def _compute_phone_masked(self):
        for rec in self:
            if rec.partner_phone:
                clean_phone = re.sub(r'\D', '', rec.partner_phone)
                if len(clean_phone) > 3:
                    rec.phone_masked = '*' * (len(clean_phone) - 3) + clean_phone[-3:]
                else:
                    rec.phone_masked = '*' * len(clean_phone)
            else:
                rec.phone_masked = False
    def _compute_last_happy_call_info(self):
        for rec in self:
            last_call = self.env['ttb.happy.call'].search(
                [('partner_id', '=', rec.partner_id.id), ('id', '!=', rec.id)],
                order="create_date desc", limit=1
            )
            rec.last_happy_call_id = last_call or False
            rec.last_happy_call_state = dict(last_call._fields['state'].selection).get(last_call.state) if last_call else False
            rec.last_happy_call_date = last_call.create_date if last_call else False

    @api.depends('last_order_id')
    def _compute_branch_id(self):
        for rec in self:
            rec.ttb_branch_id = rec.last_order_id.ttb_branch_id

    def _get_partner_phone_update(self):
        self.ensure_one()
        if self.partner_id.phone and self.partner_phone and self.partner_phone != self.partner_id.phone:
            call_phone_formatted = self.partner_phone or False
            partner_phone_formatted = self.partner_id.phone or False
            return call_phone_formatted != partner_phone_formatted
        return False

    @api.depends('partner_phone', 'partner_id')
    def _compute_is_partner_phone_update(self):
        for call in self:
            call.is_partner_phone_update = call._get_partner_phone_update()

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

    order_ids = fields.Many2many('pos.order', string='Đơn hàng liên quan', compute='_compute_order_ids')

    @api.depends('partner_id')
    def _compute_order_ids(self):
        for record in self:
            if record.partner_id:
                record.order_ids = self.env['pos.order'].sudo().search([('partner_id', '=', record.partner_id.id)], limit=100)
            else:
                record.order_ids = self.env['pos.order'].sudo()

    has_related_user = fields.Selection([
        ('yes', 'Có nhân viên liên quan'),
        ('no', 'Không có nhân viên liên quan')
    ], string='Nhân viên liên quan')
    related_employee_ids = fields.Many2many('res.users', string='Nhân viên liên quan')
    user_id = fields.Many2one('res.users', string='Nhân viên xử lý', default=lambda self: self.env.user)

    question_ids = fields.Many2many('survey.question', string='Trải nghiệm mua sắm mới')

    shopping_experience = fields.Selection([
        ('Rất hài lòng', 'Rất hài lòng'),
        ('Hài lòng', 'Hài lòng'),
        ('Bình thường', 'Bình thường'),
        ('Không hài lòng', 'Không hài lòng'),
    ], string='Trải nghiệm mua sắm')
    introduce_to_others = fields.Selection([
        ('Rất sẵn lòng', 'Rất sẵn lòng'),
        ('Sẵn lòng', 'Sẵn lòng'),
        ('Cân nhắc/ Thụ động', 'Cân nhắc/ Thụ động'),
        ('Không sẵn lòng', 'Không sẵn lòng'),
    ], string='Giới thiệu Tiến Thọ với người khác')
    improvement_suggestions = fields.Text(string='Tiến Thọ cải tiến vấn đề')
    ttb_area_ids = fields.Many2many('ttb.area', string='Khu vực', domain="[('show_in_crm', '=', True)]")
    ttb_description = fields.Selection([
        ('Khách hàng chưa hài lòng trong tầm kiểm soát của chi nhánh', 'Khách hàng chưa hài lòng trong tầm kiểm soát của chi nhánh'),
        ('Khách hàng chưa hài lòng ngoài tầm kiểm soát của chi nhánh', 'Khách hàng chưa hài lòng ngoài tầm kiểm soát của chi nhánh'),
        ('Tư vấn thông tin', 'Tư vấn thông tin'),
        ('Khác', 'Khác')
    ], string='Chủ đề')
    ttb_description_ids = fields.Many2many('ttb.description', string='Chủ đề')
    under_control_content_ids = fields.Many2many('ttb.related.content', string='Nội dung liên quan trong tầm', domain=[('type', '=', 'under_control')], relation='ttb_happy_call_under_control_content_rel')
    out_control_content_ids = fields.Many2many('ttb.related.content', string='Nội dung liên quan ngoài tầm', domain=[('type', '=', 'out_control')], relation='ttb_happy_call_out_control_content_rel')
    other_control_content_ids = fields.Many2many('ttb.related.content', string='Nội dung liên quan', domain=[('type', 'in', ['other', 'consulting'])], relation='ttb_happy_call_other_control_content_rel')

    show_under_control_content = fields.Boolean(compute='_show_control_description')
    show_out_control_content = fields.Boolean(compute='_show_control_description')
    show_other_control_content = fields.Boolean(compute='_show_control_description')

    shopping_experience_note = fields.Char(
        string="Ghi chú Trải nghiệm mua sắm",
        readonly=True,
        default='Trải nghiệm mua sắm gần đây của bạn thế nào?',
    )
    introduce_to_others_note = fields.Char(
        string="Ghi chú Giới thiệu Tiến Thọ với người khác",
        readonly=True,
        default='Trải nghiệm mua sắm gần đây của bạn thế nào?',
    )
    improvement_suggestions_note = fields.Char(
        string="Ghi chú Tiến Thọ cải tiến vấn đề",
        readonly=True,
        default='Trải nghiệm mua sắm gần đây của bạn thế nào?',
    )

    @api.model
    def default_get(self, fields_list):
        res = super(TTBHappyCall, self).default_get(fields_list)
        settings = self.env['helpdesk.settings'].search([], limit=1)
        if settings:
            res.update({
                'shopping_experience_note': settings.shopping_experience_note or res.get('shopping_experience_note'),
                'introduce_to_others_note': settings.introduce_to_others_note or res.get('introduce_to_others_note'),
                'improvement_suggestions_note': settings.improvement_suggestions_note or res.get('improvement_suggestions_note'),
            })
        return res

    @api.depends('ttb_description_ids')
    def _show_control_description(self):
        for record in self:
            record.show_under_control_content = 'under_control' in record.ttb_description_ids.mapped('type')
            record.show_out_control_content = 'out_control' in record.ttb_description_ids.mapped('type')
            record.show_other_control_content = 'other' in record.ttb_description_ids.mapped('type') or 'consulting' in record.ttb_description_ids.mapped('type')

    range_type = fields.Selection([
        ('Ngoài tầm vi phạm nhẹ', 'Ngoài tầm vi phạm nhẹ'),
        ('Ngoài tầm vi phạm nặng', 'Ngoài tầm vi phạm nặng'),
    ], string='Phân loại')

    noti_partner = fields.Selection([
        ('Khách hàng chưa hài lòng với kết quả xử lý', 'Khách hàng chưa hài lòng với kết quả xử lý'),
        ('Khách hàng cân nhắc', 'Khách hàng cân nhắc'),
        ('Khách hàng hài lòng với kết quả xử lý', 'Khách hàng hài lòng với kết quả xử lý')
    ], string='Thông báo lại khách hàng sau khi giải quyết phàn nàn')

    rating_customer = fields.Selection([
        ('Rất hài lòng', 'Rất hài lòng'),
        ('Hài lòng', 'Hài lòng'),
        ('Bình thường', 'Bình thường'),
        ('Chưa hài lòng', 'Chưa hài lòng')
    ], string='Hài lòng với NV CSKH giải quyết khiếu nại')

    last_order_id = fields.Many2one('pos.order', string='Đơn hàng gần nhất', compute='_compute_last_order_id', store=True)
    last_order_line_ids = fields.Many2many('pos.order.line', string='Chi tiết Đơn hàng gần nhất', compute='_compute_last_order_line_ids')

    @api.depends('partner_id')
    def _compute_last_order_id(self):
        for rec in self:
            if rec.partner_id:
                rec.last_order_id = self.env['pos.order'].search([('partner_id', '=', rec.partner_id.id), ('state', 'in', ['paid', 'done'])], order='date_order desc', limit=1)
            else:
                rec.last_order_id = False

    @api.depends('last_order_id')
    def _compute_last_order_line_ids(self):
        for rec in self:
            rec.last_order_line_ids = rec.last_order_id.lines

    last_order_name = fields.Char(string='Mã đơn hàng', related='last_order_id.name')
    last_order_date = fields.Datetime(string='Ngày mua', related='last_order_id.date_order')
    last_order_account_move = fields.Many2one('account.move', string='Số hóa đơn', related='last_order_id.account_move')
    last_order_cashier = fields.Char(string='Tên thu ngân', related='last_order_id.cashier')
    last_order_amount_total = fields.Float(string='Tổng tiền', related=False, compute='_compute_last_order', currency_field='last_order_currency_id', store=True)
    last_order_currency_id = fields.Many2one(related='last_order_id.currency_id')

    @api.depends('last_order_id')
    def _compute_last_order(self):
        for rec in self:
            rec.last_order_amount_total = rec.last_order_id.amount_total

    def make_phone_call(self):
        if self.state not in ['to_call', 'no_answer']:
            raise UserError(_("Chỉ có thể thực hiện cuộc gọi khi trạng thái là 'Cần gọi' hoặc 'Không nghe máy'."))
        if not self.partner_phone:
            raise UserError(_("Số điện thoại không được để trống."))
        self_sudo = self.sudo()
        self_sudo.user_id = self.env.user
        self_sudo.state = 'follow_up'
        if not self_sudo.execution_date:
            self_sudo.execution_date = fields.Datetime.now()
        if self_sudo._context.get('no_open_popup'):
            return
        return self_sudo.open_record()

    def open_record(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ttb.happy.call',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'name': self._name,
        }

    is_locked = fields.Boolean(string='Khóa', compute='_compute_is_locked', store=False)

    @api.depends('state')
    def _compute_is_locked(self):
        for record in self:
            user = self.env.user
            if user.has_group('ttb_kpi.group_ttb_kpi_tnkh_manager') or user.has_group('ttb_kpi.group_ttb_kpi_tn_cskh') or user.has_group('base.group_system') or user.has_group('ttb_kpi.group_ttb_kpi_nv_cskh'):
                record.is_locked = True
            elif record.state not in ['no_answer','follow_up'] and user.has_group('ttb_kpi.group_ttb_kpi_nv_cskh'):
                record.is_locked = True
            else:
                record.is_locked = False
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        fields_data = self.fields_get(attributes=['readonly'])
        if view_type == 'form':
            user = self.env.user
            for name_node in arch.xpath("//div/field | //group/field | //header/field"):
                if name_node.get('name') in fields_data and fields_data[name_node.get('name')].get('readonly'):
                    continue

                if user.has_group('ttb_kpi.group_ttb_kpi_tnkh_manager') or user.has_group('ttb_kpi.group_ttb_kpi_tn_cskh') or user.has_group('base.group_system'):
                    name_node.set('readonly', "0")
                elif user.has_group('ttb_kpi.group_ttb_kpi_nv_cskh'):
                    name_node.set('readonly', "state not in ['to_call','no_answer','follow_up']")
                else:
                    name_node.set('readonly', "1")

                name_node.set('force_save', "1")
        return arch, view

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

    def write(self, vals):
        check_show_under_control_content = False
        if vals.get('state') in ['success', 'refuse', 'wrong_number']:
            check_show_under_control_content = True
        res = super(TTBHappyCall, self).write(vals)
        if check_show_under_control_content:
            for rec in self:
                if rec.show_under_control_content:
                    rec.action_create_ticket()
        return res

    @api.constrains('state')
    def _check_info_state(self):
        if self.env.context.get('import_file'):
            return
        under_control_desc = self.ttb_description_ids.filtered(lambda d: d.type == 'under_control')
        for rec in self:
            # if rec.state == 'success' and not rec.shopping_experience:
            #     raise UserError('Thiếu thông tin bắt buộc: Trải nghiệm mua sắm')
            # if rec.state == 'success' and not rec.introduce_to_others:
            #     raise UserError('Thiếu thông tin bắt buộc: Giới thiệu Tiến Thọ với người khác')
            if rec.state == 'success' and not rec.improvement_suggestions and under_control_desc:
                raise UserError('Thiếu thông tin bắt buộc: Tiến Thọ cải tiến vấn đề')
    def action_create_ticket(self):
        self.ensure_one()
        ticket = self.env['helpdesk.ticket'].search([('happy_call_id', '=', self.id)], limit=1)
        if not ticket:
            under_control_desc = self.ttb_description_ids.filtered(lambda d: d.type == 'under_control')
            under_control_content = self.under_control_content_ids

            related_dept_ids = False
            if self.ttb_branch_id:
                chi_nhanh_dept = self.env['hr.department'].search([('complete_name', '=', 'Chi nhánh')], limit=1)
                if chi_nhanh_dept:
                    related_dept_ids = [(6, 0, [chi_nhanh_dept.id])]
                else:
                    related_dept_ids = ''

            vals = {
                'happy_call_id': self.id,
                'partner_id': self.partner_id.id,
                'source_channel': 'Happy call',
                'ttb_branch_id': self.ttb_branch_id.id,
                'process_ttb_branch_id': self.ttb_branch_id.id,
                'ttb_description_ids': [(6, 0, under_control_desc.ids)],
                'under_control_content_ids': [(6, 0, under_control_content.ids)],
                'customer_description': self.improvement_suggestions,
                'related_department_ids': related_dept_ids,
                'has_related_user': self.has_related_user,
                'related_employee_ids': False,
                'support_description': False,
                'last_order_name': self.last_order_name,
                'last_order_date': self.last_order_date,
                'last_order_cashier': self.last_order_cashier,
                'last_order_id': self.last_order_id.id,
            }
            ticket = self.env['helpdesk.ticket'].with_context(igone_check_branch=True).create(vals)
        return ticket

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
            
    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super(TTBHappyCall, self).fields_get(allfields=allfields, attributes=attributes)
        if 'string' in res.get('create_uid', {}):
            res['create_uid']["string"] = "Người tạo"
        if 'string' in res.get('create_date', {}):
            res['create_date']["string"] = "Ngày tạo"
        if 'string' in res.get('write_uid', {}):
            res['write_uid']["string"] = "Người cập nhật"
        if 'string' in res.get('write_date', {}):
            res['write_date']["string"] = "Ngày cập nhật"
        return res

    voip_call_ids = fields.One2many('voip.call', 'ttb_happy_call_id', string='Lịch sử cuộc gọi', readonly=True)
