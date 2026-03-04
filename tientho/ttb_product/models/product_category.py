from odoo import api, fields, models, Command, _
from odoo.exceptions import ValidationError
from odoo.osv import expression
from itertools import product


class ProductCategory(models.Model):
    _inherit = "product.category"

    ttb_sequence_id = fields.Many2one(comodel_name='ir.sequence', string='Mã tăng dần', readonly=True, copy=False)
    active = fields.Boolean(default=True)
    sku_number = fields.Integer('Số SKU')
    ttb_tax_id = fields.Many2one('account.tax', 'Thuế bán')
    code_augges = fields.Char("Mã Augges", help="Mã ngành của danh mục trong Augges")

    def _create_ttb_sequence(self):
        self = self.sudo()
        for categ in self:
            if not categ.category_code:
                continue
            vals = {
                'name': _('%(categ)s Sequence %(code)s', categ=categ.name, code=categ.category_code),
                'prefix': categ.category_code[:4], 'padding': 6,
                'implementation': 'no_gap',
            }
            if not categ.ttb_sequence_id:
                seq = self.env['ir.sequence'].create(vals)
                categ.write({'ttb_sequence_id': seq.id})
            else:
                categ.ttb_sequence_id.write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        res._create_ttb_sequence()
        return res

    def write(self, vals):
        res = super().write(vals)
        if 'category_code' in vals:
            self._create_ttb_sequence()
        return res

    ttb_user_id = fields.Many2one(string='Người phụ trách', comodel_name='res.users')
    category_code = fields.Char('Mã MCH', index=True)
    category_level = fields.Integer('Cấp MCH', compute='_compute_category_level', store=True, recursive=True)
    mch_description = fields.Html(string='Hướng dẫn')

    @api.depends('parent_id', 'parent_id.category_level')
    def _compute_category_level(self):
        for rec in self:
            parent_level = rec.parent_id.category_level or 0
            rec.category_level = parent_level + 1

    @api.constrains('category_code')
    def _check_category_code(self):
        for rec in self:
            existed = self.sudo().search([('id', '!=', rec.id), ('category_code', '=', rec.category_code)], limit=1)
            if existed:
                raise ValidationError(_('Mã MCH %s đã được sử dụng', rec.category_code))

    complete_name = fields.Char(
        compute='_compute_complete_name1', recursive=False
    )

    @api.depends('name', 'category_code')
    def _compute_complete_name1(self):
        for category in self:
            if category.category_code:
                category.complete_name = '%s | %s' % (category.category_code, category.name)
            else:
                category.complete_name = category.name

    allowed_attribute_ids = fields.One2many(
        'product.category.attribute', 'category_id',
        string='Allowed Attributes'
    )

    attribute_value_rate_ids = fields.One2many(
        'product.category.attribute.value', 'category_id',
        string='Thiết lập tỉ lệ SKU'
    )

    # sku_number = fields.Integer('SKU xử lý')
    sku_by_attribute_ids = fields.One2many('ttb.sku.attribute', 'category_id', string='SKU theo thuộc tính')

    @api.onchange('allowed_attribute_ids')
    def onchange_allowed_attribute_ids(self):
        new_value_ids = self.allowed_attribute_ids.filtered(lambda x: x.sku_flag).value_ids._origin
        current_value_ids = self.attribute_value_rate_ids.value_id._origin

        delete_value_ids = current_value_ids.filtered(lambda x: x not in new_value_ids)
        add_value_ids = new_value_ids.filtered(lambda x: x not in current_value_ids)

        delete_ids = self.attribute_value_rate_ids.filtered(lambda x: x.value_id in delete_value_ids)

        self.attribute_value_rate_ids = [Command.delete(item.id) for item in delete_ids] + [Command.create({
            'category_id': self.id,
            'attribute_id': item.attribute_id.id,
            'value_id': item.id,
        }) for item in add_value_ids]

    def delete_combine(self):
        pass

    @api.onchange('attribute_value_rate_ids')
    def onchange_attribute_value_rate_ids(self):
        for rec in self:
            vals = []
            for line in rec.attribute_value_rate_ids.filtered(lambda x: x.sku_rate > 0):
                attribute_id = line.attribute_id.id
                new_vals = [{
                    'attributes': {attribute_id},
                    'value_ids': line.value_id,
                    'rate': line.sku_rate,
                    'name': line.value_id.name,
                    'level': 1,
                }]
                for item in vals:
                    new_vals.append(item)
                    if attribute_id not in item['attributes']:
                        new_vals.append({
                            'attributes': item['attributes'] | {attribute_id},
                            'value_ids': item['value_ids'] | line.value_id,
                            'rate': item['rate'] * line.sku_rate,
                            'name': '%s - %s' % (item['name'], line.value_id.name),
                            'level': item['level'] + 1
                        })
                vals = new_vals

            max_level = max([item['level'] for item in vals]) if vals else 0

            rec.sku_by_attribute_ids = [Command.clear()] + [Command.create({
                'category_id': rec.id,
                'name': item['name'],
                'rate': item['rate'],
                'value_ids': item['value_ids'].ids,
                # 'number': round(item['rate'] * rec.sku_number),
            }) for item in vals if item['level'] == max_level]
