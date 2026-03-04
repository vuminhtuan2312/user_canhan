from odoo import *
from odoo import api, Command, fields, models, SUPERUSER_ID, _
from odoo.exceptions import UserError, ValidationError
import pytz
import io
import xlsxwriter
import base64
from odoo.fields import Date, Datetime
from collections import defaultdict
from bs4 import BeautifulSoup

class PurchaseOrder(models.Model):
    _name = 'purchase.order'
    _inherit = ['purchase.order', 'ttb.approval.mixin']

    ttb_open_ok = fields.Boolean(string='Mở đơn', default=False, copy=False, readonly=True)
    is_ttb_open_ok = fields.Boolean(string='Có thể mở đơn', compute='_compute_is_ttb_open_ok')
    ttb_editable = fields.Boolean(store=False)
    product_category_id = fields.Many2one(string='Nhóm hàng', comodel_name='product.category', domain="[('category_level', 'in', [1,2,3])]")
    advance_payment_status = fields.Selection(string='Trạng thái tạm ứng',
                     selection=[('draft', 'Mới'), ('advance_issued', 'Đã tạm ứng'),
                                ('advance_cleared', 'Đã hoàn ứng')], copy=False)

    advance_request_lines = fields.One2many(string='Dòng phiếu tạm ứng', comodel_name='advance.request.line', inverse_name='po_id', copy=False)
    advance_request_count = fields.Integer(string='Số phiếu tạm ứng', compute='_compute_advance_request_count')

    @api.depends('advance_request_lines')
    def _compute_advance_request_count(self):
        for rec in self:
            rec.advance_request_count = len(rec.advance_request_lines)

    def action_view_advance_requests(self):
        self.ensure_one()
        advance_request_lines = self.env['advance.request.line'].search([('po_id', '=', self.id)])
        advance_requests = advance_request_lines.mapped('advance_request_id')

        action = {
            'name': 'Phiếu tạm ứng',
            'type': 'ir.actions.act_window',
            'res_model': 'advance.request',
            'view_mode': 'list,form',
            'domain': [('id', 'in', advance_requests.ids)],
            'context': {'default_po_id': self.id},
        }

        if len(advance_requests) == 1:
            action['view_mode'] = 'form'
            action['res_id'] = advance_requests.id

        return action


    @api.depends('picking_type_id', 'state')
    def _compute_is_ttb_open_ok(self):
        for rec in self:
            rec.is_ttb_open_ok = rec.picking_type_id.warehouse_id.reception_steps == 'one_step' and rec.state not in ['draft', 'done']

    def ttb_action_open(self):
        for rec in self.filtered(lambda x: x.is_ttb_open_ok):
            rec.write({'ttb_open_ok': True})

    ttb_quantity_total = fields.Float(string='Tổng số lượng', compute='_compute_ttb_quantity_total', store=True)

    @api.depends('order_line.product_qty')
    def _compute_ttb_quantity_total(self):
        for rec in self:
            rec.ttb_quantity_total = sum(rec.order_line.filtered(lambda x: x.product_id.type != 'service').mapped('product_qty'))

    ttb_tax_type = fields.Selection(string='Phân loại thuế', selection=[('tax', 'Có thuế'), ('no_tax', 'Không thuế')], required=True, default='tax')

    @api.onchange('ttb_tax_type')
    def onchange_ttb_tax_type(self):
        self.order_line._compute_tax_id()

    ttb_approval_id = fields.Many2one(string='Tờ trình duyệt giá', comodel_name='ttb.purchase.approval', readonly=True, copy=False)
    ttb_invoice_partner = fields.Many2one(string='Thông tin xuất hóa đơn', comodel_name='res.partner', compute='_compute_ttb_invoice_partner', store=True, readonly=False, required=False, check_company=True, precompute=True, index='btree_not_null')
    ttb_shipping_partner = fields.Many2one(string='Thông tin nhận hàng', related='picking_type_id.warehouse_id.partner_id')
    ttb_company_partner_id = fields.Many2one(related='company_id.partner_id')

    @api.depends('company_id')
    def _compute_ttb_invoice_partner(self):
        for order in self:
            order.ttb_invoice_partner = order.company_id.partner_id.address_get(['invoice'])['invoice'] if order.company_id else False

    def action_import_product(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'import',
            'target': 'new',
            'name': 'Nhập sản phẩm',
            'params': {
                'context': {'default_order_id': self.id},
                'active_model': 'purchase.order.line',
            }
        }

    ttb_receipt_date = fields.Date(string='Ngày nhập kho', compute='_compute_ttb_receipt_date', store=True)

    @api.depends('picking_ids.state')
    def _compute_ttb_receipt_date(self):
        for rec in self:
            date_dones = rec.picking_ids.filtered(lambda x: x.state == 'done' and x.picking_type_code == 'incoming').mapped('date_done')
            valid_dates = [date for date in date_dones if date is not False]
            incoming_dates = min(valid_dates) if valid_dates else False
            if incoming_dates:
                rec.ttb_receipt_date = incoming_dates.astimezone(pytz.timezone(self.env.user.tz or 'Asia/Ho_Chi_Minh')).date()
            else:
                rec.ttb_receipt_date = False

    def _onchange_company_id(self):
        return

    picking_type_id = fields.Many2one(default=None, compute='_compute_picking_type_id', store=True, readonly=False)

    @api.onchange('picking_type_id')
    def ttb_onchange_picking_type_id(self):
        if self.picking_type_id and self.ttb_branch_id != self.picking_type_id.ttb_branch_id:
            self.ttb_branch_id = self.picking_type_id.ttb_branch_id
        if self.picking_type_id and self.ttb_type != self.picking_type_id.ttb_type:
            self.ttb_type = self.picking_type_id.ttb_type

    @api.depends('ttb_branch_id', 'ttb_type')
    def _compute_picking_type_id(self):
        for rec in self:
            if rec.ttb_type != 'imported_goods':
                rec.picking_type_id = self.env['stock.warehouse'].search([('ttb_branch_id', '=', rec.ttb_branch_id.id), ('ttb_type', '=', rec.ttb_type)], limit=1).in_type_id

    def get_flow_domain(self):
        domain = super().get_flow_domain()
        return osv.expression.AND([domain, ['|', ('purchase_type', '=', False), ('purchase_type', '=', self.ttb_type)]])

    ttb_allocation_id = fields.Many2one(string='Sản phẩm phân bổ', comodel_name='ttb.product.allocation', readonly=True, copy=False)
    ttb_type = fields.Selection(string='Loại đơn mua', selection=[('sale', 'Mua hàng kinh doanh'), ('not_sale', 'Mua hàng không kinh doanh'),
                                                                  ('material', 'Mua nguyên vật liệu'), ('imported_goods', 'Dự trù nhập khẩu')], required=True, default='sale')

    ttb_vat = fields.Char(string='Mã số thuế', related='partner_id.vat')
    ttb_partner_code = fields.Char(string='Mã NCC', related='partner_id.ref')
    ttb_receipt_doc = fields.Binary(string='Phiếu nhập kho', copy=False, readonly=True)
    ttb_receipt_doc_name = fields.Char(string='Tên Phiếu nhập kho', copy=False, readonly=True)
    ttb_vendor_doc = fields.Binary(string='Phiếu giao hàng NCC', copy=False, readonly=True)
    ttb_vendor_doc_name = fields.Char(string='Tên Phiếu giao hàng NCC', copy=False, readonly=True)
    ttb_vendor_invoice = fields.Binary(string='Hóa đơn GTGT', copy=False, readonly=True)
    ttb_vendor_invoice_name = fields.Char(string='Tên Hóa đơn GTGT', copy=False, readonly=True)
    ttb_vendor_invoice_no = fields.Char(string='Số hóa đơn NCC', copy=False, readonly=False)
    ttb_vendor_invoice_code = fields.Char(string='Ký hiệu hóa đơn NCC', copy=False, readonly=False)
    ttb_vendor_invoice_date = fields.Date(string='Ngày hóa đơn NCC', copy=False, readonly=False)
    ttb_document_done = fields.Boolean(string='Đầy đủ chứng từ', compute='_compute_ttb_document_done', store=True)

    ttb_vendor_delivery = fields.Binary(string='Biên bản bàn giao', copy=False)
    ttb_acceptance_report = fields.Binary(string='Biên bản nghiệm thu', copy=False)

    delivery_date_expected = fields.Date(string='Ngày giao hàng dự kiến')
    payment_term_note = fields.Text(string='Điều kiện thanh toán')
    additional_note = fields.Text(string='Ghi chú khác')

    china_stock_location = fields.Many2one('stock.location', 'Kho nhập khẩu TQ')
    vietnam_stock_location = fields.Many2one('stock.location', 'Kho nhập khẩu Việt Nam')
    shipping_warehouse_id = fields.Many2one(related='company_id.shipping_warehouse_id', string='Kho đi đường', store=True)

    @api.depends(lambda self: [name for name, field in self._fields.items() if field.store and name not in ['ttb_document_done']])
    def _compute_ttb_document_done(self):
        for rec in self:
            ttb_document_done = rec.ttb_document_done

            if rec.ttb_vendor_doc and rec.ttb_vendor_invoice and not ttb_document_done:
                ttb_document_done = True
            if ttb_document_done and rec.ttb_accountant_accept == 'not_ok':
                ttb_document_done = False
            rec.ttb_document_done = ttb_document_done

    description = fields.Char(string='Diễn giải', related='ttb_request_id.description')
    cost_inland_china = fields.Float(string='Chi phí vận chuyển nội địa TQ', digits='Product Price', default=0.0)
    cost_international_shipping = fields.Float(string='Chi phí vận chuyển quốc tế', digits='Product Price', default=0.0)
    cost_vat = fields.Float(string='Thuế Vat', digits='Product Price')
    cost_inspection = fields.Float(string='Phí kiểm định', digits='Product Price', default=0.0)
    cost_sterilize = fields.Float(string='Phí hun trùng', digits='Product Price', default=0.0)
    cost_chemical_test = fields.Float(string='Chi phí kiểm hóa', digits='Product Price', default=0.0)
    cost_customs = fields.Float(string='Phí chi ngoài hải quan', digits='Product Price', default=0.0)
    cost_lift = fields.Float(string='Phí nâng hạ', digits='Product Price', default=0.0)
    cost_other = fields.Float(string='Chi phí khác', digits='Product Price', default=0.0)
    cost_shipping_total = fields.Float(string='Tổng chi phí vận chuyển', compute='_compute_cost_total', store=True)
    cost_other_total = fields.Float(string='Tổng chi phí khác', compute='_compute_cost_total', store=True)
    cost_total = fields.Float(string='Tổng chi phí', compute='_compute_cost_total', store=True)

    @api.depends('cost_inland_china', 'cost_international_shipping', 'cost_vat', 'cost_inspection', 'cost_sterilize',
                 'cost_chemical_test', 'cost_customs', 'cost_lift', 'cost_other')
    def _compute_cost_total(self):
        for rec in self:
            rec.cost_total = sum([rec.cost_inland_china, rec.cost_international_shipping, rec.cost_vat, rec.cost_other,
                                  rec.cost_inspection, rec.cost_sterilize, rec.cost_chemical_test, rec.cost_customs, rec.cost_lift])
            rec.cost_shipping_total = sum([rec.cost_inland_china, rec.cost_international_shipping])
            rec.cost_other_total = sum([ rec.cost_vat,rec.cost_inspection, rec.cost_sterilize, rec.cost_chemical_test,
                                         rec.cost_customs, rec.cost_lift, rec.cost_other])

    def button_confirm(self):
        if self.ttb_type == 'imported_goods':
            if not self.cost_shipping_total and self.request_type:
                raise UserError(_('Vui lòng nhập các chi phí vận chuyển!'))
        return super().button_confirm()

    ttb_accountant_accept = fields.Selection(string='Xác nhận của kế toán', selection=[('not_ok', 'Chứng từ cần điều chỉnh'), ('ok', 'Chứng từ hợp lệ')])
    ttb_accountant_note = fields.Text(string='Ghi chú của kế toán')
    ttb_doc_user_id = fields.Many2one(string='Người tải tài liệu', readonly=True, copy=False, comodel_name='res.users')
    # ttb_doc_user_id = fields.Many2one(string='Người tải tài liệu', compute='_compute_ttb_doc_user_id', store=True, comodel_name='res.users')

    # @api.depends('ttb_vendor_doc', 'ttb_vendor_invoice')
    # def _compute_ttb_doc_user_id(self):
    #     for rec in self:
    #         if rec.ttb_vendor_doc == rec._origin.ttb_vendor_doc and rec.ttb_vendor_invoice == rec._origin.ttb_vendor_invoice:
    #             rec.ttb_doc_user_id = rec._origin.ttb_doc_user_id
    #             continue
    #         rec.ttb_doc_user_id = self.env.user.id if rec._origin.id or rec.ttb_vendor_doc or rec.ttb_vendor_invoice else False

    ttb_accountant_id = fields.Many2one(string='Kế toán xác nhận tài liệu', compute='_compute_ttb_accountant_id', store=True, comodel_name='res.users')

    @api.depends('ttb_accountant_accept')
    def _compute_ttb_accountant_id(self):
        for rec in self:
            if rec.ttb_accountant_accept == rec._origin.ttb_accountant_accept:
                rec.ttb_accountant_id = rec._origin.ttb_accountant_id
                continue
            rec.ttb_accountant_id = self.env.user.id if rec._origin.id or rec.ttb_accountant_accept else False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            partner_id = vals.get('partner_id')
            if partner_id:
                partner = self.env['res.partner'].browse(partner_id)
                if not partner.ref:
                    raise UserError("Nhà cung cấp chưa có mã tham chiếu. Vui lòng cập nhật trước khi tạo")

            if not vals.get('ttb_vendor_doc') and not vals.get('ttb_vendor_invoice'):
                vals['ttb_doc_user_id'] = False
            if not vals.get('ttb_accountant_accept'):
                vals['ttb_accountant_id'] = False
        return super().create(vals_list)

    order_user_id = fields.Many2one(string='Người đặt hàng', comodel_name='res.users', compute='_compute_order_user_id', store=True, readonly=False)

    @api.onchange('ttb_type')
    def _onchange_ttb_type(self):
        if self.ttb_type == 'imported_goods':
            default_branch = self.env['ttb.branch'].search([('name', '=', 'Tổng kho nhập khẩu')], limit=1)
            default_picking_type = self.env.company.import_warehouse_id.in_type_id
            if not default_branch:
                raise UserError(
                    "Chưa có cơ sở Tổng kho nhập khẩu, vui lòng tạo mới trước khi lập yêu cầu mua hàng nhập khẩu")
            if not default_picking_type:
                raise UserError("Chưa có thiết lập loại hoạt động 'Loại' trong kho nhập khẩu")
            self.ttb_branch_id = default_branch.id
            self.picking_type_id = default_picking_type.id

    @api.depends('request_type')
    def _compute_order_user_id(self):
        for rec in self:
            if rec.request_type:
                rec.order_user_id = None
            else:
                params = self.env['ir.config_parameter'].sudo().get_param('ttb_importes_goods.order_user_id', 'TT02220')
                user_id = self.env['res.users'].search([('login', '=', params)], limit=1)
                rec.order_user_id = user_id.id if user_id else None

    def write(self, vals):
        accountant_by_record = {}
        if 'ttb_accountant_accept' in vals:
            accountant_by_record = {rec: rec.ttb_accountant_accept for rec in self}
        res = super().write(vals)
        if 'order_user_id' in vals and vals['order_user_id']:
            message = _("Bạn đã được phân công là người mua hàng cho PO %s. Vui lòng kiểm tra thông tin.") % (
                                vals.get('name', self.name))
            user_id = self.env['res.users'].browse(vals['order_user_id'])
            self.sudo().message_post(
                body=message,
                partner_ids=[user_id.partner_id.id]
            )
        for record in accountant_by_record:
            if record.ttb_accountant_accept != accountant_by_record.get(record):
                record.ttb_accountant_id = self.env.user.id
            if not accountant_by_record.get(record) and record.ttb_accountant_accept != accountant_by_record.get(record) and record.ttb_accountant_accept == 'not_ok' and record.picking_ids:
                record.sudo().picking_ids.write({'ttb_sent_doc': False, 'ttb_document_done': False})

        if 'purchase_order_status' in vals:
            for rec in self:
                if vals['purchase_order_status'] == 'supplier_payment' and not rec.purchase_date:
                    raise UserError('Điền đầy đủ thông tin trong tab Mua hàng NCC Trung quốc trước khi chuyển trạng thái sang Thanh toán NCC')
                if vals['purchase_order_status'] == 'waiting' and (not rec.payment_date_cn or not rec.payment_bill_cn or not rec.purchase_date):
                    raise UserError('Điền đầy đủ thông tin trong tab Mua hàng NCC Trung quốc và Thanh toán NCC trước khi chuyển trạng thái sang Chờ NCC Trung Quốc phát hàng')
                if vals['purchase_order_status'] == 'done' and (not rec.payment_date_cn or not rec.payment_bill_cn or not rec.purchase_date or not rec.shipping_date or not rec.expected_date):
                    raise UserError('Điền đầy đủ thông tin trong tab Mua hàng NCC Trung quốc, Chờ NCC Trung Quốc phát hàng và Thanh toán NCC trước khi chuyển trạng thái sang Hoàn thành')
                if vals['purchase_order_status'] == 'done' and rec.number_of_cases_total <= 0:
                    raise UserError('Đơn hàng chưa có số kiện. Vui lòng kiểm tra lại!')
                
                # Create picking when status becomes 'done' for imported goods
                if vals['purchase_order_status'] == 'done' and rec.ttb_type == 'imported_goods':
                    rec._create_picking_imported_goods()

        if 'state' in vals:
            for rec in self:
                if vals['state'] == 'purchase' and rec.ttb_type == 'imported_goods':
                    if not rec.china_stock_location or not rec.vietnam_stock_location:
                        raise UserError(
                            'Điền đầy đủ thông tin kho nhập khẩu TQ và kho nhập khẩu Việt Nam trước khi gửi duyệt PO')

        if 'purchase_order_status' in vals:
            for rec in self:
                if rec.purchase_order_status == 'supplier_payment':
                    rec.date_of_purchase_completion = fields.Date.today()
                elif rec.purchase_order_status == 'waiting':
                    rec.date_of_payment_completion = fields.Date.today()
                elif rec.purchase_order_status == 'done':
                    rec.date_of_wait_completion = fields.Date.today()
        return res

    ttb_branch_id = fields.Many2one(string='Cơ sở', comodel_name='ttb.branch', required=True)

    def _prepare_picking_imported_goods(self):
        return {
            'picking_type_id': self.picking_type_id.id,
            'partner_id': self.partner_id.id,
            'user_id': False,
            'date': self.date_order,
            'origin': self.name,
            'location_id': self.partner_id.property_stock_supplier.id,
            'location_dest_id': self.china_stock_location.id,
            'company_id': self.company_id.id,
            'ttb_stage': '1',
            'state': 'draft',
        }

    def _create_picking(self):
        self = self.sudo()
        if self.ttb_type == 'imported_goods':
            return True
        
        res = super(PurchaseOrder, self)._create_picking()
        for line in self.order_line:
            line.move_ids.write({'sequence': line.sequence})
        return res

    def _create_picking_imported_goods(self):
        StockPicking = self.env['stock.picking']
        for order in self:
            if order.picking_ids.filtered(lambda x: x.state != 'cancel'):
                continue
            
            res = order._prepare_picking_imported_goods()
            picking = StockPicking.with_user(SUPERUSER_ID).create(res)
            moves = order.order_line._create_stock_moves(picking)
            moves = moves.filtered(lambda x: x.state not in ('done', 'cancel'))._action_confirm()
            seq = 0
            for move in sorted(moves, key=lambda move: move.date):
                seq += 5
                move.sequence = seq
            moves._action_assign()
            # Get following pickings (created by push rules) to confirm them as well.
            forward_pickings = self.env['stock.picking']._get_impacted_pickings(moves)
            (picking | forward_pickings).action_confirm()
            picking.message_post_with_source(
                'mail.message_origin_link',
                render_values={'self': picking, 'origin': order},
                subtype_xmlid='mail.mt_note',
            )
        return True



    def button_cancel(self):
        self = self.sudo()
        return super(PurchaseOrder, self).button_cancel()

    def _add_picking_info(self, activity):
        self = self.sudo()
        return super(PurchaseOrder, self)._add_picking_info(activity)

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
            user_ids = self.line_ids.mapped('product_id.categ_id.ttb_user_id')
        return user_ids

    @api.depends('user_id')
    def _compute_sent_ok(self):
        for rec in self:
            rec.sent_ok = rec.user_id and self.env.user == rec.user_id

    def button_approve(self):
        for order in self:
            if order.state in ['draft', 'sent']:
                if not order.sent_ok: continue
                process_id, approval_line_ids = order.get_approval_line_ids()
                order.write({'process_id': process_id.id,
                             'date_sent': fields.Datetime.now(),
                             'state': 'to approve',
                             'approval_line_ids': [(5, 0, 0)] + approval_line_ids})
                if order.env.user.id not in order.current_approve_user_ids.ids:
                    order.send_notify(message='Bạn cần duyệt đơn mua hàng', users=order.current_approve_user_ids, subject='Đơn mua hàng cần duyệt')
                order.button_approve()
                continue
            if not order.approve_ok and order.rule_line_ids: continue
            if order.state_change('approved'):
                order.sudo().write({'date_approved': fields.Datetime.now()})
                super(PurchaseOrder, order).button_approve()
                if order.rule_line_ids:
                    order.send_notify(message='Đơn mua hàng của bạn đã được duyệt', users=order.user_id, subject='Đơn mua hàng đã duyệt')
                    order.send_notify(message='Bạn được phân công thực hiện đơn mua hàng', users=order.notif_user_ids, subject='Đơn mua hàng cần thực hiện')
            else:
                order.send_notify(message='Bạn cần duyệt đơn mua hàng', users=order.current_approve_user_ids, subject='Đơn mua hàng cần duyệt')

    def action_reject(self):
        if self.state != 'to approve': return
        if not self.approve_ok: return
        self.state_change('rejected')
        if self.rule_line_ids.search([('notif_only', '=', False), ('res_id', 'in', self.ids), ('res_model', '=', self._name)], order='sequence asc', limit=1).state == 'rejected':
            self.sudo().write({'state': 'draft'})
            self.send_notify(message='Đơn mua hàng của bạn đã bị từ chối', users=self.user_id, subject='Đơn mua hàng bị từ chối')
        else:
            self.send_notify(message='Bạn cần duyệt đơn mua hàng', users=self.current_approve_user_ids, subject='Đơn mua hàng cần duyệt')
        return True

    def _approval_allowed(self):
        return True

    locker_ok = fields.Boolean(string='Có thể khóa', compute='_compute_locker_ok')

    @api.depends('user_id', 'notif_user_ids')
    def _compute_locker_ok(self):
        for rec in self:
            rec.locker_ok = self.env.user.id in (rec.user_id | rec.notif_user_ids).ids

    def _add_supplier_to_product(self):
        return

    def button_done(self):
        res = super().button_done()
        for record in self:
            pickings_to_cancel = record.picking_ids.filtered(lambda x: x.state != 'done')
            if pickings_to_cancel:
                pickings_to_cancel.action_cancel()
            record.send_notify(message='Đơn mua hàng của bạn đã hoàn thành', users=record.user_id, subject='Đơn mua hàng đã hoàn thành')
        for request in self.mapped('ttb_request_id'):
            request = request.sudo()
            if request.state == 'done': continue
            if request.po_ids and all(po.state == 'done' for po in request.po_ids):
                request.action_done()
        return res

    warehouse_id = fields.Many2one(related='picking_type_id.warehouse_id')
    ttb_request_id = fields.Many2one(string='Đơn yêu cầu', comodel_name='ttb.purchase.request', copy=False, readonly=True)
    ttb_batch_id = fields.Many2one(string='Đơn tổng hợp', comodel_name='ttb.purchase.batch', copy=False, readonly=True)
    ttb_consign = fields.Boolean(string='Ký gửi', compute='_compute_ttb_consign', store=True, readonly=False)

    cbm_total = fields.Float(string='Tổng CBM', related='ttb_request_id.cbm_total')
    number_of_cases_total = fields.Float(string='Tổng số kiện')
    currency_id = fields.Many2one(string='Tiền tệ', compute='compute_currency_id', readonly=False, store=True)
    exchange_rate = fields.Float(string='Tỷ giá', related='ttb_request_id.exchange_rate', readonly=False)
    profit_margin = fields.Float(string='Tỷ suất lợi nhuận', default=2.0)
    price_amount_cn = fields.Float(string='Tổng tiền(Tệ)', compute='compute_price_amount_cn')
    request_type = fields.Boolean(string='Loại yêu cầu', related='ttb_request_id.request_type',
                                  help='True là loại yêu cầu mua hàng nhập khẩu đồ chơi/văn phòng phẩm, False là hàng quà tặng')
    discount_total = fields.Float(string='Tổng chiết khấu(Tệ)', compute='_compute_discount_total')

    purchase_order_status = fields.Selection(string='Trạng thái đơn hàng',
                                             selection=[('advance_payment', 'Tạm ứng'),
                                                        ('ordered', 'Mua hàng NCC Trung quốc'),
                                                        ('supplier_payment', 'Thanh toán NCC'),
                                                        ('waiting', 'Chờ NCC Trung Quốc phát hàng'),
                                                        ('done', 'Hoàn thành')])

    purchase_date = fields.Date(string='Ngày mua hàng NCC')
    shipping_date = fields.Date(string='Ngày NCC phát hàng')
    expected_date = fields.Date(string='Ngày dự kiến nhận hàng nội địa Trung')

    date_of_purchase_completion = fields.Date(string='Ngày HT mua hàng NCC', readonly=True)
    date_of_payment_completion = fields.Date(string='Ngày HT thanh toán NCC', readonly=True)
    date_of_wait_completion = fields.Date(string='Ngày HT chờ NCC phát hàng', readonly=True)

    payment_date_cn = fields.Date(string='Ngày thanh toán NCC')
    payment_bill_cn = fields.Binary(string='Bill thanh toán NCC')

    attachment = fields.Binary(string='File đính kèm', related='ttb_request_id.attachment')
    is_gift_category = fields.Boolean(string="Là nhóm Quà tặng", compute="_compute_is_gift_category")

    @api.depends('product_category_id')
    def _compute_is_gift_category(self):
        for rec in self:
            rec.is_gift_category = False
            if rec.product_category_id.id == 12:
                rec.is_gift_category = True
    @api.depends('ttb_request_id.currency_id')
    def compute_currency_id(self):
        for rec in self:
            if rec.ttb_request_id.currency_id:
                rec.currency_id = rec.ttb_request_id.currency_id

    @api.depends('order_line.product_qty', 'order_line.price_unit_cn')
    def compute_price_amount_cn(self):
        for rec in self:
            total = 0
            for line in rec.order_line:
                total += line.product_qty * line.price_unit_cn
            rec.price_amount_cn = total

    @api.depends('order_line.ttb_discount_amount', 'order_line.product_qty')
    def _compute_discount_total(self):
        for rec in self:
            discount_total = 0
            for line in rec.order_line:
                discount_total += line.ttb_discount_amount * line.product_qty
            rec.discount_total = discount_total / rec.exchange_rate if rec.exchange_rate else 0

    @api.depends('partner_id')
    def _compute_ttb_consign(self):
        for rec in self:
            rec.ttb_consign = rec.partner_id.ttb_consign

    def _prepare_picking(self):
        res = super()._prepare_picking()
        if not self.ttb_consign:
            return res
        return {
            **res,
            'owner_id': self.partner_id.id,
        }

    def action_print_excel(self):
        for order in self:
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            sheet = workbook.add_worksheet("Purchase Order")

            # Định dạng
            bold = workbook.add_format({'bold': True, 'font_name': 'Times New Roman', 'align': 'center', 'valign': 'vcenter',})
            border = workbook.add_format({'border': 1, 'font_name': 'Times New Roman'})
            border_center = workbook.add_format(
                {'border': 1, 'align': 'center', 'valign': 'vcenter', 'font_name': 'Times New Roman', 'bold': True})
            money_table = workbook.add_format({'border': 1, 'num_format': '#,##0', 'font_name': 'Times New Roman'})
            footer = workbook.add_format({'font_name': 'Times New Roman','align': 'center', 'valign': 'vcenter'})
            left_cell_format = workbook.add_format({
                "font_name": "Times New Roman",
                "valign": "vcenter",
                "border": 0,
                "left": 1,
                'num_format': '#,##0'
            })
            right_bottom_cell_format = workbook.add_format({
                "font_name": "Times New Roman",
                "valign": "vcenter",
                "border": 0,
                "right": 1,
                "bottom": 1,
                'num_format': '#,##0'
            })
            right_cell_format = workbook.add_format({
                "font_name": "Times New Roman",
                "valign": "vcenter",
                "border": 0,
                "right": 1,
                'num_format': '#,##0'
            })
            top_cell_format = workbook.add_format({
                "font_name": "Times New Roman",
                "valign": "vcenter",
                "border": 0,
                "top": 1,
                "right": 1,
                "left": 1,
                'font_size': 11,
                'bold': True,
                'num_format': '#,##0'
            })
            bottom_cell_format = workbook.add_format({
                "font_name": "Times New Roman",
                "valign": "vcenter",
                "border": 0,
                "left": 1,
                "bottom": 1,
                'num_format': '#,##0'
            })
            left_right_cell_format = workbook.add_format({
                "font_name": "Times New Roman",
                "valign": "vcenter",
                "border": 0,
                "left": 1,
                "right": 1,
                'num_format': '#,##0'
            })
            left_right_bottom_cell_format = workbook.add_format({
                "font_name": "Times New Roman",
                "valign": "vcenter",
                "border": 0,
                "left": 1,
                "right": 1,
                "bottom": 1,
                'num_format': '#,##0'
            })
            top_left_cell_format = workbook.add_format({
                "font_name": "Times New Roman",
                "valign": "vcenter",
                "border": 0,
                "left": 1,
                "top": 1,
                'num_format': '#,##0'
            })
            top_right_cell_format = workbook.add_format({
                "font_name": "Times New Roman",
                "valign": "vcenter",
                "border": 0,
                "right": 1,
                "top": 1,
                'num_format': '#,##0'
            })
            # Cột
            sheet.set_column("A:A", 20)
            sheet.set_column("B:B", 25)
            sheet.set_column("C:C", 25)
            sheet.set_column("D:D", 18)
            sheet.set_column("E:E", 10)
            sheet.set_column("F:F", 20)
            sheet.set_column("G:G", 25)
            sheet.set_column("H:H", 15)

            sheet.merge_range("A1:F1", "ĐƠN ĐẶT HÀNG", workbook.add_format({
                'bold': True,
                'font_size': 16,
                'align': 'center',
                'valign': 'vcenter',
                'font_name': 'Times New Roman'
            }))

            # ========== THÔNG TIN HÓA ĐƠN ==========
            sheet.merge_range("A2:D2", "Thông tin xuất hóa đơn", top_cell_format)
            invoice_partner = order.ttb_invoice_partner

            sheet.merge_range("A3:D3", invoice_partner.name or '', left_right_cell_format)
            sheet.merge_range("A4:D4", invoice_partner.contact_address or '', left_right_cell_format)
            sheet.write("A5", "MST: " + (invoice_partner.vat or ''), left_cell_format)

            sheet.merge_range("B5:D5", order.company_id.partner_id.vat or '', right_cell_format)
            sheet.merge_range("A6:D6", "Địa chỉ giao hàng", left_right_cell_format)
            sheet.merge_range("A7:D7", order.company_id.partner_id.name or '', left_right_cell_format)
            sheet.merge_range("A8:D8", order.company_id.country_id.name or '', left_right_cell_format)
            sheet.merge_range("A9:D9", '', left_right_bottom_cell_format)

            sheet.merge_range("F2:G2", "Thông tin đơn hàng", top_cell_format)
            sheet.write("F3", "Số đơn hàng", left_cell_format)
            sheet.write("G3", order.name or '', right_cell_format)
            sheet.write("F4", "Ngày đặt hàng", left_cell_format)
            sheet.write("G4", Date.to_string(order.date_order), right_cell_format)
            sheet.write("F5", "Cơ sở", left_cell_format)
            sheet.write("G5", order.ttb_branch_id.name, right_cell_format)
            sheet.write("F6", "Người đặt hàng", left_cell_format)
            sheet.write("G6", order.user_id.name or '', right_cell_format)
            sheet.write("F7", "Số điện thoại", left_cell_format)
            sheet.write("G7", order.user_id.phone or '', right_cell_format)
            sheet.write("F8", "Email", left_cell_format)
            sheet.write("G8", order.user_id.email or '', right_cell_format)
            sheet.write("F9", "Ngày giao hàng", left_cell_format)
            sheet.write("G9", Date.to_string(order.date_planned or order.date_order), right_cell_format)
            sheet.write("F10", "Ghi chú", bottom_cell_format)
            html_content = order.notes or ''
            plain_text = BeautifulSoup(html_content, 'html.parser').get_text()
            sheet.write("G10", plain_text, right_bottom_cell_format)

            # ========== NHÀ CUNG CẤP ==========
            sheet.merge_range("A11:D11", "Nhà cung cấp", top_cell_format)
            sheet.merge_range("A12:D12", order.partner_id.name or '', left_right_cell_format)
            sheet.merge_range("A13:D13", order.partner_id.contact_address or '', left_right_bottom_cell_format)

            # ========== BẢNG SẢN PHẨM ==========
            headers = ["STT", "Mã vạch", "Tên hàng", "ĐVT", "Số lượng", "Đơn giá", "Thành tiền"]
            sheet.write_row("A16", headers, border_center)

            row = 15
            total = 0
            for idx, line in enumerate(order.order_line, start=1):
                sheet.write(row + 1, 0, idx, border_center)
                sheet.write(row + 1, 1, line.product_id.barcode_vendor or '', border)
                sheet.write(row + 1, 2, line.product_id.name or '', border)
                sheet.write(row + 1, 3, line.product_uom.name or '', border)
                sheet.write(row + 1, 4, line.product_qty, border)
                sheet.write(row + 1, 5, line.price_unit, money_table)
                sheet.write(row + 1, 6, line.price_subtotal, money_table)
                total += line.price_subtotal
                row += 1

            # ========== TỔNG KẾT ==========
            sheet.merge_range(row + 2, 4, row + 2, 5, "Tổng giá trị trước thuế", top_left_cell_format)
            sheet.write(row + 2, 6, total, top_right_cell_format)

            # Tính thuế theo mức
            tax_summary = defaultdict(float)
            for line in order.order_line:
                base = line.price_subtotal
                for tax in line.taxes_id:
                    if tax.amount_type == 'percent':
                        key = f"Thuế GTGT {int(tax.amount)}%"
                        tax_summary[key] += base * tax.amount / 100

            # Ghi từng loại thuế
            tax_total = 0.0
            current_row = row + 3
            for tax_label, tax_amount in sorted(tax_summary.items()):
                sheet.merge_range(current_row, 4, current_row, 5, tax_label, left_cell_format)
                sheet.write(current_row, 6, tax_amount, right_cell_format)
                tax_total += tax_amount
                current_row += 1

            # Tổng thuế
            sheet.merge_range(current_row, 4, current_row, 5, "Thuế GTGT", left_cell_format)
            sheet.write(current_row, 6, tax_total, right_cell_format)
            current_row += 1

            # Tổng đơn hàng
            sheet.merge_range(current_row, 4, current_row, 5, "Tổng giá trị đơn hàng", bottom_cell_format)
            sheet.write(current_row, 6, total + tax_total, right_bottom_cell_format)

            # ========== CHỮ KÝ ==========
            sheet.write(row + 10, 1, "Người lập phiếu", bold)
            sheet.write(row + 10, 3, "Bộ phận kho vận", bold)
            sheet.write(row + 10, 6, "Người giao hàng", bold)
            sheet.write(row + 15, 1, order.user_id.name or '', footer)

            # Hoàn tất
            workbook.close()
            output.seek(0)

            attachment = self.env['ir.attachment'].create({
                'name': f"{order.name}_phieu_nhap_hang.xlsx",
                'type': 'binary',
                'datas': base64.b64encode(output.read()),
                'res_model': 'purchase.order',
                'res_id': order.id,
                'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            })

            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{attachment.id}?download=true',
                'target': 'self',
            }

    def action_change_purchase_order_status(self):
        context = self.env.context.get('purchase_order_status')
        if context == 'advance_payment':
            self.purchase_order_status = 'ordered'
        elif context == 'ordered':
            self.purchase_order_status = 'supplier_payment'
        elif context == 'supplier_payment':
            self.purchase_order_status = 'waiting'
        elif context == 'waiting':
            self.purchase_order_status = 'done'
        else:
            raise UserError('Trạng thái không hợp lệ')

