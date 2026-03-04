from odoo import api, fields, models, _


class ProductZoneReport(models.AbstractModel):
    _name = 'product.zone.report'
    _inherit = 'account.report.custom.handler'
    _description = 'Báo cáo sản phẩm theo khu vực'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        options['column_headers'] = []
        options['columns'] = [
            {
                'name': 'Sản phẩm',
                'expression_label': 'product_name',
                'class': 'text',
                'type': 'string',
                'column_group_key': '1',
            },
            {
                'name': 'Phiếu kho',
                'expression_label': 'picking_name',
                'class': 'text',
                'type': 'string',
                'column_group_key': '2',
            },
            {
                'name': 'Ngày hoàn thành',
                'expression_label': 'date_done',
                'class': 'date',
                'type': 'date',
                'column_group_key': '3',
            },
            {
                'name': 'Số lượng',
                'expression_label': 'quantity',
                'class': 'number',
                'type': 'float',
                'column_group_key': '4',
            },
        ]

    def _customize_warnings(self, report, options, all_column_groups_expression_totals, warnings):
        warnings.clear()

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals=None, warnings=None):
        lines = []

        date_from = options['date']['date_from']
        date_to = options['date']['date_to']

        # SQL lấy sản phẩm có >= 2 phiếu kho và thuộc 2 zone khác nhau
        query = """
            SELECT
                pp.id as product_id,
                pt.name->>'en_US' as product_name,
                STRING_AGG(DISTINCT sp.name, ', ' ORDER BY sp.name) as picking_names,
                MAX(sp.date_done) as date_done,
                SUM(sm.quantity) as total_qty
            FROM stock_move sm
            INNER JOIN stock_picking sp ON sm.picking_id = sp.id
            INNER JOIN product_product pp ON sm.product_id = pp.id
            INNER JOIN product_template pt ON pp.product_tmpl_id = pt.id
            INNER JOIN stock_location sl_src ON sm.location_id = sl_src.id
            INNER JOIN stock_location sl_dest ON sm.location_dest_id = sl_dest.id
            WHERE sp.state = 'done'
                AND sp.date_done >= %s
                AND sp.date_done <= %s
            GROUP BY pp.id, pt.name->>'en_US'
            HAVING COUNT(DISTINCT sp.id) >= 2
            ORDER BY pp.id
        """

        self.env.cr.execute(query, [date_from, date_to])
        products_data = self.env.cr.dictfetchall()

        for index, product_data in enumerate(products_data):
            product_record = {
                'product_name': product_data['product_name'],
                'picking_name': product_data['picking_names'],
                'date_done': product_data['date_done'],
                'quantity': product_data['total_qty'],
            }

            line_columns = []
            for column in options['columns']:
                expr = column['expression_label']
                value = product_record.get(expr)
                line_columns.append(report._build_column_dict(value, column, options=options))

            lines.append({
                'id': f"line_product_{product_data['product_id']}_{index}",
                'name': '',
                'columns': line_columns,
                'level': 1,
                'unfoldable': False,
                'unfolded': False,
            })

        return [(0, line) for line in lines]
