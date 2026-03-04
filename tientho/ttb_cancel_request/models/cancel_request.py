from odoo import models, fields, api, Command
from odoo.exceptions import UserError, ValidationError


class CancelRequest(models.Model):
    _name = 'cancel.request'
    _description = 'Đề xuất hủy hàng'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Mã đề xuất', readonly=True, default='New')
    date_request = fields.Datetime(string='Ngày đề nghị', default=fields.Datetime.now, readonly=True)
    date_approve = fields.Datetime(string='Ngày duyệt', readonly=True)
    user_id = fields.Many2one('res.users', string='Người đề nghị', default=lambda self: self.env.user, readonly=True)


    branch_id = fields.Many2one('ttb.branch', string='Cơ sở', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Kho', required=True)

    reason_id = fields.Many2one('cancel.reason', string='Lý do hủy hàng',
                                domain="[('active', '=', True)]", required=True)

    line_ids = fields.One2many('cancel.request.line', 'request_id', string='Chi tiết sản phẩm')
    total_amount = fields.Float(string='Tổng giá trị hủy', compute='_compute_total_amount', store=True)

    state = fields.Selection([
        ('new', 'Mới'),
        ('wait_pick', 'Đợi nhặt hàng'),
        ('wait_transfer', 'Đợi chuyển VP'),
        ('wait_approve', 'Đợi duyệt'),
        ('wait_cancel', 'Đợi hủy hàng'),
        ('done', 'Hoàn tất'),
        ('cancel', 'Hủy')
    ], string='Trạng thái', default='new', tracking=True)

    picking_ids = fields.One2many('stock.picking', 'cancel_request_id', string='Phiếu kho')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('cancel.request') or 'New'
        return super().create(vals_list)

    @api.depends('line_ids.subtotal')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = sum(rec.line_ids.mapped('subtotal'))

    # --- Actions ---
    def action_send_pick(self):
        self.ensure_one()
        self.state = 'wait_pick'
        self._create_picking(step='pick')

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_approve(self):
        self.ensure_one()
        self.write({
            'state': 'wait_cancel',
            'date_approve': fields.Datetime.now()
        })
        self._create_picking(step='cancel')

    # --- Logic tạo Picking ---
    def _create_picking(self, step):
        """ 
        step: 'pick' (Nhặt hàng), 'transfer' (Chuyển VP), 'cancel' (Hủy)
        """
        StockPicking = self.env['stock.picking']

        # Xác định Picking Type và Locations dựa trên step
        picking_type = None
        location_src_id = None
        location_dest_id = None

        if step == 'pick':
            # Loại trả lại (Return) - Cần config đúng trên Warehouse hoặc tìm theo sequence code
            picking_type = self.env['stock.picking.type'].search([
                ('warehouse_id', '=', self.warehouse_id.id),
                ('code', '=', 'incoming')  # Giả định Return dùng incoming hoặc cấu hình riêng
            ], limit=1)
            # Fallback logic nếu cần chính xác "Loại trả lại"

        elif step == 'transfer':
            picking_type = self.env['stock.picking.type'].search([
                ('warehouse_id', '=', self.warehouse_id.id),
                ('code', '=', 'internal')
            ], limit=1)

        elif step == 'cancel':
            picking_type = self.env['stock.picking.type'].search([
                ('warehouse_id', '=', self.warehouse_id.id),
                ('code', '=', 'outgoing')
            ], limit=1)

            # Logic Location cho bước hủy: Source là Dest của bước Transfer
            prev_transfer = self.picking_ids.filtered(lambda p: p.picking_type_code == 'internal' and p.state == 'done')
            if prev_transfer:
                location_src_id = prev_transfer[-1].location_dest_id.id

        if not picking_type:
            raise UserError(f"Không tìm thấy loại hoạt động phù hợp cho bước {step}")

        # Gán Location mặc định nếu chưa được override
        if not location_src_id:
            location_src_id = picking_type.default_location_src_id.id
        if not location_dest_id:
            location_dest_id = picking_type.default_location_dest_id.id

        # Tạo Lines
        move_lines = []
        for line in self.line_ids:
            qty = 0
            if step == 'pick':
                qty = 0  # Yêu cầu = 0, sau cập nhật thực tế
            elif step == 'transfer':
                qty = line.qty_picked
            elif step == 'cancel':
                qty = line.qty_office_received

            # Nếu qty = 0 ở các bước sau thì skip (trừ bước pick đầu tiên nhập thực tế)
            if step != 'pick' and qty == 0:
                continue

            move_lines.append(Command.create({
                'product_id': line.product_id.id,
                'product_uom': line.uom_id.id,
                'product_uom_qty': qty,  # Nhu cầu
                'quantity': 0 if step == 'pick' else qty,  # Số lượng hoàn tất (cho trường hợp transfer/cancel)
                'name': line.product_id.name,
                'location_id': location_src_id,
                'location_dest_id': location_dest_id,
            }))

        vals = {
            'picking_type_id': picking_type.id,
            'location_id': location_src_id,
            'location_dest_id': location_dest_id,
            'origin': self.name,
            'cancel_request_id': self.id,
            'move_ids_without_package': move_lines,
        }
        return StockPicking.create(vals)
