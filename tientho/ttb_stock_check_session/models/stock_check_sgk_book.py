from odoo import models, fields, api

from odoo.exceptions import UserError


class StockCheckSgkBook(models.Model):
    _name = 'stock.check.sgk.book'
    _description = 'Kiểm tồn sách giáo khoa'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(default=lambda self: self.env['ir.sequence'].next_by_code('stock.check.sgk.book'), string='Mã phiên', tracking=True)
    user_id = fields.Many2one(string='Người tạo', comodel_name='res.users', default=lambda self: self.env.uid, readonly=True, tracking=True)
    branch_id = fields.Many2one(string='Cơ sở', comodel_name='ttb.branch', required=True, tracking=True)
    create_date = fields.Datetime(string='Ngày tạo', readonly=True, tracking=True)
    line_ids = fields.One2many(comodel_name='stock.check.sgk.book.line', inverse_name='session_id', string='Danh sách sản phẩm')
    active = fields.Boolean(default=True)
    state = fields.Selection(
        string="Trạng thái kiểm",
        selection=[
            ('draft', 'Đang chờ'),
            ('done', 'Hoàn thành')
        ],
        default='draft',
        tracking=True
    )
    user_by = fields.Many2one('res.users', string='Người thực hiện', tracking=True)
    done_date = fields.Datetime(string='Ngày hoàn thành', readonly=True, tracking=True)
    image_1920 = fields.Image(string="Ảnh sản phẩm", related='line_ids.image_1920', store=True)
    product_id = fields.Many2one(string="Tên sách", related='line_ids.product_id', store=True)
    note = fields.Char(string="Ghi chú")

    def action_mark_done(self):
        if self.line_ids.state_check == 'draft':
            raise UserError("Vui lòng kiểm hết sản phẩm trong phiên kiểm.")

        self.state = 'done'
        self.done_date = fields.Datetime.now()
        self.user_by = self.env.user.id

class StockCheckSgkBookLine(models.Model):
    _name = 'stock.check.sgk.book.line'
    _description = 'Chi tiết sản phẩm sách giáo khoa'

    session_id = fields.Many2one(comodel_name='stock.check.sgk.book', string='Phiên kiểm', required=True, readonly=1, tracking=True)
    product_id = fields.Many2one(comodel_name='product.product', string='Tên sách', tracking=True)
    stock_qty = fields.Float(string='Số lượng tồn', readonly=1, tracking=True)
    user_by = fields.Many2one('res.users', string='Người thực hiện', related='session_id.user_by', store=True, tracking=True)
    qty_real = fields.Float(string='Số lượng thực tế', readonly=1, tracking=True)
    diff_qty = fields.Float(string='Lệch', compute='_compute_diff_qty', store=True, readonly=1, help='Số lượng thực tế trừ số lượng lý thuyết', tracking=True)
    barcode = fields.Char(string='Mã vạch', tracking=True)
    state = fields.Selection(string='Trạng thái', related='session_id.state', store=True, readonly=1, tracking=True)
    can_check_inventory = fields.Boolean(compute='_compute_can_check_inventory')
    image_1920 = fields.Image(string="Ảnh sản phẩm", compute="_compute_image_1920", store=False)
    last_qty_add = fields.Float(string="SL bổ sung cuối", readonly=1, tracking=True)
    code_ncc = fields.Char(string='Mã nhà cung cấp', tracking=True)
    reference_code = fields.Char(string='Mã tham chiếu', tracking=True)
    done_date = fields.Datetime(string="Ngày hoàn thành", related='session_id.done_date', store=True, readonly=1, tracking=True)
    note = fields.Char(string="Ghi chú", tracking=True)
    time_done_real = fields.Datetime(string='Thời gian hoàn thành thực')
    barcode_k = fields.Char(string="Mã vạch K")
    state_check = fields.Selection(
        string='Trạng thái kiểm từng dòng', selection=[
            ('draft', 'Chưa kiểm'),
            ('done', 'Đã kiểm')
        ],
        default='draft', readonly=1)
    def _compute_image_1920(self):
        for line in self:
            image = self.env['ttb.product.image'].search(
                [('product_tmpl_id', '=', line.product_id.product_tmpl_id.id)],
                limit=1
            )
            line.image_1920 = image.image_1920 if image else False

    def _compute_can_check_inventory(self):
        self.can_check_inventory = False
        if self.session_id.user_by.id == self.env.uid:
            self.can_check_inventory = True

    def open_check_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Cập nhật tồn',
            'res_model': 'stock.check.sgk.book.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_line_id': self.id,
                'default_qty_real': self.qty_real
            }
        }

    @api.depends('qty_real', 'stock_qty')
    def _compute_diff_qty(self):
        for line in self:
            line.diff_qty = (line.qty_real or 0.0) - (line.stock_qty or 0.0)

    def open_add_qty_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Nhập bổ sung',
            'res_model': 'add.qty.sgk.book.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_line_id': self.id,
            }
        }