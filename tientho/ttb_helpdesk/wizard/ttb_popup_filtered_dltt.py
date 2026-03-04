import ast
from odoo import api, fields, models, _

class TtbPopupFilteredDLTT(models.Model):
    _name = 'ttb.popup.filtered.dltt'
    _inherit = 'ttb.popup.filtered.base'
    _description = 'Lọc báo cáo CRM dltt'

    related_content_ids = fields.Many2many('ttb.related.content', string='Nội dung liên quan')
    level = fields.Selection([
        ('Nặng', 'Nặng'),
        ('Nhẹ', 'Nhẹ'),
        ('Không tính lỗi', 'Không tính lỗi')
    ], string='Mức độ')

    def btn_apply_filters(self):
        self.env['ttb.transaction.out.report'].get_data(self.get_report())
