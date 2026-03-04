from odoo import fields, models, api
from odoo.exceptions import UserError

class BarcodeChangeRequest(models.Model):
    _name = 'barcode.change.request'
    _description = 'Yêu cầu chuyển mã'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'ttb.approval.mixin']

    name = fields.Char(string='Mã phiếu', required=True, readonly=True, copy=False, default='Mới')
    branch_id = fields.Many2one(string='Cơ sở', comodel_name='ttb.branch',     default=lambda self: self.env.user.ttb_branch_ids[:1].id)
    warehouse_export_id = fields.Many2one('stock.warehouse', string='Kho xuất', domain="[('ttb_branch_id', '=', branch_id)]")
    warehouse_import_id = fields.Many2one('stock.warehouse', string='Kho nhập', domain="[('ttb_branch_id', '=', branch_id)]")
    description = fields.Char(string='Diễn giải')
    note = fields.Text(string='Ghi chú')
    request_date = fields.Datetime(string='Ngày đề nghị', default= fields.Datetime.now)
    request_user_id = fields.Many2one('res.users', string='Người đề nghị', default=lambda self: self.env.user, tracking=True)
    approve_date = fields.Datetime(string='Ngày phê duyệt')
    state = fields.Selection([
        ('draft', 'Mới'),
        ('pending', 'Chờ duyệt'),
        ('done', 'Đã duyệt'),
        ('cancel', 'Hủy'),
    ], default='draft', tracking=True)

    line_ids = fields.One2many('barcode.change.request.line', 'request_id', string='Chi tiết sản phẩm')
    import_stock_picking_id = fields.Many2one('stock.picking', string='Phiếu nhập kho')
    export_stock_picking_id = fields.Many2one('stock.picking', string='Phiếu xuất kho')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == 'Mới':
                vals['name'] = self.env['ir.sequence'].next_by_code('barcode.change.request') or 'Mới'
        return super().create(vals_list)

    def action_send_approve(self):
        if self.state != 'draft': return
        if not self.sent_ok: return

        process_id, approval_line_ids = self.get_approval_line_ids()
        self.write({'process_id': process_id.id,
                    'date_sent': fields.Datetime.now(),
                    'state': 'pending',
                    'approval_line_ids': [(5, 0, 0)] + approval_line_ids})
        if self.env.user.id not in self.current_approve_user_ids.ids:
            self.send_notify(message='Bạn cần duyệt phiếu yêu cầu chuyển mã', users=self.current_approve_user_ids, subject='Yêu cầu chuyển mã')
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
                'state': 'done',
                'approve_date': fields.Datetime.now()
            })
            self._create_picking_change_request()

            self.send_notify(
                message=f'Phiếu yêu cầu chuyển mã {self.name} đã được duyệt, vui lòng kiểm tra phiếu xuất và nhập kho',
                users=self.request_user_id,
                subject='Yêu cầu chuyển mã'
            )
        return True

    def action_cancel(self):
        self.write({
            'state': 'draft'
        })

    def _create_picking_change_request(self):
        self.ensure_one()
        if not self.warehouse_export_id or not self.warehouse_import_id:
            raise UserError('Vui lòng chọn kho xuất và kho nhập trước khi duyệt yêu cầu chuyển mã')

        # Prepare move values for export picking
        export_moves = []
        for line in self.line_ids:
            export_moves.append((0, 0, {
                'name': line.product_from_id.display_name,
                'product_id': line.product_from_id.id,
                'product_uom': line.product_from_id.uom_id.id,
                'product_uom_qty': line.qty_export,
                'location_id': self.warehouse_export_id.lot_stock_id.id,
                'location_dest_id': self.warehouse_import_id.lot_stock_id.id,
            }))

        # Create export picking
        export_picking = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse_export_id.out_type_id.id,
            'location_id': self.warehouse_export_id.lot_stock_id.id,
            'location_dest_id': self.warehouse_import_id.lot_stock_id.id,
            'scheduled_date': self.approve_date or fields.Datetime.now(),
            'origin': self.name,
            'barcode_request_id': self.id,
            'move_ids_without_package': export_moves,
        })

        # Prepare move values for import picking
        import_moves = []
        for line in self.line_ids:
            import_moves.append((0, 0, {
                'name': line.product_to_id.display_name,
                'product_id': line.product_to_id.id,
                'product_uom': line.product_to_id.uom_id.id,
                'product_uom_qty': line.qty_import,
                'location_id': self.warehouse_export_id.lot_stock_id.id,
                'location_dest_id': self.warehouse_import_id.lot_stock_id.id,
            }))

        # Create import picking
        import_picking = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse_import_id.in_type_id.id,
            'location_id': self.warehouse_export_id.lot_stock_id.id,
            'location_dest_id': self.warehouse_import_id.lot_stock_id.id,
            'scheduled_date': self.approve_date or fields.Datetime.now(),
            'origin': self.name,
            'barcode_request_id': self.id,
            'move_ids_without_package': import_moves,
        })

        self.write({
            'export_stock_picking_id': export_picking.id,
            'import_stock_picking_id': import_picking.id,
        })
