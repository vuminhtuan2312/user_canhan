from odoo import api, fields, models, _
from odoo.exceptions import UserError

class ProductMchSetter(models.Model):
    _name = 'product.mch.setter'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Gán MCH cho sản phẩm'
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.template', 'Sản phẩm', tracking=True)
    default_code = fields.Char('Mã sản phẩm', related='product_id.default_code', store=True, tracking=True)
    list_price = fields.Float('Giá bán', related='product_id.list_price', store=True, tracking=True)

    branch_id = fields.Many2one('ttb.branch', 'Cơ sở', tracking=True)
    user_id = fields.Many2one('res.users', 'Người xử lý', tracking=True)
    processed = fields.Boolean('Đã xử lý', default=False, compute='compute_processed', store=True, tracking=True)
    @api.depends('categ_id_level_1', 'categ_id_level_2', 'categ_id_level_3', 'categ_id_level_4', 'categ_id_level_5')
    def compute_processed(self):
        for rec in self:
            rec.processed = rec.categ_id_level_1 and rec.categ_id_level_2 and rec.categ_id_level_3 and rec.categ_id_level_4 and rec.categ_id_level_5
    menu_type = fields.Char('Menu', default='menu1')

    categ_id_level_1 = fields.Many2one('product.category',
                                       string='MCH1',
                                       domain="[('parent_id', '=', False),('category_level', '=', 1)]",
                                       store=True, readonly=False, tracking=True,
                                       )
    categ_id_level_2 = fields.Many2one('product.category',
                                       string='MCH2',
                                       domain="[('parent_id', '=?', categ_id_level_1),('category_level', '=', 2)]",
                                       store=True, readonly=False, tracking=True,
                                       )
    categ_id_level_3 = fields.Many2one('product.category',
                                       string='MCH3',
                                       domain="[('parent_id', '=?', categ_id_level_2),('category_level', '=', 3)]",
                                       store=True, readonly=False, tracking=True,
                                       )
    categ_id_level_4 = fields.Many2one('product.category',
                                       string='MCH4',
                                       domain="[('parent_id', '=?', categ_id_level_3),('category_level', '=', 4)]",
                                       store=True, readonly=False, tracking=True,
                                       )
    categ_id_level_5 = fields.Many2one('product.category',
                                       string='MCH5',
                                       domain="[('parent_id', '=?', categ_id_level_4),('category_level', '=', 5)]",
                                       store=True, readonly=False, tracking=True,
                                       )

    def onchange_level(self, level):
        categ_id = self[f'categ_id_level_{level}']
        # Gán lại cha. Chỉ cần gán lại 1 cấp sau đó sẽ có hiệu ứng dây chuyền
        if level > 1 and categ_id:
            self[f'categ_id_level_{level - 1}'] = categ_id.parent_id

        # Gán cấp con bằng False nếu không thỏa mãn quan hệ cha con.
        # Gán tất cả để tính được categ_id
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

    def action_processed_and_next(self):
        if not (self.categ_id_level_1 and self.categ_id_level_2 and self.categ_id_level_3 and self.categ_id_level_4 and self.categ_id_level_5):
            raise UserError('Chưa đủ thông tin MCH')

        self.write({'user_id': self.env.user.id, 'processed': True})
        # self.product_id.write({
        #     'categ_id_level_1': self.categ_id_level_1,
        #     'categ_id_level_2': self.categ_id_level_2,
        #     'categ_id_level_3': self.categ_id_level_3,
        #     'categ_id_level_4': self.categ_id_level_4,
        #     'categ_id_level_5': self.categ_id_level_5,
        # })

        next_product = self.search([('user_id', '=', False), ('menu_type', '=', self.menu_type), ('processed', '=', False)], limit=1)

        if next_product:
            next_product.user_id = self.env.user
            return {
                'type': 'ir.actions.act_window',
                'name': _('Thông tin MCH'),
                'res_model': 'product.mch.setter',
                'view_mode': 'form',
                'res_id': next_product.id,
            }

