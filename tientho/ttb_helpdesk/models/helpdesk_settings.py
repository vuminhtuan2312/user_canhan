from email.policy import default

from odoo import fields, models, api

class HelpdeskSettings(models.Model):
    _name = 'helpdesk.settings'
    _description = 'Helpdesk Settings'
    _rec_name = "description"

    description = fields.Text(default='Cấu hình câu hỏi')
    shopping_experience_note = fields.Char('Ghi chú câu hỏi cho trải nghiệm khách hàng')
    introduce_to_others_note = fields.Char('Ghi chú Giới thiệu Tiến Thọ với người khác')
    improvement_suggestions_note = fields.Char('Ghi chú Tiến Thọ cải tiến vấn đề')

    @api.model
    def find_or_create_and_open(self):
        settings_record = self.env['helpdesk.settings'].search([], limit=1)
        if not settings_record:
            settings_record = self.env['helpdesk.settings'].create({})

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'helpdesk.settings',
            'view_mode': 'form',
            'res_id': settings_record.id,
            'target': 'inline',
            'name': 'Helpdesk Settings',
        }
