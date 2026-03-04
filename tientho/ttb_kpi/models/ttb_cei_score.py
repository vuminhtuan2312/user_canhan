from datetime import datetime
from odoo import api, fields, models, _, Command
from odoo.exceptions import ValidationError

class TtbCeiScore(models.Model):
    _name = 'ttb.cei.score'
    _description = 'Đánh giá điểm CEI'

    user_branch_id = fields.Many2one(string='Cơ sở', comodel_name='ttb.branch', required=True)
    date = fields.Date(string='Kỳ đánh giá', required=True)
    manager_score = fields.Float(string='Điểm quản lý', default=0)
    branch_manager_score = fields.Float(string='Điểm giám đốc', default=0)
    report_ids = fields.One2many(string='Danh sách phiếu đánh giá nhiệm vụ', comodel_name='ttb.task.report', inverse_name='cei_id', required=False)

    @api.constrains('manager_score')
    def _check_manager_score(self):
        for rec in self:
            if rec.manager_score < 0:
                raise ValidationError('Điểm CEI của quản lý phải lớn hơn 0')

    @api.constrains('branch_manager_score')
    def _check_branch_manager_score(self):
        for rec in self:
            if rec.branch_manager_score < 0:
                raise ValidationError('Điểm CEI của quản lý phải lớn hơn 0')

    @api.model_create_multi
    def create(self, vals_list):
        result = self.env[self._name]
        vals_list_new = []
        for vals in vals_list:
            date_month = datetime.strptime(vals.get('date'), '%Y-%m-%d').date().month
            date_year = datetime.strptime(vals.get('date'), '%Y-%m-%d').date().year
            record = self.search([('user_branch_id', '=', vals.get('user_branch_id'))]).filtered(lambda r: r.date and r.date.month == date_month and r.date.year == date_year)
            if record:
                record.write({
                    'manager_score': vals.get('manager_score'),
                    'branch_manager_score': vals.get('branch_manager_score')
                })
                result |= record
            else:
                vals_list_new.append(vals)

        if vals_list_new:
            results = super(TtbCeiScore, self).create(vals_list_new)
            for res in results:
                task_report = self.env['ttb.task.report'].sudo().search([
                    ('kpi_type_id.code', '=', 'CSKH'),
                    ('user_branch_id', '=', res.user_branch_id.id),
                ])
                task_report_to_write = task_report.filtered(lambda r: r.deadline and r.deadline.month == res.date.month and r.deadline.year == res.date.year)
                if task_report_to_write:
                    task_report_to_write.write({
                        'cei_id': res.id,
                        'manager_score': res.manager_score,
                        'branch_manager_score': res.branch_manager_score,
                    })
            result |= results
        return result

    def write(self, vals):
        if 'user_branch_id' in vals or 'date' in vals:
            for rec in self:
                if 'date' in vals:
                    date_month = datetime.strptime(vals.get('date'), '%Y-%m-%d').date().month
                    date_year = datetime.strptime(vals.get('date'), '%Y-%m-%d').date().year

                else:
                    date_month = rec.date.month
                    date_year = rec.date.year

                if 'user_branch_id' in vals:
                    user_branch_id = vals.get('user_branch_id')
                else:
                    user_branch_id = rec.user_branch_id.id

                if self.env['ttb.cei.score'].search([('id', '!=', rec.id),
                                ('user_branch_id', '=', user_branch_id)]).filtered(lambda r: r.date and r.date.month == date_month and r.date.year == date_year):
                    raise ValidationError(f"Đã có bản ghi đánh giá {self.env['ttb.branch'].browse([user_branch_id]).name} và tháng {date_month}/{date_year}.")

                # unlink task report cu
                rec.write({
                    'report_ids': [Command.unlink(r.id) for r in rec.report_ids]
                })

                # tim task report trong thang moi
                reports = self.env['ttb.task.report'].sudo().search([
                    ('kpi_type_id.code', '=', 'CSKH'),
                    ('user_branch_id', '=', user_branch_id)])

                reports_to_write = reports.filtered(lambda r: r.deadline and r.deadline.month == date_month and r.deadline.year == date_year)
                # neu tim duoc thi update o ban ghi cua ttb task report
                if reports_to_write:
                    reports_to_write.write({
                        'cei_id': rec.id,
                        'manager_score': rec.manager_score or vals.get('manager_score'),
                        'branch_manager_score': rec.branch_manager_score or vals.get('branch_manager_score'),
                        'user_branch_id': user_branch_id
                    })

        return super(TtbCeiScore, self).write(vals)

    def button_date_range(self):
        popup_id = self.env['ttb.popup.filtered'].search(
            [('create_uid', '=', self.env.uid), ('res_model', '=', self._name)], limit=1)
        if not popup_id:
            popup_id = self.env['ttb.popup.filtered'].create({'res_model': self._name})
        action = self.env['ir.actions.actions']._for_xml_id('ttb_kpi.ttb_popup_filtered_action')
        action['context'] = {'active_model': self._name}
        action['target'] = 'new'
        action['res_id'] = popup_id.id
        return action
