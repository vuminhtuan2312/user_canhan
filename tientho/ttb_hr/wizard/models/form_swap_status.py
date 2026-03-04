from odoo.exceptions import UserError
from odoo import api, fields, models

class FormSwapStatus(models.TransientModel):
    _name = 'form.swap.status'
    _description = 'Form Swap Status'

    plan_recruitment_id = fields.Many2one('plan.of.recruitment')
    status = fields.Selection([('new', 'Mới'), ('doing', 'Đang làm'), ('done', ' Hoàn thành'), ('cancel', 'Hủy')],
                              string='Trạng thái', default='new')

    def button_confirm(self):
        self.plan_recruitment_id.status = self.status
