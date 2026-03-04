from odoo import api, fields, models, _
from odoo.exceptions import UserError


class TTBRelatedContent(models.Model):
    _name = 'ttb.related.content'
    _description = 'Nội dung liên quan'

    name = fields.Char(string='Tên nội dung', required=True)
    ttb_description_id = fields.Many2one('ttb.description', string='Chủ đề')
    type = fields.Char(string='Loại Chủ đề', compute='_compute_type', store=True, readonly=False)

    @api.depends('ttb_description_id', 'ttb_description_id.type')
    def _compute_type(self):
        for record in self:
            if record.ttb_description_id:
                record.type = record.ttb_description_id.type
            else:
                record.type = 'other'

    level = fields.Selection([
        ('Nặng', 'Nặng'),
        ('Nhẹ', 'Nhẹ'),
        ('Không tính lỗi', 'Không tính lỗi')
    ], string='Cấp độ')
