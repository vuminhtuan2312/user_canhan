from odoo import fields, models, api
from odoo.exceptions import UserError
from datetime import timedelta


class StockTransferRequest(models.Model):
    _name = 'stock.transfer.request'
    _description = 'Đề nghị điều chuyển hàng'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'ttb.approval.mixin']

    name = fields.Char(string='Mã điều chuyển', required=True, readonly=True, copy=False, default='Mới')
    transfer_type = fields.Selection([('transfer', 'Điều chuyển'), ('scrap', 'Xuất hủy'), ('consume', 'Xuất dùng')],string='Loại', required=True, tracking=True)
    request_user_id = fields.Many2one('res.users', string='Người đề nghị', default=lambda self: self.env.user, tracking=True)
    request_date = fields.Datetime(string='Ngày đề nghị', default=fields.Datetime.now)
    approve_date = fields.Datetime(string='Ngày phê duyệt')
    source_warehouse_id = fields.Many2one('stock.warehouse', string='Kho nguồn', related='request_user_id.property_warehouse_id', store=True, readonly=True)
    dest_warehouse_id = fields.Many2one('stock.warehouse',string='Kho đích')
    picking_ids = fields.One2many('stock.picking', 'transfer_request_id', string='Phiếu điều chuyển')
    in_picking_id = fields.Many2one('stock.picking', string='Phiếu điều chuyển nhập')
    line_ids = fields.One2many('stock.transfer.request.line', inverse_name='request_id', string='Chi tiết điều chuyển hàng')
    state = fields.Selection([
        ('draft', 'Mới'),
        ('pending', 'Đang duyệt'),
        ('approved', 'Đã duyệt'),
        ('transfered', 'Đã DC'),
        ('cs_receive', 'CS nhận hàng')
    ], string='Trạng thái', default='draft', tracking=True)
    note = fields.Char(string='Lý do điều chuyển', tracking=True)
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == 'Mới':
                vals['name'] = self.env['ir.sequence'].next_by_code('stock.transfer.request') or 'Mới'
        return super().create(vals_list)

    def action_import_product(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'import',
            'target': 'new',
            'name': 'Nhập sản phẩm',
            'params': {
                'context': {'default_request_id': self.id},
                'active_model': 'stock.transfer.request.line',
            }
        }
    # Tạo phiếu đề nghị điều chuyển
    def _create_internal_picking(self):
        self.ensure_one()

        warehouse = self.source_warehouse_id

        picking_type = self.env['stock.picking.type'].sudo().search([
            ('code', '=', 'internal'),
            ('warehouse_id', '=', warehouse.id),
            ('name', 'ilike', 'nội bộ')
        ], limit=1)

        if not picking_type:
            raise UserError('Không tìm thấy loại phiếu điều chuyển nội bộ.')

        scheduled_date = (self.approve_date or fields.Datetime.now()) + timedelta(days=1)

        picking_vals = {
            'picking_type_id': picking_type.id,
            'location_id': warehouse.lot_stock_id.id,
            'location_dest_id': warehouse.transit_location.id,
            'scheduled_date': scheduled_date,
            'origin': self.name,
            'transfer_request_id': self.id,
            'move_ids_without_package': [],
            'user_id': False,  # Do not assign responsible user at creation
        }
        # Aggregate lines by product to create a single move per product
        product_map = {}
        for line in self.line_ids:
            pid = line.product_id.id
            if pid not in product_map:
                product_map[pid] = {
                    'product': line.product_id,
                    'uom_id': line.uom_id.id,
                    'qty': 0,
                }
            # accumulate requested quantities (ensure numeric)
            qty_line = float(line.quantity or 0)
            product_map[pid]['qty'] += qty_line

        moves = []
        for pid, data in product_map.items():
            prod = data['product']
            qty = data['qty']
            uom_id = data['uom_id']
            # create stock.move entries; move lines will be attached to picking after creation
            moves.append((0, 0, {
                'name': prod.display_name,
                'product_id': pid,
                'product_uom': uom_id,
                'product_uom_qty': qty,
                'quantity': 0,
                'location_id': warehouse.lot_stock_id.id,
                'location_dest_id': warehouse.view_location_id.id,
            }))

        picking_vals['move_ids_without_package'] = moves

        # Create picking without auto-assigning a responsible user by passing a context flag
        # The stock.picking create override will check this context and avoid filling user_id.
        picking = self.env['stock.picking'].with_context(no_assign_user=True).create(picking_vals)

        # Attach stock.move.line records to the picking.move_line_ids
        # Create one move_line per move (qty_done = 0) so they appear on picking.move_line_ids.
        move_line_cmds = []
        for mv in picking.move_ids_without_package:
            move_line_cmds.append((0, 0, {
                'move_id': mv.id,
                'product_id': mv.product_id.id,
                'product_uom_id': mv.product_uom.id,
                'qty_done': 0,
                'location_id': mv.location_id.id,
                'location_dest_id': mv.location_dest_id.id,
            }))
        if move_line_cmds:
            picking.move_line_ids = move_line_cmds

        # Append picking to the picking_ids list instead of assigning single value
        self.picking_ids = [(4, picking.id)]
        return picking

    def action_send_approve(self):
        if self.state != 'draft': return
        if not self.sent_ok: return

        process_id, approval_line_ids = self.get_approval_line_ids()
        self.write({'process_id': process_id.id,
                    'date_sent': fields.Datetime.now(),
                    'state': 'pending',
                    'approval_line_ids': [(5, 0, 0)] + approval_line_ids})
        if self.env.user.id not in self.current_approve_user_ids.ids:
            self.send_notify(message='Bạn cần duyệt phiếu yêu cầu chuyển hàng giữa các cơ sở', users=self.current_approve_user_ids, subject='Yêu cầu chuyển hàng giữa các cơ sở')
        self.action_approve()
        return True

    def action_approve(self):
        self.ensure_one()
        if self.state != 'pending':
            return

        self.state_change('approved')

        all_approved = not self.rule_line_ids.filtered(lambda l: not l.notif_only and l.state != 'approved')
        if all_approved:
            self.sudo().write({
                'state': 'approved',
                'approve_date': fields.Datetime.now()
            })

            self._create_internal_picking()

            self.send_notify(
                message='Bạn cần duyệt phiếu yêu cầu chuyển hàng giữa các cơ sở',
                users=self.request_user_id,
                subject='Yêu cầu chuyển hàng giữa các cơ sở'
            )
        return True

    def action_reset(self):
        self.write({
            'state': 'draft'
        })