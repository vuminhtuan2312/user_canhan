from odoo import models, fields, api


class TtbTaskReportKpi(models.Model):
    _name = 'ttb.task.report.kpi'
    _description = 'KPi đánh giá nhiệm vụ'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    report_id = fields.Many2one(string='Đánh giá nhiệm vụ', comodel_name='ttb.task.report', required=True)
    kpi_type = fields.Many2one(string='Loại KPI', comodel_name='ttb.kpi.type')
    number_of_item = fields.Integer(string='Số hạng mục đánh giá')
    date = fields.Datetime(string='Ngày đánh giá', related='report_id.date', store=True)
    total_rate = fields.Float(string='Điểm tỷ trọng theo tiêu chí')
    average_rate = fields.Float(string='Điểm trung bình', readonly=True, aggregator="avg")
    group = fields.Selection(string='Nhóm đánh giá', related='report_id.group', store=True)
    date = fields.Datetime(string='Ngày đánh giá', related='report_id.date', store=True)
    reviewer_id = fields.Many2one(string='Người đánh giá', related='report_id.reviewer_id', store=True)
    kpi_type_id = fields.Many2one(string='Loại KPI', related='report_id.kpi_type_id', store=True)
    user_job_id = fields.Many2one(string='Chức vụ người được đánh giá', related='report_id.user_job_id', store=True)
    user_branch_id = fields.Many2one(string='Cơ sở được đánh giá', related='report_id.user_branch_id', store=True)
    area_id = fields.Many2one(string='Khu vực', related='report_id.area_id', store=True)
    categ_id = fields.Many2one(string='Quầy', related='report_id.categ_id', store=True)
    user_id = fields.Many2one(string='Người được đánh giá', related='report_id.user_id', store=True)
    user_ids = fields.Many2many(string='Nhóm được đánh giá', related='report_id.user_ids')
    state = fields.Selection(string='Trạng thái', related='report_id.state',store=True)
    creation_month = fields.Integer(string='Tháng sinh phiếu', related='report_id.creation_month',store=True)
    period = fields.Integer(string='Kỳ sinh phiếu', related='report_id.period',store=True)
    total_rate_cluster = fields.Float(string='Điểm tỷ trọng theo cụm')
    def button_filterd_date(self):
        popup_id = self.env['ttb.popup.filtered'].search([('create_uid', '=', self.env.uid), ('res_model', '=', self._name)], limit=1)
        if not popup_id:
            popup_id = self.env['ttb.popup.filtered'].create({'res_model': self._name})
        action = self.env["ir.actions.actions"]._for_xml_id("ttb_kpi.ttb_popup_filtered_action")
        action["context"] = {'active_model': self._name}
        action['target'] = 'new'
        action['res_id'] = popup_id.id
        return action
