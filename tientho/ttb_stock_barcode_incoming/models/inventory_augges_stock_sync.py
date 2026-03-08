from odoo import api, fields, models, _
from odoo.exceptions import UserError


class InventoryAuggesStockSync(models.Model):
    _name = "inventory.augges.stock.sync"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Đồng bộ tồn kho Augges"

    inventory_id = fields.Many2one(
        'period.inventory',
        string='Đợt kiểm kê',
        required=True
    )

    product_aug_id = fields.Char(
        string='ID sản phẩm Augges'
    )

    kho_id = fields.Many2one(
        'stock.picking.type',
        string='Kho bán lẻ',
    )

    qty = fields.Float(
        string='Tồn Augges T0'
    )

    mch2 = fields.Char(
        string='MCH2'
    )

    has_mch2 = fields.Boolean(
        string='Có MCH2',
        default=False
    )

    is_inventoried = fields.Boolean(
        string='Đã kiểm kê',
        default=False
    )