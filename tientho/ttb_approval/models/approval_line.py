from odoo import *


class ApprovalLine(models.Model):
    _name = 'ttb.approval.line'
    _description = 'Thông tin phê duyệt'
    _order = 'res_model,res_id,sequence'

    approve_user_ids = fields.Many2many(string='Người có thể duyệt', domain=['|', ('active', '=', True), ('active', '=', False)], comodel_name='res.users', required=True)
    user_id = fields.Many2one(string='Người duyệt', comodel_name='res.users')
    login = fields.Char(string='Tài khoản', related='user_id.login')
    date_approved = fields.Datetime(string='Ngày duyệt')
    state = fields.Selection(string='Trạng thái', selection=[('sent', 'Chờ duyệt'), ('approved', 'Đã duyệt'), ('rejected', 'Từ chối')], default='sent', required=True, readonly=True, copy=False)
    sequence = fields.Integer(string='Trình tự')
    res_model = fields.Char(string='Model tài nguyên')
    res_id = fields.Many2oneReference(string='ID tài nguyên', index=True, model_field='res_model')
    reference = fields.Char(string='Tài liệu duyệt', compute='_compute_reference', readonly=True, store=False)
    notif_only = fields.Boolean(string='Chỉ thông báo', default=False)

    @api.depends('res_model', 'res_id')
    def _compute_reference(self):
        for res in self:
            res.reference = "%s,%s" % (res.res_model, res.res_id)
