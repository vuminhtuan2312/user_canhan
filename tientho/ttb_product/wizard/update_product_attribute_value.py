from odoo import fields, models, api
from odoo.exceptions import UserError

class UpdateProductAttributeValue(models.TransientModel):
    _name = 'update.product.attribute.value.wizard'
    _description = 'Popup cập nhật thuộc tính cho sản phẩm'

    product_id = fields.Many2one('product.template', 'Sản phẩm')

    attribute_line_ids = fields.One2many(
        'product.template.attribute.line.wizard',
        'wizard_id',
        'Product Attributes'
    )


    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        product = self.env['product.template'].browse(self._context.get('active_id'))

        lines = []
        allowed_attrs = product.categ_id_level_5.allowed_attribute_ids

        for attr_line in allowed_attrs:
            product_attr_line = product.attribute_line_ids.filtered(
                lambda l: l.attribute_id.id == attr_line.attribute_id.id
            )
            values = product_attr_line.value_ids.ids if product_attr_line else []

            lines.append((0, 0, {
                'attribute_id': attr_line.attribute_id.id,
                'mch5_value_ids': [(6, 0, attr_line.value_ids.ids)],
                'value_ids': [(6, 0, values)],
                'sequence': product_attr_line.sequence if product_attr_line else 10,
            }))

        res['product_id'] = product.id
        res['attribute_line_ids'] = lines
        return res

    def action_confirm(self):
        self.ensure_one()
        tmpl = self.product_id

        for line in self.attribute_line_ids:
            if not line.value_ids:
                raise UserError(
                    f"Hãy chọn ít nhất một giá trị cho thuộc tính: {line.attribute_id.name}"
                )

        # Tiếp tục cập nhật như cũ
        current_lines = {l.attribute_id.id: l for l in tmpl.attribute_line_ids}
        wizard_lines = {l.attribute_id.id: l for l in self.attribute_line_ids}

        attr_ids_in_wizard = set(wizard_lines.keys())
        attr_ids_in_current = set(current_lines.keys())

        unlink_commands = [(2, current_lines[attr_id].id, 0)
                           for attr_id in attr_ids_in_current - attr_ids_in_wizard]

        update_commands = []
        for attr_id in attr_ids_in_current & attr_ids_in_wizard:
            line = current_lines[attr_id]
            values = wizard_lines[attr_id].value_ids.ids
            update_commands.append((1, line.id, {'value_ids': [(6, 0, values)]}))

        create_commands = []
        for attr_id in attr_ids_in_wizard - attr_ids_in_current:
            wizard_line = wizard_lines[attr_id]
            create_commands.append((0, 0, {
                'attribute_id': attr_id,
                'value_ids': [(6, 0, wizard_line.value_ids.ids)],
                'sequence': wizard_line.sequence,
            }))

        tmpl.write({
            'attribute_line_ids': unlink_commands + update_commands + create_commands
        })

        return {'type': 'ir.actions.act_window_close'}




class ProductTemplateAttributeLineWizard(models.TransientModel):
    _name = 'product.template.attribute.line.wizard'
    _description = "Product Template Attribute Line Wizard"

    wizard_id = fields.Many2one(
        'update.product.attribute.value.wizard',
        required=True,
        string='Wizard'
    )

    sequence = fields.Integer("Sequence", default=10)

    attribute_id = fields.Many2one(
        comodel_name='product.attribute',
        string="Thuộc tính",
        ondelete='restrict',
        required=True,
        index=True)

    mch5_value_ids = fields.Many2many(
        comodel_name='product.attribute.value',
        relation='product_tmpl_attr_line_wizard_mch5_rel',  # tên M2M khác biệt
        string='Giá trị được phép chọn'
    )

    value_ids = fields.Many2many(
        comodel_name='product.attribute.value',
        relation='product_tmpl_attr_line_wizard_val_rel',  # tên M2M khác biệt
        string="Giá trị",
        domain="[('attribute_id', '=', attribute_id), ('id', 'in', mch5_value_ids)]",
        ondelete='restrict')