from odoo import models, fields
from datetime import timedelta

class AutoPurchaseRequest(models.Model):
    _name = 'auto.purchase.request'
    _description = 'Tự động đặt hàng'

    name = fields.Char('Tên')
    # start_date = fields.Date('Ngày bắt đầu')
    end_date = fields.Date('Ngày đề xuất đặt hàng', default=fields.Date.today, required=True)
    
    warehouse_ids = fields.Many2many('stock.warehouse', string='Kho')
    product_ids = fields.Many2many('product.product', string='Sản phẩm')
    # has_sale = fields.Boolean('Có bán')
    partner_ids = fields.Many2many('res.partner', string='Nhà cung cấp')
    mch_ids = fields.Many2many('product.category', string='MCH', help='Chọn MCH1 hoặc MCH2 hoặc MCH3')

    line_count = fields.Integer('Line tự tính số lượng đặt hàng', compute='compute_line_count')
    selected_line_count = fields.Integer('Line đã chọn để tạo PR', compute='compute_line_count')
    purchase_request_count = fields.Integer('PR đã tạo', compute='compute_line_count')

    lead_time = fields.Integer('Lead time (ngày)', default=3)
    stock_day = fields.Integer('Kỳ vọng đáp ứng (ngày)', default=7, required=True)
    check_day = fields.Integer('Thời gian lấy mẫu (ngày)', default=7, required=True)

    fix_stock = fields.Boolean('Lấy tồn 0 nếu tồn âm', default=True)
    company_id = fields.Many2one(string='Công ty', comodel_name='res.company', required=True, default=lambda self: self.env.company)

    pr_ids = fields.Many2many(string='Danh sách PR', comodel_name='ttb.purchase.request', copy=False)
    pr_count = fields.Integer('Số lượng PR đã tạo', compute='_compute_pr_count')
    def _compute_pr_count(self):
        for rec in self:
            rec.pr_count = len(rec.pr_ids)

    def compute_line_count(self):
        for rec in self:
            self.line_count = self.env['auto.purchase.request.line'].search_count([('auto_id', '=', rec.id)])
            self.selected_line_count = self.env['auto.purchase.request.line'].search_count([('auto_id', '=', rec.id), ('is_select', '=', True)])

    def action_cap_nhat_ton(self):
        date_order = self.end_date or fields.Date.today()
        self.env['hang.ton.kho'].cap_nhat_ton(date_order)

    def action_auto_quantity(self):
        date_order = self.end_date or fields.Date.today()
        sngay = date_order.strftime("%y%m%d")

        domain_mch = ''
        if self.mch_ids:
            mch_ids = self.env['product.category'].search([('id', 'child_of', self.mch_ids.ids)])
            domain_mch = 'AND pc.id in %s' % str(mch_ids.ids).replace(']', ')').replace('[', '(')
        domain_partner = ''
        if self.partner_ids:
            domain_partner = 'AND rp.id in %s' % str(self.partner_ids.ids).replace('[', '(').replace(']', ')')

        start_date = date_order - timedelta(days=self.check_day)
        domain_start_date = " AND po.date_order >= '%s'" % start_date.strftime('%Y-%m-%d')
        domain_end_date = " AND po.date_order <= '%s'" % date_order.strftime('%Y-%m-%d')

        domain_warehouse = ''
        if self.warehouse_ids:
            domain_warehouse = ' AND sw.id in %s' % str(self.warehouse_ids.ids).replace('[', '(').replace(']', ')')
        domain_product = ''
        if self.product_ids:
            domain_product = ' AND pol.product_id in %s' % str(self.product_ids.ids).replace('[', '(').replace(']', ')')

        query = f"""
            delete from auto_purchase_request_line where auto_id = {self.id};

            insert into auto_purchase_request_line (
                auto_id, product_id, warehouse_id, partner_id, qty_stock, qty_sale, qty_pr, qty_po, 
                
                lead_time, stock_day, check_day,

                qty_sale_series, qty_avg, qty_std
            )

            SELECT
                {self.id} auto_id,
                pp.id product_id,
                sw.id warehouse_id,
                {'rp.id' if self.partner_ids else 'NULL'} partner_id,
                {'GREATEST(coalesce(htk.sl_ton, 0), 0)' if self.fix_stock else 'coalesce(htk.sl_ton, 0)'},
                coalesce(data_sale.so_luong_ban, 0),
                coalesce(data_pr.qty_pr, 0),
                coalesce(data_po.qty_po, 0),

                {self.lead_time}, {self.stock_day}, {self.check_day},


                data_sale.qty_sale_series,
                coalesce(data_sale.qty_avg, 0),
                coalesce(data_sale.qty_std, 0)
            FROM
                -- Số lượng bán
                (
                    SELECT 
                        id_kho_augges,
                        product_id,
                        sum(qty_by_day) so_luong_ban,

                        STRING_AGG(qty_by_day::text, ',' ORDER BY sngay) AS qty_sale_series,

                        sum(qty_by_day) / {self.check_day} as qty_avg,
                        stddev_samp(qty_by_day) as qty_std

                    FROM (

                        SELECT
                            id_kho_augges,
                            product_id,
                            po.date_order::date as sngay,
                            SUM(pol.qty) qty_by_day
                        FROM
                            pos_order_line pol
                            JOIN pos_order po ON po.id = pol.order_id
                        WHERE 1 = 1
                            {domain_start_date}
                            {domain_end_date}
                            {domain_product}
                        GROUP BY
                            id_kho_augges,
                            product_id,
                            po.date_order::date
                    ) daily_sales

                    GROUP BY
                        id_kho_augges,
                        product_id
                ) data_sale

                left join stock_warehouse sw on sw.id_augges = data_sale.id_kho_augges
                LEFT JOIN product_product pp ON pp.id = data_sale.product_id
                LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
                {'LEFT JOIN product_supplierinfo psi ON psi.product_id = pp.id OR psi.product_tmpl_id = pp.product_tmpl_id left join res_partner rp on rp.id = psi.partner_id' if self.partner_ids else ''}
                LEFT JOIN product_category pc ON pc.id = pt.categ_id

                -- Số lượng tồn kho
                left join hang_ton_kho htk on htk.id_kho = data_sale.id_kho_augges
                    and htk.sngay = '{sngay}'
                    and htk.id_hang = pt.augges_id
                    and htk.id_kho = data_sale.id_kho_augges

                -- Số lượng đang có trong Đề nghị đặt hàng (Chưa tạo đơn mua hàng)
                left join (
                    SELECT
                        product_id,
                        SUM(demand_qty) qty_pr
                    FROM
                        ttb_purchase_request_line prl
                        JOIN ttb_purchase_request pr ON pr.id = prl.request_id
                    WHERE
                        1=1
                        AND prl.product_id IS NOT NULL
                        AND pr.state IN ('new', 'sent', 'approved')
                    GROUP BY
                        product_id
                ) data_pr on data_pr.product_id = pp.id

                -- Số lượng đang cho trong Đơn mua hàng (chưa nhận hàng)
                left join (
                    SELECT
                        pol.product_id,
                        SUM(
                            pol.product_qty - pol.qty_received
                        ) qty_po
                    FROM
                        purchase_order_line pol
                        JOIN purchase_order po ON po.id = pol.order_id
                    GROUP BY
                        pol.product_id
                ) data_po on data_po.product_id = pp.id
            WHERE 1 = 1
                {domain_mch}
                {domain_partner}
                {domain_warehouse}
            ;

            UPDATE auto_purchase_request_line set 
                qty_ss = ceil(1.644853627 * qty_std * sqrt(lead_time)),
                qty_reorder = ceil(1.0 * lead_time * qty_avg + ceil(1.644853627 * qty_std * sqrt(lead_time))),
                qty_auto = case 
                    when qty_stock <= lead_time * qty_avg + ceil(1.644853627 * qty_std * sqrt(lead_time)) 
                        then ceil(qty_avg * stock_day - qty_stock)
                    else 0
                end,
                qty_final = GREATEST(
                    case 
                        when qty_stock <= lead_time * qty_avg + ceil(1.644853627 * qty_std * sqrt(lead_time)) 
                            then ceil(qty_avg * stock_day - qty_stock)
                        else 0
                    end
                    - qty_pr - qty_po
                , 0)
            WHERE auto_id = {self.id}
            ;

        """
        # print(query)
        self.env.cr.execute(query)

    def open_auto_detail(self):
        action = self.env["ir.actions.actions"]._for_xml_id("ttb_purchase.auto_purchase_request_line_action")
        action['context'] = {'create': 0, 'search_default_groupby_warehouse_id': 1, 'search_default_has_qty_final': 1}
        action['domain'] = [('auto_id', '=', self.id)]
        return action

    def open_auto_detail_selected(self):
        action = self.env["ir.actions.actions"]._for_xml_id("ttb_purchase.auto_purchase_request_line_action")
        action['context'] = {'create': 0, 'search_default_groupby_warehouse_id': 1, 'search_default_has_qty_final': 1}
        action['domain'] = [('auto_id', '=', self.id), ('is_select', '=', True)]
        return action

    def open_pr_created(self):
        action = self.env["ir.actions.actions"]._for_xml_id("ttb_purchase.purchase_request_action")
        action['context'] = {'create': 0}
        action['domain'] = [('id', 'in', self.pr_ids.ids)]
        return action

    def action_create_purchase_request(self):        
        # if self.state != 'selected':
        #     return

        auto_line_ids = self.env['auto.purchase.request.line'].search([
            ('pr_line_id', '=', False),
            ('is_select', '=', True),
            ('is_pr', '=', False),
        ])
        
        line_ids_by_partner = {}
        for line in auto_line_ids:
            warehouse_id = line.warehouse_id.id
            if warehouse_id not in line_ids_by_partner: 
                line_ids_by_partner[warehouse_id] = line
            else:
                line_ids_by_partner[warehouse_id] |= line

        pr_ids = []
        for warehouse_id in line_ids_by_partner:
            line_ids = []
            for line in line_ids_by_partner[warehouse_id]:
                line_ids += [(0, 0, {
                    'product_id': line.product_id.id,
                    'demand_qty': line.qty_final,
                    'partner_id': line.partner_id.id,
                })]

            vals = {
                'description': 'Đặt hàng tự động',
                'branch_id': line.warehouse_id.ttb_branch_id.id,
                'company_id': self.company_id.id,
                'line_ids': line_ids,
            }
            pr_ids += [(0, 0, vals)]
        if pr_ids:
            self.write({'pr_ids': pr_ids})
        auto_line_ids.is_pr = True

    def open_auto_stock(self):
        action = self.env["ir.actions.actions"]._for_xml_id("ttb_purchase.auto_hang_ton_kho_action")
        action['context'] = {'create': 0}
        action['domain'] = [('sngay', '=', self.end_date.strftime("%y%m%d"))]
        return action


