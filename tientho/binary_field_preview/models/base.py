from odoo import models, fields, api
import mimetypes

class BaseModel(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def get_attachment_preview(self, model, field_name, record_id):
        record = self.env[model].browse(record_id)
        if not record.exists():
            return {}
        attachment = self.env['ir.attachment'].search([
            ('res_model', '=', model),
            ('res_field', '=', field_name),
            ('res_id', '=', record_id)
        ], limit=1)
        if attachment:
            mimetype = attachment.mimetype or mimetypes.guess_type(attachment.name)[0]
            return {
                'id': attachment.id,
                'name': attachment.name,
                'mimetype': mimetype,
                'url': f'/web/content/{attachment.id}',
            }
        return {}