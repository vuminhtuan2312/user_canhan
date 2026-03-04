from odoo import fields, models, api


class AdjustMch5Wizard(models.Model):
    _name = 'adjust.mch5.wizard'
    _description = 'Điều chỉnh MCH5'

    line_id = fields.Many2one('stock.check.line', string='Dòng kiểm tồn', required=True)
    categ_id_level_1 = fields.Many2one('product.category',
                                       string='MCH1',
                                       domain="[('parent_id', '=', False),('category_level', '=', 1)]",
                                       store=True, readonly=False
                                       )
    categ_id_level_2 = fields.Many2one('product.category',
                                       string='MCH2',
                                       domain="[('parent_id', '=?', categ_id_level_1),('category_level', '=', 2)]",
                                       store=True, readonly=False
                                       )
    categ_id_level_3 = fields.Many2one('product.category',
                                       string='MCH3',
                                       domain="[('parent_id', '=?', categ_id_level_2),('category_level', '=', 3)]",
                                       store=True, readonly=False
                                       )
    categ_id_level_4 = fields.Many2one('product.category',
                                       string='MCH4',
                                       domain="[('parent_id', '=?', categ_id_level_3),('category_level', '=', 4)]",
                                       store=True, readonly=False
                                       )
    categ_id_level_5 = fields.Many2one('product.category',
                                       string='MCH5',
                                       domain="[('parent_id', '=?', categ_id_level_4),('category_level', '=', 5)]",
                                       store=True, readonly=False,
                                       )

    def onchange_level(self, level):
        categ_id = self[f'categ_id_level_{level}']
        if level > 1 and categ_id:
            self[f'categ_id_level_{level - 1}'] = categ_id.parent_id

        for level_up in range(level + 1, 6):
            key = f'categ_id_level_{level_up}'
            key_parent = f'categ_id_level_{level_up - 1}'

            if not self[key_parent] or (self[key] and self[key].parent_id != self[key_parent]):
                self[key] = False

        for level_categ in range(5, 0, -1):
            key = f'categ_id_level_{level_categ}'
            if self[key] or level_categ == 1:
                break

    @api.onchange('categ_id_level_1')
    def onchange_level_1(self):
        self.onchange_level(1)

    @api.onchange('categ_id_level_2')
    def onchange_level_2(self):
        self.onchange_level(2)

    @api.onchange('categ_id_level_3')
    def onchange_level_3(self):
        self.onchange_level(3)

    @api.onchange('categ_id_level_4')
    def onchange_level_4(self):
        self.onchange_level(4)

    @api.onchange('categ_id_level_5')
    def onchange_level_5(self):
        self.onchange_level(5)

    def action_apply(self):
        self.ensure_one()
        if self.categ_id_level_5:
            self.line_id.categ_id = self.categ_id_level_5.complete_name

        return {'type': 'ir.actions.act_window_close'}

