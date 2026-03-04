from odoo import api, fields, models, _


class TtbTaskCategory(models.Model):
    _name = 'ttb.task.category'
    _description = 'Danh mục nhiệm vụ'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _default_sequence(self):
        return (self.search([], order="sequence desc", limit=1).sequence or 0) + 1

    name = fields.Char(string='Danh mục', required=True)
    sequence = fields.Integer(string='Thứ tự', required=True, default=_default_sequence)
    company_id = fields.Many2one(comodel_name='res.company', string='Công ty', index=True, default=lambda self: self.env.company)