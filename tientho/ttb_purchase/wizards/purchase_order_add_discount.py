from odoo import *


class PurchaseOrderAddDiscount(models.TransientModel):
    _name = 'purchase.order.add.discount.wizard'
    _description = 'Chọn chiết khấu'

    discount = fields.Float(string='Chiết khấu (%)', default=0)
    discount_money = fields.Float(string='Chiết khấu (tệ)', default=0)

    def do(self):
        records = self.env[self._context.get('active_model')].browse(self._context.get('active_ids'))
        if not self._context.get('money', False):
            records.filtered(lambda x: x.state == 'draft').order_line.write({'discount': self.discount, 'discount_type': 'percent'})
        else:
            for rec in records.filtered(lambda x: x.state == 'draft'):
                discount_money = self.discount_money * rec.exchange_rate / rec.ttb_quantity_total
                rec.order_line.write({'ttb_discount_amount': discount_money, 'discount_type': 'money'})
        return
