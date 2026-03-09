# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    khu_vuc = fields.Selection([
        ('kvc', 'KVC'),
        ('kbl', 'KBL'),
        ('khac', 'Khác'),
    ], string='Khu vực', compute='_compute_khu_vuc', store=True)

    @api.depends('order_id.name')
    def _compute_khu_vuc(self):
        for line in self:
            order_name = (line.order_id.name or '').upper()

            if 'KVC' in order_name:
                line.khu_vuc = 'kvc'
            elif 'BL' in order_name:
                line.khu_vuc = 'kbl'
            else:
                line.khu_vuc = 'khac'

