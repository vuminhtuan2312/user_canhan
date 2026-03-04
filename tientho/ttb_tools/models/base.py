from odoo import api, models

class BaseModel(models.AbstractModel):
    _inherit = "base"

    def smart_button_action(self, xml_id):
        action = self.env["ir.actions.actions"]._for_xml_id(xml_id)
        if len(self) == 1:
            action.update({
                'res_id': self.id,
                'view_mode': 'form',
                'views': [(False, 'form')],
                'target': 'current',
            })
        else:
            action.update({
                'domain': [('id', 'in', self.ids)],
                'view_mode': 'tree,form',
            })
        return action
