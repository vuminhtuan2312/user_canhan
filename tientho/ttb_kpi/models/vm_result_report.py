import datetime
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class BaoCaoKetQuaChamVM(models.AbstractModel):
    _name = 'kpi.result.vm.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Báo cáo kết quả chấm VM'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        options['unfold_all'] = (options.get('filter_unfold_all') or options.get('unfold_all'))
        options['hide_filter_rounding_unit'] = True
        options['header_parents'] = True
        options['column_headers'] = []
        options['columns'] = [
            {
                'name': 'Đã chấm',
                'expression_label': 'total_checked_manage',
                'class': 'number',
                'type': 'number',
                'figure_type': 'integer',
                'column_group_key': '1',
            },
            {
                'name': 'Chưa chấm',
                'expression_label': 'total_unchecked_manage',
                'class': 'number',
                'type': 'number',
                'figure_type': 'integer',
                'column_group_key': '1',
            },
            {
                'name': 'Số lượng trễ hạn',
                'expression_label': 'total_overdue_manage',
                'class': 'number',
                'type': 'number',
                'figure_type': 'integer',
                'column_group_key': '1',
            },
            {
                'name': 'Tỷ lệ hoàn thành',
                'expression_label': 'done_percentage_manage',
                'class': 'number',
                'type': 'number',
                'figure_type': 'percentage',
                'column_group_key': '1',
            },
            {
                'name': 'Điểm trung bình',
                'expression_label': 'avg_score_manage',
                'class': 'number',
                'type': 'number',
                'figure_type': 'percentage',
                'column_group_key': '1',
            },
            {
                'name': 'Đã chấm',
                'expression_label': 'total_checked_branch',
                'class': 'number',
                'type': 'number',
                'figure_type': 'integer',
                'column_group_key': '1',
            },
            {
                'name': 'Chưa chấm',
                'expression_label': 'total_unchecked_branch',
                'class': 'number',
                'type': 'number',
                'figure_type': 'integer',
                'column_group_key': '1',
            },
            {
                'name': 'Số lượng trễ hạn',
                'expression_label': 'total_overdue_branch',
                'class': 'number',
                'type': 'number',
                'figure_type': 'integer',
                'column_group_key': '1',
            },
            {
                'name': 'Tỷ lệ hoàn thành',
                'expression_label': 'done_percentage_branch',
                'class': 'number',
                'type': 'number',
                'figure_type': 'percentage',
                'column_group_key': '1',
            },
            {
                'name': 'Điểm trung bình',
                'expression_label': 'avg_score_branch',
                'class': 'number',
                'type': 'number',
                'figure_type': 'percentage',
                'column_group_key': '1',
            },
            {
                'name': 'Đã chấm',
                'expression_label': 'total_checked_region_direct',
                'class': 'number',
                'type': 'number',
                'figure_type': 'integer',
                'column_group_key': '1',
            },
            {
                'name': 'Chưa chấm',
                'expression_label': 'total_unchecked_region_direct',
                'class': 'number',
                'type': 'number',
                'figure_type': 'integer',
                'column_group_key': '1',
            },
            {
                'name': 'Số lượng trễ hạn',
                'expression_label': 'total_overdue_region_direct',
                'class': 'number',
                'type': 'number',
                'figure_type': 'integer',
                'column_group_key': '1',
            },
            {
                'name': 'Tỷ lệ hoàn thành',
                'expression_label': 'done_percentage_direct',
                'class': 'number',
                'type': 'number',
                'figure_type': 'percentage',
                'column_group_key': '1',
            },
            {
                'name': 'Điểm trung bình',
                'expression_label': 'avg_score_region_direct',
                'class': 'number',
                'type': 'number',
                'figure_type': 'percentage',
                'column_group_key': '1',
            },
            {
                'name': 'Đã chấm',
                'expression_label': 'total_checked_region_cross',
                'class': 'number',
                'type': 'number',
                'figure_type': 'integer',
                'column_group_key': '1',
            },
            {
                'name': 'Chưa chấm',
                'expression_label': 'total_unchecked_region_cross',
                'class': 'number',
                'type': 'number',
                'figure_type': 'integer',
                'column_group_key': '1',
            },
            {
                'name': 'Số lượng trễ hạn',
                'expression_label': 'total_overdue_region_cross',
                'class': 'number',
                'type': 'number',
                'figure_type': 'integer',
                'column_group_key': '1',
            },
            {
                'name': 'Tỷ lệ hoàn thành',
                'expression_label': 'done_percentage_region_cross',
                'class': 'number',
                'type': 'number',
                'figure_type': 'percentage',
                'column_group_key': '1',
            },
            {
                'name': 'Điểm trung bình',
                'expression_label': 'avg_score_region_cross',
                'class': 'number',
                'type': 'number',
                'figure_type': 'percentage',
                'column_group_key': '1',
            },
            {
                'name': 'Đã chấm',
                'expression_label': 'total_checked',
                'class': 'number',
                'type': 'number',
                'figure_type': 'integer',
                'column_group_key': '1',
            },
            {
                'name': 'Chưa chấm',
                'expression_label': 'total_unchecked',
                'class': 'number',
                'type': 'number',
                'figure_type': 'integer',
                'column_group_key': '1',
            },
            {
                'name': 'Điểm trung bình',
                'expression_label': 'avg_score',
                'class': 'number',
                'type': 'number',
                'figure_type': 'percentage',
                'column_group_key': '1',
            },
            {
                'name': 'Điểm TB cơ sở',
                'expression_label': 'avg_score_branch_self',
                'class': 'number',
                'type': 'number',
                'figure_type': 'percentage',
                'column_group_key': '1',
            },
        ]

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals=None, warnings=None):
        kpi_type_id = self.env.ref('ttb_kpi.ttb_kpi_type_vm').id
        date_from = options['date']['date_from']
        date_to = options['date']['date_to']
        query = f"""
            SELECT
                b.name as brand_name,
                b.id as brand_id,
                COALESCE(c.name,'') as counter_name,
                COALESCE(c.id,'-1') as counter_id,
                -- Quản lý
                COUNT(DISTINCT t.id) FILTER (WHERE t."group" = 'manager') AS total_need_check_manage,
                COUNT(DISTINCT t.id) FILTER (WHERE t."group" = 'manager' AND t.state = 'done') AS total_checked_manage,
                COUNT(DISTINCT t.id) FILTER (WHERE t."group" = 'manager' AND t.state = 'overdue') AS total_overdue_manage,
                COALESCE((COUNT(DISTINCT t.id) FILTER (WHERE t."group" = 'manager' AND t.state = 'done') * 1.0
                ) / NULLIF(COUNT(DISTINCT t.id) FILTER (WHERE t."group" = 'manager'), 0),0) * 100 AS done_percentage_manage,
                COUNT(DISTINCT t.id) FILTER (WHERE t."group" = 'manager') - COUNT(DISTINCT t.id) FILTER (WHERE t."group" = 'manager' AND t.state = 'done') AS total_unchecked_manage,
                COALESCE(AVG(k.average_rate) FILTER (WHERE t."group" = 'manager' AND t.state = 'done'), 0) * 100 AS avg_score_manage,

                -- Giám đốc chi nhánh (branch_mannager)
                COUNT(DISTINCT t.id) FILTER (WHERE t."group" = 'branch_mannager') AS total_need_check_branch,
                COUNT(DISTINCT t.id) FILTER (WHERE t."group" = 'branch_mannager' AND t.state = 'done') AS total_checked_branch,
                COUNT(DISTINCT t.id) FILTER (WHERE t."group" = 'branch_mannager' AND t.state = 'overdue') AS total_overdue_branch,
                COALESCE((COUNT(DISTINCT t.id) FILTER (WHERE t."group" = 'branch_mannager' AND t.state = 'done') * 1.0
                ) / NULLIF(COUNT(DISTINCT t.id) FILTER (WHERE t."group" = 'branch_mannager'), 0),0) * 100 AS done_percentage_branch,
                COUNT(DISTINCT t.id) FILTER (WHERE t."group" = 'branch_mannager') - COUNT(DISTINCT t.id) FILTER (
                    WHERE t."group" = 'branch_mannager' AND t.state = 'done') AS total_unchecked_branch,
                COALESCE(AVG(k.average_rate) FILTER (WHERE t."group" = 'branch_mannager' AND t.state = 'done'), 0) * 100 AS avg_score_branch,

                -- Giám đốc vùng trực tiếp (region_manager và branch_id thuộc evaluator)
                COUNT(DISTINCT t.id) FILTER (WHERE t."group" = 'region_manager') AS total_need_check_region_direct,
                COUNT(DISTINCT t.id) FILTER (WHERE t."group" = 'region_manager' AND t.state = 'done') AS total_checked_region_direct,
                COUNT(DISTINCT t.id) FILTER (WHERE t."group" = 'region_manager' AND t.state = 'overdue') AS total_overdue_region_direct,
                COALESCE((COUNT(DISTINCT t.id) FILTER (WHERE t."group" = 'region_manager' AND t.state = 'done') * 1.0
                ) / NULLIF(COUNT(DISTINCT t.id) FILTER (WHERE t."group" = 'region_manager'), 0),0) * 100 AS done_percentage_direct,
                COUNT(DISTINCT t.id) FILTER (WHERE t."group" = 'region_manager') - COUNT(DISTINCT t.id) FILTER (
                    WHERE t."group" = 'region_manager' AND t.state = 'done') AS total_unchecked_region_direct,
                COALESCE(AVG(k.average_rate) FILTER (WHERE t."group" = 'region_manager' AND t.state = 'done'), 0) * 100 AS avg_score_region_direct,

                -- Giám đốc vùng chấm chéo (region_manager và branch_id )
                COUNT(DISTINCT t.id) FILTER (
                    WHERE t."group" = 'cross_dot_area_manager'
                ) AS total_need_check_region_cross,
                COUNT(DISTINCT t.id) FILTER (
                    WHERE t."group" = 'cross_dot_area_manager' AND t.state = 'done'
                ) AS total_checked_region_cross,
                COUNT(DISTINCT t.id) FILTER (WHERE t."group" = 'cross_dot_area_manager' AND t.state = 'overdue') AS total_overdue_region_cross,
                COALESCE((COUNT(DISTINCT t.id) FILTER (WHERE t."group" = 'cross_dot_area_manager' AND t.state = 'done') * 1.0
                ) / NULLIF(COUNT(DISTINCT t.id) FILTER (WHERE t."group" = 'cross_dot_area_manager'), 0),0) * 100 AS done_percentage_region_cross,
                COUNT(DISTINCT t.id) FILTER (
                    WHERE t."group" = 'cross_dot_area_manager'
                ) - COUNT(DISTINCT t.id) FILTER (
                    WHERE t."group" = 'cross_dot_area_manager' AND t.state = 'done') AS total_unchecked_region_cross,
                COALESCE(AVG(k.average_rate) FILTER (
                    WHERE t."group" = 'cross_dot_area_manager' AND t.state = 'done'
                ), 0) * 100 AS avg_score_region_cross

            FROM ttb_task_report t
            LEFT JOIN ttb_task_report_line l ON l.report_id = t.id
            LEFT JOIN res_users r ON t.user_id = r.id
            LEFT JOIN ttb_branch b ON t.user_branch_id = b.id
            LEFT JOIN product_category c ON t.categ_id = c.id
            LEFT JOIN ttb_task_report_kpi k ON t.id = k.report_id
            WHERE t.kpi_type_id = {kpi_type_id} AND t.deadline BETWEEN DATE '{date_from}' AND DATE '{date_to}'
            GROUP BY b.name, COALESCE(c.name,''), b.id, COALESCE(c.id,'-1')
            ORDER BY b.id, COALESCE(c.id,'-1')
        """
        self.env.cr.execute(query)
        results = self.env.cr.dictfetchall()
        lines = []

        count_done_percentage_manage = 0
        count_done_percentage_branch = 0
        count_done_percentage_region_direct = 0
        count_done_percentage_region_cross = 0
        count_avg_score_manage = 0
        count_avg_score_branch = 0
        count_avg_score_region_direct = 0
        count_avg_score_region_cross = 0
        count_t_avg_score = 0
        t_total_need_check_manage = 0
        t_total_checked_manage = 0
        t_total_unchecked_manage = 0
        t_total_need_check_branch = 0
        t_total_checked_branch = 0  # This was missing!
        t_total_unchecked_branch = 0
        t_total_need_check_region_direct = 0
        t_total_checked_region_direct = 0
        t_total_unchecked_region_direct = 0
        t_total_need_check_region_cross = 0
        t_total_checked_region_cross = 0
        t_total_unchecked_region_cross = 0
        t_avg_score_manage = 0
        t_avg_score_branch = 0
        t_avg_score_region_direct = 0
        t_avg_score_region_cross = 0
        t_total_overdue_manage = 0
        t_total_overdue_branch = 0
        t_total_overdue_region_direct = 0
        t_total_overdue_region_cross = 0
        t_done_percentage_manage = 0
        t_done_percentage_branch = 0
        t_done_percentage_region_direct = 0
        t_done_percentage_region_cross = 0
        t_avg_score = 0

        group_branch_id = list(set([item['brand_id'] for item in results]))
        for branch in group_branch_id:
            result_branch = [item for item in results if item['brand_id'] == branch]
            # Line cơ sở
            total_need_check_manage = sum(item['total_need_check_manage'] for item in result_branch)
            total_checked_manage = sum(item['total_checked_manage'] for item in result_branch)
            total_unchecked_manage = sum(item['total_unchecked_manage'] for item in result_branch)
            total_need_check_branch = sum(item['total_need_check_branch'] for item in result_branch)
            total_checked_branch = sum(item['total_checked_branch'] for item in result_branch)
            total_unchecked_branch = sum(item['total_unchecked_branch'] for item in result_branch)
            total_need_check_region_direct = sum(item['total_need_check_region_direct'] for item in result_branch)
            total_checked_region_direct = sum(item['total_checked_region_direct'] for item in result_branch)
            total_unchecked_region_direct = sum(item['total_unchecked_region_direct'] for item in result_branch)
            total_need_check_region_cross = sum(item['total_need_check_region_cross'] for item in result_branch)
            total_checked_region_cross = sum(item['total_checked_region_cross'] for item in result_branch)
            total_unchecked_region_cross = sum(item['total_unchecked_region_cross'] for item in result_branch)
            total_overdue_manage = sum(item['total_overdue_manage'] for item in result_branch)
            total_overdue_branch = sum(item['total_overdue_branch'] for item in result_branch)
            total_overdue_region_direct = sum(item['total_overdue_region_direct'] for item in result_branch)
            total_overdue_region_cross = sum(item['total_overdue_region_cross'] for item in result_branch)

            def avg_by_area(data, score_key):
                area_scores = {}
                for item in data:
                    area_id = item.get('counter_id')
                    value = item.get(score_key, 0)
                    if area_id and value and value > 0:
                        if area_id not in area_scores:
                            area_scores[area_id] = []
                        area_scores[area_id].append(value)
                area_avg = [sum(scores) / len(scores) for scores in area_scores.values() if scores]
                return sum(area_avg) / len(area_avg) if area_avg else 0

            # Tính trung bình phần trăm hoàn thành (theo từng khu vực)
            done_percentage_manage = (
                total_checked_manage * 100 / (total_checked_manage + total_unchecked_manage)
                if (total_checked_manage + total_unchecked_manage) else 0
            )
            done_percentage_branch = (
                total_checked_branch * 100 / (total_checked_branch + total_unchecked_branch)
                if (total_checked_branch + total_unchecked_branch) else 0
            )
            done_percentage_region_direct = (
                total_checked_region_direct * 100 / (total_checked_region_direct + total_unchecked_region_direct)
                if (total_checked_region_direct + total_unchecked_region_direct) else 0
            )
            done_percentage_region_cross = (
                total_checked_region_cross * 100 / (total_checked_region_cross + total_unchecked_region_cross)
                if (total_checked_region_cross + total_unchecked_region_cross) else 0
            )
            # Tính điểm trung bình (theo từng khu vực)
            avg_score_manage = avg_by_area(result_branch, 'avg_score_manage')
            avg_score_branch = avg_by_area(result_branch, 'avg_score_branch')
            avg_score_region_direct = avg_by_area(result_branch, 'avg_score_region_direct')
            avg_score_region_cross = avg_by_area(result_branch, 'avg_score_region_cross')
            total_need_check = (total_need_check_region_direct + total_need_check_region_cross)
            total_checked = (total_checked_region_direct + total_checked_region_cross)
            total_unchecked = (total_unchecked_region_direct + total_unchecked_region_cross)
            avg_score = (avg_score_region_direct + avg_score_region_cross) / 2
            avg_score_branch_self = (avg_score_manage + avg_score_branch) / 2

            # Cộng dồn tổng các trường
            t_total_need_check_manage += total_need_check_manage
            t_total_checked_manage += total_checked_manage
            t_total_unchecked_manage += total_unchecked_manage
            t_total_need_check_branch += total_need_check_branch
            t_total_checked_branch += total_checked_branch
            t_total_unchecked_branch += total_unchecked_branch
            t_total_need_check_region_direct += total_need_check_region_direct
            t_total_checked_region_direct += total_checked_region_direct
            t_total_unchecked_region_direct += total_unchecked_region_direct
            t_total_need_check_region_cross += total_need_check_region_cross
            t_total_checked_region_cross += total_checked_region_cross
            t_total_unchecked_region_cross += total_unchecked_region_cross
            t_total_overdue_manage += total_overdue_manage
            t_total_overdue_branch += total_overdue_branch
            t_total_overdue_region_direct += total_overdue_region_direct
            t_total_overdue_region_cross += total_overdue_region_cross

            # Cộng dồn điểm trung bình
            if avg_score_manage > 0:
                t_avg_score_manage += avg_score_manage
                count_avg_score_manage += 1
            if avg_score_branch > 0:
                t_avg_score_branch += avg_score_branch
                count_avg_score_branch += 1
            if avg_score_region_direct > 0:
                t_avg_score_region_direct += avg_score_region_direct
                count_avg_score_region_direct += 1
            if avg_score_region_cross > 0:
                t_avg_score_region_cross += avg_score_region_cross
                count_avg_score_region_cross += 1
            if done_percentage_manage > 0:
                t_done_percentage_manage += done_percentage_manage
                count_done_percentage_manage += 1
            if done_percentage_branch > 0:
                t_done_percentage_branch += done_percentage_branch
                count_done_percentage_branch += 1
            if done_percentage_region_direct > 0:
                t_done_percentage_region_direct += done_percentage_region_direct
                count_done_percentage_region_direct += 1
            if done_percentage_region_cross > 0:
                t_done_percentage_region_cross += done_percentage_region_cross
                count_done_percentage_region_cross += 1
            if avg_score > 0:
                t_avg_score += avg_score
                count_t_avg_score += 1

            result_value = {
                    'total_checked_manage': total_checked_manage,
                    'total_unchecked_manage': total_unchecked_manage, 'avg_score_manage': avg_score_manage,
                    'total_checked_branch': total_checked_branch,
                    'total_unchecked_branch': total_unchecked_branch, 'avg_score_branch': avg_score_branch,
                    'total_checked_region_direct': total_checked_region_direct,
                    'total_unchecked_region_direct': total_unchecked_region_direct,
                    'avg_score_region_direct': avg_score_region_direct,
                    'total_checked_region_cross': total_checked_region_cross,
                    'total_unchecked_region_cross': total_unchecked_region_cross,
                    'avg_score_region_cross': avg_score_region_cross,
                    'total_checked': total_checked,
                    'total_unchecked': total_unchecked, 'avg_score_branch_self': avg_score_branch_self,
                    'avg_score': avg_score,
                    'total_overdue_manage': total_overdue_manage, 'total_overdue_branch': total_overdue_branch,
                    'total_overdue_region_cross': total_overdue_region_cross,
                    'total_overdue_region_direct': total_overdue_region_direct,
                    'done_percentage_manage': done_percentage_manage, 'done_percentage_branch': done_percentage_branch,
                    'done_percentage_direct': done_percentage_region_direct,
                    'done_percentage_region_cross': done_percentage_region_cross
            }
            total_line_columns = []
            for column in options['columns']:
                expr = column['expression_label']
                value = result_value.get(expr)
                total_line_columns.append(report._build_column_dict(value, column, options=options))
            lines.append({
                'id': f"~ttb.branch~{branch}",
                'name': result_branch[0]['brand_name'],
                'columns': total_line_columns,
                'level': 1,
                'unfoldable': True,
                'unfolded': options.get('unfold_all'),
            })
            for item in result_branch:
                line_columns = []
                for column in options['columns']:
                    expr = column['expression_label']
                    if expr == 'total_checked':
                        value = item.get('total_checked_region_direct') + item.get('total_checked_region_cross')
                    elif expr == 'total_unchecked':
                        value = item.get('total_unchecked_region_direct') + item.get('total_unchecked_region_cross')
                    elif expr == 'avg_score':
                        value = (item.get('avg_score_region_direct') + item.get('avg_score_region_cross')) / 2
                    elif expr == 'avg_score_branch_self':
                        value = (item.get('avg_score_branch') + item.get('avg_score_manage')) / 2
                    else:
                        value = item.get(expr)
                    line_columns.append(report._build_column_dict(value, column, options=options))
                lines.append({
                    'id': f"~ttb.branch~{branch}|~product.category~{item['counter_id']}",
                    'name': item['counter_name'],
                    'columns': line_columns,
                    'level': 2,
                    'unfoldable': False,
                    'unfolded': False,
                    'parent_id': f"~ttb.branch~{branch}",
                })

        # Calculate final totals after the loop
        # t_total_need_check = (
        #         t_total_need_check_region_direct
        #         + t_total_need_check_region_cross
        # )
        t_total_checked = (
                t_total_checked_region_direct
                + t_total_checked_region_cross
        )
        t_total_unchecked = (
                t_total_unchecked_region_direct
                + t_total_unchecked_region_cross
        )

        avg_score_manage_final = t_avg_score_manage / count_avg_score_manage if count_avg_score_manage else 0
        avg_score_branch_final = t_avg_score_branch / count_avg_score_branch if count_avg_score_branch else 0
        avg_score_region_direct_final = t_avg_score_region_direct / count_avg_score_region_direct if count_avg_score_region_direct else 0
        avg_score_region_cross_final = t_avg_score_region_cross / count_avg_score_region_cross if count_avg_score_region_cross else 0
        avg_score_final = (avg_score_region_direct_final + avg_score_region_cross_final) / 2
        avg_scoce_branch_self_final = (avg_score_branch_final + avg_score_manage_final) / 2
        done_percentage_manage_final = t_done_percentage_manage / count_done_percentage_manage if count_done_percentage_manage else 0
        done_percentage_branch_final = t_done_percentage_branch / count_done_percentage_branch if count_done_percentage_branch else 0
        done_percentage_region_direct_final = t_done_percentage_region_direct / count_done_percentage_region_direct if count_done_percentage_region_direct else 0
        done_percentage_region_cross_final = t_done_percentage_region_cross / count_done_percentage_region_cross if count_done_percentage_region_cross else 0

        # Total line
        total_value = {'brand_name': 'Tổng',
                       'total_checked_manage': t_total_checked_manage,
                       'total_unchecked_manage': t_total_unchecked_manage,
                       'avg_score_manage': avg_score_manage_final,
                       'total_checked_branch': t_total_checked_branch,
                       'total_unchecked_branch': t_total_unchecked_branch,
                       'avg_score_branch': avg_score_branch_final,
                       'total_checked_region_direct': t_total_checked_region_direct,
                       'total_unchecked_region_direct': t_total_unchecked_region_direct,
                       'avg_score_region_direct': avg_score_region_direct_final,
                       'total_checked_region_cross': t_total_checked_region_cross,
                       'total_unchecked_region_cross': t_total_unchecked_region_cross,
                       'avg_score_region_cross': avg_score_region_cross_final,
                       'total_checked': t_total_checked,
                       'total_unchecked': t_total_unchecked, 'avg_score_branch_self': avg_scoce_branch_self_final,
                       'avg_score': avg_score_final,
                       'total_overdue_manage': t_total_overdue_manage,
                       'total_overdue_branch': t_total_overdue_branch,
                       'total_overdue_region_cross': t_total_overdue_region_cross,
                       'total_overdue_region_direct': t_total_overdue_region_direct,
                       'done_percentage_manage': done_percentage_manage_final,
                       'done_percentage_branch': done_percentage_branch_final,
                       'done_percentage_direct': done_percentage_region_direct_final,
                       'done_percentage_region_cross': done_percentage_region_cross_final
                       }
        total_line_columns = []
        for total_column in options['columns']:
            expr = total_column['expression_label']
            value = total_value.get(expr)
            total_line_columns.append(report._build_column_dict(value, total_column, options=options))
        lines.append({
            'id': f"~total_id~",
            'name': 'Tổng',
            'columns': total_line_columns,
            'level': 1,
            'unfoldable': False,
            'unfolded': False,
        })
        return [(0, line) for line in lines]

    def _customize_warnings(self, report, options, all_column_groups_expression_totals, warnings):
        warnings.clear()

