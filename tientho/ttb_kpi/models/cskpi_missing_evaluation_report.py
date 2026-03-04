import datetime
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CskpiMissingEvaluationReport(models.AbstractModel):
    _name = 'cskpi.missing.evaluation.report'
    _inherit = 'account.report.custom.handler'
    _description = 'Báo cáo số phiếu chấm thiếu CSKH'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        options['unfold_all'] = (options.get('filter_unfold_all') or options.get('unfold_all'))
        options['hide_filter_rounding_unit'] = True
        options['column_headers'] = []
        options['columns'] = [
            {
                'name': 'Khu vực',
                'expression_label': 'area_name',
                'class': 'text',
                'type': 'string',
                'column_group_key': '1',
            },
            {
                'name': 'Nhóm đánh giá',
                'expression_label': 'task_group',
                'class': 'text',
                'type': 'string',
                'column_group_key': '1',
            },
            {
                'name': 'Người đánh giá',
                'expression_label': 'reviewer_name',
                'class': 'text',
                'type': 'string',
                'column_group_key': '1',
            },
            {
                'name': 'Người được đánh giá',
                'expression_label': 'user_name',
                'class': 'text',
                'type': 'string',
                'column_group_key': '1',
            },
            {
                'name': 'CS cần chấm (phiếu)',
                'expression_label': 'cs_total_task',
                'class': 'number',
                'figure_type': 'integer',
                'type': 'integer',
                'column_group_key': '1',
            },
            {
                'name': 'CS đã chấm (phiếu)',
                'expression_label': 'cs_done_task',
                'class': 'number',
                'figure_type': 'integer',
                'type': 'integer',
                'column_group_key': '1',
            },
            {
                'name': 'CS chấm thiếu (phiếu)',
                'expression_label': 'cs_not_done_task',
                'class': 'number',
                'figure_type': 'integer',
                'type': 'integer',
                'column_group_key': '1',
            },
            {
                'name': 'Tỷ lệ chấm CS',
                'expression_label': 'cs_rate',
                'class': 'number',
                'figure_type': 'percentage',
                'type': 'percentage',
                'column_group_key': '1',
            },
            {
                'name': 'GS cần chấm (phiếu)',
                'expression_label': 'gs_total_task',
                'class': 'number',
                'figure_type': 'integer',
                'type': 'integer',
                'column_group_key': '1',
            },
            {
                'name': 'GS đã chấm (phiếu)',
                'expression_label': 'gs_done_task',
                'class': 'number',
                'figure_type': 'integer',
                'type': 'integer',
                'column_group_key': '1',
            },
            {
                'name': 'GS chấm thiếu (phiếu)',
                'expression_label': 'gs_not_done_task',
                'class': 'number',
                'figure_type': 'integer',
                'type': 'integer',
                'column_group_key': '1',
            },
            {
                'name': 'Tỷ lệ chấm GS',
                'expression_label': 'gs_rate',
                'class': 'number',
                'figure_type': 'percentage',
                'type': 'percentage',
                'column_group_key': '1',
            },
            {
                'name': 'Tổng số phiếu cần chấm (phiếu)',
                'expression_label': 'total_task_report',
                'class': 'number',
                'figure_type': 'integer',
                'type': 'integer',
                'column_group_key': '1',
            },
            {
                'name': 'Tổng số phiếu đã chấm (phiếu)',
                'expression_label': 'task_report_done',
                'class': 'number',
                'figure_type': 'integer',
                'type': 'integer',
                'column_group_key': '1',
            },
            {
                'name': 'Tổng số phiếu chấm thiếu (phiếu)',
                'expression_label': 'task_report_not_done',
                'class': 'number',
                'figure_type': 'integer',
                'type': 'integer',
                'column_group_key': '1',
            },
            {
                'name': 'Tỷ lệ chấm',
                'expression_label': 'total_rate',
                'class': 'number',
                'figure_type': 'percentage',
                'type': 'percentage',
                'column_group_key': '1',
            }
        ]

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals=None, warnings=None):
        lines = []
        kpi_type_id = self.env.ref('ttb_kpi.ttb_kpi_type_cskh').id
        date_from = options['date']['date_from']
        date_to = options['date']['date_to']
        query = f"""
                WITH user_mapping AS (
                    SELECT 
                        ttb_task_report_id, 
                        MAX(res_users_id) AS res_users_id
                    FROM res_users_ttb_task_report_rel
                    GROUP BY ttb_task_report_id
                )

                SELECT 
                    task.user_branch_id AS user_branch_id,
                    br.name AS brand_name,

                    COALESCE(task.user_id, um.res_users_id, -1) AS user_id,                       
                    COALESCE(rp.name, '') AS user_name,  
                    COALESCE(ru.login, '') AS user_code,

                    COUNT(DISTINCT task.id) FILTER (
                        WHERE task.group = 'manager' AND (task.user_id IS NOT NULL OR um.res_users_id IS NOT NULL)
                    ) AS cs_total_task,

                    COUNT(DISTINCT task.id) FILTER (
                        WHERE task.state = 'done' AND task.group = 'manager' AND (task.user_id IS NOT NULL OR um.res_users_id IS NOT NULL)
                    ) AS cs_done_task,

                    COUNT(DISTINCT task.id) FILTER (
                        WHERE task.group = 'manager' AND (task.user_id IS NOT NULL OR um.res_users_id IS NOT NULL)
                    ) - 
                    COUNT(DISTINCT task.id) FILTER (
                        WHERE state = 'done' AND task.group = 'manager' AND (task.user_id IS NOT NULL OR um.res_users_id IS NOT NULL)
                    ) AS cs_not_done_task,

                    CASE 
                        WHEN COUNT(DISTINCT task.id) FILTER (
                                WHERE task.group = 'manager' AND (task.user_id IS NOT NULL OR um.res_users_id IS NOT NULL)
                             ) > 0 THEN
                            (COUNT(DISTINCT task.id) FILTER (
                                WHERE state = 'done' AND task.group = 'manager' AND (task.user_id IS NOT NULL OR um.res_users_id IS NOT NULL)
                             ) * 100.0) /
                            COUNT(DISTINCT task.id) FILTER (
                                WHERE task.group = 'manager' AND (task.user_id IS NOT NULL OR um.res_users_id IS NOT NULL)
                            )
                        ELSE 0
                    END AS cs_rate,

                    COALESCE(task.reviewer_id, -1) AS reviewer_id,
                    COALESCE(rrp.name, '') AS reviewer_name,
                    COALESCE(rru.login, '') AS reviewer_code,

                    COUNT(DISTINCT task.id) FILTER (WHERE task.group = 'cs') AS gs_total_task,

                    COUNT(DISTINCT task.id) FILTER (WHERE state = 'done' AND task.group = 'cs') AS gs_done_task,

                    COUNT(DISTINCT task.id) FILTER (WHERE task.group = 'cs' ) 
                    - 
                    COUNT(DISTINCT task.id) FILTER (WHERE state = 'done' AND task.group = 'cs') AS gs_not_done_task,
                    CASE 
                        WHEN COUNT(DISTINCT task.id) FILTER (WHERE task.group = 'cs') > 0 THEN
                            (COUNT(DISTINCT task.id) FILTER (WHERE state = 'done' AND task.group = 'cs') * 100.0) / COUNT(DISTINCT task.id) FILTER (WHERE task.group = 'cs' )
                        ELSE 0
                    END AS gs_rate,

                    COUNT(DISTINCT task.id) AS total_task_report,
                    COUNT(DISTINCT task.id) FILTER (WHERE state = 'done') AS task_report_done,
                    COUNT(DISTINCT task.id) - COUNT(DISTINCT task.id) FILTER (WHERE state = 'done') AS task_report_not_done,

                    CASE 
                        WHEN COUNT(DISTINCT task.id) > 0 THEN
                            (COUNT(DISTINCT task.id) FILTER (WHERE state = 'done') * 100.0) / COUNT(DISTINCT task.id)
                        ELSE 0
                    END AS total_rate,

                    COALESCE(task.area_id, -1) AS area_id,
                    COALESCE(ta.name, '') AS area_name,
                    task.group AS task_group

                FROM ttb_task_report AS task

                LEFT JOIN user_mapping um ON um.ttb_task_report_id = task.id
                LEFT JOIN ttb_branch AS br ON br.id = task.user_branch_id
                LEFT JOIN res_users AS rru ON rru.id = task.reviewer_id
                LEFT JOIN res_partner AS rrp ON rrp.id = rru.partner_id

                LEFT JOIN res_users AS ru ON ru.id = COALESCE(task.user_id, um.res_users_id)
                LEFT JOIN res_partner AS rp ON rp.id = ru.partner_id
                LEFT JOIN ttb_area AS ta ON ta.id = task.area_id

                WHERE task.kpi_type_id = {kpi_type_id} AND task.deadline BETWEEN DATE '{date_from}' AND DATE '{date_to}'

                GROUP BY 
                    task.user_branch_id, br.name,
                    COALESCE(task.reviewer_id, -1), COALESCE(rrp.name, ''),
                    COALESCE(task.user_id, um.res_users_id, -1), COALESCE(rp.name, ''), 
                    COALESCE(rru.login, ''), COALESCE(ru.login, ''),
                    COALESCE(ta.name, ''), task.group, COALESCE(task.area_id, -1)

                ORDER BY 
                    task.user_branch_id,
                    split_part(COALESCE(rrp.name, ''), ' ', array_length(string_to_array(COALESCE(rrp.name, ''), ' '), 1)),
                    split_part(COALESCE(rp.name, ''), ' ', array_length(string_to_array(COALESCE(rp.name, ''), ' '), 1))

                """
        self.env.cr.execute(query)

        result = self.env.cr.dictfetchall()
        group_user_branch_id = list(set([item['user_branch_id'] for item in result]))
        for branch in group_user_branch_id:
            result_branch = [item for item in result if item['user_branch_id'] == branch]
            #Line cơ sở
            branch_cs_task_report = sum(item['cs_total_task'] for item in result_branch)
            branch_cs_task_report_done = sum(item['cs_done_task'] for item in result_branch)
            branch_cs_task_report_not_done = sum(item['cs_not_done_task'] for item in result_branch)
            branch_cs_rate = (branch_cs_task_report_done / branch_cs_task_report) * 100 if branch_cs_task_report else 0

            branch_gs_task_report = sum(item['gs_total_task'] for item in result_branch)
            branch_gs_task_report_done = sum(item['gs_done_task'] for item in result_branch)
            branch_gs_task_report_not_done = sum(item['gs_not_done_task'] for item in result_branch)
            branch_gs_rate = (branch_gs_task_report_done / branch_gs_task_report) * 100 if branch_gs_task_report else 0

            branch_task_report = sum(item['total_task_report'] for item in result_branch)
            branch_task_report_done = sum(item['task_report_done'] for item in result_branch)
            branch_task_report_not_done = sum(item['task_report_not_done'] for item in result_branch)
            branch_rate = (branch_task_report_done / branch_task_report) * 100 if branch_task_report else 0.0
            branch_value = {
                'area_name': '',
                'task_group': '',
                'reviewer_name': '',
                'user_id': '',
                'cs_total_task': branch_cs_task_report,
                'cs_done_task': branch_cs_task_report_done,
                'cs_not_done_task': branch_cs_task_report_not_done,
                'cs_rate': branch_cs_rate,
                'gs_total_task': branch_gs_task_report,
                'gs_done_task': branch_gs_task_report_done,
                'gs_not_done_task': branch_gs_task_report_not_done,
                'gs_rate': branch_gs_rate,
                'total_task_report': branch_task_report,
                'task_report_done': branch_task_report_done,
                'task_report_not_done': branch_task_report_not_done,
                'total_rate': branch_rate
            }
            total_line_columns = []
            for column in options['columns']:
                expr = column['expression_label']
                value = branch_value.get(expr)
                total_line_columns.append(report._build_column_dict(value, column, options=options))
            lines.append({
                'id': f"~ttb.branch~{branch}",
                'name': result_branch[0]['brand_name'],
                'columns': total_line_columns,
                'level': 1,
                'unfoldable': True,
                'unfolded': options.get('unfold_all'),
            })
            group_area_id = list(set([item['area_id'] for item in result_branch]))
            for area_id in group_area_id:
                result_area = [item for item in result_branch if item['area_id'] == area_id]
                #line khu vực
                area_cs_task_report = sum(item['cs_total_task'] for item in result_area)
                area_cs_task_report_done = sum(item['cs_done_task'] for item in result_area)
                area_cs_task_report_not_done = sum(item['cs_not_done_task'] for item in result_area)
                area_cs_rate = (area_cs_task_report_done / area_cs_task_report) * 100 if area_cs_task_report else 0

                area_gs_task_report = sum(item['gs_total_task'] for item in result_area)
                area_gs_task_report_done = sum(item['gs_done_task'] for item in result_area)
                area_gs_task_report_not_done = sum(item['gs_not_done_task'] for item in result_area)
                area_gs_rate = (area_gs_task_report_done / area_gs_task_report) * 100 if area_gs_task_report else 0

                area_task_report = sum(item['total_task_report'] for item in result_area)
                area_task_report_done = sum(item['task_report_done'] for item in result_area)
                area_task_report_not_done = sum(item['task_report_not_done'] for item in result_area)
                area_rate = (area_task_report_done / area_task_report) * 100 if area_task_report else 0.0
                area_value = {
                    'brand_name': '',
                    'area_name': result_area[0]['area_name'],
                    'task_group': '',
                    'reviewer_name': '',
                    'user_id': '',
                    'cs_total_task': area_cs_task_report,
                    'cs_done_task': area_cs_task_report_done,
                    'cs_not_done_task': area_cs_task_report_not_done,
                    'cs_rate': area_cs_rate,
                    'gs_total_task': area_gs_task_report,
                    'gs_done_task': area_gs_task_report_done,
                    'gs_not_done_task': area_gs_task_report_not_done,
                    'gs_rate': area_gs_rate,
                    'total_task_report': area_task_report,
                    'task_report_done': area_task_report_done,
                    'task_report_not_done': area_task_report_not_done,
                    'total_rate': area_rate
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
                group_task_group = list(set([item['task_group'] for item in result_area]))
                for task_group in group_task_group:
                    result_group = [item for item in result_area if item['task_group'] == task_group]
                    # line group
                    group_cs_task_report = sum(item['cs_total_task'] for item in result_group)
                    group_cs_task_report_done = sum(item['cs_done_task'] for item in result_group)
                    group_cs_task_report_not_done = sum(item['cs_not_done_task'] for item in result_group)
                    group_cs_rate = (group_cs_task_report_done / group_cs_task_report) * 100 if group_cs_task_report else 0

                    group_gs_task_report = sum(item['gs_total_task'] for item in result_group)
                    group_gs_task_report_done = sum(item['gs_done_task'] for item in result_group)
                    group_gs_task_report_not_done = sum(item['gs_not_done_task'] for item in result_group)
                    group_gs_rate = (group_gs_task_report_done / group_gs_task_report) * 100 if group_gs_task_report else 0

                    group_task_report = sum(item['total_task_report'] for item in result_group)
                    group_task_report_done = sum(item['task_report_done'] for item in result_group)
                    group_task_report_not_done = sum(item['task_report_not_done'] for item in result_group)
                    group_rate = (group_task_report_done / group_task_report) * 100 if group_task_report else 0.0
                    group_name = {'region_manager': 'Quản lý vùng', 'branch_mannager': 'Quản lý cơ sở', 'cs': 'Trải nghiệm khách hàng', 'manager': 'Quản lý trực tiếp'}
                    group_value = {
                        'brand_name': '',
                        'area_name': '',
                        'task_group': group_name.get(task_group, ''),
                        'reviewer_name': '',
                        'user_id': '',
                        'cs_total_task': group_cs_task_report,
                        'cs_done_task': group_cs_task_report_done,
                        'cs_not_done_task': group_cs_task_report_not_done,
                        'cs_rate': group_cs_rate,
                        'gs_total_task': group_gs_task_report,
                        'gs_done_task': group_gs_task_report_done,
                        'gs_not_done_task': group_gs_task_report_not_done,
                        'gs_rate': group_gs_rate,
                        'total_task_report': group_task_report,
                        'task_report_done': group_task_report_done,
                        'task_report_not_done': group_task_report_not_done,
                        'total_rate': group_rate
                    }
                    total_line_columns = []
                    for column in options['columns']:
                        expr = column['expression_label']
                        value = group_value.get(expr)
                        total_line_columns.append(report._build_column_dict(value, column, options=options))
                    lines.append({
                        'id': f"~ttb.branch~{branch}|~ttb.area~{area_id}|~ttb.group~{task_group}",
                        'name': '',
                        'columns': total_line_columns,
                        'level': 1,
                        'unfoldable': True,
                        'unfolded': options.get('unfold_all'),
                        'parent_id': f"~ttb.branch~{branch}|~ttb.area~{area_id}",
                    })
                    group_reviewer_id = list(set([item['reviewer_id'] for item in result_group]))
                    for reviewer in group_reviewer_id:
                        result_reviewer = [item for item in result_group if item['reviewer_id'] == reviewer]
                        #line người đánh giá
                        result_cs_task_report = sum(item['cs_total_task'] for item in result_reviewer)
                        result_cs_task_report_done = sum(item['cs_done_task'] for item in result_reviewer)
                        result_cs_task_report_not_done = sum(item['cs_not_done_task'] for item in result_reviewer)
                        result_cs_rate = (result_cs_task_report_done / result_cs_task_report) * 100 if result_cs_task_report else 0

                        result_gs_task_report = sum(item['gs_total_task'] for item in result_reviewer)
                        result_gs_task_report_done = sum(item['gs_done_task'] for item in result_reviewer)
                        result_gs_task_report_not_done = sum(item['gs_not_done_task'] for item in result_reviewer)
                        result_gs_rate = (result_gs_task_report_done / result_gs_task_report) * 100 if result_gs_task_report else 0

                        result_task_report = sum(item['total_task_report'] for item in result_reviewer)
                        result_task_report_done = sum(item['task_report_done'] for item in result_reviewer)
                        result_task_report_not_done = sum(item['task_report_not_done'] for item in result_reviewer)
                        result_rate = (result_task_report_done / result_task_report) * 100 if result_task_report else 0.0
                        result_value = {
                            'brand_name': '',
                            'area_name': '',
                            'task_group':'',
                            'reviewer_name': f"{result_reviewer[0]['reviewer_code']} {result_reviewer[0]['reviewer_name']}",
                            'user_id': '',
                            'cs_total_task': result_cs_task_report,
                            'cs_done_task': result_cs_task_report_done,
                            'cs_not_done_task': result_cs_task_report_not_done,
                            'cs_rate': result_cs_rate,
                            'gs_total_task': result_gs_task_report,
                            'gs_done_task': result_gs_task_report_done,
                            'gs_not_done_task': result_gs_task_report_not_done,
                            'gs_rate': result_gs_rate,
                            'total_task_report': result_task_report,
                            'task_report_done': result_task_report_done,
                            'task_report_not_done': result_task_report_not_done,
                            'total_rate': result_rate
                        }
                        total_line_columns = []
                        for column in options['columns']:
                            expr = column['expression_label']
                            value = result_value.get(expr)
                            total_line_columns.append(report._build_column_dict(value, column, options=options))
                        lines.append({
                            'id': f"~ttb.branch~{branch}|~ttb.area~{area_id}|~ttb.group~{task_group}|~res.user~{reviewer}",
                            'name': '',
                            'columns': total_line_columns,
                            'level': 2,
                            'unfoldable': True,
                            'unfolded': options.get('unfold_all'),
                            'parent_id': f"~ttb.branch~{branch}|~ttb.area~{area_id}|~ttb.group~{task_group}",
                        })
                        #line người được đánh giá
                        for record in result_reviewer:
                            line_columns = []
                            for column in options['columns']:
                                expr = column['expression_label']
                                value = record.get(expr)
                                if expr in ['brand_name', 'reviewer_name', 'area_name', 'task_group', 'reviewer_name']:
                                    value = ''
                                if expr == 'user_name':
                                    value = f"{record.get('user_code', '')} {record.get('user_name', '')}"
                                line_columns.append(report._build_column_dict(value, column, options=options))
                            lines.append({
                                'id': f"~ttb.branch~{branch}|~ttb.area~{area_id}|~ttb.group~{task_group}|~res.user~{reviewer}|~res.users~{record['user_id']}",
                                'name': '',
                                'columns': line_columns,
                                'level': 3,
                                'unfoldable': False,
                                'unfolded': False,
                                'parent_id': f"~ttb.branch~{branch}|~ttb.area~{area_id}|~ttb.group~{task_group}|~res.user~{reviewer}",
                            })
        #Total line
        total_cs_task_report = sum(item['cs_total_task'] for item in result)
        total_cs_task_report_done = sum(item['cs_done_task'] for item in result)
        total_cs_task_report_not_done = sum(item['cs_not_done_task'] for item in result)
        total_cs_rate = (total_cs_task_report_done / total_cs_task_report) * 100 if total_cs_task_report else 0

        total_gs_task_report = sum(item['gs_total_task'] for item in result)
        total_gs_task_report_done = sum(item['gs_done_task'] for item in result)
        total_gs_task_report_not_done = sum(item['gs_not_done_task'] for item in result)
        total_gs_rate = (total_gs_task_report_done / total_gs_task_report) * 100 if total_gs_task_report else 0

        total_task_report = sum(item['total_task_report'] for item in result)
        total_task_report_done = sum(item['task_report_done'] for item in result)
        total_task_report_not_done = sum(item['task_report_not_done'] for item in result)
        total_rate = (total_task_report_done/total_task_report) * 100 if total_task_report else 0.0
        total_value = {
            'brand_name': '',
            'reviewer_name': '',
            'user_name': 'Tổng',
            'cs_total_task': total_cs_task_report,
            'cs_done_task': total_cs_task_report_done,
            'cs_not_done_task': total_cs_task_report_not_done,
            'cs_rate': total_cs_rate,
            'gs_total_task': total_gs_task_report,
            'gs_done_task': total_gs_task_report_done,
            'gs_not_done_task': total_gs_task_report_not_done,
            'gs_rate': total_gs_rate,
            'total_task_report': total_task_report,
            'task_report_done': total_task_report_done,
            'task_report_not_done': total_task_report_not_done,
            'total_rate': total_rate
        }
        total_line_columns = []
        for total_column in options['columns']:
            expr = total_column['expression_label']
            value = total_value.get(expr)
            total_line_columns.append(report._build_column_dict(value, total_column, options=options))
        lines.append({
            'id': f"~total_id~",
            'name': '',
            'columns': total_line_columns,
            'level': 1,
            'unfoldable': False,
            'unfolded': False,
        })
        return [(0, line) for line in lines]

    #ẩn cảnh báo bút toán
    def _customize_warnings(self, report, options, all_column_groups_expression_totals, warnings):
        warnings.clear()

class VmkpiMissingEvaluationReport(models.AbstractModel):
    _name = 'vmkpi.missing.evaluation.report'
    _inherit = 'account.report.custom.handler'
    _description = 'Báo cáo số chấm thiếu VM'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        options['unfold_all'] = (options.get('filter_unfold_all') or options.get('unfold_all'))
        options['hide_filter_rounding_unit'] = True
        options['column_headers'] = []
        options['columns'] = [
            {
                'name': 'Quầy',
                'expression_label': 'categ_name',
                'class': 'text',
                'type': 'string',
                'column_group_key': '1',
            },
            {
                'name': 'Quản lý',
                'expression_label': 'group_manager',
                'class': 'text',
                'type': 'string',
                'column_group_key': '1',
            },
            {
                'name': 'Cần chấm',
                'expression_label': 'task_report',
                'class': 'number',
                'figure_type': 'integer',
                'type': 'integer',
                'column_group_key': '1',
            },
            {
                'name': 'Đã chấm',
                'expression_label': 'task_report_done',
                'class': 'number',
                'figure_type': 'integer',
                'type': 'integer',
                'column_group_key': '1',
            },
            {
                'name': 'Chấm thiếu',
                'expression_label': 'task_report_not_done',
                'class': 'number',
                'figure_type': 'integer',
                'type': 'integer',
                'column_group_key': '1',
            },
            {
                'name': 'Tỷ lệ hoàn thành của quản lý',
                'expression_label': 'manager_rate',
                'class': 'number',
                'figure_type': 'percentage',
                'type': 'percentage',
                'column_group_key': '1',
            },
            {
                'name': 'Giám đốc',
                'expression_label': 'group_direction',
                'class': 'text',
                'type': 'string',
                'column_group_key': '1',
            },
            {
                'name': 'Cần chấm',
                'expression_label': 'direction_task_report',
                'class': 'number',
                'figure_type': 'integer',
                'type': 'integer',
                'column_group_key': '1',
            },
            {
                'name': 'Đã chấm',
                'expression_label': 'direction_task_report_done',
                'class': 'number',
                'figure_type': 'integer',
                'type': 'integer',
                'column_group_key': '1',
            },
            {
                'name': 'Chấm thiếu',
                'expression_label': 'direction_report_not_done',
                'class': 'number',
                'figure_type': 'integer',
                'type': 'integer',
                'column_group_key': '1',
            },
            {
                'name': 'Tỷ lệ hoàn thành của giám đốc',
                'expression_label': 'direction_rate',
                'class': 'number',
                'figure_type': 'percentage',
                'type': 'percentage',
                'column_group_key': '1',
            },
            {
                'name': 'Tỷ lệ hoàn thành',
                'expression_label': 'total_rate',
                'class': 'number',
                'figure_type': 'percentage',
                'type': 'percentage',
                'column_group_key': '1',
            }
        ]

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals=None, warnings=None):
        lines = []
        kpi_type_id = self.env.ref('ttb_kpi.ttb_kpi_type_vm').id
        date_from = options['date']['date_from']
        date_to = options['date']['date_to']
        self.env.cr.execute(f"""select task.user_branch_id as user_branch_id,
                       br.name as brand_name,
                       COALESCE(task.categ_id, -1) as categ_id,
                       pc.name as categ_name,
                       task.group as task_group,
                       COALESCE(task.reviewer_id, -1) as reviewer_id,
                       COALESCE(rrp.name, '') as reviewer_name,
                       COALESCE(rru.login, '') as reviewer_code,
                       COUNT(DISTINCT task.id) AS total_task_report,
                       COUNT(DISTINCT CASE WHEN state = 'done' THEN task.id ELSE NULL END) AS task_report_done,
                       COUNT(DISTINCT task.id) - COUNT(DISTINCT CASE WHEN state = 'done' THEN task.id ELSE NULL END) as task_report_not_done,
                       (COUNT(DISTINCT CASE WHEN state = 'done' THEN task.id ELSE NULL END) * 100)::float /COUNT(DISTINCT task.id) as total_rate
                from ttb_task_report as task
                left join res_users_ttb_task_report_rel user_rel on user_rel.ttb_task_report_id = task.id
                left join ttb_branch as br on br.id = task.user_branch_id
                left join product_category as pc on pc.id = task.categ_id
                left join res_users as rru on rru.id = task.reviewer_id
                left join res_partner as rrp on rrp.id = rru.partner_id
                where task.kpi_type_id = {kpi_type_id} and task.group <> 'cs' AND task.deadline BETWEEN DATE '{date_from}' AND DATE '{date_to}'
                group by task.user_branch_id, br.name, COALESCE(task.categ_id, -1), pc.name, task.group, COALESCE(task.reviewer_id, -1),  COALESCE(rrp.name, ''), COALESCE(rru.login, '')
                order by task.user_branch_id, COALESCE(task.categ_id, -1), task.group, COALESCE(task.reviewer_id, -1)
                """)
        result = self.env.cr.dictfetchall()
        total_manager_task_report = 0
        total_manager_task_report_done = 0
        total_manager_task_report_not_done = 0
        total_director_task_report = 0
        total_director_task_report_done = 0
        total_director_task_report_not_done = 0

        group_user_branch_id = list(set([item['user_branch_id'] for item in result]))
        for branch in group_user_branch_id:
            result_branch = [item for item in result if item['user_branch_id'] == branch]
            group_manager_result = [item for item in result_branch if item['task_group'] == 'manager']
            group_director_result = [item for item in result_branch if item['task_group'] in ['region_manager', 'branch_mannager']]

            branch_manager_task_report = sum(item['total_task_report'] for item in group_manager_result)
            branch_manager_task_report_done = sum(item['task_report_done'] for item in group_manager_result)
            branch_manager_task_report_not_done = sum(item['task_report_not_done'] for item in group_manager_result)
            manager_rate = (branch_manager_task_report_done/branch_manager_task_report) * 100 if branch_manager_task_report > 0 else 0.0

            branch_director_task_report = sum(item['total_task_report'] for item in group_director_result)
            branch_director_task_report_done = sum(item['task_report_done'] for item in group_director_result)
            branch_director_task_report_not_done = sum(item['task_report_not_done'] for item in group_director_result)
            direction_rate = (branch_director_task_report_done/branch_director_task_report) * 100 if branch_director_task_report > 0 else 0.0

            branch_rate = ((branch_manager_task_report_done + branch_director_task_report_done) /(branch_manager_task_report + branch_director_task_report)) * 100 if (branch_manager_task_report + branch_director_task_report) > 0 else 0.0

            total_manager_task_report += branch_manager_task_report
            total_manager_task_report_done += branch_manager_task_report_done
            total_manager_task_report_not_done += branch_manager_task_report_not_done
            total_director_task_report += branch_director_task_report
            total_director_task_report_done += branch_director_task_report_done
            total_director_task_report_not_done += branch_director_task_report_not_done

            branch_value = {
                            'group_manager': '', 'task_report': branch_manager_task_report, 'task_report_done': branch_manager_task_report_done, 'task_report_not_done': branch_manager_task_report_not_done, 'manager_rate':manager_rate,
                            'group_direction': '', 'direction_task_report': branch_director_task_report, 'direction_task_report_done': branch_director_task_report_done, 'direction_report_not_done': branch_director_task_report_not_done, 'direction_rate': direction_rate,
                            'total_rate': branch_rate}
            total_line_columns = []
            for column in options['columns']:
                expr = column['expression_label']
                value = branch_value.get(expr)
                total_line_columns.append(report._build_column_dict(value, column, options=options))
            lines.append({
                'id': f"~ttb.branch~{branch}",
                'name': result_branch[0]['brand_name'],
                'columns': total_line_columns,
                'level': 1,
                'unfoldable': True,
                'unfolded': options.get('unfold_all'),
            })
            group_categ_id = list(set([item['categ_id'] for item in result_branch]))
            for categ in group_categ_id:
                result_categ = [item for item in result_branch if item['categ_id'] == categ]
                group_manager_result = [item for item in result_categ if item['task_group'] == 'manager']
                group_director_result = [item for item in result_categ if item['task_group'] in ['region_manager', 'branch_mannager']]

                list_group_manager = list(set([f"{item['reviewer_code']} {item['reviewer_name']}" for item in group_manager_result if item['reviewer_code']]))
                group_manager = '\n'.join(str(s) for s in list_group_manager)
                categ_manager_task_report = sum(item['total_task_report'] for item in group_manager_result)
                categ_manager_task_report_done = sum(item['task_report_done'] for item in group_manager_result)
                categ_manager_task_report_not_done = sum(item['task_report_not_done'] for item in group_manager_result)
                manager_rate = (categ_manager_task_report_done / categ_manager_task_report) * 100 if categ_manager_task_report > 0 else 0.0

                list_group_direction = list(set([f"{item['reviewer_code']} {item['reviewer_name']}" for item in group_director_result if item['reviewer_code']]))
                group_direction = '\n'.join(str(s) for s in list_group_direction)
                categ_director_task_report = sum(item['total_task_report'] for item in group_director_result)
                categ_director_task_report_done = sum(item['task_report_done'] for item in group_director_result)
                categ_director_task_report_not_done = sum(item['task_report_not_done'] for item in group_director_result)
                direction_rate = (categ_director_task_report_done/categ_director_task_report) * 100 if categ_director_task_report > 0 else 0.0

                categ_rate = ((categ_manager_task_report_done + categ_director_task_report_done) / (categ_manager_task_report + categ_director_task_report)) * 100 if (categ_manager_task_report + categ_director_task_report) > 0 else 0.0

                categ_value = {'categ_name': result_categ[0]['categ_name'],
                                'group_manager': group_manager, 'task_report': categ_manager_task_report,
                                'task_report_done': categ_manager_task_report_done,
                                'task_report_not_done': categ_manager_task_report_not_done,
                                'manager_rate': manager_rate,
                                'group_direction': group_direction, 'direction_task_report': categ_director_task_report,
                                'direction_task_report_done': categ_director_task_report_done,
                                'direction_report_not_done': categ_director_task_report_not_done,
                                'direction_rate': direction_rate,
                                'total_rate': categ_rate}
                total_line_columns = []
                for column in options['columns']:
                    expr = column['expression_label']
                    value = categ_value.get(expr)
                    if expr == 'brand_name':
                        value = ''
                    total_line_columns.append(report._build_column_dict(value, column, options=options))
                lines.append({
                    'id': f"~ttb.branch~{branch}|~product.category~{categ}",
                    'name': '',
                    'columns': total_line_columns,
                    'level': 2,
                    'unfoldable': False,
                    'unfolded': False,
                    'parent_id': f"~ttb.branch~{branch}",
                })

        total_manager_rate = (total_manager_task_report_done  / total_manager_task_report ) * 100 if total_manager_task_report > 0 else 0
        total_direction_rate = (total_director_task_report_done/ total_director_task_report) * 100 if total_director_task_report > 0 else 0
        branch_rate = ((total_manager_task_report_done + total_director_task_report_done) / (total_manager_task_report + total_director_task_report)) * 100 if (total_manager_task_report + total_director_task_report) > 0 else 0
        total_value = {'categ_name': '',
                       'group_manager': 'Tổng', 'task_report': total_manager_task_report,
                       'task_report_done': total_manager_task_report_done,
                       'task_report_not_done': total_manager_task_report_not_done,
                       'manager_rate': total_manager_rate,
                       'group_direction': '', 'direction_task_report': total_director_task_report,
                       'direction_task_report_done': total_director_task_report_done,
                       'direction_report_not_done': total_director_task_report_not_done,
                       'direction_rate': total_direction_rate,
                       'total_rate': branch_rate}
        total_line_columns = []
        for total_column in options['columns']:
            expr = total_column['expression_label']
            value = total_value.get(expr)
            total_line_columns.append(report._build_column_dict(value, total_column, options=options))
        lines.append({
            'id': f"~total_id~",
            'name': '',
            'columns': total_line_columns,
            'level': 1,
            'unfoldable': False,
            'unfolded': False,
        })
        return [(0, line) for line in lines]

    def _customize_warnings(self, report, options, all_column_groups_expression_totals, warnings):
        warnings.clear()

