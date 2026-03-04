from odoo import *


class ApprovalProcess(models.Model):
    _name = 'ttb.approval.process'
    _description = 'Quy trình duyệt'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    @api.ondelete(at_uninstall=False)
    def _unlink_except_linked_to_approval(self):
        for model in self.mapped('model_id'):
            if self.env[model.model].search_count([('process_id', 'in', self.filtered(lambda x: x.model_id.id == model.id).ids)], limit=1):
                raise exceptions.UserError('Quy trình duyệt đã được sử dụng không thể xóa, nếu không còn nhu cầu hãy thực hiện lưu trữ')

    name = fields.Char(string='Tên quy trình', required=True, default='Mới', tracking=True)
    model_id = fields.Many2one(string='Loại chứng từ', comodel_name='ir.model', domain='[("model","!=","ttb.approval.mixin"),("field_id.name","=","rule_line_ids")]', required=True, ondelete='cascade', tracking=True)
    model = fields.Char(string='Model', related='model_id.model')
    company_id = fields.Many2one(string='Công ty áp dụng', comodel_name='res.company')
    purchase_type = fields.Selection(string='Loại đơn mua', selection=[('sale', 'Mua hàng kinh doanh'), ('not_sale', 'Mua hàng không kinh doanh'), ('material', 'Mua nguyên vật liệu'), ('imported_goods', 'Dự trù nhập khẩu')], tracking=True)
    domain = fields.Char(string='Điều kiện', default='[]')
    rule_ids = fields.One2many(string='Quy tắc', comodel_name='ttb.approval.rule', inverse_name='process_id', copy=True)
    active = fields.Boolean(string='Hoạt động', default=True, required=True)

    @api.depends("rule_ids")
    def _compute_max_line_sequence(self):
        for record in self:
            record.max_line_sequence = max(record.mapped("rule_ids.sequence") or [0]) + 1

    max_line_sequence = fields.Integer(string="Max sequence in lines", compute="_compute_max_line_sequence", store=True)

    @api.constrains('rule_ids')
    def constrains_rule_ids_notify(self):
        for record in self:
            if all(rule.notif_only for rule in record.rule_ids):
                continue
            if all(not rule.notif_only for rule in record.rule_ids):
                continue
            max_sequence_not_notif = max(record.rule_ids.filtered(lambda x: not x.notif_only).mapped('visible_sequence'))
            if any(rule.visible_sequence < max_sequence_not_notif for rule in record.rule_ids.filtered(lambda x: x.notif_only)):
                raise exceptions.ValidationError('Chỉ có thể thực hiện thông báo cho người dùng ở cuối quy trình duyệt')

    def write(self, vals):
        res = super().write(vals)
        if vals.get('rule_ids') and any(rule[0] != 4 for rule in vals.get('rule_ids')):
            self.message_post(body=f'{self.env.user.name} đã cập nhật quy tắc')
        return res
