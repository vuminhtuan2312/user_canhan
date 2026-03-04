from odoo import *


class ProductAllocation(models.Model):
    _name = 'ttb.product.allocation'
    _description = 'Sản phẩm phân bổ'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    def action_import_product(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'import',
            'target': 'new',
            'name': 'Nhập sản phẩm',
            'params': {
                'context': {'default_allocation_id': self.id},
                'active_model': 'ttb.product.allocation.line',
            }
        }

    def action_to_pr(self):
        action = self.env["ir.actions.actions"]._for_xml_id("ttb_purchase.purchase_request_action")
        action['context'] = {'create': 0}
        action['domain'] = [('id', 'in', self.pr_ids.ids)]
        return action

    def action_pr_created(self):
        pr_ids = []
        if self.state != 'selected':
            return
        for branch in self.mapped('line_ids.order_line.branch_id'):
            line_ids = []
            details_by_branch = self.mapped('line_ids.order_line').filtered(lambda x: x.branch_id.id == branch.id)
            for product in details_by_branch.mapped('product_id'):
                details_by_product = details_by_branch.filtered(lambda x: x.product_id.id == product.id)
                quantity = sum(details_by_product.mapped('quantity'))
                if not quantity: continue
                line_ids += [(0, 0, {
                    'product_id': product.id,
                    'demand_qty': quantity,
                    'partner_id': self.partner_id.id,
                })]
            if not line_ids: continue
            vals = {
                'allocation_id': self.id,
                'branch_id': branch.id,
                'company_id': self.company_id.id,
                'line_ids': line_ids,
            }
            pr_ids += [(0, 0, vals)]
        if pr_ids:
            self.write({'pr_ids': pr_ids, 'state': 'pr_created'})

    def action_to_po(self):
        action = self.env["ir.actions.actions"]._for_xml_id("purchase.act_res_partner_2_purchase_order")
        action['context'] = {'create': 0}
        action['domain'] = [('id', 'in', self.po_ids.ids)]
        return action

    def action_po_created(self, partner, ttype='sale'):
        po_ids = []
        if self.state != 'selected':
            return
        for branch in self.mapped('line_ids.order_line.branch_id'):
            order_line = []
            details_by_branch = self.mapped('line_ids.order_line').filtered(lambda x: x.branch_id.id == branch.id)
            for product in details_by_branch.mapped('product_id'):
                details_by_product = details_by_branch.filtered(lambda x: x.product_id.id == product.id)
                quantity = sum(details_by_product.mapped('quantity'))
                if not quantity: continue
                order_line += [(0, 0, {
                    'product_id': product.id,
                    'product_qty': quantity,
                    'product_uom': product.uom_id.id,
                })]
            picking_type_id = self.env['stock.warehouse'].search([('ttb_type', '=', ttype), ('ttb_branch_id', '=', branch.id)], limit=1).in_type_id.id
            if not picking_type_id:
                picking_type_id = self.env['stock.warehouse'].search([('ttb_branch_id', '=', branch.id)], limit=1).in_type_id.id
            if not picking_type_id:
                picking_type_id = self.env.user.property_warehouse_id.in_type_id.id
            if not picking_type_id:
                picking_type_id = self.env['stock.warehouse'].search([], limit=1).in_type_id.id

            if not order_line: continue
            vals = {
                'ttb_allocation_id': self.id,
                'ttb_branch_id': branch.id,
                'company_id': self.company_id.id,
                'partner_id': partner.id,
                'currency_id': self.company_id.currency_id.id,
                'date_order': fields.Date.today(),
                'picking_type_id': picking_type_id,
                'order_line': order_line
            }
            po_ids += [(0, 0, vals)]
        if po_ids:
            self.write({'po_ids': po_ids, 'state': 'po_created'})

    po_ids = fields.One2many(string='PO', comodel_name='purchase.order', inverse_name='ttb_allocation_id')
    po_count = fields.Integer(string='Số lượng PO', compute='_compute_po_count')

    @api.depends('po_ids')
    def _compute_po_count(self):
        for rec in self:
            rec.po_count = len(rec.po_ids)

    pr_ids = fields.One2many(string='PR', comodel_name='ttb.purchase.request', inverse_name='allocation_id')
    pr_count = fields.Integer(string='Số lượng PR', compute='_compute_pr_count')

    @api.depends('pr_ids')
    def _compute_pr_count(self):
        for rec in self:
            rec.pr_count = len(rec.pr_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == 'Mới':
                vals['name'] = self.env['ir.sequence'].next_by_code('product.allocation') or 'Mới'
        return super().create(vals_list)

    def action_selected(self):
        domain = tools.safe_eval.safe_eval(self.product_domain or '[]')
        if self.partner_id:
            domain += [('seller_ids','any',[('partner_id','=',self.partner_id.id)])]
        products = self.env['product.product'].search(domain)
        line_ids = []
        for product in products:
            if self.partner_id:
                seller = product._select_seller(
                    partner_id=self.partner_id,
                    quantity=None,
                    date=self.date.date() if self.date else fields.Date.context_today(self),
                    uom_id=product.uom_id)
                if not seller:
                    continue
            line_ids += [(0, 0, {
                'product_id': product.id,
                'uom_id': product.uom_id.id,
            })]
        if line_ids:
            self.write({'state': 'selected', 'line_ids': [(5, 0, 0)] + line_ids})
        return

    def action_product_allocate(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "ttb.product.allocation.detail",
            "views": [[False, "grid"]],
            "domain": [('order_id', 'in', self.line_ids.ids)],
            "context": {'create': 0, 'show_branch': self.branch_ids.ids},
            "name": "Phân bổ",
            "target": "current",
        }

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_new(self):
        self.write({'state': 'new'})

    name = fields.Char(string='Mã phân bổ', required=True, readonly=True, copy=False, default='Mới')
    partner_id = fields.Many2one(string='Nhà cung cấp', comodel_name='res.partner')
    product_domain = fields.Char(string='Điều kiện khác', default='[]')
    branch_ids = fields.Many2many(string='Cơ sở', comodel_name='ttb.branch')
    user_id = fields.Many2one(string='Người phụ trách', comodel_name='res.users', default=lambda self: self.env.user)
    date = fields.Datetime(string='Thời gian phân bổ', default=lambda self: fields.Datetime.now())
    state = fields.Selection(string='Trạng thái', selection=[('new', 'Mới'),
                                                             ('selected', 'Đã chọn SP'),
                                                             ('pr_created', 'Đã tạo PR'),
                                                             ('po_created', 'Đã tạo PO'),
                                                             ('cancel', 'Hủy')
                                                             ], required=True, copy=False, default='new', readonly=True)
    line_ids = fields.One2many(string='Chi tiết sản phẩm', comodel_name='ttb.product.allocation.line', inverse_name='allocation_id')
    company_id = fields.Many2one(string='Công ty', comodel_name='res.company', required=True, default=lambda self: self.env.company)
