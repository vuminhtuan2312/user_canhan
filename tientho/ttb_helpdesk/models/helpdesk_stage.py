from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError

from email.policy import default


class HelpdeskStage(models.Model):
    _inherit = "helpdesk.stage"

    use_for = fields.Selection([
        ('Mới', 'Mới'),
        ('Trao đổi nội bộ', 'Trao đổi nội bộ'),
        ('Đồng thuận', 'Đồng thuận'),
        ('Loại bỏ', 'Loại bỏ'),
        ('Hoàn thành', 'Hoàn thành'),
        ('Trễ hạn', 'Trễ hạn')
    ], string='Loại giai đoạn', tracking=True)
