from odoo import fields, models, api

class TaskReportApprover(models.Model):
    _name = 'ttb.task.report.approver'
    _description = 'Người phê duyệt phiếu KPI'

    report_id = fields.Many2one('ttb.task.report', string='Phiếu KPI', ondelete='cascade')
    user_id = fields.Many2one('res.users', string='Người phê duyệt', required=True)
    state = fields.Selection([
        ('waiting', 'Chờ duyệt'),
        ('approved', 'Đã duyệt'),
    ], string='Trạng thái', default='waiting')
    approved_date = fields.Datetime(string='Ngày duyệt')