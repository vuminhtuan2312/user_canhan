import ast
from odoo import api, fields, models, _
from odoo.osv import expression

class TtbPopupFiltered(models.Model):
    _name = 'ttb.popup.filtered'
    _description = 'Lọc ngày tháng báo cáo'

    date_from = fields.Date(string='Từ ngày')
    date_to = fields.Date(string='Đến ngày')
    res_model = fields.Char(string='Model name')

    def button_confirm(self):
        action = False
        if self.env.context.get('active_model') == 'ttb.task.report.line':
            action = self.env["ir.actions.actions"]._for_xml_id("ttb_kpi.ttb_task_report_line_action")
        if self.env.context.get('active_model') == 'ttb.task.report.kpi':
            action = self.env["ir.actions.actions"]._for_xml_id("ttb_kpi.ttb_task_report_kpi_action")
        if self.env.context.get('active_model') == 'ttb.task.report':
            action = self.env["ir.actions.actions"]._for_xml_id("ttb_kpi.ttb_task_report_action")
        if self.env.context.get('active_model') == 'ttb.cei.score':
            action = self.env["ir.actions.actions"]._for_xml_id("ttb_kpi.ttb_cei_score_action")
        domain_date = []
        if self.date_from:
            domain_date.append(('date', '>=', self.date_from))
        if self.date_to:
            domain_date.append(('date', '<=', self.date_to))
        domain = expression.AND([ast.literal_eval(action['domain'] or '[]'),domain_date])
        action.update({'domain': domain})
        action['target'] = 'main'
        return action
