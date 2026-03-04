# -*- coding: utf-8 -*-
from odoo import models, fields, api

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    ttb_job_category = fields.Selection(
        selection=[
            ('playground', 'Khu vui chơi'),
            ('retail', 'Bán lẻ'),
            ('warehouse', 'Kho'),
            ('other', 'Khác')
        ],
        string='Phân loại công việc',
        help="Logic ưu tiên phân công dựa trên loại công việc"
    )

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        area_id = self.env.context.get('prioritize_area_id')

        if not area_id:
            return super().name_search(name, args, operator, limit)

        # Ưu tiên khu vực: tối đa 10 người, toàn bộ ưu tiên (thuộc khu vực) xếp trên đầu
        max_display = 10
        prioritized = super().name_search(
            name, args + [('ttb_area_ids', 'in', [area_id])], operator, max_display
        )
        if len(prioritized) >= max_display:
            return prioritized[:max_display]
        prioritized_ids = {p[0] for p in prioritized}
        need = max_display - len(prioritized)
        others_raw = super().name_search(name, args, operator, max_display + len(prioritized_ids))
        others = [(i, n) for i, n in others_raw if i not in prioritized_ids][:need]
        return prioritized + others