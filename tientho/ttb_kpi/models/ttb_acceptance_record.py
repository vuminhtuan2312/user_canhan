from odoo import models, api, fields

class TtbAcceptanceRecord(models.Model):
    _name = 'ttb.acceptance.record'
    _description = 'Phiếu nghiệm thu'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model
    def default_get(self, fields):
        result = super(TtbAcceptanceRecord, self).default_get(fields)
        if self._context.get('kpi_type_id', False) == 'ANAT':
            result['kpi_type_id'] = self.env.ref('ttb_kpi.ttb_kpi_type_anat')
        if self._context.get('kpi_type_id', False) == 'PCCC':
            result['kpi_type_id'] = self.env.ref('ttb_kpi.ttb_kpi_type_pccc')
        return result

    name = fields.Char(string='Mã nghiệm thu', required=True, readonly=True, default='Mới', copy=False)
    user_id = fields.Many2one(string='Người nghiệm thu', comodel_name='res.users', default=lambda self: self.env.user, required=True)
    kpi_type_id = fields.Many2one(string='Loại KPI', comodel_name='ttb.kpi.type', required=True)
    deadline = fields.Date(string='Hạn nghiệm thu')
    date = fields.Datetime(string='Ngày nghiệm thu')
    state = fields.Selection([
        ('new', 'Mới'),
        ('approved', 'Đã nghiệm thu'),
        ('overdue', 'Trễ hạn')
    ], string='Trạng thái', default='new', tracking=True)
    line_ids = fields.Many2many(string="Danh sách tiêu chí không đạt", comodel_name='ttb.task.report.line', domain="[('fail', '=', True)]")
    user_branch_id = fields.Many2one(string='Cơ sở', comodel_name='ttb.branch')
    # original_report_id = fields.Many2one('ttb.task.report', string='Phiếu đánh giá gốc', required=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name', False) == 'Mới':
                vals['name'] = self.env['ir.sequence'].next_by_code('ttb.acceptance.record')
        return super(TtbAcceptanceRecord, self).create(vals_list)

    def button_done(self):
        done_date = fields.Datetime.now()
        for rec in self:
            rec.state = 'approved'
            rec.line_ids.process_status = 'done'
            rec.date = done_date
    def reopen_approval(self):
        return {
            'name': 'Lý do đề xuất mở lại',
            'type': 'ir.actions.act_window',
            'res_model': 'reopen.acceptance.record.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_model': self._name,
                'default_message': '',
                'default_model_id': self.id,
            }
        }