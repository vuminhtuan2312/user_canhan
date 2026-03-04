from odoo import api, models, fields


class TtbTnkhkpiT2Report(models.AbstractModel):
    _name = 'ttb.tnkhkpi.t2.report'
    _inherit = 'account.report.custom.handler'
    _description = 'Báo cáo kết quả chấm TNKH phiếu T2'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        options['unfold_all'] = (options.get('filter_unfold_all') or options.get('unfold_all'))
        options['hide_filter_rounding_unit'] = True
        options['column_headers'] = []
        options['columns'] = [
            {
                'name': 'Khu vực chấm',
                'expression_label': 'area_name',
                'class': 'number',
                'type': 'integer',
                'figure_type': 'integer',
                'column_group_key': '1',
            },
            {
                'name': 'Người chấm',
                'expression_label': 'reviewer_name',
                'class': 'number',
                'type': 'integer',
                'figure_type': 'integer',
                'column_group_key': '1',
            },
            {
                'name': 'Người được chấm',
                'expression_label': 'user_name',
                'class': 'number',
                'type': 'integer',
                'figure_type': 'integer',
                'column_group_key': '1',
            },
            {
                'name': 'Số phiếu cần chấm',
                'expression_label': 'total_votes',
                'class': 'number',
                'type': 'integer',
                'figure_type': 'integer',
                'column_group_key': '1',
            },
            {
                'name': 'Số phiếu đã chấm',
                'expression_label': 'completed_votes',
                'class': 'number',
                'type': 'integer',
                'figure_type': 'integer',
                'column_group_key': '2',
            },
            {
                'name': 'Tỷ lệ hoàn thành phiếu chấm',
                'expression_label': 'percent_completed',
                'class': 'number',
                'type': 'percentage',
                'figure_type': 'percentage',
                'column_group_key': '3',
            },
            {
                'name': 'Phiếu đạt',
                'expression_label': 'pass_votes',
                'class': 'number',
                'type': 'integer',
                'figure_type': 'integer',
                'column_group_key': '4',
            },
            {
                'name': 'Phiếu không đạt',
                'expression_label': 'fail_votes',
                'class': 'number',
                'type': 'integer',
                'figure_type': 'integer',
                'column_group_key': '5',
            },
            {
                'name': 'Tỷ lệ đạt',
                'expression_label': 'percent_pass',
                'class': 'number',
                'type': 'percentage',
                'figure_type': 'percentage',
                'column_group_key': '6',
            },
            {
                'name': 'Tỷ lệ không đạt',
                'expression_label': 'percent_fail',
                'class': 'number',
                'type': 'percentage',
                'figure_type': 'percentage',
                'column_group_key': '7',
            },
        ]

    def _customize_warnings(self, report, options, all_column_groups_expression_totals, warnings):
        warnings.clear()


    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals=None, warnings=None):
        lines = []
        date_from = options['date']['date_from']
        date_to = options['date']['date_to']

        query = f"""
            WITH filtered AS (
                SELECT
                    r.user_id AS user_id,
                    r.id AS report_id,
                    r.state,
                    r.area_id,
                    r.reviewer_id,
                    r.user_branch_id,
                    r.kpi_type_id,
                    r.number_votes,
                    r.group,
                    line.x_pass,
                    line.fail,
                    ru.login AS user_login,
                    rp.name AS user_name
                FROM ttb_task_report r
                LEFT JOIN ttb_task_report_line line ON line.report_id = r.id
                LEFT JOIN res_users ru ON ru.id = r.user_id
                LEFT JOIN res_partner AS rp ON rp.id = ru.partner_id
                JOIN ttb_kpi_type kpi ON r.kpi_type_id = kpi.id
                WHERE kpi.code = 'CSKH'
                  AND r.group = 'cs'
                  AND r.number_votes = 'T2'
                  AND r.deadline BETWEEN DATE '{date_from}' AND DATE '{date_to}'
            ),
            grouped AS (
                SELECT
                    user_id,
                    user_branch_id,
                    user_login,
                    area_id,
                    reviewer_id,
                    user_name,
                    COUNT(DISTINCT report_id)  AS total_votes,
                    COUNT(DISTINCT report_id) FILTER (WHERE state = 'done') AS completed_votes,
                    COUNT(DISTINCT report_id) FILTER (
                        WHERE state = 'done'
                        AND NOT EXISTS (
                            SELECT 1
                            FROM ttb_task_report_line l2
                            WHERE l2.report_id = filtered.report_id AND (l2.fail = 'true')
                        )
                    ) AS pass_votes,
                    COUNT(DISTINCT report_id) FILTER (
                        WHERE state = 'done'
                        AND EXISTS (
                            SELECT 1
                            FROM ttb_task_report_line l3
                            WHERE l3.report_id = filtered.report_id AND (l3.fail = 'true'))
                    ) AS fail_votes 
                FROM filtered
                GROUP BY user_id,user_branch_id, user_login, area_id, reviewer_id, user_name
            )
            SELECT
                user_id,
                user_branch_id,
                user_login,
                area_id,
                reviewer_id,
                total_votes,
                user_name,
                completed_votes,
                ROUND(100 * completed_votes::DECIMAL / NULLIF(total_votes, 0), 2) AS percent_completed,
                pass_votes,
                fail_votes,
                ROUND(100 * pass_votes::DECIMAL / NULLIF(completed_votes, 0), 2) AS percent_pass,
                ROUND(100 * fail_votes::DECIMAL / NULLIF(completed_votes, 0), 2) AS percent_fail
            FROM grouped
            ORDER BY user_id, user_branch_id, user_login, area_id, reviewer_id, user_name
        """

        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()

        group_user_branch_id = list(set([item['user_branch_id'] for item in result]))
        for branch in group_user_branch_id:
            result_branch = [item for item in result if item['user_branch_id'] == branch]
            #Line cơ sở
            branch_total_votes = sum(item['total_votes'] for item in result_branch)
            branch_completed_votes = sum(item['completed_votes'] for item in result_branch)
            branch_percent_completed = (branch_completed_votes / branch_total_votes) * 100 if branch_total_votes else 0
            branch_pass_votes = sum(item['pass_votes'] for item in result_branch)
            branch_fail_votes = sum(item['fail_votes'] for item in result_branch)
            branch_percent_pass = (branch_pass_votes / branch_completed_votes) * 100 if branch_completed_votes else 0
            branch_percent_fail = (branch_fail_votes / branch_completed_votes) * 100 if branch_completed_votes else 0
            branch_name = self.env['ttb.branch'].browse(branch).name

            branch_value = {
                'total_votes': branch_total_votes,
                'completed_votes': branch_completed_votes,
                'percent_completed': branch_percent_completed,
                'pass_votes': branch_pass_votes,
                'fail_votes': branch_fail_votes,
                'percent_pass': branch_percent_pass,
                'percent_fail': branch_percent_fail,
            }
            total_line_columns = []
            for column in options['columns']:
                expr = column['expression_label']
                value = branch_value.get(expr)
                total_line_columns.append(report._build_column_dict(value, column, options=options))
            lines.append({
                'id': f"~ttb.branch~{branch}",
                'name': branch_name,
                'columns': total_line_columns,
                'level': 1,
                'unfoldable': True,
                'unfolded': options.get('unfold_all'),
            })
            group_area_id = list(set([item['area_id'] for item in result_branch]))
            for area_id in group_area_id:
                result_area = [item for item in result_branch if item['area_id'] == area_id]
                # Line khu vực
                area_total_votes = sum(item['total_votes'] for item in result_area)
                area_completed_votes = sum(item['completed_votes'] for item in result_area)
                area_percent_completed = (area_completed_votes / area_total_votes) * 100 if area_total_votes else 0
                area_pass_votes = sum(item['pass_votes'] for item in result_area)
                area_fail_votes = sum(item['fail_votes'] for item in result_area)
                area_percent_pass = (area_pass_votes / area_completed_votes) * 100 if area_completed_votes else 0
                area_percent_fail = (area_fail_votes / area_completed_votes) * 100 if area_completed_votes else 0
                area_name = self.env['ttb.area'].browse(area_id).name

                area_value = {
                    'area_name': area_name,
                    'user_name': '',
                    'reviewer_name': '',
                    'total_votes': area_total_votes,
                    'completed_votes': area_completed_votes,
                    'percent_completed': area_percent_completed,
                    'pass_votes': area_pass_votes,
                    'fail_votes': area_fail_votes,
                    'percent_pass': area_percent_pass,
                    'percent_fail': area_percent_fail,
                }
                total_line_columns = []
                for column in options['columns']:
                    expr = column['expression_label']
                    value = area_value.get(expr)
                    total_line_columns.append(report._build_column_dict(value, column, options=options))
                lines.append({
                    'id': f"~ttb.branch~{branch}|~ttb.area~{area_id}",
                    'name': '',
                    'columns': total_line_columns,
                    'level': 1,
                    'unfoldable': True,
                    'unfolded': options.get('unfold_all'),
                    'parent_id': f"~ttb.branch~{branch}",
                })
                group_reviewer_id = list(set([item['reviewer_id'] for item in result_area]))
                for reviewer in group_reviewer_id:
                    result_reviewer = [item for item in result_area if item['reviewer_id'] == reviewer]
                    # Line người đánh giá
                    reviewer_total_votes = sum(item['total_votes'] for item in result_reviewer)
                    reviewer_completed_votes = sum(item['completed_votes'] for item in result_reviewer)
                    reviewer_percent_completed = (reviewer_completed_votes / reviewer_total_votes) * 100 if reviewer_total_votes else 0
                    reviewer_pass_votes = sum(item['pass_votes'] for item in result_reviewer)
                    reviewer_fail_votes = sum(item['fail_votes'] for item in result_reviewer)
                    reviewer_percent_pass = (reviewer_pass_votes / reviewer_completed_votes) * 100 if reviewer_completed_votes else 0
                    reviewer_percent_fail = (reviewer_fail_votes / reviewer_completed_votes) * 100 if reviewer_completed_votes else 0
                    reviewer_name = self.env['res.users'].browse(reviewer).name if reviewer else ''

                    reviewer_value = {
                        'area_name': '',
                        'reviewer_name': reviewer_name,
                        'user_name': '',
                        'total_votes': reviewer_total_votes,
                        'completed_votes': reviewer_completed_votes,
                        'percent_completed': reviewer_percent_completed,
                        'pass_votes': reviewer_pass_votes,
                        'fail_votes': reviewer_fail_votes,
                        'percent_pass': reviewer_percent_pass,
                        'percent_fail': reviewer_percent_fail,
                    }
                    total_line_columns = []
                    for column in options['columns']:
                        expr = column['expression_label']
                        value = reviewer_value.get(expr)
                        total_line_columns.append(report._build_column_dict(value, column, options=options))
                    lines.append({
                        'id': f"~ttb.branch~{branch}|~ttb.area~{area_id}|~res.user~{reviewer}",
                        'name': '',
                        'columns': total_line_columns,
                        'level': 1,
                        'unfoldable': True,
                        'unfolded': options.get('unfold_all'),
                        'parent_id': f"~ttb.branch~{branch}|~ttb.area~{area_id}",
                    })
                    # line người được đánh giá
                    for record in result_reviewer:
                        line_columns = []
                        for column in options['columns']:
                            expr = column['expression_label']
                            value = record.get(expr)
                            if expr in ['brand_name', 'reviewer_name', 'area_name']:
                                value = ''
                            if expr == 'user_name':
                                value = f"{record.get('user_login', '')} {record.get('user_name', '')}"
                            if value is not None:
                                line_columns.append(report._build_column_dict(value, column, options=options))
                            else:
                                line_columns.append(
                                    report._build_column_dict(0, column, options=options))

                        lines.append({
                            'id': f"~ttb.branch~{branch}|~ttb.area~{area_id}|~res.user~{reviewer}|~res.users~{record['user_id']}",
                            'name': '',
                            'columns': line_columns,
                            'level': 2,
                            'unfoldable': False,
                            'unfolded': False,
                            'parent_id': f"~ttb.branch~{branch}|~ttb.area~{area_id}|~res.user~{reviewer}",
                        })
        #Total line
        total_votes = sum(item['total_votes'] for item in result)
        completed_votes = sum(item['completed_votes'] for item in result)
        percent_completed = (completed_votes / total_votes) * 100 if total_votes else 0
        pass_votes = sum(item['pass_votes'] for item in result)
        fail_votes = sum(item['fail_votes'] for item in result)
        percent_pass = (pass_votes / completed_votes) * 100 if completed_votes else 0
        percent_fail = (fail_votes / completed_votes) * 100 if completed_votes else 0

        total_value = {
            'total_votes': total_votes,
            'completed_votes': completed_votes,
            'percent_completed': percent_completed,
            'pass_votes': pass_votes,
            'fail_votes': fail_votes,
            'percent_pass': percent_pass,
            'percent_fail': percent_fail,
        }
        total_line_columns = []
        for column in options['columns']:
            expr = column['expression_label']
            value = total_value.get(expr)
            total_line_columns.append(report._build_column_dict(value, column, options=options))
        lines.append({
            'id': f"~total_id~",
            'name': 'Tổng',
            'columns': total_line_columns,
            'level': 1,
            'unfoldable': False,
            'unfolded': False,
        })
        return [(0, line) for line in lines]