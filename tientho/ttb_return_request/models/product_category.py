from odoo import api, models, fields

class ProductCategory(models.Model):
    _inherit = 'product.category'

    rotation_return_days = fields.Integer(string="Vòng quay trả hàng (ngày)")

    @api.model
    def create(self, vals):
        if not vals.get('rotation_return_days') and vals.get('parent_id'):
            parent = self.browse(vals['parent_id'])
            if parent:
                vals['rotation_return_days'] = parent.rotation_return_days
        return super().create(vals)

    def write(self, vals):
        res = super().write(vals)
        if 'rotation_return_days' in vals:
            for rec in self:
                children = self.search([('parent_id', '=', rec.id)])
                children.write({'rotation_return_days': rec.rotation_return_days})
        return res
