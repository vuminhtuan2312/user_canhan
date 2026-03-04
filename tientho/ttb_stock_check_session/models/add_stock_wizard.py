from odoo import api, models, fields

class AddStockWizard(models.TransientModel):
    _name = 'add.stock.wizard'
    _description = 'Cập nhật tồn bổ sung'

    qty_add = fields.Float(string="Số lượng bổ sung", required=True)
    sgk_id = fields.Many2one(comodel_name='sgk.book', string='SGK')

    def action_add_qty(self):
        for wizard in self:
            wizard.sgk_id.stock_value += wizard.qty_add
        return {'type': 'ir.actions.act_window_close'}