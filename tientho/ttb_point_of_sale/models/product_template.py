from odoo import fields, models, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    duplicate_product_ids = fields.Many2many(
        comodel_name='product.template',
        relation='product_template_duplicate_rel',
        column1='src_id',
        column2='dup_id',
        string='Sản phẩm trùng mã hàng',
    )

    def write(self, vals):
        if 'duplicate_product_ids' in vals and not self.env.context.get('syncing_duplicates'):
            for product in self:
                # Lưu trạng thái cũ
                old_ids = set(product.duplicate_product_ids.ids)

                # Thực hiện lưu trước để có dữ liệu mới
                res = super(ProductTemplate, product).write(vals)

                # Trạng thái mới
                new_ids = set(product.duplicate_product_ids.ids)

                # Xác định sản phẩm được thêm và bị gỡ
                added_ids = new_ids - old_ids
                removed_ids = old_ids - new_ids

                # Thêm liên kết ngược
                if added_ids:
                    for pid in added_ids:
                        other = self.browse(pid)
                        if product.id not in other.duplicate_product_ids.ids:
                            other.with_context(syncing_duplicates=True).write({
                                'duplicate_product_ids': [(4, product.id)]
                            })

                # Gỡ liên kết ngược
                if removed_ids:
                    for pid in removed_ids:
                        other = self.browse(pid)
                        if product.id in other.duplicate_product_ids.ids:
                            other.with_context(syncing_duplicates=True).write({
                                'duplicate_product_ids': [(3, product.id)]
                            })
                return res
        else:
            return super(ProductTemplate, self).write(vals)