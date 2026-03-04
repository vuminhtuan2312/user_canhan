import ast
from odoo import api, fields, models, _

class TtbPopupFilteredHPC(models.Model):
    _name = 'ttb.popup.filtered.hpc'
    _inherit = 'ttb.popup.filtered.base'
    _description = 'Lọc báo cáo CRM hpc'

    related_content_ids = fields.Many2many('ttb.related.content', string='Nội dung liên quan')
    level = fields.Selection([
        ('Nặng', 'Nặng'),
        ('Nhẹ', 'Nhẹ'),
        ('Không tính lỗi', 'Không tính lỗi')
    ], string='Mức độ')

    def btn_apply_filters(self):
        self.env['ttb.hpc.out.report'].get_data(self.get_report())
