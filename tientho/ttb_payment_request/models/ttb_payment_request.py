from odoo import models, fields, api
from odoo.exceptions import UserError

class PaymentRequest(models.Model):
    _name = 'ttb.payment.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Đề xuất thanh toán'

    name = fields.Char(string='Đề xuất', required=True, tracking=True, default='New')
    purchase_order_id = fields.Many2one('purchase.order', string='Đơn mua hàng', tracking=True)
    currency_id = fields.Many2one('res.currency', 'Currency', required=True, default=lambda self: self.env.company.currency_id.id)
    amount_total_purchase = fields.Monetary('Số tiền mua hàng', related='purchase_order_id.amount_total')
    
    amount_total = fields.Monetary(string='Số tiền thanh toán', tracking=True)
    percent_total = fields.Float(string='% thanh toán', tracking=True)

    amount_remain = fields.Monetary('Số tiền còn lại', compute='_compute_amount_paid')
    
    amount_paid = fields.Monetary(string='Số tiền đã thanh toán', compute='_compute_amount_paid', store=True, tracking=True)
    user_id = fields.Many2one('res.users', string='Người đề xuất', default=lambda self: self.env.user, tracking=True)
    payment_date = fields.Date(string='Ngày thanh toán')
    due_date = fields.Date(string='Thời hạn thanh toán')
    payment_method = fields.Many2one('account.journal', string='Phương thức thanh toán', tracking=True, domain="[('type', 'in', ['bank', 'cash'])]")
    bank_account_name = fields.Char(string='Họ tên người nhận')
    bank_account_number = fields.Char(string='Số tài khoản')
    bank_id = fields.Many2one('res.bank', string='Ngân hàng')
    payment_type = fields.Selection([
        ('request', 'Đề xuất thanh toán'),
        ('advance', 'Tạm ứng')
    ], string='Loại', default='request', required=True, tracking=True)

    partner_id = fields.Many2one('res.partner', string='Người nhận')

    state = fields.Selection([
        ('draft', 'Mới'),
        ('sent', 'Đã gửi duyệt'),
        ('approved', 'Đã duyệt'),
        ('cancelled', 'Hủy')
    ], string='Trạng thái', default='draft', tracking=True)

    payment_ids = fields.One2many('account.payment', 'payment_request_id', string='Phiếu chi')
    note = fields.Text(string='Ghi chú')
    account_type_from = fields.Selection([
        ('personal', 'Cá nhân'),
        ('company', 'Công ty')
    ], string='Đi tiền từ tài khoản', required=1, default='company')

    file_contract = fields.Binary(string='Hợp đồng', attachment=True)
    file_invoice = fields.Binary(string='Hoá đơn', attachment=True)

    file_others = fields.Many2many(
        comodel_name='ir.attachment',
        string="Chứng từ khác",
        help="Upload hoặc kéo thả các tài liệu, chứng từ liên quan vào đây."
    )

    is_printed = fields.Boolean('Đã in phiếu', default=False)

    # Một số trường tài liệu
    ttb_type = fields.Selection(related='purchase_order_id.ttb_type')
    ttb_receipt_doc = fields.Binary(string='Phiếu nhập kho')
    ttb_vendor_doc = fields.Binary(string='Phiếu giao hàng NCC')
    ttb_vendor_invoice = fields.Binary(string='Hóa đơn GTGT')
    ttb_vendor_delivery = fields.Binary(string='Biên bản bàn giao')
    ttb_acceptance_report = fields.Binary(string='Biên bản nghiệm thu')

    @api.onchange('partner_id')
    def change_partner_id(self):
        bank = self.partner_id.bank_ids[:1]
        self.bank_account_name = self.partner_id.name
        self.bank_account_number = bank.acc_number
        self.bank_id = bank.bank_id

    @api.onchange('purchase_order_id', 'payment_type')
    def onchange_purchase_order_id(self):
        if self.payment_type == 'request':
            payment_request_ids = self.purchase_order_id.payment_request_ids.filtered(lambda payment: payment.state == 'approved' and payment != self)
            self.amount_total = self.purchase_order_id.amount_total - sum(payment_request_ids.mapped('amount_total'))


            if self.ttb_type == 'sale':
                self.ttb_receipt_doc = self.purchase_order_id.ttb_receipt_doc
                self.ttb_vendor_doc = self.purchase_order_id.ttb_vendor_doc
            else:
                self.ttb_vendor_delivery = self.purchase_order_id.ttb_vendor_delivery
                self.ttb_acceptance_report = self.purchase_order_id.ttb_acceptance_report

        else:
            self.amount_total = 0

    @api.onchange('amount_total')
    def onchange_amount_total(self):
        print('amount_total')
        self.percent_total = self.amount_total / self.purchase_order_id.amount_total if self.purchase_order_id.amount_total else 0

    @api.onchange('percent_total')
    def onchange_percent_total(self):
        print('percent_total')
        self.amount_total = self.percent_total * self.purchase_order_id.amount_total

    @api.model
    def create(self, vals):
        code = 'seq_payment_request' if vals.get('payment_type') == 'request' else 'seq_payment_advance'
        vals['name'] = self.env['ir.sequence'].next_by_code(code) or 'New'
        return super().create(vals)

    @api.depends(
        'purchase_order_id',
        'purchase_order_id.payment_request_ids'
    )
    def _compute_amount_paid(self):
        for rec in self:
            payment_request_ids = rec.purchase_order_id.payment_request_ids.filtered(lambda payment: payment.state == 'approved' and payment.id != rec.id)
            rec.amount_paid = sum(payment_request_ids.mapped('amount_total'))
            rec.amount_remain = rec.purchase_order_id.amount_total - sum(payment_request_ids.mapped('amount_total'))

    def action_approve1(self):
        for rec in self:
            rec.state = 'approved'

            # -- Kiểm tra journal --
            journal = self.env['account.journal'].search([('type', '=', 'bank')], limit=1)
            if not journal:
                raise UserError("Chưa cấu hình sổ nhật ký loại ngân hàng.")

            if rec.amount_total > 0:
                if rec.amount_total + rec.amount_paid > rec.amount_total_purchase:
                    raise UserError('Không hợp lệ do tổng đề nghị thanh toán lớn hơn số tiền mua hàng')

                if not rec.partner_id:
                    raise UserError("Vui lòng điền người nhận thanh toán.")

                payment = self.env['account.payment'].create({
                    'payment_type': 'outbound',
                    'partner_type': 'supplier',
                    'partner_id': rec.partner_id.id,
                    'amount': rec.amount_total,
                    'journal_id': journal.id,
                    'date': fields.Date.context_today(rec),
                    'payment_method_id': self.env.ref('account.account_payment_method_manual_out').id,
                    'payment_request_id': rec.id,
                })

                rec.message_post(
                    body=f"Đã tạo phiếu chi <a href='/web#id={payment.id}&model=account.payment'>{payment.name}</a> số tiền {payment.amount} cho đề xuất."
                )

    def action_reject(self):
        self.write({'state': 'draft'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset_to_draft(self):
        self.write({'state': 'draft', 'approve_date': False})

    def open_payment(self):
        if not self.payment_ids: 
            raise UserError('Không có phiếu chi')
        
        return self.payment_ids.smart_button_action('account.action_account_payments_payable')

    def action_print_and_mark_as_printed(self):
        """
        Phương thức này được gọi bởi nút "In Phiếu".
        Nó sẽ cập nhật trường is_printed và sau đó trả về hành động báo cáo.
        """
        self.ensure_one() # Đảm bảo chỉ chạy trên 1 bản ghi

        # 1. Cập nhật trường is_printed thành True nếu nó chưa phải là True
        if not self.is_printed:
            self.write({'is_printed': True})
        
        # 2. Tìm và trả về hành động báo cáo (report action)
        #    'ttb_payment_request.action_report_payment_request' là ID của report action bạn đã tạo.
        return self.env.ref('ttb_payment_request.action_report_payment_request').report_action(self)

    def action_view_purchase_order(self):
        if self.purchase_order_id:
            xml_id = 'ttb_purchase.purchase_order_sale_action' if self.purchase_order_id.ttb_type == 'sale' else 'ttb_purchase.purchase_order_not_sale_action'
            result = self.env['ir.actions.act_window']._for_xml_id(xml_id)
            result['res_id'] = self.purchase_order_id.id
            result['views'] = [(False, 'form')]
        else:
            result = {'type': 'ir.actions.act_window_close'}

        return result


    # @api.model
    # def fields_get(self, allfields=None, attributes=None):
    #     res = super().fields_get(allfields, attributes)
    #     for fname in res:
    #         if res[fname].get('readonly', False):
    #             continue
    #         res[fname].update({
    #             'states': {
    #                 'waiting': [('readonly', True)],
    #                 'approved': [('readonly', True)],
    #                 'rejected': [('readonly', True)],
    #                 'cancelled': [('readonly', True)],
    #             }
    #         })
    #     return res

# Quy trình phê duyệt
class PaymentRequestApproval(models.Model):
    _name = 'ttb.payment.request'
    _inherit = ['ttb.payment.request', 'ttb.approval.mixin']

    # approve_date = fields.Datetime(string='Ngày duyệt')

    def action_sent(self):
        if self.state != 'draft': return
        if not self.sent_ok: return

        if self.payment_type == 'advance' and not self.file_contract:
            raise UserError('Để gửi duyệt Thanh toán tạm ứng cần có hợp đồng.')

        process_id, approval_line_ids = self.get_approval_line_ids()
        self.write({'process_id': process_id.id,
                    'date_sent': fields.Datetime.now(),
                    'state': 'sent',
                    'approval_line_ids': [(5, 0, 0)] + approval_line_ids})
        if self.env.user.id not in self.current_approve_user_ids.ids:
            self.send_notify(message='Bạn cần duyệt đề xuất thanh toán', users=self.current_approve_user_ids, subject='Đề xuất thanh toán cần duyệt')
        return True

    def action_approve(self):
        if self.state != 'sent': return
        if not self.approve_ok and self.rule_line_ids: return

        if self.amount_total + self.amount_paid > self.amount_total_purchase:
            raise UserError('Không hợp lệ do tổng đề xuất thanh toán lớn hơn số tiền mua hàng')

        if self.state_change('approved'):
            self.sudo().write({'state': 'approved', 'date_approved': fields.Datetime.now()})
            if self.rule_line_ids:
                self.send_notify(message='Đề xuất thanh toán của bạn đã được duyệt', users=self.user_id, subject='Đề xuất thanh toán đã duyệt')
                # self.send_notify(message='Bạn được phân công thực hiện đề xuất thanh toán', users=self.notif_user_ids, subject='Đề xuất thanh toán cần thực hiện')
        else:
            self.send_notify(message='Bạn cần duyệt đề xuất thanh toán', users=self.current_approve_user_ids, subject='Đề xuất thanh toán cần duyệt')
        
        return True

    def action_reject(self):
        if self.state != 'sent': return
        if not self.approve_ok: return
        self.state_change('rejected')
        if self.rule_line_ids.search([('notif_only', '=', False), ('res_id', 'in', self.ids), ('res_model', '=', self._name)], order='sequence asc', limit=1).state == 'rejected':
            self.sudo().write({'state': 'draft'})
            self.send_notify(message='Đề xuất thanh toán của bạn đã bị từ chối', users=self.user_id, subject='Đề xuất thanh toán bị từ chối')
        else:
            self.send_notify(message='Bạn cần duyệt đề xuất thanh toán', users=self.current_approve_user_ids, subject='Đề xuất thanh toán cần duyệt')
        return True
    
