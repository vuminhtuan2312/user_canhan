from odoo import models, fields, api
from dateutil.relativedelta import relativedelta
import pandas as pd
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta

class WizardCoverageWeek(models.TransientModel):
    _name = 'wizard.coverage.week'
    _description = 'POP UP báo cáo độ phủ theo tuần'

    branch = fields.Many2many(string='Cơ sở', comodel_name='ttb.branch')
    categ_ids = fields.Many2many(comodel_name='product.category', string='Nhóm sản phẩm')
    product_tag_ids = fields.Many2many(comodel_name='product.tag', string='Thẻ')
    date_range = fields.Date(string="Xem đến ngày", required=True, default=fields.Date.today)

    def action_confirm(self):
        for wizard in self:
            if not wizard.date_range:
                raise ValidationError("Vui lòng chọn ngày xem báo cáo.")

            # Tính khoảng thời gian theo tuần
            start_week = wizard.date_range - timedelta(days=wizard.date_range.weekday())
            end_week = wizard.date_range

            same_day_last_month = wizard.date_range - relativedelta(months=1)
            start_week_same_month = same_day_last_month - timedelta(days=same_day_last_month.weekday())
            end_week_same_month = same_day_last_month

            same_day_last_year = wizard.date_range - relativedelta(years=1)
            start_week_same_year = same_day_last_year - timedelta(days=same_day_last_year.weekday())
            end_week_same_year = same_day_last_year

            selected_category_ids = wizard.categ_ids.ids
            product_ids = self.env['product.product'].search([
                ('product_tmpl_id.categ_id', 'child_of', selected_category_ids)
            ]).ids
            if not product_ids:
                continue

            branches = wizard.branch
            if not branches:
                branches = self.env['ttb.branch'].search(
                    [('id', 'in', [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26])])

            # Xóa báo cáo cũ
            self.env['report.coverage.week'].search([]).unlink()

            for branch in branches:
                domain_base = [
                    ('product_id', 'in', product_ids),
                    ('order_id.state', '=', 'done'),
                    ('order_id.ttb_branch_id', '=', branch.id)
                ]
                if wizard.product_tag_ids:
                    domain_base.append(('product_id.product_tmpl_id.product_tag_ids', 'in', wizard.product_tag_ids.ids))

                def group_sales(domain):
                    data = self.env['pos.order.line'].read_group(domain, ['price_subtotal_incl:sum'], [])
                    return data[0]['price_subtotal_incl'] if data else 0.0

                sales_week = group_sales(
                    domain_base + [('order_id.date_order', '>=', start_week), ('order_id.date_order', '<=', end_week)])
                sales_same_week_month = group_sales(domain_base + [('order_id.date_order', '>=', start_week_same_month),
                                                                   ('order_id.date_order', '<=', end_week_same_month)])
                sales_same_week_year = group_sales(domain_base + [('order_id.date_order', '>=', start_week_same_year),
                                                                  ('order_id.date_order', '<=', end_week_same_year)])

                days_in_week = (end_week - start_week).days + 1
                avg_day = sales_week / days_in_week if days_in_week else 0.0
                growth_week_month = ((sales_week / sales_same_week_month) - 1) if sales_same_week_month else 0.0
                growth_week_year = ((sales_week / sales_same_week_year) - 1) if sales_same_week_year else 0.0

                # Tồn từ AUGESS
                product_augges_ids = [p.product_tmpl_id.augges_id for p in
                                      self.env['product.product'].browse(product_ids) if p.product_tmpl_id.augges_id]
                warehouses = self.env['stock.warehouse'].search([('ttb_branch_id', '=', branch.id)])
                branch_warehouse_ids = [w.id_augges for w in warehouses if w.id_augges]

                ids_kho_str = ','.join(map(str, branch_warehouse_ids))
                ids_hang_str = ','.join(map(str, product_augges_ids))

                nam = wizard.date_range.strftime("%Y")
                thang = wizard.date_range.strftime("%m")
                sngay = wizard.date_range.strftime("%y%m%d")
                dau_thang = wizard.date_range.strftime("%y%m01")

                # Giống với báo cáo phủ theo tháng:
                # Xét về đầu kỳ thì code dưới đây không giống các code khác (code khác lấy đầu kỳ là đầu năm hoặc 1/9/2025)
                query = f"""
                          SELECT ID_Kho, ID_Hang, Ma_Hang, Ma_Tong, SUM(Sl_Cky) AS SL_Ton, SUM(So_Luong) AS So_Luong,
                              {nam} as nam,
                              {thang} as mm,
                              {sngay} as sngay
                          FROM 
                          ( 

                          SELECT Htk.ID_Kho, Htk.ID_Hang, DmH.Ma_Hang, ISNULL(DmH.Ma_Tong,SPACE(25)) AS Ma_Tong, SUM(Htk.So_Luong) AS Sl_Cky, CAST(0 AS money) AS So_Luong 
                          FROM Htk 
                          LEFT JOIN DmKho ON Htk.ID_Kho  = DmKho.ID 
                          LEFT JOIN DmH   ON Htk.ID_Hang = DmH.ID 
                          LEFT JOIN DmNh  ON DmH.ID_Nhom = DmNh.ID 
                          WHERE HTK.Nam = {nam} AND HtK.ID_Dv = 0 AND Htk.Mm = {thang} AND Htk.ID_Kho IN ({ids_kho_str}) AND Htk.ID_Hang IN ({ids_hang_str})
                          GROUP BY Htk.ID_Kho, Htk.ID_Hang, DmH.Ma_Hang, DmH.Ma_Tong 

                          UNION ALL 
                          SELECT SlNxM.ID_Kho, SlNxD.ID_Hang, DmH.Ma_Hang, ISNULL(DmH.Ma_Tong,SPACE(25)) AS Ma_Tong, 
                          SUM(CASE WHEN DmNx.Ma_Ct IN ('NK','NM','PN','NS','NL') THEN SlNxD.So_Luong ELSE -SlNxD.So_Luong END) AS Sl_Cky, 
                          SUM(CASE WHEN SlNxD.SNgay >='{sngay}' AND DmNx.Ma_Ct IN ('XK','XB','NL') THEN (CASE WHEN DmNx.Ma_Ct IN ('XK','XB') THEN SlNxD.So_Luong ELSE -SlNxD.So_Luong END) ELSE CAST(0 AS money) END) AS So_Luong 
                          FROM SlNxD 
                          LEFT JOIN SlNxM ON SlNxD.ID      = SlNxM.ID 
                          LEFT JOIN DmNx  ON SlNxM.ID_Nx   = DmNx.ID 
                          LEFT JOIN DmH   ON SlNxD.ID_Hang = DmH.ID 
                          LEFT JOIN DmNh  ON DmH.ID_Nhom   = DmNh.ID 
                          WHERE SlNxM.Sngay >= '{dau_thang}' AND SlNxM.Sngay <= '{sngay}' AND SlNxM.ID_Dv = 0 AND SlNxD.ID_Kho IN ({ids_kho_str})  AND SlNxD.ID_Hang IN ({ids_hang_str})  
                          GROUP BY SlNxM.ID_Kho, SlNxD.ID_Hang, DmH.Ma_Hang, DmH.Ma_Tong 

                          UNION ALL 
                          SELECT SlBlM.ID_Kho, SlBlD.ID_Hang, DmH.Ma_Hang, ISNULL(DmH.Ma_Tong,SPACE(25)) AS Ma_Tong, SUM(- SlBlD.So_Luong) AS Sl_Cky, 
                          SUM(CASE WHEN SlBlD.SNgay >='{sngay}' THEN SlBlD.So_Luong ELSE CAST(0 AS money) END) AS So_Luong 
                          FROM SlBlD 
                          LEFT JOIN SlBlM ON SlBlD.ID      = SlBlM.ID 
                          LEFT JOIN DmH   ON SlBlD.ID_Hang = DmH.ID 
                          LEFT JOIN DmNh  ON DmH.ID_Nhom   = DmNh.ID 
                          WHERE SlBlM.Sngay >= '{dau_thang}' AND SlBlM.Sngay <= '{sngay}' AND SlBlM.ID_Dv = 0 AND ISNULL(SlBlD.ID_Kho,SlBlM.ID_Kho) IN ({ids_kho_str})  AND SlBlD.ID_Hang IN ({ids_hang_str})  
                          GROUP BY SlBlM.ID_Kho, SlBlD.ID_Hang, DmH.Ma_Hang, DmH.Ma_Tong 

                          UNION ALL 
                          SELECT SlDcD.ID_KhoX AS ID_Kho, SlDcD.ID_Hang, DmH.Ma_Hang, ISNULL(DmH.Ma_Tong,SPACE(25)) AS Ma_Tong, SUM(- SlDcD.So_Luong) AS Sl_Cky, 
                          CAST(0 AS money) AS So_Luong 
                          FROM SlDcD 
                          LEFT JOIN SlDcM ON SlDcD.ID      = SlDcM.ID 
                          LEFT JOIN DmKho ON SlDcD.ID_KhoX = DmKho.ID 
                          LEFT JOIN DmH   ON SlDcD.ID_Hang = DmH.ID 
                          LEFT JOIN DmNh  ON DmH.ID_Nhom   = DmNh.ID 
                          WHERE SlDcM.Sngay >= '{dau_thang}' AND SlDcM.Sngay <= '{sngay}' AND SlDcM.ID_Dv = 0 AND SlDcD.ID_KhoX IN ({ids_kho_str}) AND SlDcD.ID_Hang IN ({ids_hang_str}) 
                          GROUP BY SlDcD.ID_KhoX, SlDcD.ID_Hang, DmH.Ma_Hang, DmH.Ma_Tong 

                          UNION ALL 
                          SELECT SlDcD.ID_KhoN AS ID_Kho, SlDcD.ID_Hang, DmH.Ma_Hang, ISNULL(DmH.Ma_Tong,SPACE(25)) AS Ma_Tong, 
                          SUM(SlDcD.So_Luong) AS Sl_Cky, CAST(0 AS money) AS So_Luong 
                          FROM SlDcD 
                          LEFT JOIN SlDcM ON SlDcD.ID      = SlDcM.ID 
                          LEFT JOIN DmKho ON SlDcD.ID_KhoN = DmKho.ID 
                          LEFT JOIN DmH   ON SlDcD.ID_Hang = DmH.ID 
                          LEFT JOIN DmNh  ON DmH.ID_Nhom   = DmNh.ID 
                          WHERE SlDcM.Sngay >= '{dau_thang}' AND SlDcM.Sngay <= '{sngay}' AND SlDcM.ID_Dv = 0 AND SlDcD.ID_KhoN IN ({ids_kho_str}) AND SlDcD.ID_Hang IN ({ids_hang_str})
                          GROUP BY SlDcD.ID_KhoN, SlDcD.ID_Hang, DmH.Ma_Hang, DmH.Ma_Tong 

                          ) AS Dt_Hang 
                          WHERE Sl_Cky<>0 OR So_Luong<>0 
                          GROUP BY ID_Kho, ID_Hang, Ma_Hang, Ma_Tong 
                          """
                conn = self.env['ttb.tools'].get_mssql_connection()
                df = pd.read_sql(query, conn)
                print(df.columns)
                stock_augess_dict = dict(zip(df['ID_Hang'], df['SL_Ton']))

                num_covered = 0
                num_not_covered = 0
                total_stock_qty = 0.0
                total_stock_value = 0.0
                lines_data = []

                products = self.env['product.product'].browse(product_ids)
                for product in products:
                    aug_id = product.product_tmpl_id.augges_id
                    stock_qty = stock_augess_dict.get(aug_id, 0.0)
                    po_line = self.env['purchase.order.line'].search(
                        [('product_id', '=', product.id), ('order_id.state', 'in', ['purchase', 'done'])],
                        order='date_order desc',
                        limit=1
                    )
                    last_price = po_line.price_unit if po_line else 0.0

                    min_qty_config = self.env['ttb.coverage.config'].search([
                        ('product_id', '=', product.id),
                        ('branch_id', '=', branch.id)
                    ], limit=1)
                    min_qty = min_qty_config.min_qty if min_qty_config else 0.0

                    # Doanh thu riêng từng sản phẩm
                    sales_week_p = group_sales(domain_base + [('product_id', '=', product.id),
                                                              ('order_id.date_order', '>=', start_week),
                                                              ('order_id.date_order', '<=', end_week)])
                    sales_same_week_month_p = group_sales(domain_base + [('product_id', '=', product.id),
                                                                         ('order_id.date_order', '>=',
                                                                          start_week_same_month),
                                                                         ('order_id.date_order', '<=',
                                                                          end_week_same_month)])
                    sales_same_week_year_p = group_sales(domain_base + [('product_id', '=', product.id),
                                                                        ('order_id.date_order', '>=',
                                                                         start_week_same_year),
                                                                        ('order_id.date_order', '<=',
                                                                         end_week_same_year)])
                    growth_week_month_p = (
                                (sales_week_p / sales_same_week_month_p) - 1) if sales_same_week_month_p else 0.0
                    growth_week_year_p = (
                                (sales_week_p / sales_same_week_year_p) - 1) if sales_same_week_year_p else 0.0
                    avg_day_p = sales_week_p / days_in_week if days_in_week else 0.0
                    avg_stock_days_p = (stock_qty / avg_day_p) if avg_day_p else 0.0

                    covered_status = 'yes' if stock_qty >= min_qty else 'no'
                    if covered_status == 'yes':
                        num_covered += 1
                    else:
                        num_not_covered += 1

                    total_stock_qty += stock_qty
                    total_stock_value += stock_qty * last_price

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

                    lines_data.append((0, 0, {
                        'mch1': mch1,
                        'mch2': mch2,
                        'mch3': mch3,
                        'mch4': mch4,
                        'mch5': mch5,
                        'product_id': product.id,
                        'sales_week': sales_week_p,
                        'sales_same_week_month': sales_same_week_month_p,
                        'sales_same_week_year': sales_same_week_year_p,
                        'growth_week_month': growth_week_month_p,
                        'growth_week_year': growth_week_year_p,
                        'stock_qty': stock_qty,
                        'stock_value': stock_qty * last_price,
                        'avg_day': avg_day_p,
                        'avg_stock_days': avg_stock_days_p,
                        'min_qty': min_qty,
                        'covered': covered_status,
                    }))

                total_products = num_covered + num_not_covered
                coverage_percent = (num_covered / total_products) if total_products else 0.0
                avg_stock_days = (total_stock_qty / avg_day) if avg_day else 0.0

                self.env['report.coverage.week'].create({
                    'branch': branch.name,
                    'sales_week': sales_week,
                    'sales_same_week_month': sales_same_week_month,
                    'sales_same_week_year': sales_same_week_year,
                    'growth_week_month': growth_week_month,
                    'growth_week_year': growth_week_year,
                    'avg_day': avg_day,
                    'stock_qty': total_stock_qty,
                    'avg_stock_days': avg_stock_days,
                    'num_covered': num_covered,
                    'num_not_covered': num_not_covered,
                    'coverage_percent': coverage_percent,
                    'total_value': total_stock_value,
                    'coverage_line_ids': lines_data,
                })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Báo cáo độ phủ theo tuần',
            'res_model': 'report.coverage.week',
            'view_mode': 'list,form',
            'target': 'current',
            'views': [(self.env.ref('ttb_point_of_sale.view_report_coverage_week_list').id, 'list'),
                      (self.env.ref('ttb_point_of_sale.view_report_coverage_week_form').id, 'form')],
        }

    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}