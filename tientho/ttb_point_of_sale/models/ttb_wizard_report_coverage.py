from odoo import models, fields, api
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import pandas as pd
from odoo.exceptions import ValidationError, UserError

class WizardReportCoverage(models.TransientModel):
    _name = 'wizard.report.coverage'
    _description = 'Báo cáo độ phủ'

    branch = fields.Many2many(string='Cơ sở', comodel_name='ttb.branch')
    categ_ids = fields.Many2many(comodel_name='product.category', string='Nhóm sản phẩm')
    product_tag_ids = fields.Many2many(comodel_name='product.tag', string='Thẻ')
    date_range = fields.Date(string="Xem đến ngày", required=True, default=fields.Date.today)
    period = fields.Selection([
        ('view_month', 'Xem theo tháng'),
        ('view_week', 'Xem theo tuần'),
    ], string="Chọn chu kỳ", required=True)

    def action_confirm(self):
        for wizard in self:
            # Xác định khoảng thời gian
            if wizard.period == 'view_week':
                start_date = wizard.date_range - timedelta(days=wizard.date_range.weekday())
            elif wizard.period == 'view_month':
                start_date = wizard.date_range.replace(day=1)
            end_date = wizard.date_range

            date_1m = (wizard.date_range - relativedelta(months=1)) + timedelta(days=1)
            start_7d = wizard.date_range - timedelta(days=7)

            # Xóa dữ liệu cũ
            self.env['ttb.report.coverage'].search([]).unlink()

            # domain sản phẩm tự động child_of
            selected_category_ids = wizard.categ_ids.ids
            product_ids = self.env['product.product'].search([
                ('product_tmpl_id.categ_id', 'child_of', selected_category_ids)
            ]).ids
            if not product_ids:
                continue
            # không chọn cơ sở lấy hết
            branches = wizard.branch
            if not branches:
                branches = self.env['ttb.branch'].search([('id', 'in', [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26])])

            # Xử lý từng branch
            for branch in branches:
                domain_base = [
                    ('product_id', 'in', product_ids),
                    ('order_id.state', '=', 'done'),
                    ('order_id.ttb_branch_id', '=', branch.id)
                ]
                if wizard.product_tag_ids:
                    domain_base.append(('product_id.product_tmpl_id.product_tag_ids', 'in', wizard.product_tag_ids.ids))
                # Lấy dữ liệu POS
                def group_sales(domain):
                    data = self.env['pos.order.line'].read_group(domain, ['price_subtotal_incl:sum'], [])
                    return data[0]['price_subtotal_incl'] if data else 0.0

                if wizard.branch:
                    domain_base += [('order_id.ttb_branch_id', 'in', wizard.branch.ids)]
                if wizard.product_tag_ids:
                    domain_base += [('product_id.product_tmpl_id.product_tag_ids', 'in', wizard.product_tag_ids.ids)]

                total_1m = group_sales(
                    domain_base + [('order_id.date_order', '>=', date_1m), ('order_id.date_order', '<=', end_date)])
                total_period = group_sales(
                    domain_base + [('order_id.date_order', '>=', start_date), ('order_id.date_order', '<=', end_date)])
                total_7d = group_sales(
                    domain_base + [('order_id.date_order', '>=', start_7d), ('order_id.date_order', '<=', end_date)])
                avg_7d = total_7d / 7.0 if total_7d else 0.0
                growth = ((total_1m / total_period) - 1) if total_period else 0.0

                # Lấy tồn từ AUGESS
                product_augges_ids = [p.product_tmpl_id.augges_id for p in self.env['product.product'].browse(product_ids) if p.product_tmpl_id.augges_id]
                warehouses = self.env['stock.warehouse'].search([('ttb_branch_id', '=', branch.id)])
                branch_warehouse_ids = [w.id_augges for w in warehouses if w.id_augges]

                ids_kho_str = ','.join(map(str, branch_warehouse_ids))
                ids_hang_str = ','.join(map(str, product_augges_ids))
                nam = wizard.date_range.strftime("%y")
                thang = wizard.date_range.strftime("%m")
                sngay = wizard.date_range.strftime("%y%m%d")
                dau_thang = wizard.date_range.strftime("%y%m01")

                # Phần này không dùng tới nữa
                query = f"""
                    SELECT ID_Hang, SUM(Sl_Cky) AS Sl_Ton
                    FROM (
                        SELECT Htk.ID_Hang, SUM(Htk.So_Luong) AS Sl_Cky
                        FROM Htk
                        WHERE HTK.Nam = {nam} AND HTK.Mm = {thang}
                          AND Htk.ID_Kho IN ({ids_kho_str})
                          AND Htk.ID_Hang IN ({ids_hang_str})
                        GROUP BY Htk.ID_Hang
                        UNION ALL
                        SELECT SlNxD.ID_Hang,
                               SUM(CASE WHEN DmNx.Ma_Ct IN ('NK','NM','PN','NS','NL') THEN SlNxD.So_Luong ELSE -SlNxD.So_Luong END)
                        FROM SlNxD
                        LEFT JOIN SlNxM ON SlNxD.ID = SlNxM.ID
                        LEFT JOIN DmNx  ON SlNxM.ID_Nx = DmNx.ID
                        WHERE SlNxM.Sngay >= '{dau_thang}' AND SlNxM.Sngay <= '{sngay}'
                          AND SlNxD.ID_Kho IN ({ids_kho_str})
                          AND SlNxD.ID_Hang IN ({ids_hang_str})
                        GROUP BY SlNxD.ID_Hang
                    ) AS T
                    GROUP BY ID_Hang
                """
                conn = self.env['ttb.tools'].get_mssql_connection()
                df = pd.read_sql(query, conn)
                stock_augess_dict = dict(zip(df['ID_Hang'], df['Sl_Ton']))

                # Tính tồn, tồn TB, tồn tối thiểu & % phủ
                num_covered = 0
                num_not_covered = 0
                total_stock_qty = 0.0
                total_stock_value = 0.0
                min_qty_default = 5

                products = self.env['product.product'].browse(product_ids)
                for product in products:
                    aug_id = product.product_tmpl_id.augges_id
                    stock_qty = stock_augess_dict.get(aug_id, 0.0)
                    po_line = self.env['purchase.order.line'].search(
                        [('product_id', '=', product.id), ('order_id.state', 'in', ['purchase', 'done'])],
                        order='date_order desc',
                        limit=1
                    )
                    category = product.product_tmpl_id.categ_id
                    mch1 = mch2 = mch3 = mch4 = mch5 = ''
                    while category:
                        if category.category_level == 5:
                            mch5 = category.complete_name
                        elif category.category_level == 4:
                            mch4 = category.complete_name
                        elif category.category_level == 3:
                            mch3 = category.complete_name
                        elif category.category_level == 2:
                            mch2 = category.complete_name
                        elif category.category_level == 1:
                            mch1 = category.complete_name
                        category = category.parent_id

                    last_price = po_line.price_unit if po_line else 0.0
                    min_qty =  min_qty_default

                    total_stock_qty += stock_qty
                    total_stock_value += stock_qty * last_price

                    if stock_qty >= min_qty:
                        num_covered += 1
                    else:
                        num_not_covered += 1

                total_products = num_covered + num_not_covered
                coverage_percent = (num_covered / total_products * 100) if total_products else 0.0
                avg_stock_days = (total_stock_qty / avg_7d) if avg_7d else 0.0
                # Tạo báo cáo
                self.env['ttb.report.coverage'].create({
                    'branch': branch.name,
                    'mch1': mch1,
                    'mch2': mch2,
                    'mch3': mch3,
                    'mch4': mch4,
                    'mch5': mch5,
                    'sales_1m': total_1m,
                    'sales_period': total_period,
                    'growth': growth,
                    'avg_7d': avg_7d,
                    'stock_qty': total_stock_qty,
                    'avg_stock_days': avg_stock_days,
                    'num_covered': num_covered,
                    'num_not_covered': num_not_covered,
                    'coverage_percent': coverage_percent,
                    'total_value': total_stock_value,
                })

            return {
                'type': 'ir.actions.act_window',
                'name': 'Báo cáo độ phủ',
                'res_model': 'ttb.report.coverage',
                'view_mode': 'list,form',
                'target': 'current',
                'views': [(self.env.ref('ttb_point_of_sale.view_report_coverage_list').id, 'list'),(self.env.ref('ttb_point_of_sale.view_report_coverage_form').id, 'form')],

            }

    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}