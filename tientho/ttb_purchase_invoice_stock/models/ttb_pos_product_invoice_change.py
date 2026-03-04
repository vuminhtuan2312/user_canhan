from odoo import api, fields, models, _
from odoo import tools
from odoo.exceptions import UserError

class TtbPosProductInvoiceChange(models.Model):
    _name = 'ttb.pos.product.invoice.change'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Xác nhận sản phẩm thay thế'
    _order = "change_tax_ids_amount, id"

    pos_line_id = fields.Many2one(string='Chi tiết đơn hàng', comodel_name='pos.order.line', index=True)
    pos_id = fields.Many2one(string='Mã đơn', comodel_name='pos.order', readonly=True)
    location_id = fields.Many2one(string='Địa điểm', comodel_name='stock.location', related='pos_id.warehouse_id.lot_stock_id')
    product_origin_id = fields.Many2one(string='Sản phẩm', comodel_name='product.product', readonly=True, index=True)
    qty_origin = fields.Float(string='Số lượng', readonly=True)
    qty_needed = fields.Float(string='Số lượng cần', readonly=True)
    qty = fields.Float(string='Tồn hiện có', compute='_compute_qty')
    diff_name = fields.Float('Tương hợp về tên')
    stock_name_number = fields.Integer('Số sản phẩm có tồn thoả mãn')

    @api.depends('product_change_id')
    def _compute_qty(self):
        for rec in self:
            rec.qty = rec.product_change_id.with_context(location=rec.location_id.id).free_qty

    origin_product_price = fields.Float('Giá sản phẩm gốc', related='pos_line_id.price_unit', store=True)
    product_change_id = fields.Many2one(string='Sản phẩm thay thế', comodel_name='product.product', 
        domain="[('list_price', '>=', origin_product_price * 0.85), ('list_price', '<=', origin_product_price * 1.15)]",
        index=True
    )

    # Các trường nối tới bảng cha. Mỗi tab là 1 trường nối
    pos_change_id = fields.Many2one(string='Pos sp thay thế', comodel_name='ttb.pos.invoice', index=True)
    pos_not_change_id = fields.Many2one(string='Pos sp ko thay thế', comodel_name='ttb.pos.invoice', index=True)
    pos_delete_id = fields.Many2one(string='Pos xoá sản phẩm', comodel_name='ttb.pos.invoice', index=True)
    pos_notax_id = fields.Many2one(string='Pos dòng ko thuế', comodel_name='ttb.pos.invoice', index=True)
    # pos_hastax_id = fields.Many2one(string='Pos dòng có thuế', comodel_name='ttb.pos.invoice', index=True)

    tax_ids = fields.Many2many('account.tax', string='Thuế', domain="[('type_tax_use', '=', 'sale')]")

    origin_tax_ids = fields.Many2many('account.tax', string='Thuế gốc', related='pos_line_id.tax_ids')
    change_tax_ids = fields.Many2many('account.tax', string='Thuế sptt', related='product_change_id.taxes_id', readonly=False)

    tax_ids_amount = fields.Float('% Thuế', compute="compute_tax_ids_amount", store=True)
    origin_tax_ids_amount = fields.Float('% Thuế gốc', compute="compute_origin_tax_ids_amount", store=True)
    change_tax_ids_amount = fields.Float('% Thuế sptt', compute="compute_change_tax_ids_amount", store=True)
    is_change = fields.Boolean('Thay đổi thuế', default=False)

    @api.onchange('tax_ids')
    def onchange_tax_ids(self):
        for rec in self:
            rec.is_change = True

    @api.depends('tax_ids')
    def compute_tax_ids_amount(self):
        for rec in self:
            rec.tax_ids_amount = rec.tax_ids[:1].amount

    @api.depends('origin_tax_ids')
    def compute_origin_tax_ids_amount(self):
        for rec in self:
            rec.origin_tax_ids_amount = rec.origin_tax_ids[:1].amount

    @api.depends('change_tax_ids')
    def compute_change_tax_ids_amount(self):
        for rec in self:
            rec.change_tax_ids_amount = rec.change_tax_ids[:1].amount


class TtbPosProductFixChange(models.Model):
    _name = 'ttb.pos.product.fix.change'
    _inherit = ['mail.thread']
    _description = 'Sản phẩm thay thế cố định'

    product_id = fields.Many2one('product.product', 'Sản phẩm', context={'active_test': False}, tracking=1)
    change_product_id = fields.Many2one('product.product', 'Sản phẩm thay thế', context={'active_test': False}, tracking=1)
    active = fields.Boolean(tracking=1)

class TtbPosProductNoChange(models.Model):
    _name = 'ttb.pos.product.no.change'
    _inherit = ['mail.thread']
    _description = 'Sản phẩm không thay thế'

    product_id = fields.Many2one('product.product', 'Sản phẩm', context={'active_test': False})
    active = fields.Boolean(tracking=1)

