import ast
from odoo import api, fields, models, _

class TtbPopupFilteredCSKH(models.Model):
    _name = 'ttb.popup.filtered.cskh'
    _inherit = 'ttb.popup.filtered.base'
    _description = 'Lọc báo cáo CRM cskh'

    survey_state = fields.Selection([
        ('to_call', 'Cần gọi'),
        ('success', 'HPC thành công'),
        ('refuse', 'Từ chối phỏng vấn'),
        ('wrong_number', 'Sai số khách hàng báo'),
        ('follow_up', 'Theo dõi'),
        ('no_contact', 'Không liên lạc được'),
        ('no_answer', 'Không nghe máy'),
    ], string='Trạng thái khảo sát')
    user_id = fields.Many2one('res.users', string='Người xử lý')

    def btn_apply_filters(self):
        self.env['ttb.kpi.report'].get_data(self.get_report())
