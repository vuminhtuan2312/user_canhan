from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import base64
import io
import os
from docxtpl import DocxTemplate
from odoo.modules import get_module_path

def convert_number_to_words(amount):
    """Chuyển đổi số tiền thành chữ tiếng Việt"""
    if amount == 0:
        return "Không đồng"

    units = ["", "nghìn", "triệu", "tỷ"]
    ones = ["", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]

    def read_block(number):
        """Đọc một khối 3 chữ số"""
        result = ""
        hundred = number // 100
        ten = (number % 100) // 10
        one = number % 10

        if hundred > 0:
            result += ones[hundred] + " trăm "
            if ten == 0 and one > 0:
                result += "lẻ "

        if ten > 1:
            result += ones[ten] + " mươi "
            if one == 1:
                result += "mốt "
            elif one == 5:
                result += "lăm "
            elif one > 0:
                result += ones[one] + " "
        elif ten == 1:
            result += "mười "
            if one == 5:
                result += "lăm "
            elif one > 0:
                result += ones[one] + " "
        else:
            if one > 0:
                result += ones[one] + " "

        return result.strip()

    # Tách số thành các khối 3 chữ số
    blocks = []
    temp = int(amount)
    while temp > 0:
        blocks.append(temp % 1000)
        temp //= 1000

    # Đọc từng khối
    result = ""
    for i in range(len(blocks) - 1, -1, -1):
        if blocks[i] > 0:
            result += read_block(blocks[i]) + " " + units[i] + " "

    result = result.strip().capitalize() + " đồng"
    return result