class AutoPurchaseRequestLine(models.Model):
    _name = 'auto.purchase.request.line'
    _description = 'Chi tiết tự động đặt hàng'
    _rec_name = 'product_id'

    auto_id = fields.Many2one('auto.purchase.request')
    product_id = fields.Many2one('product.product')
    warehouse_id = fields.Many2one('stock.warehouse')
    partner_id = fields.Many2one('res.partner')

    qty_auto = fields.Float('SL gợi ý')
    qty_pr = fields.Float('SL PR')
    qty_po = fields.Float('SL PO')
    qty_final = fields.Float('SL đặt', help="SL gợi ý trừ đi SL đã ở PR, PO")

    qty_sale = fields.Float('SL bán')
    qty_stock = fields.Float('SL tồn')
    qty_sale_series = fields.Char('Chuỗi SL bán')
    qty_avg = fields.Float('SL bán trung bình')
    qty_std = fields.Float('SL độ lệch chuẩn')
    qty_ss = fields.Float('SL Safety stock')

    qty_reorder = fields.Float('Reoder point')

    lead_time = fields.Integer('Lead time (ngày)', default=3)
    stock_day = fields.Integer('Kỳ vọng đáp ứng (ngày)', default=7, required=True)
    check_day = fields.Integer('Thời gian lấy mẫu (ngày)', default=7, required=True)


    is_select = fields.Boolean('Chọn')
    is_pr = fields.Boolean('Đã tạo PR')

    pr_line_id = fields.Many2one('ttb.purchase.request.line')

    def action_select_line(self):
        self.is_select = True

    def action_unselect_line(self):
        self.is_select = False
