from odoo import *


class ApprovalRule(models.Model):
    _name = 'ttb.approval.rule'
    _description = 'Quy tắc duyệt'
    _order = 'sequence'

    process_id = fields.Many2one(string='Quy trình', comodel_name='ttb.approval.process', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Trình tự (Technical)', help="Gives the sequence of this line when displaying.", default=9999)
    visible_sequence = fields.Integer(string="Trình tự", help="Displays the sequence of the line.", compute="_compute_visible_sequence", store=True)

    @api.depends("sequence", "process_id.rule_ids")
    def _compute_visible_sequence(self):
        for process in self.mapped("process_id"):
            sequence = 1
            rule_ids = process.rule_ids
            for line in sorted(rule_ids, key=lambda rule_id: rule_id.sequence):
                line.visible_sequence = sequence
                sequence += 1

    method = fields.Selection(string='Phương thức', selection=[('title', 'Vai trò'),
                                                               ('department', 'Phòng/Ban'),
                                                               ('manager', 'Quản lý'),
                                                               ('title_manager', 'Vai trò quản lý'),
                                                               ('mch_manager', 'Quản lý MCH'),
                                                               ('user', 'Người chỉ định')],
                              required=True, default='title')
    job_id = fields.Many2one(string='Vai trò duyệt', comodel_name='hr.job')
    department_id = fields.Many2one(string='Phòng/Ban phê duyệt', comodel_name='hr.department')
    user_id = fields.Many2one(string='Người phê duyệt', comodel_name='res.users')
    all_approve = fields.Selection(string='Số lượng duyệt', selection=[('1', 'Chỉ 1 người'),
                                                                       ('all', 'Tất cả')],
                                   required=True, default='1')
    notif_only = fields.Boolean(string='Chỉ thông báo', default=False)
    company_id = fields.Many2one(related='process_id.company_id')
