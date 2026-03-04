from odoo import api, models, fields
from odoo.exceptions import ValidationError, UserError
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import pandas as pd


class PlanReturnRequest(models.Model):
    _name = "plan.return.request"
    _description = "Dự trù hàng trả lại"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'ttb.approval.mixin']

    name = fields.Char(string='Mã dự trù', required=True, readonly=True, copy=False, default='Mới')
    branch_id = fields.Many2many(string='Cơ sở', comodel_name='ttb.branch')
    user_id = fields.Many2one(string='Người tạo', comodel_name='res.users', default=lambda self: self.env.user)
    date = fields.Datetime(string='Thời gian tạo', default=lambda self: fields.Datetime.now())
    state = fields.Selection(string='Trạng thái', selection=[('new', 'Mới'), ('tl_created', 'Đã tạo TL')],default='new', tracking=True)
    return_request_ids = fields.One2many(string="Yêu cầu trả hàng đã tạo", comodel_name='ttb.return.request', inverse_name='plan_tl_id')
    state_view_report = fields.Selection(string='Trạng thái xem báo cáo', selection=[('new', 'Chưa xem'), ('viewed', 'Đã xem')], default='new', traking=True)
    categ_id_level_1 = fields.Many2one('product.category',
                                       string='MCH1',
                                       domain="[('parent_id', '=', False),('category_level', '=', 1)]",
                                       store=True, readonly=False, tracking=True
                                       )
    categ_id_level_2 = fields.Many2one('product.category',
                                       string='MCH2',
                                       domain="[('parent_id', '=?', categ_id_level_1),('category_level', '=', 2)]",
                                       store=True, readonly=False, tracking=True
                                       )
    categ_id_level_3 = fields.Many2one('product.category',
                                       string='MCH3',
                                       domain="[('parent_id', '=?', categ_id_level_2),('category_level', '=', 3)]",
                                       store=True, readonly=False, tracking=True
                                       )
    categ_id_level_4 = fields.Many2one('product.category',
                                       string='MCH4',
                                       domain="[('parent_id', '=?', categ_id_level_3),('category_level', '=', 4)]",
                                       store=True, readonly=False, tracking=True
                                       )
    categ_id_level_5 = fields.Many2one('product.category',
                                       string='MCH5',
                                       domain="[('parent_id', '=?', categ_id_level_4),('category_level', '=', 5)]",
                                       store=True, readonly=False, tracking=True
                                       )
    supplier_ids = fields.Many2one(comodel_name='res.partner', string='Nhà cung cấp', required=True)

    def onchange_level(self, level):
        categ_id = self[f'categ_id_level_{level}']
        if level > 1 and categ_id:
            self[f'categ_id_level_{level - 1}'] = categ_id.parent_id

        for level_up in range(level + 1, 6):
            key = f'categ_id_level_{level_up}'
            key_parent = f'categ_id_level_{level_up - 1}'

            if not self[key_parent] or (self[key] and self[key].parent_id != self[key_parent]):
                self[key] = False

        for level_categ in range(5, 0, -1):
            key = f'categ_id_level_{level_categ}'
            if self[key] or level_categ == 1:
                break

    @api.onchange('categ_id_level_1')
    def onchange_level_1(self):
        self.onchange_level(1)

    @api.onchange('categ_id_level_2')
    def onchange_level_2(self):
        self.onchange_level(2)

    @api.onchange('categ_id_level_3')
    def onchange_level_3(self):
        self.onchange_level(3)

    @api.onchange('categ_id_level_4')
    def onchange_level_4(self):
        self.onchange_level(4)

    @api.onchange('categ_id_level_5')
    def onchange_level_5(self):
        self.onchange_level(5)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == 'Mới':
                vals['name'] = self.env['ir.sequence'].next_by_code('plan.return.request') or 'Mới'
        return super().create(vals_list)
    # Lấy MCH
    def get_selected_category_ids(self):
        self.ensure_one()
        selected_categ = (
                self.categ_id_level_5 or self.categ_id_level_4 or
                self.categ_id_level_3 or self.categ_id_level_2 or
                self.categ_id_level_1
        )
        if not selected_categ:
            raise UserError("Vui lòng chọn ít nhất 1 cấp nhóm MCH.")

        categs = self.env['product.category'].search([('id', 'child_of', selected_categ.id)])
        return categs.ids
    # Lấy đơn giá gần nhất
    def get_last_po_info(self, product):
        po_line = self.env['purchase.order.line'].search(
            [('product_id', '=', product.id),
             ('order_id.state', 'in', ['purchase', 'done'])],
            order='date_order desc',
            limit=1
        )
        if po_line:
            supplier = po_line.order_id.partner_id
            return {
                'supplier_id': supplier.id,
                'supplier_code': supplier.ref,
                'last_purchase_price': po_line.price_unit
            }
        return {
            'supplier_id': False,
            'supplier_code': '',
            'last_purchase_price': 0.0
        }
    # Lấy hàng đang về
    def get_incoming_qty(self, product_tmpl_id, branch_id):
        StockMove = self.env['stock.move']

        warehouse = self.env['stock.warehouse'].search([('ttb_branch_id', '=', branch_id)], limit=1)
        if not warehouse:
            return 0.0

        location_dest_id = warehouse.lot_stock_id.id
        moves = StockMove.search([
            ('product_id.product_tmpl_id', '=', product_tmpl_id),
            ('state', '=', 'assigned'),
            ('picking_id.picking_type_id.code', '=', 'incoming'),
            ('picking_id.state', '=', 'assigned'),
            ('location_dest_id', '=', location_dest_id),
            ('picking_id.purchase_id.state', '=', 'purchase'),
        ])

        incoming_qty = 0
        for move in moves:
            quantity_done = sum(move.move_line_ids.mapped('qty_done'))
            remaining_qty = move.product_uom_qty - quantity_done
            if remaining_qty > 0:
                incoming_qty += remaining_qty

        return incoming_qty

    def get_stock_from_augges(self, branch_warehouse_ids, product_augges_ids):
        ids_kho_str = ','.join(map(str, branch_warehouse_ids))
        ids_hang_str = ','.join(map(str, product_augges_ids))

        day = fields.Date.today()
        nam = day.strftime("%Y")
        thang = day.strftime("01")
        sngay = day.strftime("%y%m%d")
        dau_thang = "260101"
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
        return dict(zip(df['ID_Hang'], df['SL_Ton']))

    def action_view_report_plan(self):
        self.ensure_one()
        branch_default_kho = {
            14: 9,
            15: 78,
            16: 28,
            17: 12,
            18: 6,
            19: 5,
            20: 53,
            21: 27,
            22: 20,
            23: 15,
            24: 60,
            25: 68,
            26: 22
        }

        today = date.today()
        date_1m = (today - relativedelta(months=1))
        date_3m = (today - relativedelta(months=3))
        date_2w = today - timedelta(weeks=2)
        if not self.branch_id:
            raise ValidationError("Vui lòng chọn Cơ sở!")

        selected_category_ids = self.get_selected_category_ids()
        domain = [('categ_id', 'in', selected_category_ids)]
        if self.supplier_ids:
            supplierinfo_records = self.env['product.supplierinfo'].search([
                ('partner_id', 'in', self.supplier_ids.ids)
            ])
            product_ids = supplierinfo_records.mapped('product_tmpl_id').ids
            if not product_ids:
                raise UserError("Không có sản phẩm nào thuộc các Nhà cung cấp đã chọn.")
            domain.append(('id', 'in', product_ids))
        product_tmpls = self.env['product.template'].search(domain)

        if not product_tmpls:
            raise UserError("Không tìm thấy sản phẩm nào thuộc nhóm MCH đã chọn.")
        product_tmpl_ids = product_tmpls.ids

        products_dict = {p.id: p for p in product_tmpls}
        product_augges_ids = [p.augges_id for p in product_tmpls if p.augges_id]

        PosLine = self.env['pos.order.line']

        def build_summary(lines, date_type):
            summary = {}
            for line in lines:
                if not line.order_id.ttb_branch_id:
                    continue
                product_tmpl_id = line.product_id.product_tmpl_id.id
                branch_id = line.order_id.ttb_branch_id.id
                key = (branch_id, product_tmpl_id)

                if key not in summary:
                    summary[key] = {
                        'total_sales_3m_sys': 0.0,
                        'total_sales_1m_sys': 0.0,
                        'total_sales_2w_qty': 0.0,
                        'total_sales_2w_amount': 0.0,
                    }
                if date_type == '3m':
                    summary[key]['total_sales_3m_sys'] += line.qty
                elif date_type == '1m':
                    summary[key]['total_sales_1m_sys'] += line.qty
                elif date_type == '2w':
                    summary[key]['total_sales_2w_qty'] += line.qty
                    summary[key]['total_sales_2w_amount'] += line.price_subtotal_incl
            return summary

        domain_base = [
            ('order_id.state', '=', 'done'),
            ('order_id.ttb_branch_id', 'in', self.branch_id.ids),
            ('product_id.product_tmpl_id', 'in', product_tmpl_ids),
        ]
        s3 = build_summary(PosLine.search(domain_base + [('order_id.date_order', '>=', date_3m)]), '3m')
        s1 = build_summary(PosLine.search(domain_base + [('order_id.date_order', '>=', date_1m)]), '1m')
        s2 = build_summary(PosLine.search(domain_base + [('order_id.date_order', '>=', date_2w)]), '2w')

        product_summary_all = s3
        for k, v in s1.items():
            product_summary_all.setdefault(k, {}).update({'total_sales_1m_sys': v['total_sales_1m_sys']})
        for k, v in s2.items():
            product_summary_all.setdefault(k, {}).update({
                'total_sales_2w_qty': v['total_sales_2w_qty'],
                'total_sales_2w_amount': v['total_sales_2w_amount'],
            })

        if not product_summary_all:
            raise UserError("Không tìm thấy dữ liệu POS cho các sản phẩm này trong cơ sở")

        stock_map_per_branch = {}
        for branch in self.branch_id:
            default_kho_id = branch_default_kho.get(branch.id)

            if default_kho_id:
                stock_map_per_branch[(branch.id, None)] = self.get_stock_from_augges([default_kho_id], product_augges_ids)
            else:
                warehouses = self.env['stock.warehouse'].search([('ttb_branch_id', '=', branch.id)])
                all_ids = [w.id_augges for w in warehouses if w.id_augges]
                stock_map_per_branch[(branch.id, None)] = self.get_stock_from_augges(all_ids, product_augges_ids) if all_ids else {}

        records = []
        for (branch_id, product_tmpl_id), data in product_summary_all.items():
            product = products_dict.get(product_tmpl_id)

            if not product:
                continue
            stock_map = stock_map_per_branch.get((branch_id, None), {})
            stock_qty = stock_map.get(product.augges_id, 0.0)

            po_info = self.get_last_po_info(product)
            total_value = stock_qty * po_info['last_purchase_price']
            incoming_qty = self.get_incoming_qty(product_tmpl_id, branch_id)

            total_sales_1m = data.get('total_sales_1m_sys')

            rotation_return_days = 0
            if product.categ_id:
                main_category = product.categ_id
                while main_category.parent_id:
                    main_category = main_category.parent_id
                rotation_return_days = main_category.rotation_return_days or 0
            sales_rotation = 0.0
            if rotation_return_days > 0:
                date_rotation = today - timedelta(days=rotation_return_days)
                domain_rotation = [
                    ('order_id.state', '=', 'done'),
                    ('order_id.ttb_branch_id', '=', branch_id),
                    ('product_id.product_tmpl_id', '=', product_tmpl_id),
                    ('order_id.date_order', '>=', date_rotation)
                ]
                sales_rotation = sum(PosLine.search(domain_rotation).mapped('qty'))

            # Nếu tồn kho âm thì mặc định bằng 0
            stock_qty = max(stock_qty, 0.0)
            auto_return_qty = stock_qty + incoming_qty - sales_rotation
            if auto_return_qty < 0:
                suggested_return_category = 0.0
            else:
                suggested_return_category = auto_return_qty
            records.append({
                'branch_id': branch_id,
                'pdcode': product.default_code,
                'barcode': product.barcode,
                'pdname': product.name,
                'dvt': product.uom_id.name,
                'total_sales_3m_sys': data.get('total_sales_3m_sys'),
                'total_sales_1m_sys': total_sales_1m,
                'total_sales_2w_qty': data.get('total_sales_2w_qty'),
                'stock_system_branch': stock_qty,
                'suggested_return_category': suggested_return_category,
                'sale_price': product.list_price,
                'total_value': total_value,
                'supplier_id': po_info['supplier_id'],
                'supplier_code': po_info['supplier_code'],
                'last_purchase_price': po_info['last_purchase_price'],
                'incoming_qty': incoming_qty,
                'product_id': product.id,
                'product_uom': product.uom_id.id,
                'auto_return_qty': auto_return_qty
            })
            ReportReturnRequest = self.env['report.return.request']

            if not ReportReturnRequest.search_count([('report_id', '=', self.id)]):
                for record in records:
                    record['report_id'] = self.id
                self.state_view_report = 'viewed'
                ReportReturnRequest.create(records)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Báo cáo hàng trả lại',
            'res_model': 'report.return.request',
            'view_mode': 'list',
            'target': 'current',
            'domain': [('report_id', '=', self.id)],
            'views': [(self.env.ref('ttb_return_request.view_report_return_request_list').id, 'list')],
        }
