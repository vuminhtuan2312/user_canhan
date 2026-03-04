from odoo import api, fields, models, _

class KpiScoreDifference(models.Model):
    _name = 'ttb.kpi.score.difference'
    _description = 'Phiếu chấm lệch giữa CS và GS'
    _auto = False

    report_id = fields.Many2one(string='Phiếu TNKH', comodel_name='ttb.task.report')
    origin_report_id = fields.Many2one(string='Phiếu gốc', comodel_name='ttb.task.report')
    user_id = fields.Many2one(string='Người được đánh giá', comodel_name='res.users')
    area_id = fields.Many2one(string='Khu vực', comodel_name='ttb.area')
    branch_id = fields.Many2one(string='Cơ sở được đánh giá', comodel_name='ttb.branch')
    name = fields.Char(string='Tiêu chí')
    reviewer_id = fields.Many2one(string='Người đánh giá (CS)', comodel_name='res.users')

    pass_cs = fields.Boolean(string="Đạt (TNKH)", readonly=True)
    fail_cs = fields.Boolean(string="Không đạt (TNKH)", readonly=True)
    pass_manager = fields.Boolean(string='Đạt (Quản lý nhà sách)', readonly=True)
    fail_manager = fields.Boolean(string='Không đạt (Quản lý nhà sách)', readonly=True)
    avg_score_cs = fields.Float(string='Điểm TB Giám sát', readonly=True)
    avg_score_manager = fields.Float(string='Điểm TB Quản lý', readonly=True)
    note_cs = fields.Char(string='Ghi chú (TNKH)', readonly=True)
    note_manager = fields.Char(string='Ghi chú (Quản lý nhà sách)', readonly=True)

    def _query(self):
        return f"""
            SELECT
                tnkh.id AS id,
                tnkh.id AS report_id,
                cs.id AS origin_report_id,
                tnkh.user_id AS user_id,
                tnkh.user_branch_id AS branch_id,
                tnkh.area_id,
                tnkh.reviewer_id AS reviewer_id,
                tpl.name,
                tnkh.note AS note_cs,
                cs.note note_manager,

                MAX(tn_line.x_pass::int)::boolean AS pass_cs,
                MAX(tn_line.fail::int)::boolean AS fail_cs,

                MAX(cs_line.x_pass::int)::boolean AS pass_manager,
                MAX(cs_line.fail::int)::boolean AS fail_manager,

                kpi_cs.average_rate AS avg_score_cs,
                kpi_manager.average_rate AS avg_score_manager

            FROM ttb_task_report tnkh
            JOIN ttb_task_report cs ON tnkh.origin_report_id = cs.id
            JOIN ttb_task_report_line tn_line ON tn_line.report_id = tnkh.id
            JOIN ttb_task_report_line cs_line ON cs_line.report_id = cs.id
                AND cs_line.template_line_id = tn_line.template_line_id
            JOIN ttb_task_template_line tpl ON tpl.id = tn_line.template_line_id
            JOIN ttb_branch branch ON tnkh.user_branch_id = branch.id
            JOIN ttb_area area ON area.id = tnkh.area_id

            LEFT JOIN ttb_task_report_kpi kpi_cs ON kpi_cs.report_id = tnkh.id
            LEFT JOIN ttb_task_report_kpi kpi_manager ON kpi_manager.report_id = cs.id

            WHERE tnkh.group = 'cs' AND cs.group = 'manager' AND tnkh.kpi_type_id IN (
                  SELECT id FROM ttb_kpi_type WHERE code = 'CSKH'
              ) AND tn_line.x_pass IS DISTINCT FROM cs_line.x_pass

            GROUP BY
                tnkh.id,
                cs.id,
                tnkh.user_id,
                tnkh.user_branch_id,
                tnkh.area_id,
                tnkh.reviewer_id,
                tpl.name,
                kpi_cs.average_rate,
                kpi_manager.average_rate
        """

    @property
    def _table_query(self):
        return self._query()
