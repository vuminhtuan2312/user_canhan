# -*- coding: utf-8 -*-
from odoo import models, fields, api

class TtbTaskProofImage(models.Model):
    _name = 'ttb.task.proof.image'
    _description = 'Ảnh minh chứng công việc vận hành'
    _order = 'sequence, id'

    task_id = fields.Many2one('ttb.operational.task', string='Công việc', required=True, ondelete='cascade')
    image = fields.Binary(string='Ảnh')
    media_type = fields.Selection([('image', 'Image'), ('video', 'Video')], string='Loại minh chứng')
    sequence = fields.Integer(string='Thứ tự', default=10)