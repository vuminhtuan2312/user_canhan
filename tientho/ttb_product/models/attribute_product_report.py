from odoo import api, fields, models, _


class AttributeProductReport(models.AbstractModel):
    _name = 'attribute.product.report'
    _inherit = 'account.report.custom.handler'
    _description = 'Báo cáo sản phẩm theo thuộc tính'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        options['column_headers'] = []
        options['columns'] = [
            {
                'name': 'MCH1',
                'expression_label': 'mch1',
                'class': 'text',
                'type': 'string',
                'column_group_key': '1',
            },
            {
                'name': 'MCH2',
                'expression_label': 'mch2',
                'class': 'text',
                'type': 'string',
                'column_group_key': '2',
            },
            {
                'name': 'MCH3',
                'expression_label': 'mch3',
                'class': 'text',
                'type': 'string',
                'column_group_key': '3',
            },
            {
                'name': 'MCH4',
                'expression_label': 'mch4',
                'class': 'text',
                'type': 'string',
                'column_group_key': '4',
            },
            {
                'name': 'MCH5',
                'expression_label': 'mch5',
                'class': 'text',
                'type': 'string',
                'column_group_key': '5',
            },
            {
                'name': 'Kết hợp thuộc tính',
                'expression_label': 'attribute_combination',
                'class': 'text',
                'type': 'string',
                'column_group_key': '6',
            },
            {
                'name': 'Số sản phẩm',
                'expression_label': 'product_count',
                'class': 'text',
                'type': 'string',
                'column_group_key': '7',
            },
            {
                'name': 'Tồn kho',
                'expression_label': 'inventory',
                'class': 'text',
                'type': 'Integer',
                'column_group_key': '8',
            },
            {
                'name': 'Doanh số 1 tháng',
                'expression_label': 'revenue_last_1_months',
                'class': 'text',
                'type': 'Integer',
                'column_group_key': '9',
            },
            {
                'name': 'Doanh số 3 tháng',
                'expression_label': 'revenue_last_3_months',
                'class': 'text',
                'type': 'Integer',
                'column_group_key': '10',
            },
        ]

    def _customize_warnings(self, report, options, all_column_groups_expression_totals, warnings):
        warnings.clear()

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals=None, warnings=None):
        lines = []

        query = f"""
            with 
                -- category combine value
                ccv as (
                    select cc.category_id, cc.id as combine_id, ccv.product_attribute_value_id value_id 
                    from 
                        catetory_attribute_value_combine_rel ccv
                        join ttb_sku_attribute cc on cc.id = ccv.ttb_sku_attribute_id
                ),
            
                -- category combine value count
                ccvc as (
                    select category_id, combine_id, count(*) as count_value from ccv
                    group by category_id, combine_id
                ),
            
                -- product attribute value
                pav as (
                    select pa.product_tmpl_id, pav.product_attribute_value_id value_id 
                    from 
                        product_attribute_value_product_template_attribute_line_rel pav
                        join product_template_attribute_line pa on pa.id = pav.product_template_attribute_line_id
                ),
                core_data as (
                    select ccv.category_id, ccv.combine_id, pav.product_tmpl_id
                    from 
                        ccv
                        join ccvc on ccvc.category_id = ccv.category_id and ccvc.combine_id = ccv.combine_id
                        join pav on pav.value_id = ccv.value_id
                    group by ccv.category_id, ccvc.count_value, ccv.combine_id, pav.product_tmpl_id
                        having count(pav.product_tmpl_id) = ccvc.count_value
                ),
                core_data_grouped as (
                    select category_id, combine_id, count(*) as product_count
                    from 
                        core_data
                    group by category_id, combine_id
                ),
                inventory_summary AS (
                    SELECT 
                        core_data.category_id, core_data.combine_id,
                        SUM(stq.quantity) AS inventory
                    FROM 
                        core_data
                        JOIN product_product pp ON pp.product_tmpl_id = core_data.product_tmpl_id
                        join stock_quant stq on stq.product_id = pp.id
                        join stock_location sl on sl.id = stq.location_id and sl.usage='internal'
                    GROUP BY core_data.category_id, core_data.combine_id
                ),
                sales_1_month AS (
                    SELECT 
                        core_data.category_id, core_data.combine_id,
                        SUM(pos.price_subtotal) AS revenue_last_1_months
                    FROM 
                        core_data 
                        JOIN product_product pp ON pp.product_tmpl_id = core_data.product_tmpl_id
                        JOIN product_template pt ON pt.id = pp.product_tmpl_id
                        join pos_order_line pos on pos.product_id = pp.id
                        join pos_order po on pos.order_id = po.id
                    WHERE po.date_order >= NOW() - INTERVAL '1 months'
                    GROUP BY core_data.category_id, core_data.combine_id
                ),
                sales_3_month AS (
                    SELECT 
                        core_data.category_id, core_data.combine_id,
                        SUM(pos.price_subtotal) AS revenue_last_3_months
                    FROM 
                        core_data 
                        JOIN product_product pp ON pp.product_tmpl_id = core_data.product_tmpl_id
                        JOIN product_template pt ON pt.id = pp.product_tmpl_id
                        join pos_order_line pos on pos.product_id = pp.id
                        join pos_order po on pos.order_id = po.id
                    WHERE po.date_order >= NOW() - INTERVAL '3 months'
                    GROUP BY core_data.category_id, core_data.combine_id
                )
            select 
                COALESCE(pc1.category_code || ' | ' || pc1.name, '') AS mch1,
                COALESCE(pc2.category_code || ' | ' || pc2.name, '') AS mch2,
                COALESCE(pc3.category_code || ' | ' || pc3.name, '') AS mch3,
                COALESCE(pc4.category_code || ' | ' || pc4.name, '') AS mch4,
                COALESCE(pc5.category_code || ' | ' || pc5.name, '') AS mch5,
                product_count,
                cc.name as attribute_combination,
                inventory_summary.inventory,
                revenue_last_1_months,
                revenue_last_3_months
            from 
                core_data_grouped
                join ttb_sku_attribute cc on cc.id = core_data_grouped.combine_id
                join product_category pc5 on pc5.id = core_data_grouped.category_id
                join product_category pc4 on pc4.id = pc5.parent_id
                join product_category pc3 on pc3.id = pc4.parent_id
                join product_category pc2 on pc2.id = pc3.parent_id
                join product_category pc1 on pc1.id = pc2.parent_id

                left join inventory_summary on 
                    inventory_summary.category_id = core_data_grouped.category_id 
                    and inventory_summary.combine_id = core_data_grouped.combine_id

                left join sales_1_month on 
                    sales_1_month.category_id = core_data_grouped.category_id 
                    and sales_1_month.combine_id = core_data_grouped.combine_id
                left join sales_3_month on 
                    sales_3_month.category_id = core_data_grouped.category_id 
                    and sales_3_month.combine_id = core_data_grouped.combine_id
                
        """
        # -- join product_product pp on pp.product_tmpl_id = core_data_grouped.product_tmpl_id
        # -- join product_template pt on pt.id = core_data_grouped.product_tmpl_id
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        for index, record in enumerate(result):
            line_columns = []
            for column in options['columns']:
                expr = column['expression_label']
                value = record.get(expr)
                line_columns.append(report._build_column_dict(value, column, options=options))

            lines.append({
                'id': f"line_{record['attribute_combination'].replace(' ', '_')}_{index}",
                'name': '',
                'columns': line_columns,
                'level': 1,
                'unfoldable': False,
                'unfolded': False,
            })
        return [(0, line) for line in lines]