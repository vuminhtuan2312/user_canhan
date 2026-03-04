from odoo import fields, models, api

class AddQtyKvcWizard(models.TransientModel):
    _name = 'add.qty.kvc.wizard'
    _description = 'Nhập bổ sung số lượng'

    line_id = fields.Many2one('kvc.inventory.line', string="Dòng kiểm tồn", required=True)
    qty_add = fields.Float(string="Số lượng bổ sung", required=True)

    def action_add_qty(self):
        for wizard in self:
            wizard.line_id.qty_real += wizard.qty_add
            wizard.line_id.last_qty_add = wizard.qty_add
        return {'type': 'ir.actions.act_window_close'}