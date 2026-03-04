# -*- coding: utf-8 -*-
from odoo import models, fields

class TtbArea(models.Model):
    _inherit = 'ttb.area'

    # Thay đổi logic: Một khu vực có thể thuộc nhiều cơ sở
    ttb_branch_ids = fields.Many2many(
        comodel_name='ttb.branch',
        string='Cơ sở',
        help="Khu vực này thuộc về các cơ sở nào"
    )

    type = fields.Selection(
        selection=[
            ('playground', 'Khu vui chơi'),
            ('retail', 'Bán lẻ'),
            ('warehouse', 'Kho'),
            ('other', 'Khác')
        ],
        string='Loại khu vực',
        default='playground'
    )