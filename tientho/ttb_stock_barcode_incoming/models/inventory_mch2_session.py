from odoo import models, fields

class InventoryMCH2Session(models.Model):
    _name = 'inventory.mch2.session'
    _description = 'Phiên kiểm kê MCH2'

    # Đợt kiểm kê tổng
    inventory_id = fields.Many2one(
        'period.inventory',
        string='Đợt kiểm kê',
        required=True
    )

    # Nhóm MCH2 đang kiểm kê
    mch2 = fields.Char(
        string='MCH2'
    )

    # Trạng thái workflow
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('in_progress', 'In Progress'),
            ('done', 'Done'),
            ('cancel', 'Cancel')
        ],
        string='Trạng thái',
        default='draft',
        tracking=True
    )

    # Thời điểm bắt đầu
    start_time = fields.Datetime(
        string='Thời điểm bắt đầu'
    )

    # Thời điểm kết thúc
    end_time = fields.Datetime(
        string='Thời điểm kết thúc'
    )

    # Danh sách phiếu kiểm kê
    phieu_kk_ids = fields.One2many(
        'stock.picking',
        'phieu_kk_id',
        string='Danh sách phiếu KK'
    )

    # Danh sách phiếu hậu kiểm 1
    hk1_ids = fields.One2many(
        'stock.picking',
        'hk1_id',
        string='Danh sách phiếu HK1'
    )

    # Phiếu hậu kiểm A (sản phẩm chưa kiểm kê)
    hk_a_ids = fields.One2many(
        'stock.picking',
        'hk_a_id',
        string='Danh sách phiếu HK-A'
    )