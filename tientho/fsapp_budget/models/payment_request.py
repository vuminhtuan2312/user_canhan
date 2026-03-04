# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    payment_request_approver_id = fields.Many2one(
        'res.users',
        string='Người duyệt đề xuất thanh toán',
        config_parameter='fsapp.payment_request_approver_id'
    )


class PaymentRequest(models.Model):
    _name = 'fsapp.payment.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Đề xuất thanh toán'

    name = fields.Char(string='Đề xuất', required=True, tracking=True, default='New')
    department_id = fields.Many2one('hr.department', string='Phòng/Ban', tracking=True)
    purchase_order_id = fields.Many2one('purchase.order', string='Đơn mua hàng', tracking=True)
    purchase_order_ids = fields.Many2many('purchase.order', string='Đơn mua hàng', tracking=True)
    amount_total = fields.Float(string='Số tiền thanh toán', tracking=True)
    amount_paid = fields.Float(string='Số tiền đã thanh toán', compute='_compute_amount_paid', store=True, tracking=True)
    proposer_id = fields.Many2one('res.users', string='Người đề xuất', default=lambda self: self.env.user, tracking=True)
    approver_id = fields.Many2one('res.users', string='Người duyệt', tracking=True)
    approve_date = fields.Datetime(string='Ngày duyệt')
    payment_date = fields.Date(string='Ngày thanh toán')
    due_date = fields.Date(string='Thời hạn thanh toán')
    payment_method = fields.Many2one('account.journal', string='Phương thức thanh toán', tracking=True, domain="[('type', 'in', ['bank', 'cash'])]")
    bank_account_name = fields.Char(string='Họ tên người nhận')
    bank_account_number = fields.Char(string='Số tài khoản')
    bank_name = fields.Many2one('res.bank', string='Ngân hàng')
    payment_type = fields.Selection([
        ('request', 'Đề xuất thanh toán'),
        ('advance', 'Tạm ứng')
    ], string='Loại', default='request', required=True, tracking=True)

    partner_id = fields.Many2one('res.partner', string='Người nhận')

    invoice = fields.Binary(string='Hóa đơn VAT', attachment=True)
    contract = fields.Binary(string='Hợp đồng', attachment=True)
    delivery_note = fields.Binary(string='Biên nhận giao hàng', attachment=True)
    contract_clearance = fields.Binary(string='Thanh lý hợp đồng', attachment=True)
    commitment = fields.Binary(string='Bảng cam kết', attachment=True)

    state = fields.Selection([
        ('draft', 'Mới'),
        ('waiting', 'Đang duyệt'),
        ('approved', 'Đã duyệt'),
        ('rejected', 'Không duyệt'),
        ('cancelled', 'Hủy')
    ], string='Trạng thái', default='draft', tracking=True)

    payment_ids = fields.One2many('account.payment', 'payment_request_id', string='Phiếu chi')

    can_submit = fields.Boolean(compute="_compute_can_submit")
    can_approve = fields.Boolean(compute="_compute_can_approve")
    can_cancel = fields.Boolean(compute="_compute_can_cancel")
    can_reset = fields.Boolean(compute="_compute_can_reset")

    refund_payment_ids = fields.One2many('account.payment', 'refund_payment_request_id', string='Hoàn ứng')

    refund_payment_amount = fields.Float(
        string="Số tiền hoàn ứng",
        compute='_compute_refund_payment_amount',
        store=True
    )
    note = fields.Text(string='Ghi chú')
    account_type_from = fields.Selection([
        ('Cá nhân', 'Cá nhân'),
        ('Công ty', 'Công ty')
    ], string='Đi tiền từ tài khoản', required=1)

    @api.onchange('partner_id')
    def change_partner_id(self):
        if self.partner_id.bank_ids:
            bank = self.partner_id.bank_ids[:1]
            self.bank_account_name = self.partner_id.name
            self.bank_account_number = bank.acc_number
            self.bank_name = bank.bank_id.id

    @api.model
    def create(self, vals):
        code = 'seq_payment_request' if vals.get('payment_type') == 'request' else 'seq_payment_advance'
        vals['name'] = self.env['ir.sequence'].next_by_code(code) or 'New'
        return super().create(vals)

    @api.depends('refund_payment_ids.state', 'refund_payment_ids.amount')
    def _compute_refund_payment_amount(self):
        for rec in self:
            rec.refund_payment_amount = sum(
                payment.amount for payment in rec.refund_payment_ids if payment.state == 'posted'
            )

    advance_request_id = fields.Many2one(
        'fsapp.payment.request',
        string='Tạm ứng liên quan',
        domain=[('payment_type', '=', 'advance'), ('state', '=', 'approved')]
    )

    @api.depends(
        'advance_request_id.amount_paid',
        'advance_request_id.refund_payment_ids.amount',
        'payment_ids.amount',
        'payment_ids.state',
        'amount_total'
    )
    def _compute_amount_paid(self):
        for rec in self:
            advance_paid = 0.0
            if rec.advance_request_id:
                refunded = sum(p.amount for p in rec.advance_request_id.refund_payment_ids if p.state == 'posted')
                advance_paid = rec.advance_request_id.amount_paid - refunded

            payments = sum(p.amount for p in rec.payment_ids if p.state == 'posted')
            total_paid = advance_paid + payments
            rec.amount_paid = min(rec.amount_total, total_paid)

    @api.depends('state', 'proposer_id', 'approver_id', 'create_uid')
    def _compute_can_submit(self):
        user = self.env.user
        for rec in self:
            rec.can_submit = rec.state in ('draft', 'rejected') and (user == rec.proposer_id or user == rec.create_uid)

    @api.depends('state', 'approver_id')
    def _compute_can_approve(self):
        user = self.env.user
        for rec in self:
            rec.can_approve = rec.state == 'waiting' and user == rec.approver_id

    @api.depends('state', 'approver_id', 'proposer_id', 'create_uid')
    def _compute_can_cancel(self):
        user = self.env.user
        for rec in self:
            if rec.state in ('waiting', 'rejected'):
                rec.can_cancel = user == rec.proposer_id or user == rec.create_uid
            elif rec.state == 'approved':
                rec.can_cancel = user == rec.approver_id
            else:
                rec.can_cancel = False

    @api.depends('state', 'proposer_id', 'create_uid')
    def _compute_can_reset(self):
        user = self.env.user
        for rec in self:
            rec.can_reset = rec.state == 'cancelled' and (user == rec.proposer_id or user == rec.create_uid)

    def action_submit(self):
        approver_id = int(self.env['ir.config_parameter'].sudo().get_param('fsapp.payment_request_approver_id', 0))
        self.write({
            'state': 'waiting',
            'approver_id': approver_id,
        })
        if self.payment_type == 'request' and self.purchase_order_ids:
            self.partner_id = self.purchase_order_ids.partner_id[:1]

    def action_approve(self):
        for rec in self:
            rec.state = 'approved'

            # -- Kiểm tra journal --
            journal = self.env['account.journal'].search([('type', '=', 'bank')], limit=1)
            if not journal:
                raise UserError("Chưa cấu hình sổ nhật ký loại ngân hàng.")

            # Giữ lại giá trị trước khi tạo hoàn ứng
            remaining = rec.amount_total - rec.amount_paid

            # -- Tạo phiếu thu cho Tạm ứng liên quan nếu cần --
            advance = rec.advance_request_id
            if advance:
                advance_remaining = advance.amount_paid - advance.refund_payment_amount
                if advance_remaining > 0:
                    if not advance.partner_id:
                        raise UserError("Tạm ứng liên quan chưa có người nhận.")

                    refund_payment = self.env['account.payment'].create({
                        'payment_type': 'inbound',  # Phiếu thu
                        'partner_type': 'supplier',
                        'partner_id': advance.partner_id.id,
                        'amount': rec.amount_paid,
                        'journal_id': journal.id,
                        'date': fields.Date.context_today(advance),
                        'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
                        'refund_payment_request_id': advance.id,
                    })
                    refund_payment.action_post()

                    advance.message_post(
                        body=f"Đã tạo phiếu thu hoàn ứng <a href='/web#id={refund_payment.id}&model=account.payment'>{refund_payment.name}</a> số tiền {refund_payment.amount}."
                    )

            # -- Tạo phiếu chi cho Đề xuất thanh toán --
            if remaining > 0:
                if not rec.partner_id:
                    raise UserError("Vui lòng điền người nhận thanh toán.")

                payment = self.env['account.payment'].create({
                    'payment_type': 'outbound',
                    'partner_type': 'supplier',
                    'partner_id': rec.partner_id.id,
                    'amount': remaining,
                    'journal_id': journal.id,
                    'date': fields.Date.context_today(rec),
                    'payment_method_id': self.env.ref('account.account_payment_method_manual_out').id,
                    'payment_request_id': rec.id,
                })

                rec.message_post(
                    body=f"Đã tạo phiếu chi <a href='/web#id={payment.id}&model=account.payment'>{payment.name}</a> số tiền {payment.amount} cho đề xuất."
                )


    def action_refund_amount(self, amount):
        journal = self.env['account.journal'].search([('type', '=', 'bank')], limit=1)
        if not journal:
            raise UserError("Không tìm thấy sổ nhật ký ngân hàng.")

        payment = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'partner_type': 'supplier',
            'partner_id': self.partner_id.id,
            'amount': amount,
            'journal_id': journal.id,
            'date': fields.Date.context_today(self),
            'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
            'ref': f'Hoàn ứng từ đề xuất thanh toán',
            'refund_payment_request_id': self.id,
        })
        # payment.action_post()

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset_to_draft(self):
        self.write({'state': 'draft', 'approve_date': False})

    def open_payment(self):
        self.ensure_one()
        payments = self.payment_ids.filtered(lambda p: p.state != 'cancelled')
        action = self.env.ref('account.action_account_payments_payable').sudo().read()[0]

        if len(payments) == 1:
            action.update({
                'res_id': payments.id,
                'view_mode': 'form',
                'views': [(False, 'form')],
                'target': 'current',
            })
        else:
            action.update({
                'domain': [('id', 'in', payments.ids)],
                'view_mode': 'tree,form',
            })
        return action

    def action_refund_advance(self):
        self.ensure_one()

        if self.amount_paid <= 0:
            raise UserError("Không thể hoàn ứng nếu chưa có số tiền đã thanh toán.")
        if not self.partner_id:
            raise UserError("Chưa có người nhận để tạo hoàn ứng.")

        already_refunded = sum(
            payment.amount for payment in self.refund_payment_ids if payment.state != 'cancelled'
        )
        remaining_amount = self.amount_paid - already_refunded

        if remaining_amount <= 0:
            raise UserError("Đề xuất đã hoàn ứng đủ. Không thể hoàn ứng thêm.")

        journal = self.env['account.journal'].search([('type', '=', 'bank')], limit=1)
        if not journal:
            raise UserError("Chưa cấu hình sổ nhật ký loại ngân hàng để tạo phiếu thu.")

        payment_vals = {
            'payment_type': 'inbound',
            'partner_type': 'supplier',
            'partner_id': self.partner_id.id,
            'amount': remaining_amount,
            'journal_id': journal.id,
            'date': fields.Date.context_today(self),
            'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
            'ref': f"Hoàn ứng cho {self.name}",
            'refund_payment_request_id': self.id,
        }

        payment = self.env['account.payment'].create(payment_vals)
        payment.action_post()

        self.message_post(body=f"Đã hoàn ứng thêm bằng phiếu thu <a href='/web#id={payment.id}&model=account.payment'>{payment.name}</a>")

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'res_id': payment.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def open_refund_payments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Hoàn ứng',
            'res_model': 'account.payment',
            'view_mode': 'tree,form',
            'domain': [('refund_payment_request_id', '=', self.id)],
            'context': {'create': False},
        }

    def write(self, vals):
        if vals.get('state') == 'approved' and not vals.get('approve_date'):
            vals['approve_date'] = fields.Datetime.now()
        return super().write(vals)

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super().fields_get(allfields, attributes)
        for fname in res:
            if res[fname].get('readonly', False):
                continue
            res[fname].update({
                'states': {
                    'waiting': [('readonly', True)],
                    'approved': [('readonly', True)],
                    'rejected': [('readonly', True)],
                    'cancelled': [('readonly', True)],
                }
            })
        return res


    purchase_order_count = fields.Integer(string='Số Đơn mua hàng', compute='_compute_purchase_order_count')

    @api.depends('purchase_order_ids')
    def _compute_purchase_order_count(self):
        for rec in self:
            rec.purchase_order_count = len(rec.purchase_order_ids)

    def action_view_purchase_orders(self):
        self.ensure_one()
        action = self.env.ref('purchase.purchase_rfq').sudo().read()[0]
        action['domain'] = [('id', 'in', self.purchase_order_ids.ids)]
        if len(self.purchase_order_ids) == 1:
            action['views'] = [(self.env.ref('purchase.purchase_order_form').id, 'form')]
            action['res_id'] = self.purchase_order_ids.id
        return action


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    payment_request_id = fields.Many2one('fsapp.payment.request', string='Đề xuất thanh toán')
    refund_payment_request_id = fields.Many2one('fsapp.payment.request', string='Phiếu tạm ứng')

    def action_post(self):
        res = super().action_post()
        for rec in self:
            if rec.payment_request_id:
                rec.payment_request_id.payment_date = fields.Date.context_today(rec)
        return res
