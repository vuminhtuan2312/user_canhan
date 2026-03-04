from odoo import *


class PurchaseBatch(models.Model):
    _name = 'ttb.purchase.batch'
    _description = 'Tổng hợp yêu cầu mua hàng'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    def action_create_po(self):
        lines_to_create = self.line_ids.filtered(lambda x: x.partner_id and not x.po_line_ids)
        for partner in lines_to_create.mapped('partner_id'):
            lines_by_partner = lines_to_create.filtered(lambda x: x.partner_id.id == partner.id)
            for request in lines_by_partner.mapped('pr_line_ids.request_id'):
                lines_by_pr = lines_by_partner.pr_line_ids.filtered(lambda x: x.request_id.id == request.id)
                order_line = [(5, 0, 0)]
                for product in lines_by_pr.mapped('product_id'):
                    if not product: continue
                    lines_by_product = lines_by_pr.filtered(lambda x: x.product_id.id == product.id)

                    # should be one of a kind
                    bline = self.line_ids.filtered(lambda x: x.partner_id.id == partner.id and request.id in x.pr_line_ids.request_id.ids and x.product_id.id == product.id)
                    for line in lines_by_product:
                        order_line += [(0, 0, {
                            'product_id': line.product_id.id,
                            'product_qty': line.quantity,
                            'ttb_request_line_id': line.id,
                            'ttb_batch_line_id': bline.id,
                            'product_uom': bline.uom_id.id,
                        })]
                picking_type_id = self.env['stock.warehouse'].search([('ttb_type', '=', request.type), ('ttb_branch_id', '=', request.branch_id.id)], limit=1).in_type_id.id
                if not picking_type_id:
                    picking_type_id = self.env['stock.warehouse'].search([('ttb_branch_id', '=', request.branch_id.id)], limit=1).in_type_id.id
                if not picking_type_id:
                    picking_type_id = self.env.user.property_warehouse_id.in_type_id.id
                if not picking_type_id:
                    picking_type_id = self.env['stock.warehouse'].search([], limit=1).in_type_id.id

                self.env['purchase.order'].create([{
                    'partner_id': partner.id,
                    'ttb_type': request.type,
                    'company_id': self.company_id.id,
                    'currency_id': self.currency_id.id,
                    'date_order': fields.Date.today(),
                    'ttb_request_id': request.id,
                    'ttb_branch_id': request.branch_id.id,
                    'picking_type_id': picking_type_id,
                    'ttb_batch_id': self.id,
                    'order_line': order_line
                }])
        if self.line_ids and all(line.po_line_ids for line in self.line_ids):
            self.write({'state': 'created_po'})
        elif self.line_ids and any(line.po_line_ids for line in self.line_ids):
            self.write({'state': 'creating_po'})
        for pr in self.pr_ids:
            if pr.state != 'approved': continue
            if pr.line_ids and all(line.po_line_ids for line in pr.line_ids):
                pr.write({'state': 'po_created'})
                pr.send_notify(message='Yêu cầu mua hàng của bạn đã được thực hiện đặt hàng', users=pr.user_id, subject='Yêu cầu mua hàng đã được đặt hàng')
        return True

    def action_to_po(self):
        action = self.env["ir.actions.actions"]._for_xml_id("purchase.act_res_partner_2_purchase_order")
        action['context'] = {'create': 0}
        action['domain'] = [('id', 'in', self.po_ids.ids)]
        return action

    def action_to_pr(self):
        action = self.env["ir.actions.actions"]._for_xml_id("ttb_purchase.purchase_request_action")
        action['context'] = {'create': 0}
        action['domain'] = [('id', 'in', self.pr_ids.ids)]
        return action

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == 'Mới':
                vals['name'] = self.env['ir.sequence'].next_by_code('purchase.batch') or 'Mới'
        return super().create(vals_list)

    name = fields.Char(string='Mã yêu cầu', default='Mới', readonly=True, copy=False)
    user_id = fields.Many2one(string='Người thực hiện', comodel_name='res.users', default=lambda self: self.env.user, required=True)
    date = fields.Datetime(string='Ngày thực hiện', default=lambda self: fields.Datetime.now(), required=True)
    pr_ids = fields.Many2many(string='PR gốc', comodel_name='ttb.purchase.request', compute='_compute_pr')
    pr_count = fields.Integer(string='Số lượng PR gốc', compute='_compute_pr')

    @api.depends('line_ids')
    def _compute_pr(self):
        for rec in self:
            rec.pr_ids = rec.line_ids.mapped('pr_line_ids.request_id')
            rec.pr_count = len(rec.pr_ids)

    po_ids = fields.Many2many(string='PO', comodel_name='purchase.order', compute='_compute_po')
    po_count = fields.Integer(string='Số lượng PO', compute='_compute_po')

    @api.depends('line_ids')
    def _compute_po(self):
        for rec in self:
            rec.po_ids = rec.line_ids.mapped('po_line_ids.order_id')
            rec.po_count = len(rec.po_ids)

    state = fields.Selection(string='Trạng thái', selection=[('new', 'Mới'),
                                                             ('creating_po', 'Đang tạo PO'),
                                                             ('created_po', 'Đã tạo PO')],
                             readonly=True, copy=False, default='new', required=True)
    line_ids = fields.One2many(string='Chi tiết', comodel_name='ttb.purchase.batch.line', inverse_name='batch_id')
    company_id = fields.Many2one(string='Công ty', comodel_name='res.company', required=True, default=lambda self: self.env.company)

    currency_id = fields.Many2one(string='Tiền tệ', comodel_name='res.currency', default=lambda self: self.env.company.currency_id, required=True, compute='_compute_currency_id', store=True, readonly=False)

    @api.depends('company_id')
    def _compute_currency_id(self):
        for rec in self:
            rec.currency_id = (self.company_id or self.env.company).currency_id
