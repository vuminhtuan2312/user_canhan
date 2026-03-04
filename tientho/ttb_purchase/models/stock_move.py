from odoo import *


class StockMove(models.Model):
    _inherit = 'stock.move'

    ttb_price_unit = fields.Float(string='Đơn giá', related='purchase_line_id.price_unit')
    ttb_discount = fields.Float(string='Chiết khấu %', compute='_compute_discount_and_tax')
    ttb_taxes_id = fields.Many2many(comodel_name='account.tax', string='Thuế', compute='_compute_discount_and_tax')

    product_image = fields.Binary('Hình ảnh sản phẩm', related='purchase_line_id.ttb_request_line_id.product_image')
    product_link = fields.Char('Link sản phẩm', related='purchase_line_id.ttb_request_line_id.product_link')

    @api.depends('purchase_line_id')
    def _compute_discount_and_tax(self):
        for rec in self:
            if rec.purchase_line_id:
                rec.ttb_discount = rec.purchase_line_id.discount
                rec.ttb_taxes_id = rec.purchase_line_id.taxes_id.ids
                rec.price_tax = 0.0
                rec.ttb_discount_amount = 0.0
            else:
                rec.ttb_discount = 0.0
                rec.ttb_taxes_id = False
                rec.price_tax = 0.0
                rec.ttb_discount_amount = 0.0

    def button_open_link_prd(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": self.product_link,
            "target": "new",
        }

    def _action_done(self, cancel_backorder=False):
        for rec in self:
            if rec.picking_id.picking_type_code == 'incoming' and rec.product_uom_qty and rec.quantity > (rec.product_uom_qty * (1 + rec.picking_id.partner_id.ttb_stock_limit)):
                raise exceptions.ValidationError('Không thể thực hiện nhập kho vượt quá số lượng nhu cầu')
        res = super()._action_done(cancel_backorder)
        for purchase in self.mapped('purchase_line_id.order_id'):
            purchase = purchase.sudo()
            if purchase.state == 'done': continue
            if purchase.order_line and all(line.qty_received >= line.product_qty for line in purchase.order_line):
                purchase.button_done()
        return res

    @api.onchange('quantity')
    def _ttb_onchange_quantity(self):
        if self.picking_id.picking_type_code == 'incoming' and self.product_uom_qty and self.quantity > (self.product_uom_qty * (1 + self.picking_id.partner_id.ttb_stock_limit)):
            self.quantity = min([self._origin.quantity, self.product_uom_qty * (1 + self.picking_id.partner_id.ttb_stock_limit)])
            return {
                'warning': {
                    'title': 'Cảnh báo!',
                    'message': 'Không thể thực hiện nhập kho vượt quá số lượng nhu cầu',
                }
            }

    def _prepare_base_line_for_taxes_computation(self):
        self.ensure_one()
        return self.env['account.tax']._prepare_base_line_for_taxes_computation(
            self,
            tax_ids=self.ttb_taxes_id,
            quantity=self.quantity,
            price_unit=self.ttb_price_unit,
            currency_id=self.picking_id.currency_id or self.picking_id.company_id.currency_id,
            discount = self.ttb_discount,
        )