class AdvanceRequest(models.Model):
    _name = 'advance.request'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'ttb.approval.mixin']
    _description = 'Yêu cầu tạm ứng'

    name = fields.Char(string='Mã phiếu', required=True, copy=False, readonly=True, default='Mới')
    request_user_id = fields.Many2one(comodel_name='res.users', string='Người đề nghị', default=lambda self: self.env.user)
    department_id = fields.Many2one(comodel_name='hr.department', string='Bộ phận', default=lambda self: self.env['hr.department'].search([('name', '=', 'Ngành hàng')], limit=1))
    date = fields.Date(string='Ngày lập phiếu', default=fields.Date.context_today)
    date_approved = fields.Date(string='Ngày duyệt', readonly=True)
    content = fields.Text(string='Nội dung')
    state = fields.Selection(
        selection=[('draft', 'Mới'), ('to_approve', 'Đang duyệt'), ('approved', 'Đã duyệt'),
                   ('done', 'Đã tạm ứng'), ('cancelled', 'Đã hủy'), ('refunding', 'Đang hoàn ứng'), ('refunded', 'Đã hoàn ứng')],
        string='Trạng thái', default='draft', tracking=True)

    amount_total = fields.Float(string='Tổng số tiền', currency_field='currency_id', compute='_compute_amount_total', store=True, readonly=True)
    advance_amount = fields.Float(string='Số tiền tạm ứng', currency_field='currency_id', default=0.0)
    payment_date = fields.Date(string='Ngày tạm ứng')

    actual_amount = fields.Float(string='Số tiền thực tế', compute='_compute_actual_amount', store=True, readonly=True)
    refund_amount = fields.Float(string='Số tiền hoàn ứng', compute='_compute_refund_amount', store=True, readonly=True)
    missing_goods_amount = fields.Float(string='Giá trị hàng thiếu', compute='_compute_missing_goods_amount', store=True, readonly=True)
    refund_date = fields.Date(string='Ngày hoàn ứng', readonly=True)
    party = fields.Many2one(comodel_name='res.partner', string='Đối tượng')
    payment_type = fields.Selection(selection=[('cash', 'Tiền mặt'), ('bank', 'Chuyển khoản')], string='Phương thức thanh toán', default='bank')
    account_number = fields.Char(string='Số tài khoản', compute='_compute_party', store=True, readonly=False)
    account_holder = fields.Text(string='Chủ tài khoản', compute='_compute_party', store=True, readonly=False)
    bank_id = fields.Many2one('res.bank', string='Ngân hàng', compute='_compute_party', store=True, readonly=False)
    attachment_ids = fields.Binary(string='Phiếu tạm ứng đã duyệt')
    attachment_back_ids = fields.Binary(string='Phiếu hoàn ứng đã duyệt')

    # Các trường One2many cho file đính kèm
    supplier_payment_bill_ids = fields.One2many('advance.request.attachment', 'advance_request_id',
                                                 string='Bill thanh toán NCC',
                                                 domain=[('attachment_type', '=', 'supplier_payment_bill')])
    supplier_shipping_bill_ids = fields.One2many('advance.request.attachment', 'advance_request_id',
                                                  string='Bill vận chuyển NCC',
                                                  domain=[('attachment_type', '=', 'supplier_shipping_bill')])
    wire_transfer_ids = fields.One2many('advance.request.attachment', 'advance_request_id',
                                         string='Điện chuyển tiền',
                                         domain=[('attachment_type', '=', 'wire_transfer')])
    goods_inspection_ids = fields.One2many('advance.request.attachment', 'advance_request_id',
                                            string='Phiếu kiểm hàng',
                                            domain=[('attachment_type', '=', 'goods_inspection')])
    goods_receipt_ids = fields.One2many('advance.request.attachment', 'advance_request_id',
                                         string='Phiếu nhập hàng',
                                         domain=[('attachment_type', '=', 'goods_receipt')])
    other_attachment_ids = fields.One2many('advance.request.attachment', 'advance_request_id',
                                            string='Chứng từ khác',
                                            domain=[('attachment_type', '=', 'other')])

    product_category_ids = fields.Many2many(string='Nhóm hàng', comodel_name='product.category', compute='_compute_product_category')
    count_po = fields.Integer(string='Số đơn hàng', compute='_compute_count_po')

    request_lines = fields.One2many(comodel_name='advance.request.line', inverse_name='advance_request_id', string='Chi tiết yêu cầu tạm ứng')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Mới') == 'Mới':
                vals['name'] = self.env['ir.sequence'].next_by_code('advance.request') or 'Mới'
        return super(AdvanceRequest, self).create(vals_list)

    def _check_state_transition_conditions(self, next_state):
        for rec in self:
            missing_fields = []
            
            # 1. Thông tin chung (Common for all states from to_approve onwards)
            if not rec.department_id: missing_fields.append('Bộ phận')
            if not rec.content: missing_fields.append('Nội dung')
            
            # 2. Thông tin thanh toán (Common for all states from to_approve onwards)
            if not rec.party: missing_fields.append('Đối tượng')
            if not rec.payment_type: missing_fields.append('Phương thức thanh toán')
            if rec.payment_type == 'bank':
                if not rec.account_number: missing_fields.append('Số tài khoản')
                if not rec.account_holder: missing_fields.append('Chủ tài khoản')
                if not rec.bank_id: missing_fields.append('Ngân hàng')
            if not rec.attachment_ids: missing_fields.append('Phiếu tạm ứng đã duyệt')

            if next_state == 'done':
                if not rec.payment_date: missing_fields.append('Ngày thanh toán')
                if not rec.advance_amount: missing_fields.append('Số tiền tạm ứng')

            if missing_fields:
                raise ValidationError(f"Vui lòng nhập đầy đủ các trường sau trước khi chuyển sang trạng thái {dict(self._fields['state'].selection).get(next_state)}: {', '.join(missing_fields)}")

    def action_send_approve(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            
            rec._check_state_transition_conditions('to_approve')
            
            process_id, approval_line_ids = rec.get_approval_line_ids()
            rec.write({
                'process_id': process_id.id,
                'date_sent': fields.Datetime.now(),
                'state': 'to_approve',
                'approval_line_ids': [(5, 0, 0)] + approval_line_ids
            })
            if self.env.user.id not in rec.current_approve_user_ids.ids:
                rec.send_notify(
                    message='Bạn cần duyệt yêu cầu tạm ứng', 
                    users=rec.current_approve_user_ids, 
                    subject='Yêu cầu tạm ứng cần duyệt'
                )
            rec.action_approve()

    def action_approve(self):
        for rec in self:
            if rec.state != 'to_approve':
                continue
            
            rec._check_state_transition_conditions('approved')
            
            rec.state_change('approved')
            
            all_approved = not rec.rule_line_ids.filtered(lambda l: not l.notif_only and l.state != 'approved')
            if all_approved:
                rec.write({
                    'state': 'approved',
                    'date_approved': fields.Date.today()
                })
                rec.send_notify(
                    message='Yêu cầu tạm ứng của bạn đã được duyệt',
                    users=rec.request_user_id,
                    subject='Yêu cầu tạm ứng đã duyệt'
                )

    def action_reject(self):
        for rec in self:
            if rec.state in ['to_approve', 'approved']:
                rec.state_change('draft')
                rec.write({'state': 'draft'})

    def action_cancel(self):
        for rec in self:
            if rec.state == 'draft':
                rec.write({'state': 'cancelled'})
                rec.request_lines.mapped('po_id').write({
                    'purchase_order_status': False,
                    'advance_payment_status': False
                })

    def action_done(self):
        for rec in self:
            if rec.state == 'approved':
                rec._check_state_transition_conditions('done')
                rec.write({'state': 'done'})
                rec.request_lines.mapped('po_id').write({
                    'purchase_order_status': 'ordered',
                    'advance_payment_status': 'advance_issued'
                })

    def action_start_refund(self):
        all_shortage_items = []
        for rec in self:
            if rec.state != 'done':
                continue
            for line in rec.request_lines:
                if line.po_id and line.actual_qty < line.po_qty:
                    diff = line.po_qty - line.actual_qty
                    all_shortage_items.append(f"- {rec.name} / {line.po_id.name}: Thiếu {diff} sản phẩm.")

        if all_shortage_items:
            message = "Phát hiện chênh lệch số lượng tại các đơn hàng:\n\n" + "\n".join(all_shortage_items) + "\n\nBạn có chắc chắn muốn tiếp tục hoàn ứng với số lượng thực tế này không?"
            return {
                'name': _('Cảnh báo thiếu hàng'),
                'type': 'ir.actions.act_window',
                'res_model': 'advance.request.shortage.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_advance_request_id': self.ids[0] if self.ids else False,
                    'default_shortage_message': message,
                    'active_ids': self.ids,
                }
            }
        
        return self._action_start_refund_execute()

    def _action_start_refund_execute(self):
        for rec in self:
            if rec.state == 'done':
                po_ids = rec.request_lines.mapped('po_id')

                missing_dc_picking = []
                dc_picking_not_done = []
                missing_payment_bill = []
                missing_shipping_bill = []
                missing_wire_transfer = []
                missing_check_goods = []
                missing_imported_ticket = []
                missing_shipping_cost = []

                for po in po_ids:
                    dc_picking = po.picking_ids.filtered(lambda p: p.ttb_stage == '4').sorted(key=lambda p: p.id)[:1]
                    if not dc_picking:
                        missing_dc_picking.append(po.name)
                        continue

                    if dc_picking.state != 'done':
                        dc_picking_not_done.append(f"{po.name} (Phiếu {dc_picking.name} - Trạng thái: {dict(dc_picking._fields['state'].selection).get(dc_picking.state, dc_picking.state)})")

                    if not po.payment_bill_cn:
                        missing_payment_bill.append(po.name)

                    intl_picking = po.picking_ids.filtered(lambda p: p.ttb_stage == '1')
                    if intl_picking:
                        if not intl_picking.bill_supplier:
                            missing_shipping_bill.append(po.name)

                        if not intl_picking.wire_transfer:
                            missing_wire_transfer.append(po.name)

                    if dc_picking and not dc_picking.check_goods_ticket:
                        missing_check_goods.append(po.name)

                    if dc_picking and not dc_picking.imported_ticket:
                        missing_imported_ticket.append(po.name)

                    if not po.cost_shipping_total or po.cost_shipping_total <= 0:
                        missing_shipping_cost.append(po.name)

                error_messages = []
                if missing_dc_picking:
                    error_messages.append(f"• Phát hiện PO thiếu Phiếu nhập kho DC: {', '.join(missing_dc_picking)}")

                if dc_picking_not_done:
                    error_messages.append(f"• Phát hiện PO có Phiếu nhập kho DC chưa hoàn tất: {', '.join(dc_picking_not_done)}")

                if missing_payment_bill:
                    error_messages.append(f"• Phát hiện PO thiếu Bill thanh toán NCC: {', '.join(missing_payment_bill)}")

                if missing_shipping_bill:
                    error_messages.append(f"• Phát hiện PO thiếu Bill vận chuyển NCC: {', '.join(missing_shipping_bill)}")

                if missing_wire_transfer:
                    error_messages.append(f"• Phát hiện PO thiếu Điện chuyển tiền: {', '.join(missing_wire_transfer)}")

                if missing_check_goods:
                    error_messages.append(f"• Phát hiện PO thiếu Phiếu kiểm hàng: {', '.join(missing_check_goods)}")

                if missing_imported_ticket:
                    error_messages.append(f"• Phát hiện PO thiếu Phiếu nhập hàng: {', '.join(missing_imported_ticket)}")

                if missing_shipping_cost:
                    error_messages.append(f"• Phát hiện PO thiếu Tổng chi phí vận chuyển (phải > 0): {', '.join(missing_shipping_cost)}")

                if error_messages:
                    error_message = "Lưu ý: Hệ thống cần kiểm tra đầy đủ tất cả các điều kiện; nếu thiếu bất kỳ điều kiện nào, hệ thống sẽ hiển thị một thông báo tổng hợp duy nhất để người dùng biết và bổ sung, không tách riêng thành nhiều thông báo.\n\n" + "\n".join(error_messages)
                    raise ValidationError(error_message)
                rec.write({'state': 'refunding'})

                attachment_vals_list = []
                Attachment = self.env['advance.request.attachment']
                
                for po in po_ids:
                    if po.payment_bill_cn:
                        attachment_vals_list.append({
                            'advance_request_id': rec.id,
                            'attachment_type': 'supplier_payment_bill',
                            'name': f"Bill thanh toán NCC - {po.name}.pdf",
                            'file_data': po.payment_bill_cn,
                        })
                    
                    for picking in po.picking_ids:
                        if picking.ttb_stage == '1':
                            if picking.bill_supplier:
                                attachment_vals_list.append({
                                    'advance_request_id': rec.id,
                                    'attachment_type': 'supplier_shipping_bill',
                                    'name': f"Bill vận chuyển NCC - {picking.name}.pdf",
                                    'file_data': picking.bill_supplier,
                                })
                            if picking.wire_transfer:
                                attachment_vals_list.append({
                                    'advance_request_id': rec.id,
                                    'attachment_type': 'wire_transfer',
                                    'name': f"Điện chuyển tiền - {picking.name}.pdf",
                                    'file_data': picking.wire_transfer,
                                })
                        
                        elif picking.ttb_stage == '4':
                            if picking.check_goods_ticket:
                                attachment_vals_list.append({
                                    'advance_request_id': rec.id,
                                    'attachment_type': 'goods_inspection',
                                    'name': f"Phiếu kiểm hàng - {picking.name}.pdf",
                                    'file_data': picking.check_goods_ticket,
                                })
                            if picking.imported_ticket:
                                attachment_vals_list.append({
                                    'advance_request_id': rec.id,
                                    'attachment_type': 'goods_receipt',
                                    'name': f"Phiếu nhập hàng - {picking.name}.pdf",
                                    'file_data': picking.imported_ticket,
                                })

                if attachment_vals_list:
                    Attachment.create(attachment_vals_list)
        return True



    def action_refund_done(self):
        for rec in self:
            if rec.state == 'refunding':
                if not rec.attachment_back_ids:
                    raise UserError('Chưa có thông tin phiếu hoàn ứng đã duyệt. Vui lòng cập nhật trước khi hoàn thành hoàn ứng.')
                rec.write({
                    'state': 'refunded',
                    'refund_date': fields.Date.today()
                })

    @api.depends('request_lines.amount_total')
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = sum(rec.request_lines.mapped('amount_total'))

    @api.depends('request_lines.total_actual_amount')
    def _compute_actual_amount(self):
        for rec in self:
            rec.actual_amount = sum(rec.request_lines.mapped('total_actual_amount'))

    @api.depends('advance_amount', 'actual_amount')
    def _compute_refund_amount(self):
        for rec in self:
            rec.refund_amount = rec.advance_amount - rec.actual_amount

    @api.depends('request_lines.po_value', 'request_lines.actual_value')
    def _compute_missing_goods_amount(self):
        for rec in self:
            total_po_value = sum(rec.request_lines.mapped('po_value_vnd'))
            total_actual_value = sum(rec.request_lines.mapped('actual_value_vnd'))
            rec.missing_goods_amount = total_po_value - total_actual_value

    @api.depends('party')
    def _compute_party(self):
        for rec in self:
            if rec.party:
                # Ưu tiên 1: Phiếu gần nhất
                last_request = rec.search([
                    ('party', '=', rec.party.id),
                    ('date_approved', '!=', False),
                ], order='date_approved desc', limit=1)

                if last_request:
                        rec.account_number= last_request.account_number
                        rec.account_holder= last_request.account_holder
                        rec.bank_id= last_request.bank_id.id
                else:
                    # Ưu tiên 2= Partner bank
                    if rec.party.bank_ids:
                        bank = rec.party.bank_ids[0]
                        rec.account_number= bank.acc_number
                        rec.account_holder= False
                        rec.bank_id= bank.bank_id.id
                    else:
                        rec.account_number = False
                        rec.account_holder = False
                        rec.bank_id = False

    @api.depends('request_lines', 'request_lines.product_category_id')
    def _compute_product_category(self):
        for rec in self:
            rec.product_category_ids = rec.request_lines.mapped('product_category_id')

    @api.depends('request_lines', 'request_lines.po_id')
    def _compute_count_po(self):
        for rec in self:
            rec.count_po = len(rec.request_lines.mapped('po_id'))

    @api.onchange('request_lines')
    def _onchange_request_lines_stt(self):
        for i, line in enumerate(self.request_lines, start=1):
            line.stt = i

    def unlink(self):
        for rec in self:
            if rec.state == 'done':
                raise UserError(f"Không thể xóa yêu cầu tạm ứng {rec.name} đã hoàn tất.")
            rec.request_lines.mapped('po_id').write({
                'purchase_order_status': False,
                'advance_payment_status': False
            })
        return super(AdvanceRequest, self).unlink()

    def action_print_advance_request_docx(self):
        self.ensure_one()

        if DocxTemplate is None:
            raise UserError(_("Thư viện 'docxtpl' chưa được cài đặt."))

        module_name = 'ttb_purchase'
        module_path = get_module_path(module_name)
        if not module_path:
            raise UserError(_("Không thể tìm thấy module: %s", module_name))

        template_path = os.path.join(module_path, 'data', 'Mẫu in phiếu tạm ứng.docx')

        if not os.path.exists(template_path):
            raise UserError(_("Không tìm thấy file mẫu tại đường dẫn: %s", template_path))

        doc = DocxTemplate(template_path)
        context = {
            'request': self,
            'now': fields.Datetime.now().strftime('%d-%m-%Y'),
            'amount_in_words': convert_number_to_words(self.amount_total),
            'payment_type': self.payment_type
        }

        doc.render(context)

        file_stream = io.BytesIO()
        doc.save(file_stream)
        file_stream.seek(0)
        file_b64 = base64.b64encode(file_stream.read())

        downloader = self.env['report.downloader'].create({
            'file_data': file_b64,
            'file_name': f'Phiếu tạm ứng số {self.name.replace("/", "_")}.docx',
        })

        return {
            'type': 'ir.actions.act_window',
            'name': _('Tải Hợp đồng'),
            'res_model': 'report.downloader',
            'res_id': downloader.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_print_return_request_docx(self):
        self.ensure_one()

        if DocxTemplate is None:
            raise UserError(_("Thư viện 'docxtpl' chưa được cài đặt."))

        module_name = 'ttb_purchase'
        module_path = get_module_path(module_name)
        if not module_path:
            raise UserError(_("Không thể tìm thấy module: %s", module_name))

        template_path = os.path.join(module_path, 'data', 'Mẫu in phiếu hoàn ứng.docx')

        if not os.path.exists(template_path):
            raise UserError(_("Không tìm thấy file mẫu tại đường dẫn: %s", template_path))

        doc = DocxTemplate(template_path)
        amount_total = sum(self.request_lines.mapped('amount_total'))
        context = {
            'request': self,
            'now': fields.Datetime.now().strftime('%d-%m-%Y'),
            'amount_in_words': convert_number_to_words(self.refund_amount),
            'payment_type': self.payment_type,
            'amount_total': amount_total
        }

        doc.render(context)

        file_stream = io.BytesIO()
        doc.save(file_stream)
        file_stream.seek(0)
        file_b64 = base64.b64encode(file_stream.read())

        downloader = self.env['report.downloader'].create({
            'file_data': file_b64,
            'file_name': f'Phiếu hoàn ứng số {self.name.replace("/", "_")}.docx',
        })

        return {
            'type': 'ir.actions.act_window',
            'name': _('Tải Hợp đồng'),
            'res_model': 'report.downloader',
            'res_id': downloader.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def write(self, vals):
        res = super().write(vals)
        if 'state' in vals and vals['state'] == 'refunded':
            for rec in self:
                rec.request_lines.mapped('po_id').write({
                    'advance_payment_status': 'advance_cleared'
                })
        return res

class AdvanceRequestLine(models.Model):
    _name = 'advance.request.line'
    _description = 'Chi tiết yêu cầu tạm ứng'

    advance_request_id = fields.Many2one(comodel_name='advance.request', string='Yêu cầu tạm ứng')
    stt = fields.Integer(string='STT')
    branch_id = fields.Many2one(comodel_name='ttb.branch', string='Cơ sở')
    po_id = fields.Many2one(comodel_name='purchase.order', string='Mã đơn', domain="[('state', '=', 'purchase'), ('advance_payment_status', '=', False)]")
    partner_id = fields.Many2one(comodel_name='res.partner', string='Nhà cung cấp', readonly=True)
    description = fields.Char(string='Diễn giải')
    product_category_id = fields.Many2one(string='Nhóm hàng', comodel_name='product.category', domain="[('category_level', 'in', [1,2,3])]")
    currency_rate = fields.Float(string='Tỷ giá', compute='_compute_po_fields', store=True, readonly=True)
    amount = fields.Float(string='Số tiền', currency_field='currency_id')
    amount_total = fields.Float(string='Thành tiền', currency_field='currency_id')
    po_qty = fields.Float(string='Số lượng đặt PO', compute='_compute_po_fields', store=True, readonly=True)
    po_value = fields.Float(string='Giá trị hàng PO', compute='_compute_po_fields', store=True, readonly=True)
    po_value_vnd = fields.Float(string='Giá trị hàng PO (VNĐ)', compute='_compute_po_fields', store=True, readonly=True)
    actual_qty = fields.Float(string='Số lượng thực nhận', compute='_compute_actual_fields', store=True, readonly=True)
    actual_value = fields.Float(string='Giá trị hàng thực nhận', compute='_compute_actual_fields', store=True, readonly=True)
    actual_value_vnd = fields.Float(string='Giá trị hàng thực nhận (VNĐ)', compute='_compute_actual_fields', store=True, readonly=True)
    tax_amount = fields.Float(string='Tiền thuế', compute='_compute_po_fields', store=True, readonly=True, digits='Product Price')
    pvc_tq = fields.Float(string='PVC nội địa TQ', compute='_compute_po_fields', store=True, readonly=True)
    partner_discount = fields.Float(string='NCC chiết khấu',compute='_compute_po_fields', store=True, readonly=True)
    actual_amount = fields.Float(string='Thành tiền thực tế', compute='_compute_actual_amount', store=True, readonly=True)
    pvc_intl = fields.Float(string='Phí vận chuyển quốc tế', compute='_compute_po_fields', store=True, readonly=True)
    total_shipping_cost = fields.Float(string='Tổng CP VC', compute='_compute_total_shipping_cost', store=True, readonly=True, digits='Product Price')
    vat_amount = fields.Float(string='Thuế VAT', compute='_compute_po_fields', store=True, readonly=True)
    inspection_fee = fields.Float(string='Phí kiểm định', compute='_compute_po_fields', store=True, readonly=True)
    fumigration_fee = fields.Float(string='Phí hun trùng', compute='_compute_po_fields', store=True, readonly=True)
    customs_inspection_fee = fields.Float(string='Chi phí kiểm hoá', compute='_compute_po_fields', store=True, readonly=True)
    outside_customs_fee = fields.Float(string='Chi phí ngoài hải quan', compute='_compute_po_fields', store=True, readonly=True)
    lifting_fee = fields.Float(string='Phí nâng hạ', compute='_compute_po_fields', store=True, readonly=True)
    other_fee = fields.Float(string='Chi phí khác', compute='_compute_po_fields', store=True, readonly=True)
    total_other_fee = fields.Float(string='Tổng chi phí khác', compute='_compute_total_other_fee', store=True, readonly=True)
    total_actual_amount = fields.Float(string='Tổng tiền thực tế', compute='_compute_total_actual_amount', store=True, readonly=True)

    @api.depends('pvc_tq', 'pvc_intl')
    def _compute_total_shipping_cost(self):
        for rec in self:
            rec.total_shipping_cost = rec.pvc_tq + rec.pvc_intl

    @api.depends('po_id', 'po_id.exchange_rate', 'po_id.order_line.product_qty', 'po_id.order_line.product_qty', 'po_id.price_amount_cn',
                 'po_id.cost_inland_china', 'po_id.cost_international_shipping', 'po_id.cost_vat',
                 'po_id.cost_inspection', 'po_id.cost_sterilize', 'po_id.cost_chemical_test',
                 'po_id.cost_customs', 'po_id.cost_lift', 'po_id.cost_other', 'po_id.order_line.price_tax')
    def _compute_po_fields(self):
        for rec in self:
            if rec.po_id:
                rec.currency_rate = rec.po_id.exchange_rate
                rec.po_qty = sum(rec.po_id.order_line.mapped('product_qty'))
                rec.po_value = rec.po_id.price_amount_cn
                rec.po_value_vnd = rec.po_value * rec.currency_rate
                rec.pvc_tq = rec.po_id.cost_inland_china
                rec.pvc_intl = rec.po_id.cost_international_shipping

                # Các chi phí khác từ PO
                rec.vat_amount = rec.po_id.cost_vat
                rec.inspection_fee = rec.po_id.cost_inspection
                rec.fumigration_fee = rec.po_id.cost_sterilize
                rec.customs_inspection_fee = rec.po_id.cost_chemical_test
                rec.outside_customs_fee = rec.po_id.cost_customs
                rec.lifting_fee = rec.po_id.cost_lift
                rec.other_fee = rec.po_id.cost_other
                partner_discount = 0.0
                tax_amount = 0.0
                for line in rec.po_id.order_line:
                    if line.product_qty and line.ttb_discount_amount:
                        partner_discount += line.ttb_discount_amount * line.product_qty
                        tax_amount += line.price_tax
                rec.partner_discount = partner_discount
                rec.tax_amount = tax_amount
            else:
                rec.currency_rate = 0.0
                rec.po_qty = 0.0
                rec.po_value = 0.0
                rec.po_value_vnd = 0.0
                rec.pvc_tq = 0.0
                rec.pvc_intl = 0.0
                rec.tax_amount = 0.0
                rec.vat_amount = 0.0
                rec.inspection_fee = 0.0
                rec.fumigration_fee = 0.0
                rec.customs_inspection_fee = 0.0
                rec.outside_customs_fee = 0.0
                rec.lifting_fee = 0.0
                rec.other_fee = 0.0
                rec.partner_discount = 0.0

    @api.depends('po_id', 'po_id.picking_ids', 'po_id.picking_ids.state',
                 'po_id.picking_ids.ttb_stage', 'po_id.picking_ids.move_ids_without_package.quantity',
                 'po_id.picking_ids.move_ids_without_package.purchase_line_id.price_unit_cn',
                 'currency_rate')
    def _compute_actual_fields(self):
        for rec in self:
            if rec.po_id:
                dc_picking = rec.po_id.picking_ids.filtered(
                    lambda p: p.ttb_stage == '4' and p.state == 'done'
                ).sorted(key=lambda p: p.id)[:1]

                if dc_picking:
                    rec.actual_qty = sum(dc_picking.mapped('move_ids_without_package.quantity'))

                    actual_value = 0.0
                    for move in dc_picking.mapped('move_ids_without_package'):
                        if move.purchase_line_id and move.purchase_line_id.price_unit_cn:
                            actual_value += move.quantity * move.purchase_line_id.price_unit_cn
                    rec.actual_value = actual_value

                    rec.actual_value_vnd = rec.actual_value * rec.currency_rate
                else:
                    rec.actual_qty = 0.0
                    rec.actual_value = 0.0
                    rec.actual_value_vnd = 0.0
            else:
                rec.actual_qty = 0.0
                rec.actual_value = 0.0
                rec.actual_value_vnd = 0.0

    @api.depends('actual_value_vnd', 'tax_amount', 'partner_discount')
    def _compute_actual_amount(self):
        for rec in self:
            rec.actual_amount = rec.actual_value_vnd + rec.tax_amount - rec.partner_discount

    @api.depends('vat_amount', 'inspection_fee', 'fumigration_fee', 'customs_inspection_fee',
                 'outside_customs_fee', 'lifting_fee', 'other_fee')
    def _compute_total_other_fee(self):
        for rec in self:
            rec.total_other_fee = (rec.vat_amount + rec.inspection_fee + rec.fumigration_fee +
                                  rec.customs_inspection_fee + rec.outside_customs_fee + rec.lifting_fee + rec.other_fee)

    @api.depends('actual_amount', 'total_other_fee', 'total_shipping_cost')
    def _compute_total_actual_amount(self):
        for rec in self:
            rec.total_actual_amount = rec.actual_amount + rec.total_other_fee + rec.total_shipping_cost

    @api.onchange('po_id')
    def _onchange_po_id(self):
        if self.po_id:
            self.branch_id = self.po_id.ttb_branch_id
            self.partner_id = self.po_id.partner_id
            self.description = self.po_id.description
            self.product_category_id = self.po_id.product_category_id
            self.amount = self.po_id.amount_untaxed
            self.amount_total = self.po_id.amount_total

    def unlink(self):
        for rec in self:
            if rec.po_id and rec.po_id.ttb_type == 'imported_goods':
                rec.po_id.write({
                    'purchase_order_status': False,
                    'advance_payment_status': False
                })
        return super(AdvanceRequestLine, self).unlink()

    def create(self, vals_list):
        recs = super(AdvanceRequestLine, self).create(vals_list)
        for rec in recs:
            if rec.po_id and rec.po_id.ttb_type == 'imported_goods':
                rec.po_id.write({
                    'purchase_order_status': 'advance_payment',
                    'advance_payment_status': 'draft'
                })
            if not rec.partner_id and rec.po_id.partner_id:
                rec.partner_id = rec.po_id.partner_id
        return recs
