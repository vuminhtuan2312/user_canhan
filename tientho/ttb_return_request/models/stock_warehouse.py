from odoo import models, fields, api
from odoo.exceptions import UserError

class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    return_type_id = fields.Many2one('stock.picking.type', 'Loại trả lại', check_company=True, copy=False)

class TtbBranch(models.Model):
    _inherit = "ttb.branch"

    ttb_branch_region = fields.Selection(
        [
            ("HN", "Hà Nội"),
            ("MB", "Miền Bắc"),
            ("MN", "Miền Nam"),
        ],
        string="Khu vực",
        help="Dùng để xác định cơ sở trả hàng theo khu vực (HN/MB/MN).",
    )