from odoo import *


class CallApiLog(models.Model):
    _name = 'api_call.log'
    _order = 'create_date desc, id desc'
    _description = 'API Call Log'

    user_id = fields.Many2one(string='User', comodel_name='res.users')
    res_model = fields.Char(string='Resource Model', index='trigram')
    res_id = fields.Integer(string='Resource ID')
    resource_ref = fields.Char(string='Record', compute='_compute_resource_ref')

    @api.depends('res_model', 'res_id')
    def _compute_resource_ref(self):
        for rec in self:
            if rec.res_id and rec.res_model:
                rec.resource_ref = '%s,%s' % (rec.res_model, rec.res_id or 0)
            else:
                rec.resource_ref = None

    api_type = fields.Char('API Type')
    name = fields.Char('System name')
    url = fields.Char('Request url')
    method = fields.Char('Request method')
    headers = fields.Text('Request headers', index='trigram')
    params = fields.Text('Request params', index='trigram')
    request_time = fields.Datetime('Request time')
    response_time = fields.Datetime('Response time')
    api_duration = fields.Float('Thời gian (ms)')
    response_status_code = fields.Char('Status code', help='Response status code')
    response_text = fields.Text('Response text', index='trigram')
    call_stack = fields.Text('Inspect call stack')
