from odoo import *


class ReturnrequestAddDiscount(models.TransientModel):
    _name = 'return.request.add.discount.wizard'
    _description = 'Chọn chiết khấu'

    discount = fields.Float(string='Chiết khấu (%)', default=0)

    def do(self):
        records = self.env[self._context.get('active_model')].browse(self._context.get('active_ids'))
        records.filtered(lambda x: x.state == 'draft').line_ids.write({'discount': self.discount})

