from odoo import fields, models, api

class AddQtyWizard(models.TransientModel):
    _name = 'add.qty.wizard'
    _description = 'Nhập bổ sung số lượng'

    line_id = fields.Many2one('stock.check.line', string="Dòng kiểm tồn", required=True)
    qty_add = fields.Float(string="Số lượng bổ sung", required=True)

    def action_add_qty(self):
        for wizard in self:
            wizard.line_id.qty_real += wizard.qty_add
            wizard.line_id.last_qty_add = wizard.qty_add
        return {'type': 'ir.actions.act_window_close'}