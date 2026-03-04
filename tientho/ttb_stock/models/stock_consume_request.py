from odoo import fields, models, api

from odoo.exceptions import UserError


class StockConsumeRequest(models.Model):
    _name = 'stock.consume.request'
    _description = 'Đề nghị xuất dùng'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'ttb.approval.mixin']

    name = fields.Char(string='Mã đề nghị', required=True, readonly=True, copy=False, default='Mới')
    consume_type = fields.Selection([
        ('nvl', 'Xuất NVL cho sản xuất'),
        ('tool', 'Xuất công cụ dụng cụ'),
        ('repair', 'Xuất sửa chữa cải tạo'),
        ('ho_vpp', 'Xuất cho hệ thống (HO-VPP)'),
        ('marketing', 'Xuất vật dụng ấn phẩm marketing'),
        ('internal', 'Xuất nội bộ'),
        ('charity', 'Xuất ngoại giao, từ thiện'),
        ('benefit', 'Xuất phúc lợi'),
        ('benefit_ho', 'Xuất phúc lợi HO'),
        ('sale_other', 'Xuất kho phục vụ bán hàng - khác'),
        ('sale_cost', 'Xuất kho phục vụ bán hàng (CPBH, vật tư tiêu hao)'),
        ('gift', 'Xuất kho hàng tặng (CTKM)'),
        ('decorate', 'Xuất trang trí'),
    ], string='Loại', required=True, tracking=True)
    request_user_id = fields.Many2one('res.users', string='Người đề nghị', default=lambda self: self.env.user, tracking=True)
    responsible_user_id = fields.Many2one('res.users',string='Người phụ trách',tracking=True)
    request_date = fields.Datetime(string='Ngày đề nghị', default=fields.Datetime.now)
    approve_date = fields.Datetime(string='Ngày phê duyệt')
    warehouse_id = fields.Many2one('stock.warehouse', string='Kho xuất', required=True)
    reason = fields.Text(string='Lý do xuất dùng', tracking=True)
    picking_id = fields.Many2one('stock.picking', string='Phiếu xuất kho')
    state = fields.Selection([
        ('draft', 'Mới'),
        ('pending', 'Đang duyệt'),
        ('approved', 'Đã duyệt'),
        ('done', 'Đã xuất dùng'),
        ('cancel', 'Hủy'),
    ], default='draft', tracking=True)
    line_ids = fields.One2many('stock.consume.request.line', inverse_name='request_id', string='Chi tiết đề nghị')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == 'Mới':
                vals['name'] = self.env['ir.sequence'].next_by_code('stock.consume.request') or 'Mới'
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
                'active_model': 'stock.consume.request.line',
            }
        }
    def _create_outgoing_picking(self):
        self.ensure_one()

        warehouse = self.warehouse_id

        if not warehouse.consume_location_id:
            raise UserError('Kho xuất chưa cấu hình địa điểm xuất dùng.')

        if not warehouse:
            raise UserError("Vui lòng chọn kho xuất")

        picking_type = self.env['stock.picking.type'].sudo().search([
            ('code', '=', 'outgoing'),
            ('warehouse_id', '=', self.warehouse_id.id)
        ], limit=1)

        if not picking_type:
            raise UserError('Không tìm thấy loại xuất kho cho kho đã chọn.')
        move_lines = []
        for line in self.line_ids:
            if line.quantity <= 0:
                continue

            move_lines.append((0, 0, {
                'name': line.product_id.display_name,
                'product_id': line.product_id.id,
                'product_uom': line.uom_id.id,
                'product_uom_qty': line.quantity,
                'location_id': warehouse.lot_stock_id.id,
                'location_dest_id': warehouse.consume_location_id.id,
            }))

        if not move_lines:
            raise UserError('Phiếu đề nghị chưa có sản phẩm.')

        picking = self.env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'location_id': warehouse.lot_stock_id.id,
            'location_dest_id': warehouse.consume_location_id.id,
            'scheduled_date': self.approve_date,
            'origin': self.name,
            'consume_request_id': self.id,
            'move_ids_without_package': move_lines,
            'user_id': False,
        })
        self.write({
            'picking_id': picking.id,
            'state': 'approved'
        })

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
            self.send_notify(message='Bạn cần duyệt phiếu xuất dùng', users=self.current_approve_user_ids, subject='Yêu cầu duyệt phiếu xuất dùng')
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

            self._create_outgoing_picking()

            self.send_notify(
                message='Bạn cần duyệt phiếu xuất dùng',
                users=self.request_user_id,
                subject='Yêu cầu duyệt phiếu xuất dùng'
            )
        return True

    def action_reset(self):
        self.write({
            'state': 'draft'
        })
