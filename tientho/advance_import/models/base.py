from odoo import api, models
from odoo.osv import expression

class BaseModel(models.AbstractModel):
    _inherit = "base"

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100) -> list[tuple[int, str]]:
        linking_fields = self.env.context.get('linking', [])
        for field in linking_fields:
            if self._name == linking_fields.get(field).get('field_model'):
                linking_via_field = linking_fields.get(field).get('linking_via_field')
                domain = expression.AND([[(linking_via_field, operator, name)]])
                records = self.search_fetch(domain, [linking_via_field], limit=limit)
                return [(record.id, record.display_name) for record in records.sudo()]

        return super().name_search(name, args, operator, limit)
