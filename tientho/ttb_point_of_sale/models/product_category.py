from odoo import models, api, fields


class ProductCategory(models.Model):
    _inherit = 'product.category'

    order_threshold = fields.Float(string="Ngưỡng đặt hàng (số ngày)")
    rotation_days = fields.Integer(string="Vòng quay (ngày)")

    @api.model
    def create(self,vals):
        if not vals.get('rotation_days') and vals.get('parent_id'):
            parent = self.browse(vals['parent_id'])
            if parent:
                vals['rotation_days'] = parent.rotation_days
        return super().create(vals)

    def write(self, vals):
        res = super().write(vals)
        if 'rotation_days' in vals:
            for rec in self:
                children = self.search([('parent_id', '=', rec.id)])
                children.write({'rotation_days': rec.rotation_days})
        return res