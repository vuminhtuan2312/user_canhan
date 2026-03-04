from odoo import *
from odoo import api, Command, fields, models, SUPERUSER_ID, _
from odoo.exceptions import UserError, ValidationError

class DeliveryOrder(models.Model):
    _name = 'delivery.order'
    _description = 'Delivery Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Tên phiếu', required=True, copy=False,)
    delivery_order_ids = fields.One2many('delivery.order.line', 'delivery_order_id', string='Chi tiết phiếu')
    shipment_date = fields.Date(string='Ngày xuất hàng', required=True, default=fields.Date.context_today)
    state = fields.Selection([
        ('draft', 'Mới'),
        ('confirmed', 'Xác nhận'),
        ('cancelled', 'Hủy bỏ'),
    ], string='Trạng thái', default='draft', tracking=True)
    notes = fields.Text(string='Ghi chú')

    def action_confirm(self):
        self.ensure_one()
        for rec in self.delivery_order_ids:
            rec.stock_picking_id.confirm_shipping_ticket()
        self.state = 'confirmed'

    def action_cancel(self):
        self.ensure_one()
        self.state = 'cancelled'

class DeliveryOrderLine(models.Model):
    _name = 'delivery.order.line'
    _description = 'Delivery Order Line'

    delivery_order_id = fields.Many2one('delivery.order', string='Phiếu giao hàng', required=True, ondelete='cascade')
    stock_picking_id = fields.Many2one('stock.picking', string='Phiếu điều chuyển', required=True)
    purchase_order_id = fields.Many2one('purchase.order', string='Đơn mua hàng', related='stock_picking_id.purchase_id')
    cbm_total = fields.Float(string='Tổng CBM', related='stock_picking_id.cbm_total')
    number_of_cases_total = fields.Float(string='Tổng số kiện', related='stock_picking_id.number_of_cases_total')