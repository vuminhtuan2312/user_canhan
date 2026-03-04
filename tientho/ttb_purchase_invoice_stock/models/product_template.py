from odoo import api, models, fields
from odoo.addons.ttb_tools.ai import product_similar_matcher as ttb_ai


class ProductTemplate(models.Model):
    _inherit = "product.template"

    ai_vector = fields.Text(
        string='AI Vector (JSON)',
        copy=False,
    )
    ttb_bom_ids = fields.One2many('ttb.mrp.bom', 'product_tmpl_id', 'Bill of Materials')
    categ_id_level_5_by_human = fields.Boolean('MCH5 ngành hàng')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'name' in vals and 'ai_vector' not in vals:
                vals['ai_vector'] = ttb_ai.get_vector_json(vals['name'])
        return super().create(vals_list)

    def write(self, vals):
        if 'name' in vals:
            for rec in self:
                if 'ai_vector' not in vals and rec.name != vals['name']:
                    vals['ai_vector'] = ttb_ai.get_vector_json(vals['name'])
                    break

        return super().write(vals)

    def _compute_ai_vector(self):
        has_names = self.filtered(lambda x: x.name)
        ai_vectors = ttb_ai.get_vectors_json(has_names.mapped('name'))
        i = 0
        for rec in has_names:
            rec.ai_vector = ai_vectors[i]
            i += 1
