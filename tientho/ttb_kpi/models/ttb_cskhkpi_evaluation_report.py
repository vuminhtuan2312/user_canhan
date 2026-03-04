from odoo import models, fields, api


class CskpiEvaluationReport(models.AbstractModel):
    _name = 'cskpi.evaluation.report'
    _inherit = 'account.report.custom.handler'
    _description = 'Báo cáo KPI CSKH'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        options['unfold_all'] = (options.get('filter_unfold_all') or options.get('unfold_all'))
        options['hide_filter_rounding_unit'] = True
        options['column_headers'] = []
        options['columns'] = [
            {
                'name': 'Mã nhân viên',
                'expression_label': 'user_login',
                'class': 'text',
                'type': 'string',
                'column_group_key': '1',
            },
            {
                'name': 'Người được đánh giá',
                'expression_label': 'user_id',
                'class': 'text',
                'type': 'string',
                'column_group_key': '2',
            },
            {
                'name': 'CS cần chấm (phiếu)',
                'expression_label': 'cs_total_task',
                'class': 'number',
                'type': 'integer',
                'figure_type': 'integer',
                'column_group_key': '3',
            },
            {
                'name': 'SL phiếu CS chấm',
                'expression_label': 'cs_count',
                'class': 'number',
                'type': 'integer',
                'figure_type': 'integer',
                'column_group_key': '4',
            },
            {
                'name': 'Tỷ lệ phiếu CS chấm',
                'expression_label': 'percent_cs_vote',
                'class': 'number',
                'type': 'percentage',
                'figure_type': 'percentage',
                'column_group_key': '5',
            },
            {
                'name': 'GS cần chấm (phiếu)',
                'expression_label': 'gs_total_task',
                'class': 'number',
                'type': 'integer',
                'figure_type': 'integer',
                'column_group_key': '6',
            },
            {
                'name': 'SL phiếu GS chấm',
                'expression_label': 'manager_count',
                'class': 'number',
                'type': 'integer',
                'figure_type': 'integer',
                'column_group_key': '7',
            },
            {
                'name': 'Tỷ lệ phiếu GS chấm',
                'expression_label': 'percent_recheck',
                'class': 'number',
                'type': 'percentage',
                'figure_type': 'percentage',
                'column_group_key': '8',
            },
            {
                'name': 'Điểm CS chấm',
                'expression_label': 'cs_score',
                'class': 'number',
                'type': 'percentage',
                'figure_type': 'percentage',
                'column_group_key': '9',
            },
            {
                'name': 'Điểm GS chấm',
                'expression_label': 'manager_score',
                'class': 'number',
                'type': 'percentage',
                'figure_type': 'percentage',
                'column_group_key': '10',
            },
            {
                'name': 'Điểm CSKH',
                'expression_label': 'final_score',
                'class': 'number',
                'type': 'percentage',
                'figure_type': 'percentage',
                'column_group_key': '11',
            },
            {
                'name': 'Chênh lệch',
                'expression_label': 'score_diff',
                'class': 'number',
                'type': 'percentage',
                'figure_type': 'percentage',
                'column_group_key': '12',
            },
            {
                'name': 'SL tiêu chí CS chấm đạt',
                'expression_label': 'cs_pass',
                'class': 'number',
                'type': 'number',
                'column_group_key': '13',
            },
            {
                'name': 'SL tiêu chí CS chấm không đạt',
                'expression_label': 'cs_fail',
                'class': 'number',
                'type': 'number',
                'column_group_key': '14',
            },
            {
                'name': 'SL tiêu chí GS chấm đạt',
                'expression_label': 'manager_pass',
                'class': 'number',
                'type': 'number',
                'column_group_key': '15',
            },
            {
                'name': 'SL tiêu chí GS chấm không đạt',
                'expression_label': 'manager_fail',
                'class': 'number',
                'type': 'number',
                'column_group_key': '16',
            },
            {
                'name': 'Số phiếu tiêu chuẩn',
                'expression_label': 'standard_votes',
                'class': 'number',
                'type': 'number',
                'column_group_key': '17',
            },
            {
                'name': 'Số phiếu chấm thiếu',
                'expression_label': 'remark_count',
                'class': 'number',
                'type': 'number',
                'column_group_key': '18',
            },
            {
                'name': 'Số phiếu trễ hạn',
                'expression_label': 'late_reports',
                'class': 'number',
                'type': 'number',
                'column_group_key': '18',
            },
        ]
        hidden_columns = set()
        options['show_all_field'] = (previous_options or {}).get('show_all_field', False)
        if not options['show_all_field']:
            hidden_columns.add('cs_pass')
            hidden_columns.add('cs_fail')
            hidden_columns.add('manager_pass')
            hidden_columns.add('manager_fail')
            hidden_columns.add('standard_votes')
            hidden_columns.add('remark_count')
            hidden_columns.add('late_reports')

        options['columns'] = [
            column for column in options['columns']
            if column['expression_label'] not in hidden_columns
        ]

    def _customize_warnings(self, report, options, all_column_groups_expression_totals, warnings):
        warnings.clear()

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals=None, warnings=None):
        lines = []
        date_from = options['date']['date_from']
        date_to = options['date']['date_to']
        query = f"""
            WITH user_mapping AS (
                SELECT 
                    ttb_task_report_id, 
                    MAX(res_users_id) AS res_users_id
                FROM res_users_ttb_task_report_rel
                GROUP BY ttb_task_report_id
            ),
            filtered AS (
                SELECT
                    COALESCE(r.user_id, um.res_users_id) AS user_id,
                    r.user_branch_id,
                    r.area_id,
                    r.id AS report_id,
                    r.group,
                    r.state,
                    r.deadline,
                    line.x_pass,
                    line.fail,
                    r.kpi_type_id,
                    ru.login AS user_login
                FROM ttb_task_report r
                LEFT JOIN ttb_task_report_line line ON line.report_id = r.id
                LEFT JOIN user_mapping um ON um.ttb_task_report_id = r.id
                LEFT JOIN res_users ru ON ru.id = COALESCE(r.user_id, um.res_users_id)
                JOIN ttb_kpi_type kpi ON r.kpi_type_id = kpi.id
                WHERE kpi.code = 'CSKH' 
                  AND r.user_branch_id IS NOT NULL
                  AND (r.user_id IS NOT NULL OR um.res_users_id IS NOT NULL)
                  AND r.deadline BETWEEN DATE '{date_from}' AND DATE '{date_to}'
            ),
            report_assignment AS (
                SELECT user_id, area_id, user_branch_id,
                COUNT (DISTINCT report_id) FILTER (WHERE "group" = 'manager') AS cs_total_task,
                COUNT (DISTINCT report_id) FILTER (WHERE "group" = 'cs') AS gs_total_task,
                COUNT (DISTINCT report_id) FILTER (WHERE  state = 'overdue' AND "group" = 'manager') AS late_reports
                FROM filtered
                GROUP BY user_id, area_id, user_branch_id
            ),
            grouped AS (
                SELECT
                    user_id,
                    user_branch_id,
                    area_id,
                    user_login,
                    COUNT(DISTINCT report_id) FILTER (WHERE "group" = 'manager' AND state = 'done') AS cs_count,
                    COUNT(DISTINCT report_id) FILTER (WHERE "group" = 'cs' AND state = 'done') AS manager_count,

                    COUNT(*) FILTER (WHERE "group" = 'manager' AND x_pass = 'true' AND state = 'done') AS cs_pass,
                    COUNT(*) FILTER (WHERE "group" = 'manager' AND fail = 'true' AND state = 'done') AS cs_fail,

                    COUNT(*) FILTER (WHERE "group" = 'cs' AND x_pass = 'true' AND state = 'done') AS manager_pass,
                    COUNT(*) FILTER (WHERE "group" = 'cs' AND fail = 'true' AND state = 'done') AS manager_fail,

                    COUNT(DISTINCT report_id) AS standard_votes
                FROM filtered
                GROUP BY user_id, user_branch_id, area_id, user_login
            )
            SELECT
                g.user_id,
                g.user_branch_id,
                g.user_login,
                g.area_id,
                g.cs_count,
                g.manager_count,
                g.cs_pass,
                g.cs_fail,
                g.manager_pass,
                g.manager_fail,
                g.standard_votes,
                (g.standard_votes - g.cs_count) AS remark_count,
                
                COALESCE(ra.cs_total_task, 0) AS cs_total_task,
                COALESCE(ra.gs_total_task, 0) AS gs_total_task,
                COALESCE(ra.late_reports, 0) AS late_reports,
                CASE
                    WHEN (g.cs_pass + g.cs_fail) > 0 THEN 
                        ROUND(100 * g.cs_pass::DECIMAL / NULLIF((g.cs_pass + g.cs_fail)::DECIMAL, 0), 2)
                    ELSE 0
                END AS cs_score,
                CASE
                    WHEN (g.manager_pass + g.manager_fail) > 0 THEN 
                        ROUND(100 * g.manager_pass::DECIMAL / NULLIF((g.manager_pass + g.manager_fail)::DECIMAL, 0), 2)
                    ELSE 0
                END AS manager_score,
                CASE
                    WHEN COALESCE(ra.gs_total_task, 0) > 0 THEN 
                        ROUND(100 * g.manager_count::DECIMAL / NULLIF(ra.gs_total_task::DECIMAL, 0), 2)
                    ELSE 0
                END AS percent_recheck,
                CASE
                    WHEN (g.manager_pass + g.manager_fail) = 0 THEN
                        CASE
                            WHEN (g.cs_pass + g.cs_fail) > 0 THEN 
                                ROUND(100 * g.cs_pass::DECIMAL / NULLIF((g.cs_pass + g.cs_fail)::DECIMAL, 0), 2)
                            ELSE 0
                        END
                    ELSE
                        ROUND((
                            COALESCE(100 * g.cs_pass::DECIMAL / NULLIF((g.cs_pass + g.cs_fail)::DECIMAL, 0), 0) +
                            COALESCE(100 * g.manager_pass::DECIMAL / NULLIF((g.manager_pass + g.manager_fail)::DECIMAL, 0), 0)
                        ) / 2, 2)
                END AS final_score,
                ROUND(
                    ABS(
                        CASE
                            WHEN (g.manager_pass + g.manager_fail) > 0 THEN 
                                (100 * g.manager_pass::DECIMAL / NULLIF((g.manager_pass + g.manager_fail)::DECIMAL, 0))
                            ELSE 0
                        END
                        -
                        CASE
                            WHEN (g.cs_pass + g.cs_fail) > 0 THEN 
                                (100 * g.cs_pass::DECIMAL / NULLIF((g.cs_pass + g.cs_fail)::DECIMAL, 0))
                            ELSE 0
                        END
                    ), 2
                ) AS score_diff,
                CASE
                    WHEN g.standard_votes > 0 THEN 
                        ROUND(100 * g.cs_count::DECIMAL / NULLIF(g.standard_votes::DECIMAL, 0), 2)
                    ELSE 0
                END AS percent_cs_vote
            FROM grouped g
            LEFT JOIN report_assignment ra ON g.user_id = ra.user_id AND g.area_id = ra.area_id AND g.user_branch_id = ra.user_branch_id
            WHERE g.user_branch_id IS NOT NULL;
        """

        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        t_staf_score_count = 0
        t_supervisor_score_count = 0
        t_score_difference_count = 0
        t_staff_evluation_rate_count = 0
        t_re_evaluation_rate_count = 0
        t_customer_service_score_count = 0
        # Cộng dồn điểm trung bình
        t_staf_score = 0
        t_supervisor_score = 0
        t_score_difference = 0
        t_staff_evluation_rate = 0
        t_re_evaluation_rate = 0
        t_customer_service_score = 0
        group_user_branch_id = list(set([item['user_branch_id'] for item in result]))
        for branch in group_user_branch_id:
            result_branch = [item for item in result if item['user_branch_id'] == branch]
            def get_first_score(key):
                for item in result_branch:
                    if item.get(key, 0) > 0:
                        return True
                return False
            if get_first_score('cs_score'):
                t_staf_score_count += 1
            if get_first_score('manager_score'):
                t_supervisor_score_count += 1
            if get_first_score('score_diff'):
                t_score_difference_count += 1
            if get_first_score('percent_cs_vote'):
                t_staff_evluation_rate_count += 1
            if get_first_score('percent_recheck'):
                t_re_evaluation_rate_count += 1
            if get_first_score('final_score'):
                t_customer_service_score_count += 1

            total_cs_count = sum(item['cs_count'] for item in result_branch)
            total_gs_count = sum(item['manager_count'] for item in result_branch)
            staff_criteria_passed = sum(item['cs_pass'] for item in result_branch)
            staff_criteria_failed = sum(item['cs_fail'] for item in result_branch)
            supervisor_criteria_passed = sum(item['manager_pass'] for item in result_branch)
            supervisor_criteria_failed = sum(item['manager_fail'] for item in result_branch)
            standard_form_count = sum(item['standard_votes'] for item in result_branch)
            missing_evaluation_form_count = sum(item['remark_count'] for item in result_branch)
            total_cs_task = sum(item['cs_total_task'] for item in result_branch)
            total_gs_task = sum(item['gs_total_task'] for item in result_branch)
            late_reports = sum(item['late_reports'] for item in result_branch)

            def avg_score_by_area(result_branch, score_key):
                area_scores = {}
                for item in result_branch:
                    area_id = item.get('area_id')
                    score = item.get(score_key, 0)
                    if area_id and score > 0:
                        if area_id not in area_scores:
                            area_scores[area_id] = []
                        area_scores[area_id].append(score)
                area_avg_scores = []
                for scores in area_scores.values():
                    if scores:
                        area_avg_scores.append(sum(scores) / len(scores))
                return sum(area_avg_scores) / len(area_avg_scores) if area_avg_scores else 0
            staffScore = avg_score_by_area(result_branch, 'cs_score')
            supervisorScore = avg_score_by_area(result_branch, 'manager_score')
            scoreDifference = avg_score_by_area(result_branch, 'score_diff')
            staffEvaluationRate = avg_score_by_area(result_branch, 'percent_cs_vote')
            re_evaluation_rate = avg_score_by_area(result_branch, 'percent_recheck')
            if supervisorScore == 0:
                customerServiceScore = staffScore
            else:
                customerServiceScore = avg_score_by_area(result_branch, 'final_score')
            # Cộng dồn điểm trung bình
            t_staf_score += staffScore
            t_supervisor_score += supervisorScore
            t_score_difference += scoreDifference
            t_staff_evluation_rate += staffEvaluationRate
            t_re_evaluation_rate+= re_evaluation_rate
            t_customer_service_score += customerServiceScore
            branch_name = self.env['ttb.branch'].browse(branch).name
            branch_value = {
                'user_branch_id': branch_name,
                'cs_count': total_cs_count,
                'manager_count': total_gs_count,
                'percent_recheck': re_evaluation_rate,
                'cs_score': staffScore,
                'manager_score': supervisorScore,
                'final_score': customerServiceScore,
                'score_diff': scoreDifference,
                'percent_cs_vote': staffEvaluationRate,
                'cs_pass': staff_criteria_passed,
                'cs_fail': staff_criteria_failed,
                'manager_pass': supervisor_criteria_passed,
                'manager_fail': supervisor_criteria_failed,
                'standard_votes': standard_form_count,
                'remark_count': missing_evaluation_form_count,
                'cs_total_task': total_cs_task,
                'gs_total_task': total_gs_task,
                'late_reports': late_reports
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
            # Nhóm theo khu vực
            group_area_id = list(set([item.get('area_id') for item in result_branch if 'area_id' in item]))
            for area in group_area_id:
                result_area = [item for item in result_branch if item['area_id'] == area]

                total_cs_count = sum(item['cs_count'] for item in result_area)
                total_gs_count = sum(item['manager_count'] for item in result_area)
                staff_criteria_passed = sum(item['cs_pass'] for item in result_area)
                staff_criteria_failed = sum(item['cs_fail'] for item in result_area)
                supervisor_criteria_passed = sum(item['manager_pass'] for item in result_area)
                supervisor_criteria_failed = sum(item['manager_fail'] for item in result_area)
                standard_form_count = sum(item['standard_votes'] for item in result_area)
                missing_evaluation_form_count = sum(item['remark_count'] for item in result_area)
                late_reports = sum(item['late_reports'] for item in result_area)

                valid_staff_scores = [item['cs_score'] for item in result_area if item['cs_score'] > 0]
                staffScore = sum(valid_staff_scores) / len(valid_staff_scores) if valid_staff_scores else 0

                valid_supervisor_scores = [item['manager_score'] for item in result_area if item['manager_score'] > 0]
                supervisorScore = sum(valid_supervisor_scores) / len(valid_supervisor_scores) if valid_supervisor_scores else 0

                valid_score_diffs = [item['score_diff'] for item in result_area if item['score_diff'] > 0]
                scoreDifference = sum(valid_score_diffs) / len(valid_score_diffs) if valid_score_diffs else 0

                valid_percent_votes = [item['percent_cs_vote'] for item in result_area if item['percent_cs_vote'] > 0]
                staffEvaluationRate = sum(valid_percent_votes) / len(valid_percent_votes) if valid_percent_votes else 0
                if supervisorScore == 0:
                    customerServiceScore = staffScore
                else:
                    valid_final_scores = [item['final_score'] for item in result_area if item['final_score'] > 0]
                    customerServiceScore = sum(valid_final_scores) / len(valid_final_scores) if valid_final_scores else 0
                valid_re_evaluation_rates = [item['percent_recheck'] for item in result_area if item['percent_recheck'] > 0]
                re_evaluation_rate = sum(valid_re_evaluation_rates) / len(valid_re_evaluation_rates) if valid_re_evaluation_rates else 0
                total_cs_task = sum(item['cs_total_task'] for item in result_area)
                total_gs_task = sum(item['gs_total_task'] for item in result_area)
                area_name = self.env['ttb.area'].browse(area).name
                area_value = {
                    'area_id': area_name,
                    'cs_count': total_cs_count,
                    'manager_count': total_gs_count,
                    'percent_recheck': re_evaluation_rate,
                    'cs_score': staffScore,
                    'manager_score': supervisorScore,
                    'final_score': customerServiceScore,
                    'score_diff': scoreDifference,
                    'percent_cs_vote': staffEvaluationRate,
                    'cs_pass': staff_criteria_passed,
                    'cs_fail': staff_criteria_failed,
                    'manager_pass': supervisor_criteria_passed,
                    'manager_fail': supervisor_criteria_failed,
                    'standard_votes': standard_form_count,
                    'remark_count': missing_evaluation_form_count,
                    'cs_total_task': total_cs_task,
                    'gs_total_task': total_gs_task,
                    'late_reports': late_reports
                }
                total_line_columns = []
                for column in options['columns']:
                    expr = column['expression_label']
                    value = area_value.get(expr)
                    total_line_columns.append(report._build_column_dict(value, column, options=options))

                lines.append({
                    'id': f"~ttb.branch~{branch}|~ttb.area~{area}",
                    'name': area_name,
                    'columns': total_line_columns,
                    'level': 2,
                    'unfoldable': True,
                    'unfolded': options.get('unfold_all'),
                    'parent_id': f"~ttb.branch~{branch}",
                })
                # line người được đánh giá
                for record in result_area:
                    line_columns = []
                    for column in options['columns']:
                        expr = column['expression_label']
                        value = record.get(expr)
                        if expr == 'user_id':
                            if value:
                                value = self.env['res.users'].browse(int(value)).name
                            else:
                                value = ''
                        if value is not None:
                            line_columns.append(report._build_column_dict(value, column, options=options))
                        else:
                            line_columns.append(
                                report._build_column_dict(0, column, options=options))  # hoặc giá trị mặc định khác
                    lines.append({
                        'id': f"~ttb.branch~{branch}|~ttb.area~{area}|~res.users~{record['user_id']}",
                        'name': '',
                        'columns': line_columns,
                        'level': 3,
                        'unfoldable': False,
                        'unfolded': False,
                        'parent_id': f"~ttb.branch~{branch}|~ttb.area~{area}"
                    })
        total_cs_count = sum(item['cs_count'] for item in result)
        total_gs_count = sum(item['manager_count'] for item in result)
        staff_criteria_passed = sum(item['cs_pass'] for item in result)
        staff_criteria_failed = sum(item['cs_fail'] for item in result)
        supervisor_criteria_passed = sum(item['manager_pass'] for item in result)
        supervisor_criteria_failed = sum(item['manager_fail'] for item in result)
        standard_form_count = sum(item['standard_votes'] for item in result)
        missing_evaluation_form_count = sum(item['remark_count'] for item in result)
        total_cs_task = sum(item['cs_total_task'] for item in result)
        total_gs_task = sum(item['gs_total_task'] for item in result)
        late_reports = sum(item['late_reports'] for item in result)
        staffScore = t_staf_score
        supervisorScore = t_supervisor_score
        scoreDifference = t_score_difference
        staffEvaluationRate = t_staff_evluation_rate
        if supervisorScore == 0:
            customerServiceScore = staffScore
        else:
            customerServiceScore = t_customer_service_score
        re_evaluation_rate = t_re_evaluation_rate
        staffScore_final = staffScore / t_staf_score_count if t_staf_score_count else 0
        supervisorScore_final = supervisorScore / t_supervisor_score_count if t_supervisor_score_count else 0
        scoreDifference_final = scoreDifference / t_score_difference_count if t_score_difference_count else 0
        staffEvaluationRate_final = staffEvaluationRate / t_staff_evluation_rate_count if t_staff_evluation_rate_count else 0
        customerServiceScore_final = customerServiceScore / t_customer_service_score_count if t_customer_service_score_count else 0
        re_evaluation_rate_final = re_evaluation_rate / t_re_evaluation_rate_count if t_re_evaluation_rate_count else 0
        branch_value = {
            'user_id': 'Tổng',
            'cs_count': total_cs_count,
            'manager_count': total_gs_count,
            'percent_recheck': re_evaluation_rate_final,
            'cs_score': staffScore_final,
            'manager_score': supervisorScore_final,
            'final_score': customerServiceScore_final,
            'score_diff': scoreDifference_final,
            'percent_cs_vote': staffEvaluationRate_final,
            'cs_pass': staff_criteria_passed,
            'cs_fail': staff_criteria_failed,
            'manager_pass': supervisor_criteria_passed,
            'manager_fail': supervisor_criteria_failed,
            'standard_votes': standard_form_count,
            'remark_count': missing_evaluation_form_count,
            'cs_total_task': total_cs_task,
            'gs_total_task': total_gs_task,
            'late_reports': late_reports
        }

        total_line_columns = []
        for column in options['columns']:
            expr = column['expression_label']
            value = branch_value.get(expr)
            total_line_columns.append(report._build_column_dict(value, column, options=options))

        lines.append({
            'id': f"~total_id~",
            'name': '',
            'columns': total_line_columns,
            'level': 1,
            'unfoldable': False,
            'unfolded': False,
        })
        return [(0, line) for line in lines]

class CskpiEvaluationReportEmployee(models.AbstractModel):
    _name = 'cskpi.evaluation.report.employee'
    _inherit = 'account.report.custom.handler'
    _description = 'Báo cáo KPI CSKH theo nhân viên'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        options['unfold_all'] = (options.get('filter_unfold_all') or options.get('unfold_all'))
        options['hide_filter_rounding_unit'] = True
        options['column_headers'] = []
        options['columns'] = [
            {
                'name': 'Mã nhân viên',
                'expression_label': 'user_login',
                'class': 'text',
                'type': 'string',
                'column_group_key': '1',
            },
            {
                'name': 'Người được đánh giá',
                'expression_label': 'user_id',
                'class': 'text',
                'type': 'string',
                'column_group_key': '1',
            },
            {
                'name': 'SL nhân viên',
                'expression_label': 'employee_count',
                'class': 'number',
                'type': 'number',
                'column_group_key': '2',
            },
            {
                'name': 'SL phiếu CS chấm',
                'expression_label': 'cs_count',
                'class': 'number',
                'type': 'integer',
                'figure_type': 'integer',
                'column_group_key': '3',
            },
            {
                'name': 'Tỷ lệ phiếu chấm của CS',
                'expression_label': 'percent_cs_vote',
                'class': 'number',
                'type': 'percentage',
                'figure_type': 'percentage',
                'column_group_key': '4',
            },
            {
                'name': 'SL phiếu GS chấm',
                'expression_label': 'manager_count',
                'class': 'number',
                'type': 'integer',
                'figure_type': 'integer',
                'column_group_key': '5',
            },
            {
                'name': 'Tỷ lệ phiếu chấm lại',
                'expression_label': 'percent_recheck',
                'class': 'number',
                'type': 'percentage',
                'figure_type': 'percentage',
                'column_group_key': '6',
            },
            {
                'name': 'Điểm CS chấm',
                'expression_label': 'cs_score',
                'class': 'number',
                'type': 'percentage',
                'figure_type': 'percentage',
                'column_group_key': '7',
            },
            {
                'name': 'Điểm GS chấm',
                'expression_label': 'manager_score',
                'class': 'number',
                'type': 'percentage',
                'figure_type': 'percentage',
                'column_group_key': '8',
            },
            {
                'name': 'Điểm CSKH',
                'expression_label': 'final_score',
                'class': 'number',
                'type': 'percentage',
                'figure_type': 'percentage',
                'column_group_key': '9',
            },
            {
                'name': 'Chênh lệch',
                'expression_label': 'score_diff',
                'class': 'number',
                'type': 'percentage',
                'figure_type': 'percentage',
                'column_group_key': '10',
            },
            {
                'name': 'SL tiêu chí CS chấm đạt',
                'expression_label': 'cs_pass',
                'class': 'number',
                'type': 'number',
                'column_group_key': '11',
            },
            {
                'name': 'SL tiêu chí CS chấm không đạt',
                'expression_label': 'cs_fail',
                'class': 'number',
                'type': 'number',
                'column_group_key': '12',
            },
            {
                'name': 'SL tiêu chí GS chấm đạt',
                'expression_label': 'manager_pass',
                'class': 'number',
                'type': 'number',
                'column_group_key': '13',
            },
            {
                'name': 'SL tiêu chí GS chấm không đạt',
                'expression_label': 'manager_fail',
                'class': 'number',
                'type': 'number',
                'column_group_key': '14',
            },
            {
                'name': 'Số phiếu tiêu chuẩn',
                'expression_label': 'standard_votes',
                'class': 'number',
                'type': 'number',
                'column_group_key': '15',
            },
            {
                'name': 'Số phiếu chấm thiếu',
                'expression_label': 'remark_count',
                'class': 'number',
                'type': 'number',
                'column_group_key': '16',
            },
        ]
        hidden_columns = set()
        options['show_all_field'] = (previous_options or {}).get('show_all_field', False)
        if not options['show_all_field']:
            hidden_columns.add('cs_pass')
            hidden_columns.add('cs_fail')
            hidden_columns.add('manager_pass')
            hidden_columns.add('manager_fail')
            hidden_columns.add('standard_votes')
            hidden_columns.add('remark_count')

        options['columns'] = [
            column for column in options['columns']
            if column['expression_label'] not in hidden_columns
        ]

    def _customize_warnings(self, report, options, all_column_groups_expression_totals, warnings):
        warnings.clear()

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals=None, warnings=None):
        lines = []
        date_from = options['date']['date_from']
        date_to = options['date']['date_to']
        query = f"""
                    WITH user_mapping AS (
                        SELECT 
                            ttb_task_report_id, 
                            MAX(res_users_id) AS res_users_id
                        FROM res_users_ttb_task_report_rel
                        GROUP BY ttb_task_report_id
                    ),
                    filtered AS (
                        SELECT
                            COALESCE(r.user_id, um.res_users_id) AS user_id,
                            line.user_branch_id,
                            r.id AS report_id,
                            r.group,
                            r.state,
                            line.x_pass,
                            line.fail,
                            r.kpi_type_id,
                            ru.login AS user_login
                        FROM ttb_task_report_line line
                        JOIN ttb_task_report r ON line.report_id = r.id
                        LEFT JOIN user_mapping um ON um.ttb_task_report_id = r.id
                        LEFT JOIN res_users ru ON ru.id = COALESCE(r.user_id, um.res_users_id)
                        JOIN ttb_kpi_type kpi ON r.kpi_type_id = kpi.id
                        WHERE kpi.code = 'CSKH'
                          AND (r.user_id IS NOT NULL OR um.res_users_id IS NOT NULL)
                          AND line.user_branch_id IS NOT NULL
                          AND r.deadline BETWEEN DATE '{date_from}' AND DATE '{date_to}'
                    ),
                    grouped AS (
                        SELECT
                            user_id,
                            user_branch_id,
                            user_login,
                            COUNT(DISTINCT report_id) FILTER (WHERE "group" = 'manager' AND state = 'done') AS cs_count,
                            COUNT(DISTINCT report_id) FILTER (WHERE "group" = 'cs' AND state = 'done') AS manager_count,
        
                            COUNT(*) FILTER (WHERE "group" = 'manager' AND x_pass = 'true' AND state = 'done') AS cs_pass,
                            COUNT(*) FILTER (WHERE "group" = 'manager' AND fail = 'true' AND state = 'done') AS cs_fail,
        
                            COUNT(*) FILTER (WHERE "group" = 'cs' AND x_pass = 'true' AND state = 'done') AS manager_pass,
                            COUNT(*) FILTER (WHERE "group" = 'cs' AND fail = 'true' AND state = 'done') AS manager_fail,

                            COUNT(DISTINCT report_id) AS standard_votes
                        FROM filtered
                        GROUP BY user_id, user_branch_id, user_login
                    )
                    SELECT
                        user_id,
                        user_branch_id,
                        cs_count,
                        manager_count,
                        cs_pass,
                        cs_fail,
                        manager_pass,
                        manager_fail,
                        standard_votes,
                        user_login,
                        1 AS employee_count,
                        (standard_votes - cs_count) AS remark_count,
                        CASE
                            WHEN (cs_pass + cs_fail) > 0 THEN 
                                ROUND(100 * cs_pass::DECIMAL / NULLIF((cs_pass + cs_fail)::DECIMAL, 0), 2)
                            ELSE 0
                        END AS cs_score,
                        CASE
                            WHEN (manager_pass + manager_fail) > 0 THEN 
                                ROUND(100 * manager_pass::DECIMAL / NULLIF((manager_pass + manager_fail)::DECIMAL, 0), 2)
                            ELSE 0
                        END AS manager_score,
                        ROUND(100 * manager_count::DECIMAL / 1, 2) AS percent_recheck,
                        CASE
                            WHEN (manager_pass + manager_fail) = 0 THEN
                                CASE
                                    WHEN (cs_pass + cs_fail) > 0 THEN 
                                        ROUND(100 * cs_pass::DECIMAL / NULLIF((cs_pass + cs_fail)::DECIMAL, 0), 2)
                                    ELSE 0
                                END
                            ELSE
                                ROUND((
                                    COALESCE(100 * cs_pass::DECIMAL / NULLIF((cs_pass + cs_fail)::DECIMAL, 0), 0) +
                                    COALESCE(100 * manager_pass::DECIMAL / NULLIF((manager_pass + manager_fail)::DECIMAL, 0), 0)
                                ) / 2, 2)
                        END AS final_score,
                        ROUND(
                            ABS(
                                CASE
                                    WHEN (manager_pass + manager_fail) > 0 THEN 
                                        (100 * manager_pass::DECIMAL / NULLIF((manager_pass + manager_fail)::DECIMAL, 0))
                                    ELSE 0
                                END
                                -
                                CASE
                                    WHEN (cs_pass + cs_fail) > 0 THEN 
                                        (100 * cs_pass::DECIMAL / NULLIF((cs_pass + cs_fail)::DECIMAL, 0))
                                    ELSE 0
                                END
                            ), 2
                        ) AS score_diff,
                        CASE
                            WHEN standard_votes > 0 THEN 
                                ROUND(100 * cs_count::DECIMAL / NULLIF(standard_votes::DECIMAL, 0), 2)
                            ELSE 0
                        END AS percent_cs_vote
                    FROM grouped
                    WHERE user_branch_id IS NOT NULL
                """

        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()

        group_user_branch_id = list(set([item['user_branch_id'] for item in result]))
        for branch in group_user_branch_id:
            result_branch = [item for item in result if item['user_branch_id'] == branch]

            total_cs_count = sum(item['cs_count'] for item in result_branch)
            total_gs_count = sum(item['manager_count'] for item in result_branch)
            total_employee = sum(item['employee_count'] for item in result_branch)
            staff_criteria_passed = sum(item['cs_pass'] for item in result_branch)
            staff_criteria_failed = sum(item['cs_fail'] for item in result_branch)
            supervisor_criteria_passed = sum(item['manager_pass'] for item in result_branch)
            supervisor_criteria_failed = sum(item['manager_fail'] for item in result_branch)
            standard_form_count = sum(item['standard_votes'] for item in result_branch)
            missing_evaluation_form_count = sum(item['remark_count'] for item in result_branch)
            valid_staff_scores = [item['cs_score'] for item in result_branch if item['cs_score'] > 0]
            staffScore = sum(valid_staff_scores) / len(valid_staff_scores) if valid_staff_scores else 0

            valid_supervisor_scores = [item['manager_score'] for item in result_branch if item['manager_score'] > 0]
            supervisorScore = sum(valid_supervisor_scores) / len(valid_supervisor_scores) if valid_supervisor_scores else 0

            valid_score_diffs = [item['score_diff'] for item in result_branch if item['score_diff'] > 0]
            scoreDifference = sum(valid_score_diffs) / len(valid_score_diffs) if valid_score_diffs else 0

            valid_percent_votes = [item['percent_cs_vote'] for item in result_branch if item['percent_cs_vote'] > 0]
            staffEvaluationRate = sum(valid_percent_votes) / len(valid_percent_votes) if valid_percent_votes else 0
            if supervisorScore == 0:
                customerServiceScore = staffScore
            else:
                valid_final_scores = [item['final_score'] for item in result_branch if item['final_score'] > 0]
                customerServiceScore = sum(valid_final_scores) / len(valid_final_scores) if valid_final_scores else 0
            valid_re_evaluation_rates = [item['percent_recheck'] for item in result_branch if item['percent_recheck'] > 0]
            re_evaluation_rate = sum(valid_re_evaluation_rates) / len(valid_re_evaluation_rates) if valid_re_evaluation_rates else 0
            branch_name = self.env['ttb.branch'].browse(branch).name
            branch_value = {
                'user_branch_id': branch_name,
                'cs_count': total_cs_count,
                'manager_count': total_gs_count,
                'percent_recheck': re_evaluation_rate,
                'cs_score': staffScore,
                'manager_score': supervisorScore,
                'final_score': customerServiceScore,
                'score_diff': scoreDifference,
                'percent_cs_vote': staffEvaluationRate,
                'employee_count': total_employee,
                'cs_pass': staff_criteria_passed,
                'cs_fail': staff_criteria_failed,
                'manager_pass': supervisor_criteria_passed,
                'manager_fail': supervisor_criteria_failed,
                'standard_votes': standard_form_count,
                'remark_count': missing_evaluation_form_count
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

            # line người được đánh giá
            for record in result_branch:
                line_columns = []
                for column in options['columns']:
                    expr = column['expression_label']
                    value = record.get(expr)
                    if expr == 'user_id':
                        value = self.env['res.users'].browse(int(value)).name
                    line_columns.append(report._build_column_dict(value, column, options=options))

                lines.append({
                    'id': f"~ttb.branch~{branch}|~res.users~{record['user_id']}",
                    'name': '',
                    'columns': line_columns,
                    'level': 2,
                    'unfoldable': False,
                    'unfolded': False,
                    'parent_id': f"~ttb.branch~{branch}"
                })
        total_cs_count = sum(item['cs_count'] for item in result)
        total_gs_count = sum(item['manager_count'] for item in result)
        total_employee = sum(item['employee_count'] for item in result)
        staff_criteria_passed = sum(item['cs_pass'] for item in result)
        staff_criteria_failed = sum(item['cs_fail'] for item in result)
        supervisor_criteria_passed = sum(item['manager_pass'] for item in result)
        supervisor_criteria_failed = sum(item['manager_fail'] for item in result)
        standard_form_count = sum(item['standard_votes'] for item in result)
        missing_evaluation_form_count = sum(item['remark_count'] for item in result)
        valid_staff_scores = [item['cs_score'] for item in result if item['cs_score'] > 0]
        staffScore = sum(valid_staff_scores) / len(valid_staff_scores) if valid_staff_scores else 0

        valid_supervisor_scores = [item['manager_score'] for item in result if item['manager_score'] > 0]
        supervisorScore = sum(valid_supervisor_scores) / len(valid_supervisor_scores) if valid_supervisor_scores else 0

        valid_score_diffs = [item['score_diff'] for item in result if item['score_diff'] > 0]
        scoreDifference = sum(valid_score_diffs) / len(valid_score_diffs) if valid_score_diffs else 0

        valid_percent_votes = [item['percent_cs_vote'] for item in result if item['percent_cs_vote'] > 0]
        staffEvaluationRate = sum(valid_percent_votes) / len(valid_percent_votes) if valid_percent_votes else 0
        if supervisorScore == 0:
            customerServiceScore = staffScore
        else:
            valid_final_scores = [item['final_score'] for item in result if item['final_score'] > 0]
            customerServiceScore = sum(valid_final_scores) / len(valid_final_scores) if valid_final_scores else 0
        valid_re_evaluation_rates = [item['percent_recheck'] for item in result if item['percent_recheck'] > 0]
        re_evaluation_rate = sum(valid_re_evaluation_rates) / len(valid_re_evaluation_rates) if valid_re_evaluation_rates else 0
        branch_value = {
            'user_id': 'Tổng',
            'cs_count': total_cs_count,
            'manager_count': total_gs_count,
            'percent_recheck': re_evaluation_rate,
            'cs_score': staffScore,
            'manager_score': supervisorScore,
            'final_score': customerServiceScore,
            'score_diff': scoreDifference,
            'percent_cs_vote': staffEvaluationRate,
            'employee_count': total_employee,
            'cs_pass': staff_criteria_passed,
            'cs_fail': staff_criteria_failed,
            'manager_pass': supervisor_criteria_passed,
            'manager_fail': supervisor_criteria_failed,
            'standard_votes': standard_form_count,
            'remark_count': missing_evaluation_form_count
        }

        total_line_columns = []
        for column in options['columns']:
            expr = column['expression_label']
            value = branch_value.get(expr)
            total_line_columns.append(report._build_column_dict(value, column, options=options))

        lines.append({
            'id': f"~total_id~",
            'name': '',
            'columns': total_line_columns,
            'level': 1,
            'unfoldable': False,
            'unfolded': False,
        })
        return [(0, line) for line in lines]