class VskpiMissingEvaluationReport(models.AbstractModel):
    _name = 'vskpi.missing.evaluation.report'
    _inherit = 'account.report.custom.handler'
    _description = 'Báo cáo số chấm thiếu VS'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        options['unfold_all'] = (options.get('filter_unfold_all') or options.get('unfold_all'))
        options['hide_filter_rounding_unit'] = True
        options['column_headers'] = []
        options['columns'] = [
            {
                'name': 'Khu vực',
                'expression_label': 'categ_name',
                'class': 'text',
                'type': 'string',
                'column_group_key': '1',
            },
            {
                'name': 'Quản lý',
                'expression_label': 'group_manager',
                'class': 'text',
                'type': 'string',
                'column_group_key': '1',
            },
            {
                'name': 'Cần chấm',
                'expression_label': 'task_report',
                'class': 'number',
                'figure_type': 'integer',
                'type': 'integer',
                'column_group_key': '1',
            },
            {
                'name': 'Đã chấm',
                'expression_label': 'task_report_done',
                'class': 'number',
                'figure_type': 'integer',
                'type': 'integer',
                'column_group_key': '1',
            },
            {
                'name': 'Chấm thiếu',
                'expression_label': 'task_report_not_done',
                'class': 'number',
                'figure_type': 'integer',
                'type': 'integer',
                'column_group_key': '1',
            },
            {
                'name': 'Tỷ lệ hoàn thành của quản lý',
                'expression_label': 'manager_rate',
                'class': 'number',
                'figure_type': 'percentage',
                'type': 'percentage',
                'column_group_key': '1',
            },
            {
                'name': 'Giám đốc',
                'expression_label': 'group_direction',
                'class': 'text',
                'type': 'string',
                'column_group_key': '1',
            },
            {
                'name': 'Cần chấm',
                'expression_label': 'direction_task_report',
                'class': 'number',
                'figure_type': 'integer',
                'type': 'integer',
                'column_group_key': '1',
            },
            {
                'name': 'Đã chấm',
                'expression_label': 'direction_task_report_done',
                'class': 'number',
                'figure_type': 'integer',
                'type': 'integer',
                'column_group_key': '1',
            },
            {
                'name': 'Chấm thiếu',
                'expression_label': 'direction_report_not_done',
                'class': 'number',
                'figure_type': 'integer',
                'type': 'integer',
                'column_group_key': '1',
            },
            {
                'name': 'Tỷ lệ hoàn thành của giám đốc',
                'expression_label': 'direction_rate',
                'class': 'number',
                'figure_type': 'percentage',
                'type': 'percentage',
                'column_group_key': '1',
            },
            {
                'name': 'Tỷ lệ hoàn thành',
                'expression_label': 'total_rate',
                'class': 'number',
                'figure_type': 'percentage',
                'type': 'percentage',
                'column_group_key': '1',
            }
        ]

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals=None, warnings=None):
        lines = []
        kpi_type_id = self.env.ref('ttb_kpi.ttb_kpi_type_vs').id
        date_from = options['date']['date_from']
        date_to = options['date']['date_to']
        self.env.cr.execute(f"""select task.user_branch_id as user_branch_id,
                       br.name as brand_name,
                       COALESCE(task.area_id, -1) as categ_id,
                       pc.name as categ_name,
                       task.group as task_group,
                       COALESCE(task.reviewer_id, -1) as reviewer_id,
                       COALESCE(rrp.name, '') as reviewer_name,
                       COALESCE(rru.login, '') as reviewer_code,
                       COUNT(DISTINCT task.id) AS total_task_report,
                       COUNT(DISTINCT CASE WHEN state = 'done' THEN task.id ELSE NULL END) AS task_report_done,
                       COUNT(DISTINCT task.id) - COUNT(DISTINCT CASE WHEN state = 'done' THEN task.id ELSE NULL END) as task_report_not_done,
                       (COUNT(DISTINCT CASE WHEN state = 'done' THEN task.id ELSE NULL END) * 100)::float /COUNT(DISTINCT task.id) as total_rate
                from ttb_task_report as task
                left join res_users_ttb_task_report_rel user_rel on user_rel.ttb_task_report_id = task.id
                left join ttb_branch as br on br.id = task.user_branch_id
                left join ttb_area as pc on pc.id = task.area_id
                left join res_users as rru on rru.id = task.reviewer_id
                left join res_partner as rrp on rrp.id = rru.partner_id
                where task.kpi_type_id = {kpi_type_id} and task.group <> 'cs' AND task.deadline BETWEEN DATE '{date_from}' AND DATE '{date_to}'
                group by task.user_branch_id, br.name, COALESCE(task.area_id, -1), pc.name, task.group, COALESCE(task.reviewer_id, -1),  COALESCE(rrp.name, ''), COALESCE(rru.login, '')
                order by task.user_branch_id, COALESCE(task.area_id, -1), task.group, COALESCE(task.reviewer_id, -1)
                """)
        result = self.env.cr.dictfetchall()
        total_manager_task_report = 0
        total_manager_task_report_done = 0
        total_manager_task_report_not_done = 0
        total_director_task_report = 0
        total_director_task_report_done = 0
        total_director_task_report_not_done = 0

        group_user_branch_id = list(set([item['user_branch_id'] for item in result]))
        for branch in group_user_branch_id:
            result_branch = [item for item in result if item['user_branch_id'] == branch]
            group_manager_result = [item for item in result_branch if item['task_group'] == 'manager']
            group_director_result = [item for item in result_branch if item['task_group'] in ['region_manager', 'branch_mannager']]

            branch_manager_task_report = sum(item['total_task_report'] for item in group_manager_result)
            branch_manager_task_report_done = sum(item['task_report_done'] for item in group_manager_result)
            branch_manager_task_report_not_done = sum(item['task_report_not_done'] for item in group_manager_result)
            manager_rate = (branch_manager_task_report_done/branch_manager_task_report) * 100 if branch_manager_task_report > 0 else 0.0

            branch_director_task_report = sum(item['total_task_report'] for item in group_director_result)
            branch_director_task_report_done = sum(item['task_report_done'] for item in group_director_result)
            branch_director_task_report_not_done = sum(item['task_report_not_done'] for item in group_director_result)
            direction_rate = (branch_director_task_report_done/branch_director_task_report) * 100 if branch_director_task_report > 0 else 0.0

            branch_rate = ((branch_manager_task_report_done + branch_director_task_report_done) /(branch_manager_task_report + branch_director_task_report)) * 100 if (branch_manager_task_report + branch_director_task_report) > 0 else 0.0

            total_manager_task_report += branch_manager_task_report
            total_manager_task_report_done += branch_manager_task_report_done
            total_manager_task_report_not_done += branch_manager_task_report_not_done
            total_director_task_report += branch_director_task_report
            total_director_task_report_done += branch_director_task_report_done
            total_director_task_report_not_done += branch_director_task_report_not_done

            branch_value = {
                            'group_manager': '', 'task_report': branch_manager_task_report, 'task_report_done': branch_manager_task_report_done, 'task_report_not_done': branch_manager_task_report_not_done,'manager_rate':manager_rate,
                            'group_direction': '', 'direction_task_report': branch_director_task_report, 'direction_task_report_done': branch_director_task_report_done, 'direction_report_not_done': branch_director_task_report_not_done,'direction_rate': direction_rate,
                            'total_rate': branch_rate}
            total_line_columns = []
            for column in options['columns']:
                expr = column['expression_label']
                value = branch_value.get(expr)
                total_line_columns.append(report._build_column_dict(value, column, options=options))
            lines.append({
                'id': f"~ttb.branch~{branch}",
                'name': result_branch[0]['brand_name'],
                'columns': total_line_columns,
                'level': 1,
                'unfoldable': True,
                'unfolded': options.get('unfold_all'),
            })
            group_categ_id = list(set([item['categ_id'] for item in result_branch]))
            for categ in group_categ_id:
                result_categ = [item for item in result_branch if item['categ_id'] == categ]
                group_manager_result = [item for item in result_categ if item['task_group'] == 'manager']
                group_director_result = [item for item in result_categ if item['task_group'] in ['region_manager', 'branch_mannager']]

                list_group_manager = list(set([f"{item['reviewer_code']} {item['reviewer_name']}" for item in group_manager_result if item['reviewer_code']]))
                group_manager = '\n'.join(str(s) for s in list_group_manager)
                categ_manager_task_report = sum(item['total_task_report'] for item in group_manager_result)
                categ_manager_task_report_done = sum(item['task_report_done'] for item in group_manager_result)
                categ_manager_task_report_not_done = sum(item['task_report_not_done'] for item in group_manager_result)
                manager_rate = (categ_manager_task_report_done / categ_manager_task_report) * 100 if categ_manager_task_report > 0 else 0.0
                list_group_direction = list(set([f"{item['reviewer_code']} {item['reviewer_name']}" for item in group_director_result if item['reviewer_code']]))
                group_direction = '\n'.join(str(s) for s in list_group_direction)
                categ_director_task_report = sum(item['total_task_report'] for item in group_director_result)
                categ_director_task_report_done = sum(item['task_report_done'] for item in group_director_result)
                categ_director_task_report_not_done = sum(item['task_report_not_done'] for item in group_director_result)
                direction_rate = (categ_director_task_report_done/categ_director_task_report) * 100 if categ_director_task_report > 0 else 0.0
                categ_rate = ((categ_manager_task_report_done + categ_director_task_report_done) / (categ_manager_task_report + categ_director_task_report)) * 100 if (categ_manager_task_report + categ_director_task_report) > 0 else 0.0

                categ_value = {'categ_name': result_categ[0]['categ_name'],
                                'group_manager': group_manager, 'task_report': categ_manager_task_report,
                                'task_report_done': categ_manager_task_report_done,
                                'task_report_not_done': categ_manager_task_report_not_done,
                                'manager_rate': manager_rate,
                                'group_direction': group_direction, 'direction_task_report': categ_director_task_report,
                                'direction_task_report_done': categ_director_task_report_done,
                                'direction_report_not_done': categ_director_task_report_not_done,
                                'direction_rate': direction_rate,
                                'total_rate': categ_rate}
                total_line_columns = []
                for column in options['columns']:
                    expr = column['expression_label']
                    value = categ_value.get(expr)
                    if expr == 'brand_name':
                        value = ''
                    total_line_columns.append(report._build_column_dict(value, column, options=options))
                lines.append({
                    'id': f"~ttb.branch~{branch}|~product.category~{categ}",
                    'name': '',
                    'columns': total_line_columns,
                    'level': 2,
                    'unfoldable': False,
                    'unfolded': False,
                    'parent_id': f"~ttb.branch~{branch}",
                })

        branch_rate = ((total_manager_task_report_done + total_director_task_report_done)/ (total_manager_task_report + total_director_task_report)) * 100 if (total_manager_task_report + total_director_task_report) > 0 else 0
        total_manager_rate = (total_manager_task_report_done  / total_manager_task_report ) * 100 if total_manager_task_report > 0 else 0
        total_direction_rate = (total_director_task_report_done/ total_director_task_report) * 100 if total_director_task_report > 0 else 0
        total_value = {'categ_name': '',
                       'group_manager': 'Tổng', 'task_report': total_manager_task_report,
                       'task_report_done': total_manager_task_report_done,
                       'task_report_not_done': total_manager_task_report_not_done,
                       'manager_rate': total_manager_rate,
                       'group_direction': '', 'direction_task_report': total_director_task_report,
                       'direction_task_report_done': total_director_task_report_done,
                       'direction_report_not_done': total_director_task_report_not_done,
                       'direction_rate': total_direction_rate,
                       'total_rate': branch_rate}
        total_line_columns = []
        for total_column in options['columns']:
            expr = total_column['expression_label']
            value = total_value.get(expr)
            total_line_columns.append(report._build_column_dict(value, total_column, options=options))
        lines.append({
            'id': f"~total_id~",
            'name': '',
            'columns': total_line_columns,
            'level': 1,
            'unfoldable': False,
            'unfolded': False,
        })
        return [(0, line) for line in lines]

    def _customize_warnings(self, report, options, all_column_groups_expression_totals, warnings):
        warnings.clear()
