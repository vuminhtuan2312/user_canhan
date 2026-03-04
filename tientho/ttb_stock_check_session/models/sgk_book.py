from odoo import fields, models, api

class SgkBook(models.Model):
    _name = 'sgk.book'
    _description = 'Thông tin sách giáo khoa'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(default=lambda self: self.env['ir.sequence'].next_by_code('sgk.book'), string='Mã kiểm')
    name_sgk = fields.Char(string="Tên sách")
    subject_id = fields.Many2one('sgk.subject', string='Môn học')
    grade_id = fields.Many2one('sgk.grade', string='Lớp học')
    volume_id = fields.Many2one('sgk.volume', string='Tập')
    series_id = fields.Many2one('sgk.series', string='Bộ SGK')
    stock_value = fields.Integer(string='Tồn kho', tracking=True)
    image_ids = fields.Many2many(string="Ảnh barcode", comodel_name='ir.attachment')
    ttb_branch_id = fields.Many2one(comodel_name='ttb.branch', string='Cơ sở')
    user_id = fields.Many2one(comodel_name='res.users', string='Người kiểm', tracking=True)
    state = fields.Selection(
        string="Trạng thái kiểm",
        selection=[
            ('draft', 'Đang chờ'),
            ('done', 'Hoàn thành')
        ],
        default='draft'
    )
    done_date = fields.Datetime(string='Ngày hoàn thành', readonly=True)
    can_check_inventory = fields.Boolean(
        compute='_compute_can_check_inventory'
    )
    related_image_ids = fields.Many2many(
        comodel_name='ir.attachment',
        string='Tất cả ảnh barcode theo tên sách',
        compute='_compute_related_images'
    )

    @api.depends('name_sgk')
    def _compute_related_images(self):
        for record in self:
            if record.name_sgk:
                same_books = self.env['sgk.book'].search([('name_sgk', '=', record.name_sgk)])
                all_attachments = same_books.mapped('image_ids')
                record.related_image_ids = all_attachments
            else:
                record.related_image_ids = False
    def action_mark_done(self):
        self.state = 'done'
        self.done_date = fields.Datetime.now()
        self.user_id = self.env.user

    def _compute_can_check_inventory(self):
        self.can_check_inventory = False
        if self.user_id.id == self.env.uid:
            self.can_check_inventory = True

    def open_add_stock_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Nhập bổ sung',
            'res_model': 'add.stock.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sgk_id': self.id,
            }
        }
class SgkSubject(models.Model):
    _name = 'sgk.subject'
    _description = 'Môn học'

    name = fields.Char(string='Tên môn học', required=True)

class SgkGrade(models.Model):
    _name = 'sgk.grade'
    _description = 'Lớp học'

    name = fields.Char(string='Tên lớp', required=True)

class SgkVolume(models.Model):
    _name = 'sgk.volume'
    _description = 'Tập'

    name = fields.Char(string='Tên tập', required=True)

class SgkSeries(models.Model):
    _name = 'sgk.series'
    _description = 'Bộ sách'

    name = fields.Char(string='Tên bộ SGK', required=True)
