from odoo import *

from odoo.exceptions import UserError


class PurchaseRequest(models.Model):
    _name = 'ttb.purchase.request'
    _description = 'Yêu cầu mua hàng'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'ttb.approval.mixin']
    _order = 'date desc, id desc'
    _check_company_auto = True

    is_gift_category = fields.Boolean(string="Là nhóm Quà tặng", compute="_compute_is_gift_category")

    @api.depends('product_category_ids')
    def _compute_is_gift_category(self):
        for rec in self:
            rec.is_gift_category = any(cat.id == 12 for cat in rec.product_category_ids)
    def action_import_product(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'import',
            'target': 'new',
            'name': 'Nhập sản phẩm',
            'params': {
                'context': {'default_request_id': self.id},
                'active_model': 'ttb.purchase.request.line',
            }
        }

    def action_matching_product(self):
        for rec in self.line_ids:
            if rec.item:
                product = self.env['product.product'].search(['|', ('default_code', '=', rec.item), ('barcode', '=', rec.item)], limit=1)
                rec.product_id = product.id if product else None

    def action_import_code(self):
        self.ensure_one()
        ticket = self.env['import.code.imported.goods'].create({'name': self.id})

        return {
            'type': 'ir.actions.act_window',
            'name': 'Nhập mã hàng nhập khẩu',
            'res_model': 'import.code.imported.goods',
            'res_id': ticket.id,
            'view_mode': 'form',
            'target': 'curent',
        }

    approval_date_last = fields.Datetime(string='Ngày duyệt', compute='_compute_approval_date_last', store=True)
    @api.depends("rule_line_ids.date_approved")
    def _compute_approval_date_last(self):
        for order in self:
            approval_lines = order.rule_line_ids.filtered(lambda l: l.date_approved)
            if approval_lines:
                order.approval_date_last = max(approval_lines.mapped('date_approved'))
            else:
                order.approval_date_last = False
    def _check_conditions_create_po(self):
        self.ensure_one()
        if self.type == 'imported_goods':
            is_gift = any(cat.id == 12 for cat in self.product_category_ids)
            for line in self.line_ids:
                if line.reject:
                    continue
                if is_gift:
                    if line.price_cn == 0 or line.quantity == 0:
                        raise UserError(
                            f"Dòng sản phẩm [{line.product_id.display_name}] "
                            f"(Quà tặng) thiếu dữ liệu bắt buộc:\n"
                            f"- Đơn giá tệ\n"
                            f"- Số lượng"
                        )
                else:
                    missing_fields = []
                    if line.price_cn == 0:
                        missing_fields.append("Đơn giá tệ")
                    if line.cbm == 0:
                        missing_fields.append("CBM (Khối/Kiện)")
                    if line.number_of_cases == 0:
                        missing_fields.append("Số sản phẩm/Kiện")
                    if line.quantity == 0:
                        missing_fields.append("Số lượng")

                    if missing_fields:
                        raise UserError(
                            f"Dòng sản phẩm [{line.product_id.display_name}] "
                            f"thiếu dữ liệu bắt buộc:\n- " +
                            "\n- ".join(missing_fields)
                        )
    def action_create_po(self):
        PurchaseOrder = self.env['purchase.order']
        PurchaseOrderLine = self.env['purchase.order.line']

        grouped_lines = {}
        for line in self.line_ids:
            if not line.partner_id:
                raise UserError("Vui lòng chọn đủ Nhà cung cấp trong đơn mua hàng")
            if not line.reject:
                grouped_lines.setdefault(line.partner_id, []).append(line)

        created_pos = self.env['purchase.order']

        for partner, lines in grouped_lines.items():
            # Tạo PO
            warehouse = self.env['stock.warehouse'].search([('ttb_branch_id', '=', self.branch_id.id)], limit=1)
            if not warehouse:
                continue

            picking_type = warehouse.in_type_id

            po = PurchaseOrder.create({
                'partner_id': partner.id,
                'date_order': fields.Datetime.now(),
                'ttb_branch_id': self.branch_id.id,
                'ttb_type': self.type,
                'picking_type_id': picking_type.id,
                'ttb_request_id': self.id,
                'number_of_cases_total': self.number_of_cases_total,
                'product_category_id': self.product_category_ids[:1].id
            })
            created_pos |= po
            amount_cn = sum(l.quantity * l.price_cn for l in lines)

            # Tạo các PO Line
            for l in lines:
                PurchaseOrderLine.with_context(amount_cn=amount_cn).create({
                    'order_id': po.id,
                    'product_id': l.product_id.id,
                    'product_qty': l.quantity,
                    'product_uom': l.uom_id.id,
                    'price_unit_cn': l.price_cn,
                    'date_planned': fields.Datetime.now(),
                    'name': l.description,
                    'ttb_request_line_id': l.id,
                })
            self.state = 'po_created'

        # Nếu chỉ tạo 1 PO => mở form view
        if len(created_pos) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Purchase Order',
                'view_mode': 'form',
                'res_model': 'purchase.order',
                'res_id': created_pos.id,
            }

        # Nếu nhiều PO => mở list view
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Orders',
            'view_mode': 'list,form',
            'res_model': 'purchase.order',
            'domain': [('id', 'in', created_pos.ids)],
        }

    def action_undone(self):
        if self.state == 'done':
            self.write({'state': 'po_created'})

    locker_ok = fields.Boolean(string='Có thể khóa', compute='_compute_locker_ok')

    @api.depends('user_id', 'notif_user_ids')
    def _compute_locker_ok(self):
        for rec in self:
            rec.locker_ok = self.env.user.id in (rec.user_id | rec.notif_user_ids).ids

    po_ids = fields.One2many(string='Đơn mua hàng', comodel_name='purchase.order', inverse_name='ttb_request_id')
    po_count = fields.Integer(string='Số đơn mua hàng', compute='_compute_po_count')

    def action_to_po(self):
        action = self.env["ir.actions.actions"]._for_xml_id("purchase.act_res_partner_2_purchase_order")
        action['context'] = {'create': 0}
        action['domain'] = [('id', 'in', self.po_ids.ids)]
        return action

    @api.depends('po_count')
    def _compute_po_count(self):
        for rec in self:
            rec.po_count = len(rec.po_ids)

    def action_done(self):
        if self.state != 'done':
            self.send_notify(message='Yêu cầu mua hàng của bạn đã hoàn thành', users=self.user_id, subject='Yêu cầu mua hàng đã hoàn thành')
            self.write({'state': 'done'})

    allocation_id = fields.Many2one(string='Sản phẩm phân bổ', comodel_name='ttb.product.allocation', readonly=True, copy=False)

    def get_flow_domain(self):
        domain = super().get_flow_domain()
        return osv.expression.AND([domain, ['|', ('purchase_type', '=', False), ('purchase_type', '=', self.type)]])

    def get_approve_user_ids(self, rule):
        if rule.method not in ['manager', 'title_manager', 'mch_manager']:
            return super().get_approve_user_ids(rule)
        user_ids = self.env['res.users']
        company_domain = []
        if self.fields_get(['company_id']).get('company_id') and self.company_id:
            self = self.with_company(self.company_id)
            company_domain = ['|', ('company_id', '=', self.company_id.id), ('company_id', '=', False)]
        if rule.method == 'manager':
            user_ids = self.user_id.employee_id.parent_id.user_id
        elif rule.method == 'title_manager':
            parent = self.user_id.employee_id.parent_id
            while parent:
                if parent.job_id.id == rule.job_id.id:
                    user_ids |= parent.user_id
                parent = parent.parent_id
        elif rule.method == 'mch_manager':
            user_ids = self.line_ids.mapped('user_id')
        return user_ids

    @api.depends('user_id')
    def _compute_sent_ok(self):
        for rec in self:
            rec.sent_ok = rec.user_id and self.env.user == rec.user_id

    def action_sent(self):
        self._check_conditions_create_po()
        if self.state != 'new': return
        if not self.sent_ok: return
        if self.request_type:
            for line in self.line_ids:
                if not line.item:
                    raise UserError("Vui lòng nhập mã hàng của NCC cho tất cả các dòng yêu cầu mua hàng")
        process_id, approval_line_ids = self.get_approval_line_ids()
        self.write({'process_id': process_id.id,
                    'date_sent': fields.Datetime.now(),
                    'state': 'sent',
                    'approval_line_ids': [(5, 0, 0)] + approval_line_ids})
        if self.env.user.id not in self.current_approve_user_ids.ids:
            self.send_notify(message='Bạn cần duyệt yêu cầu mua hàng', users=self.current_approve_user_ids, subject='Yêu cầu mua hàng cần duyệt')
        self.action_approve()
        return True

    def action_approve(self):
        if self.state != 'sent': return
        if not self.approve_ok and self.rule_line_ids: return
        if self.state_change('approved'):
            self.sudo().write({'state': 'approved', 'date_approved': fields.Datetime.now()})
            if self.rule_line_ids:
                self.send_notify(message='Yêu cầu mua hàng của bạn đã được duyệt', users=self.user_id, subject='Yêu cầu mua hàng đã duyệt')
                self.send_notify(message='Bạn được phân công thực hiện yêu cầu mua hàng', users=self.notif_user_ids, subject='Yêu cầu mua hàng cần thực hiện')
        else:
            self.send_notify(message='Bạn cần duyệt yêu cầu mua hàng', users=self.current_approve_user_ids, subject='Yêu cầu mua hàng cần duyệt')
        return True

    def action_reject(self):
        if self.state != 'sent': return
        if not self.approve_ok: return
        self.state_change('rejected')
        if self.rule_line_ids.search([('notif_only', '=', False), ('res_id', 'in', self.ids), ('res_model', '=', self._name)], order='sequence asc', limit=1).state == 'rejected':
            self.sudo().write({'state': 'new'})
            self.send_notify(message='Yêu cầu mua hàng của bạn đã bị từ chối', users=self.user_id, subject='Yêu cầu mua hàng bị từ chối')
        else:
            self.send_notify(message='Bạn cần duyệt yêu cầu mua hàng', users=self.current_approve_user_ids, subject='Yêu cầu mua hàng cần duyệt')
        return True

    def action_cancel(self):
        if self.state != 'new': return
        self.sudo().write({'state': 'cancel'})
        return True

    name = fields.Char(string='Mã yêu cầu', default='Mới', readonly=True, copy=False, required=True)
    description = fields.Char(string='Diễn giải', required=True)
    type = fields.Selection(string='Loại yêu cầu', selection=[('sale', 'Mua hàng kinh doanh'), ('not_sale', 'Mua hàng không kinh doanh'),
                                                              ('material', 'Mua nguyên vật liệu'), ('imported_goods', 'Dự trù nhập khẩu')],
                            required=True, default='sale')
    receipt_date = fields.Date(string='Ngày muốn nhận hàng')
    note = fields.Text(string='Ghi chú bổ sung')
    attachment = fields.Binary(string='Tệp đính kèm')
    attachment_name = fields.Char(string='Tên tệp đính kèm')
    date = fields.Datetime(string='Ngày đề nghị', required=True, default=lambda self: fields.Datetime.now())
    user_id = fields.Many2one(string='Người đề nghị', required=True, comodel_name='res.users', default=lambda self: self.env.user)
    company_id = fields.Many2one(string='Công ty', required=True, comodel_name='res.company', default=lambda self: self.env.company)
    department_id = fields.Many2one(string='Phòng/Ban', comodel_name='hr.department', compute='_compute_department_id', store=True)

    partner_id = fields.Many2one(string='Nhà cung cấp', comodel_name='res.partner')
    partner_international_id = fields.Many2one(string='Nhà cung cấp thực tế', comodel_name='res.partner')

    ttb_prd_type_total = fields.Integer(string='Số loại sản phẩm', compute='_compute_ttb_quantity_price_total')
    ttb_quantity_total = fields.Integer(string='Tổng số lượng sản phẩm', compute='_compute_ttb_quantity_price_total')
    ttb_price_total = fields.Float(string='Tổng tiền (Tệ)', compute='_compute_ttb_quantity_price_total')

    @api.depends('line_ids', 'line_ids.quantity', 'line_ids.price_cn')
    def _compute_ttb_quantity_price_total(self):
        for rec in self:
            rec.ttb_prd_type_total = len(rec.line_ids)
            quantity_total = 0
            price_total = 0.0
            for line in rec.line_ids:
                quantity_total += line.demand_qty
                price_total += line.demand_qty * line.price_cn
            rec.ttb_quantity_total = quantity_total
            rec.ttb_price_total = price_total

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id and self.partner_id:
            for line in self.line_ids:
                line.partner_id = self.partner_id.id


    @api.depends('company_id', 'user_id')
    def _compute_department_id(self):
        for rec in self:
            rec.department_id = (rec.user_id or self.env.user).with_company(rec.company_id or self.env.company).employee_id.department_id

    branch_id = fields.Many2one(string='Cơ sở', comodel_name='ttb.branch', compute='_compute_branch_id', required=True, store=True, readonly=False)
    branch_ok = fields.Boolean(string='Nhân viên thuộc cơ sở', compute='_compute_branch_id', store=True)

    @api.depends('user_id', 'company_id', 'type')
    def _compute_branch_id(self):
        for rec in self:
            if rec.type == 'imported_goods':
                default_branch = self.env['ttb.branch'].search([('name', '=', 'Tổng kho nhập khẩu')], limit=1)
                if not default_branch:
                    raise UserError(
                        "Chưa có cơ sở Tổng kho nhập khẩu, vui lòng tạo mới trước khi lập yêu cầu mua hàng nhập khẩu")
                rec.branch_id = default_branch.id
            else:
                user = (rec.user_id or self.env.user).with_company(rec.company_id or self.env.company)
                branch_id = rec.branch_id
                branch_ok = False
                if len(user.ttb_branch_ids) == 1:
                    branch_id = user.ttb_branch_ids
                    branch_ok = True
                rec.branch_id = branch_id
                rec.branch_ok = branch_ok

    currency_id = fields.Many2one(string='Tiền tệ', comodel_name='res.currency', default=lambda self: self.env.company.currency_id, required=True, compute='_compute_currency_id', store=True, readonly=False)

    @api.depends('company_id', 'type', 'po_ids.currency_id')
    def _compute_currency_id(self):
        for rec in self:
            if rec.type != 'imported_goods':
                rec.currency_id = (self.company_id or self.env.company).currency_id
            else:
                if rec.po_ids:
                    rec.currency_id = rec.po_ids[0].currency_id.id

    @api.onchange('type')
    def _onchange_currency_id(self):
        if self.type == 'imported_goods':
            self.currency_id = self.env.ref('ttb_purchase.chinese_money').id

    exchange_rate = fields.Float(string='Tỷ giá', digits='Currency', default=3750.00)
    state = fields.Selection(string='Trạng thái', selection=[('new', 'Mới'),
                                                             ('sent', 'Đang phê duyệt'),
                                                             ('approved', 'Đã duyệt'),
                                                             ('po_created', 'Đã tạo PO'),
                                                             ('done', 'Đã hoàn thành'),
                                                             ('cancel', 'Hủy')]
                             , readonly=True, copy=False, default='new', tracking=True)

    cbm_total = fields.Float(string='Tổng CBM', compute='_compute_cbm_total', store=True)
    number_of_cases_total = fields.Float(string='Tổng số kiện', compute='_compute_cbm_total', store=True)

    @api.depends('line_ids', 'line_ids.cbm', 'line_ids.product_per_case', 'line_ids.number_of_cases')
    def _compute_cbm_total(self):
        for rec in self:
            cbm_total = 0.0
            number_of_cases_total = 0.0
            for line in rec.line_ids:
                cbm_total += line.cbm * line.number_of_cases
                number_of_cases_total += line.number_of_cases
            rec.cbm_total = cbm_total
            rec.number_of_cases_total = number_of_cases_total

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == 'Mới':
                vals['name'] = self.env['ir.sequence'].next_by_code('purchase.request') or 'Mới'
        return super().create(vals_list)

    line_ids = fields.One2many(string='Chi tiết yêu cầu', comodel_name='ttb.purchase.request.line', inverse_name='request_id', copy=True)

    def write(self, vals):
        res = super().write(vals)
        if 'state' in vals and vals['state'] == 'approved':
            for rec in self:
                rec.line_ids._auto_fill_item_code()
        return res

    request_type = fields.Boolean(string='Loại yêu cầu', compute='_compute_request_type',
                                  help='True là loại yêu cầu mua hàng nhập khẩu đồ chơi/văn phòng phẩm, False là hàng quà tặng')
    product_category_ids = fields.Many2many(string='Nhóm hàng', comodel_name='product.category', domain="[('category_level', '=', 1)]")

    @api.depends('product_category_ids')
    def _compute_request_type(self):
        for rec in self:
            req_type = False
            for line in rec.product_category_ids:
                if line.id != 12:
                    req_type = True
                    break
            rec.request_type = req_type
