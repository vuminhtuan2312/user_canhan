from odoo import *


class ApprovalMixin(models.AbstractModel):
    _name = 'ttb.approval.mixin'
    _description = 'Duyệt'

    def send_notify(self, message, users, subject=''):
        if not users:
            return
        mail_template_id = 'ttb_approval.notify_record_message_template'
        for record in self:
            if not record.exists():
                continue
            self.message_subscribe(partner_ids=users.mapped('partner_id').ids)
            model_description = self.env['ir.model']._get(record._name).with_context(lang=self.env.user.lang or 'vi_VN').display_name
            values = {
                'object': record,
                'model_description': model_description,
                'message': message,
                'access_link': self.env[self._name]._notify_get_action_link('view', model=record._name, res_id=record.id),
            }
            rendered_body = self.env['ir.qweb']._render(mail_template_id, values)
            if not subject:
                subject = record.display_name
            record.message_notify(
                subject=subject,
                body=rendered_body,
                partner_ids=users.mapped('partner_id').ids,
                record_name=subject,
                subtype_xmlid='mail.mt_comment',
                email_layout_xmlid='mail.mail_notification_light',
                model_description=model_description,
                mail_auto_delete=False,
            )

    def unlink(self):
        to_line_remove = self.env['ttb.approval.line']
        for rec in self:
            to_line_remove |= self.env['ttb.approval.line'].sudo().search([('res_model', '=', rec._name), ('res_id', '=', rec.id)])
        res = super().unlink()
        to_line_remove.sudo().unlink()
        return res

    approve_ok = fields.Boolean(string='Có thể duyệt', compute='_compute_approve_ok')

    @api.depends_context('uid')
    @api.depends('current_approve_user_ids')
    def _compute_approve_ok(self):
        for rec in self:
            rec.approve_ok = rec.current_approve_user_ids and self.env.user in rec.current_approve_user_ids

    sent_ok = fields.Boolean(string='Có thể gửi', compute='_compute_sent_ok')

    @api.depends_context('uid')
    @api.depends('create_uid')
    def _compute_sent_ok(self):
        for rec in self:
            rec.sent_ok = rec.create_uid and self.env.user == rec.create_uid

    rule_line_ids = fields.One2many(string='Thông tin phê duyệt', comodel_name='ttb.approval.line', inverse_name='res_id', domain=lambda self: [('notif_only', '=', False), ('res_model', '=', self._name)], readonly=True)
    approval_line_ids = fields.One2many(string='Thông tin phê duyệt (All)', comodel_name='ttb.approval.line', inverse_name='res_id', domain=lambda self: [('res_model', '=', self._name)], readonly=True)
    process_id = fields.Many2one(string='Quy trình phê duyệt', copy=False, readonly=True, comodel_name='ttb.approval.process')
    date_sent = fields.Datetime(string='Ngày gửi duyệt', copy=False, readonly=True)
    date_approved = fields.Datetime(string='Ngày phê duyệt', copy=False, readonly=True)

    next_approve_line_id = fields.Many2one(string='Dòng duyệt tiếp theo', compute='_compute_based_on_approval_line_ids', comodel_name='ttb.approval.line', readonly=True, store=True)
    next_approve_user_ids = fields.Many2many(string='Người duyệt tiếp theo', related='next_approve_line_id.approve_user_ids', readonly=True)

    current_approve_line_id = fields.Many2one(string='Dòng duyệt hiện tại', compute='_compute_based_on_approval_line_ids', comodel_name='ttb.approval.line', readonly=True, store=True)
    current_approve_user_ids = fields.Many2many(string='Người duyệt hiện tại', related='current_approve_line_id.approve_user_ids', readonly=True)

    notif_approve_line_id = fields.Many2one(string='Dòng phân công', compute='_compute_based_on_approval_line_ids', comodel_name='ttb.approval.line', readonly=True, store=True)
    notif_user_ids = fields.Many2many(string='Người được phân công', related='notif_approve_line_id.approve_user_ids', readonly=True)

    @api.depends('approval_line_ids.state')
    def _compute_based_on_approval_line_ids(self):
        for rec in self:
            next_approve_line_id = self.env['ttb.approval.line']
            current_approve_line_id = self.env['ttb.approval.line']
            notif_approve_line_id = rec.approval_line_ids.search([('notif_only', '=', True), ('res_id', 'in', rec.ids), ('res_model', '=', rec._name)], limit=1)
            approval_line_ids = rec.approval_line_ids.search([('notif_only', '=', False), ('res_id', 'in', rec.ids), ('res_model', '=', rec._name)])
            for line in approval_line_ids:
                if next_approve_line_id and current_approve_line_id:
                    break
                if line.state == 'approved': continue
                if current_approve_line_id:
                    next_approve_line_id = line
                    break
                current_approve_line_id = line

            rec.next_approve_line_id = next_approve_line_id
            rec.current_approve_line_id = current_approve_line_id
            rec.notif_approve_line_id = notif_approve_line_id

    def get_flow_domain(self):
        company_domain = []
        if self.fields_get(['company_id']).get('company_id') and self.company_id:
            self = self.with_company(self.company_id)
            company_domain = ['|', ('company_id', '=', self.company_id.id), ('company_id', '=', False)]
        return osv.expression.AND([[('model', '=', self._name)], company_domain])

    def get_approve_user_ids(self, rule):
        user_ids = self.env['res.users']
        company_domain = []
        if self.fields_get(['company_id']).get('company_id') and self.company_id:
            self = self.with_company(self.company_id)
            company_domain = ['|', ('company_id', '=', self.company_id.id), ('company_id', '=', False)]
        if rule.method == 'title':
            user_ids = self.env['hr.employee'].search(osv.expression.AND([[('job_id', '=', rule.job_id.id)], company_domain])).mapped('user_id')
        elif rule.method == 'department':
            user_ids = self.env['hr.employee'].search(osv.expression.AND([[('department_id', '=', rule.department_id.id)], company_domain])).mapped('user_id')
        elif rule.method == 'manager':
            user_ids = self.env.user.employee_id.parent_id.user_id
        elif rule.method == 'title_manager':
            parent = self.env.user.employee_id.parent_id
            while parent:
                if parent.job_id.id == rule.job_id.id:
                    user_ids |= parent.user_id
                parent = parent.parent_id
        elif rule.method == 'mch_manager':
            pass
        elif rule.method == 'user':
            user_ids = rule.user_id
        return user_ids

    def get_approval_line_ids(self):
        self = self.sudo()
        processes = self.env['ttb.approval.process'].search(self.get_flow_domain())
        sequence = 0
        process_id = self.env['ttb.approval.process']
        approval_line_ids = []
        notif_user_ids = self.env['res.users']
        for process in processes:
            if not self.filtered_domain(tools.safe_eval.safe_eval(process.domain or '[]')):
                continue
            for rule in process.rule_ids:
                approve_user_ids = self.get_approve_user_ids(rule)
                if not approve_user_ids: continue
                if rule.notif_only:
                    notif_user_ids |= approve_user_ids
                    continue
                if rule.all_approve == '1':
                    sequence += 1
                    approval_line_ids.append((0, 0, {
                        'res_model': self._name,
                        'res_id': self.id,
                        'sequence': sequence,
                        'state': 'sent',
                        'notif_only': rule.notif_only,
                        'approve_user_ids': [(6, 0, approve_user_ids.ids)],
                    }))
                else:
                    for approver in approve_user_ids:
                        sequence += 1
                        approval_line_ids.append((0, 0, {
                            'res_model': self._name,
                            'res_id': self.id,
                            'sequence': sequence,
                            'state': 'sent',
                            'notif_only': rule.notif_only,
                            'approve_user_ids': [(6, 0, approver.ids)],
                        }))
            process_id = process
            break
        if notif_user_ids:
            sequence += 1
            approval_line_ids.append((0, 0, {
                'res_model': self._name,
                'res_id': self.id,
                'sequence': sequence,
                'state': 'approved',
                'notif_only': True,
                'approve_user_ids': [(6, 0, notif_user_ids.ids)],
            }))
        return process_id, approval_line_ids

    def state_change(self, approve_state):
        self = self.sudo()
        user = self.env.user
        rule_line_ids = self.rule_line_ids.search([('notif_only', '=', False), ('res_id', 'in', self.ids), ('res_model', '=', self._name)])
        if not rule_line_ids:
            return True
        if user not in rule_line_ids.mapped('approve_user_ids'):
            return False
        update_value = dict(state=approve_state, date_approved=fields.Datetime.now(), user_id=user.id)
        approval_line_ids = []
        for approval in rule_line_ids:
            if approval_line_ids and user.id not in approval.approve_user_ids.ids:
                if approval.state == 'rejected':
                    approval_line_ids += [(1, approval.id, {'state': 'sent'})]
                next_approval = self.rule_line_ids.search([('sequence', '>', approval.sequence), ('notif_only', '=', False), ('res_id', 'in', self.ids), ('res_model', '=', self._name)], limit=1)
                self.write(dict(approval_line_ids=approval_line_ids))
                return False
            if approval.state != 'sent': continue
            if user.id not in approval.approve_user_ids.ids: return False
            approval_line_ids += [(1, approval.id, update_value)]
            if approve_state == 'rejected':
                previous_approval = self.rule_line_ids.search([('sequence', '<', approval.sequence), ('notif_only', '=', False), ('res_id', 'in', self.ids), ('res_model', '=', self._name)], order='sequence desc')
                previous_approver = self.env['res.users']
                for previous in previous_approval:
                    if previous_approver and previous_approver != previous.user_id:
                        break
                    approval_line_ids += [(1, previous.id, {'state': 'sent'})]
                    if not previous_approver:
                        previous_approver = previous.user_id
                self.write(dict(approval_line_ids=approval_line_ids))
                break
        if not approval_line_ids or approve_state == 'rejected':
            return False
        self.write(dict(approval_line_ids=approval_line_ids))
        return True
