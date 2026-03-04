from odoo import *
from odoo import api, Command, fields, models, SUPERUSER_ID, _
from odoo.exceptions import UserError, ValidationError

class ComplaintTicket(models.Model):
    _name = 'complaint.ticket'
    _description = 'Phiếu khiếu nại'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'ttb.approval.mixin']

    name = fields.Char(string='Complaint ID', required=True, copy=False, default='New')
    stock_picking = fields.Many2one('stock.picking', string='Phiếu vận chuyển', required=True, readonly=True)
    complaint_date = fields.Datetime(string='Ngày khiếu lại', default=fields.Datetime.now, required=True, readonly=True)
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('to_approve', 'Đang duyệt'),
        ('approved', 'Đang xử lý'),
        ('resolved', 'Đã giải quyết'),
        ('cancel', 'Đã hủy')
    ], string='Status', default='draft', tracking=True)
    assigned_to = fields.Many2one('res.users', string='Người khiếu nại', tracking=True, readonly=True, default=lambda self: self.env.user)
    complanit_line_ids = fields.One2many('complaint.ticket.line', 'complaint_id', string='Chi tiết khiếu nại')
    product_ids  = fields.Many2many('product.product', string='Sản phẩm khả dụng', compute='_compute_product_ids', store=True)
    attachments_complaint = fields.Binary(string='Tệp khiếu nại đính kèm')
    attachments_progress = fields.Binary(string='Tệp xử lý đính kèm')
    has_po = fields.Boolean(string='Đã tạo PO bù', default=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('complaint.ticket') or 'New'
        return super(ComplaintTicket, self).create(vals_list)

    @api.depends('stock_picking')
    def _compute_product_ids(self):
        for rec in self:
            if rec.stock_picking:
                rec.product_ids = rec.stock_picking.move_ids.mapped('product_id')

    def button_sent_complaint(self):
        for rec in self:
            if rec.state != 'draft':
                continue

            process_id, approval_line_ids = rec.get_approval_line_ids()
            rec.write({
                'process_id': process_id.id,
                'date_sent': fields.Datetime.now(),
                'state': 'to_approve',
                'approval_line_ids': [(5, 0, 0)] + approval_line_ids
            })
            if self.env.user.id not in rec.current_approve_user_ids.ids:
                rec.send_notify(
                    message='Bạn cần duyệt phiếu khiếu nại',
                    users=rec.current_approve_user_ids,
                    subject='Phiếu khiếu lại cần duyệt cần duyệt'
                )
            rec.button_confirm_complaint()

    def button_confirm_complaint(self):
        for rec in self:
            if rec.state != 'to_approve':
                continue

            rec.state_change('approved')

            all_approved = not rec.rule_line_ids.filtered(lambda l: not l.notif_only and l.state != 'approved')
            if all_approved:
                rec.write({
                    'state': 'approved',
                    'date_approved': fields.Date.today()
                })
                rec.send_notify(
                    message='Phiếu khiếu nại của bạn đã được duyệt',
                    users=rec.assigned_to,
                    subject='Phiếu khiếu nại đã duyệt'
                )

    def button_complete_complaint(self):
        self.ensure_one()
        if self.assigned_to:
            message = _("Phiếu khiếu nại %s của phiếu vận chuyển %s đã hoàn tất xử lý.") % (self.name,
                                                                                            self.stock_picking.name)
            self.sudo().message_post(
                body=message,
                partner_ids=[self.assigned_to.partner_id.id]
            )
        self.state = 'resolved'

    def button_cancel_complaint(self):
        self.ensure_one()
        if self.assigned_to:
            message = _("Phiếu khiếu nại %s của phiếu vận chuyển %s đã bị hủy.") % (self.name,
                                                                                    self.stock_picking.name)
            self.sudo().message_post(
                body=message,
                partner_ids=[self.assigned_to.partner_id.id]
            )
        self.state = 'cancel'

    def button_create_po(self):
        self.ensure_one()
        po_line_vals = []
        for line in self.complanit_line_ids:
            price_unit = self.stock_picking.move_ids.filtered(lambda x: x.product_id == line.product_id).price_unit
            po_line_vals.append((0, 0, {
                'product_id': line.product_id.id,
                'product_qty': line.quantity,
                'product_uom': line.product_id.uom_id.id,
                'price_unit': price_unit if price_unit else 0,
            }))
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.stock_picking.purchase_id.partner_id.id,
            'date_order': fields.Datetime.now(),
            'origin': self.stock_picking.name,
            'company_id': self.stock_picking.company_id.id,
            'ttb_type': 'sale',
            'order_line': po_line_vals,
            'ttb_branch_id': self.stock_picking.ttb_branch_id.id,
            'picking_type_id': self.stock_picking.picking_type_id.id,
        })
        self.has_po = True

    def button_view_po(self):
        po_id = self.env['purchase.order'].search([('origin', '=', self.stock_picking.name), ('state', '=', 'draft')], limit=1)
        if not po_id:
            raise UserError(_('Không tìm thấy đơn mua hàng nào!'))
        return {
            'name': _('Purchase Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'res_id': po_id.id,
            'target': 'current',
        }

class ComplaintLine(models.Model):
    _name = 'complaint.ticket.line'
    _description = 'Complaint Ticket Line'

    complaint_id = fields.Many2one('complaint.ticket', string='Complaint Reference', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Sản phẩm', required=True)
    status = fields.Selection([('damaged', 'Hư hỏng'),
                               ('missing', 'Thiếu'),
                               ('excess', 'Thừa'),], string='Trạng thái', required=True)
    quantity = fields.Integer(string='Số lượng', required=True)
    reason = fields.Text(string='Lý do', required=True)
    resolution_notes = fields.Text(string='Ghi chú giải quyết')

