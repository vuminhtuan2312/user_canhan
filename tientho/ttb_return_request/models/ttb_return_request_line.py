from odoo import models, fields, api
import pandas as pd

class TtbReturnRequestLine(models.Model):
    _name = 'ttb.return.request.line'
    _description = 'Chi tiết đề nghị trả hàng'

    request_id = fields.Many2one('ttb.return.request', string='Phiếu đề nghị', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Sản phẩm', required=True)
    categ_id_level_1 = fields.Many2one(comodel_name='product.category',string="MCH1",related='product_id.categ_id_level_1',store=True)
    default_code = fields.Char(string='Mã sản phẩm', compute='_compute_default_code')
    quantity = fields.Float(string='SL trả KNH up')
    stock_system = fields.Float(string='SL tồn hệ thống')
    quantity_hold = fields.Float(string='SL giữ KNH up')
    unit_price = fields.Float(string='Đơn giá trả')
    qty_picked = fields.Float(string='SL nhặt', copy= False)
    qty_fail = fields.Float(string='SL không đạt', copy= False)
    qty_vp_received = fields.Float(string='SL VP nhận', copy= False)
    qty_return_supplier = fields.Float(
        string='SL trả NCC',
        compute='_compute_qty_return_supplier',
        store=True,
    )
    qty_supplier_received = fields.Float(
        string='SL NCC nhận',
        compute='_compute_qty_supplier_received',
        store=True, copy= False
    )
    qty_supplier_return = fields.Float(string='SL NCC trả')
    state = fields.Selection(string='Trạng thái', related='request_id.state')
    amount = fields.Float(string='Thành tiền', compute='_compute_amount')
    confirm_vendor_price  = fields.Float(string='Giá NCC xác nhận', copy=True)

    ttb_taxes_id = fields.Many2many('account.tax', string='Thuế', context={'active_test': False})
    price_tax = fields.Float(string='Tiền thuế', compute='_compute_tax_and_discout_amount')
    discount = fields.Float(string='% CK', default=0.0)
    ttb_discount_amount = fields.Float(string='CK tiền', compute='_compute_tax_and_discout_amount')
    vendor_product_name = fields.Text(string='Tên sản phẩm NCC',compute='_compute_vendor_product_name',
                                      inverse='_inverse_vendor_product_name', store=True, readonly=False)
    uom_id = fields.Many2one(string="Đơn vị tính", comodel_name='uom.uom', related='product_id.uom_id')
    po_id = fields.Many2one('purchase.order', string='Đơn mua liên kết',)
    date_approve_po = fields.Datetime(string='Ngày duyệt đơn mua liên kết', related='po_id.date_approve')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id and not self.uom_id:
            self.uom_id = self.product_id.uom_id

    def _prepare_base_line_for_taxes_computation(self):
        self.ensure_one()
        return self.env['account.tax']._prepare_base_line_for_taxes_computation(
            self,
            tax_ids=self.ttb_taxes_id,
            quantity=self.quantity if self.request_id.state in ('draft', 'pending') else self.qty_supplier_received ,
            price_unit=self.confirm_vendor_price,
            currency_id=self.env.company.currency_id,
        )

    @api.depends('qty_vp_received')
    def _compute_qty_return_supplier(self):
        for rec in self:
            rec.qty_return_supplier = rec.qty_vp_received

    @api.depends('qty_return_supplier')
    def _compute_qty_supplier_received(self):
        for rec in self:
            rec.qty_supplier_received = rec.qty_return_supplier
    @api.depends('product_id')
    def _compute_default_code(self):
        for rec in self:
            rec.default_code = rec.product_id.barcode or rec.product_id.default_code

    def _compute_return_unit_price(self):
        PurchaseLine = self.env['purchase.order.line']

        last_po_line = PurchaseLine.search(
            [
                ('product_id', '=', self.product_id.id),
                ('order_id.state', 'in', ['purchase', 'done']),
            ],
            order='create_date desc',
            limit=1
        )
        if last_po_line:
            base_price = last_po_line.price_unit
            return base_price, last_po_line.order_id

        base_price = self.product_id.product_tmpl_id.last_price or 0.0
        return base_price, None

    def _compute_tax_and_discount(self):
        last_po_line = self.env['purchase.order.line'].search(
            [
                ('product_id', '=', self.product_id.id), ('date_approve', '!=', False),
            ],
            order='date_approve desc',
            limit=1
        )
        if last_po_line:
            taxes = last_po_line.taxes_id.ids
            discount_percent = last_po_line.discount or 0.0
            return taxes, discount_percent

        taxes = self.product_id.product_tmpl_id.supplier_taxes_id.ids
        discount_percent = 0.0
        return taxes, discount_percent


    @api.onchange('product_id')
    def _onchange_unit_price(self):
        if self.product_id:
           self.unit_price, self.po_id = self._compute_return_unit_price()
           self.ttb_taxes_id, self.discount = self._compute_tax_and_discount()

    @api.depends('product_id', 'request_id.supplier_id')
    def _compute_vendor_product_name(self):
        for rec in self:
            rec.vendor_product_name = False

            if not rec.product_id:
                continue

            partner = rec.request_id.supplier_id
            product = rec.product_id

            if partner:
                supplierinfo = self.env['product.supplierinfo'].search([
                    ('partner_id', '=', partner.id),
                    ('product_tmpl_id', '=', product.product_tmpl_id.id),
                ], limit=1)
                if supplierinfo and supplierinfo.product_name:
                    rec.vendor_product_name = supplierinfo.product_name
                    continue
            rec.vendor_product_name = product.display_name

    def _inverse_vendor_product_name(self):
        for rec in self:
            if not rec.product_id or not rec.request_id.supplier_id:
                continue

            supplierinfo = self.env['product.supplierinfo'].search([
                ('partner_id', '=', rec.request_id.supplier_id.id),
                ('product_tmpl_id', '=', rec.product_id.product_tmpl_id.id),
            ], limit=1)

            if supplierinfo:
                supplierinfo.product_name = rec.vendor_product_name

    @api.model_create_multi
    def create(self, vals_list):
        if self._context.get('import_mode') == 'update_price':
            request_id = self._context.get('default_request_id')
            if not request_id:
                return self.env['ttb.return.request.line']

            request = self.env['ttb.return.request'].browse(request_id)
            existing_lines = request.line_ids

            fake_records = self.env['ttb.return.request.line']

            for vals in vals_list:
                product_id = vals.get('product_id')
                if not product_id:
                    continue

                product = self.env['product.product'].browse(product_id)
                if not product.exists():
                    continue

                line = existing_lines.filtered(lambda l: l.product_id.id == product.id)
                if not line:
                    continue

                update_vals = {}
                if vals.get('vendor_product_name') is not None:
                    update_vals['vendor_product_name'] = vals['vendor_product_name']

                if vals.get('confirm_vendor_price') is not None:
                    update_vals['confirm_vendor_price'] = vals['confirm_vendor_price']

                if vals.get('quantity') is not None:
                    update_vals['quantity'] = vals['quantity']

                if vals.get('ttb_taxes_id') is not None:
                    update_vals['ttb_taxes_id'] = vals.get('ttb_taxes_id')

                if vals.get('discount') is not None:
                    update_vals['discount'] = vals.get('discount')

                if update_vals:
                    line.write(update_vals)

                fake_records |= line

            return fake_records

        records = super().create(vals_list)

        stock_cache = {}
        for rec in records:
            if rec.product_id and not rec.unit_price:
                rec.unit_price, rec.po_id = rec._compute_return_unit_price()

            if  rec.product_id and (not rec.ttb_taxes_id or rec.discount):
                ttb_taxes_id, discount = rec._compute_tax_and_discount()
                if not rec.ttb_taxes_id:
                    rec.ttb_taxes_id = ttb_taxes_id
                if not rec.discount:
                    rec.discount = discount

            if rec.unit_price is not None and not rec.confirm_vendor_price:
                rec.confirm_vendor_price = rec.unit_price

            if not rec.vendor_product_name:
                rec.vendor_product_name = rec._get_vendor_product_name()

            request = rec.request_id
            if not request or not rec.product_id:
                continue

            id_kho = request.stock_warehouse_id.id_augges
            id_hang = rec.product_id.augges_id

            if not id_kho or not id_hang:
                continue

            key = (id_kho, id_hang)

            if key not in stock_cache:
                try:
                    stock_cache[key] = rec.get_augges_quantity(id_kho, id_hang)
                except Exception:
                    stock_cache[key] = 0.0

            rec.stock_system = stock_cache[key]

        return records

    @api.depends('confirm_vendor_price', 'qty_supplier_received', 'ttb_discount_amount', 'price_tax')
    def _compute_amount(self):
        for rec in self:
            if rec.request_id.state not in ('draft', 'pending'):
                rec.amount = rec.qty_supplier_received * (rec.confirm_vendor_price - rec.ttb_discount_amount) + rec.price_tax
            else:
                rec.amount = rec.quantity * (rec.confirm_vendor_price - rec.ttb_discount_amount) + rec.price_tax

    def _get_vendor_product_name(self):
        self.ensure_one()

        partner = self.request_id.supplier_id
        product = self.product_id

        if not partner or not product:
            return product.display_name if product else False

        supplierinfo = self.env['product.supplierinfo'].search([
            ('partner_id', '=', partner.id),
            ('product_tmpl_id', '=', product.product_tmpl_id.id)
        ], limit=1)

        if supplierinfo and supplierinfo.product_name:
            return supplierinfo.product_name

        return product.display_name

    @api.onchange('product_id')
    def _onchange_product_vendor_name(self):
        for rec in self:
            if rec.product_id:
                rec.vendor_product_name = rec._get_vendor_product_name()

    @api.depends('ttb_taxes_id', 'discount', 'confirm_vendor_price', 'qty_supplier_received')
    def _compute_tax_and_discout_amount(self):
        for line in self:
            base_line = line._prepare_base_line_for_taxes_computation()
            self.env['account.tax']._add_tax_details_in_base_line(base_line, self.env.company)
            price_subtotal = base_line['tax_details']['raw_total_excluded_currency']
            price_total = base_line['tax_details']['raw_total_included_currency']
            line.price_tax = price_total - price_subtotal
            if line.discount:
                line.ttb_discount_amount = (line.confirm_vendor_price * line.discount) / 100
            else:
                line.ttb_discount_amount = 0.0

    def get_augges_quantity(self, id_kho, id_hang):
        day = fields.Date.today()
        nam = day.strftime("%Y")
        thang = day.strftime("01")
        sngay = day.strftime("%y%m%d")
        dau_nam = "260101"

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
        WHERE HTK.Nam = {nam} AND HtK.ID_Dv = 0 AND Htk.Mm = {thang} AND Htk.ID_Kho = {id_kho} AND Htk.ID_Hang = {id_hang}
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
        WHERE SlNxM.Sngay >= '{dau_nam}' AND SlNxM.Sngay <= '{sngay}' AND SlNxM.ID_Dv = 0 AND SlNxD.ID_Kho = {id_kho}  AND SlNxD.ID_Hang = {id_hang}  
        GROUP BY SlNxM.ID_Kho, SlNxD.ID_Hang, DmH.Ma_Hang, DmH.Ma_Tong 

        UNION ALL 
        SELECT SlBlM.ID_Kho, SlBlD.ID_Hang, DmH.Ma_Hang, ISNULL(DmH.Ma_Tong,SPACE(25)) AS Ma_Tong, SUM(- SlBlD.So_Luong) AS Sl_Cky, 
        SUM(CASE WHEN SlBlD.SNgay >='{sngay}' THEN SlBlD.So_Luong ELSE CAST(0 AS money) END) AS So_Luong 
        FROM SlBlD 
        LEFT JOIN SlBlM ON SlBlD.ID      = SlBlM.ID 
        LEFT JOIN DmH   ON SlBlD.ID_Hang = DmH.ID 
        LEFT JOIN DmNh  ON DmH.ID_Nhom   = DmNh.ID 
        WHERE SlBlM.Sngay >= '{dau_nam}' AND SlBlM.Sngay <= '{sngay}' AND SlBlM.ID_Dv = 0 AND ISNULL(SlBlD.ID_Kho,SlBlM.ID_Kho) = {id_kho}  AND SlBlD.ID_Hang = {id_hang}  
        GROUP BY SlBlM.ID_Kho, SlBlD.ID_Hang, DmH.Ma_Hang, DmH.Ma_Tong 

        UNION ALL 
        SELECT SlDcD.ID_KhoX AS ID_Kho, SlDcD.ID_Hang, DmH.Ma_Hang, ISNULL(DmH.Ma_Tong,SPACE(25)) AS Ma_Tong, SUM(- SlDcD.So_Luong) AS Sl_Cky, 
        CAST(0 AS money) AS So_Luong 
        FROM SlDcD 
        LEFT JOIN SlDcM ON SlDcD.ID      = SlDcM.ID 
        LEFT JOIN DmKho ON SlDcD.ID_KhoX = DmKho.ID 
        LEFT JOIN DmH   ON SlDcD.ID_Hang = DmH.ID 
        LEFT JOIN DmNh  ON DmH.ID_Nhom   = DmNh.ID 
        WHERE SlDcM.Sngay >= '{dau_nam}' AND SlDcM.Sngay <= '{sngay}' AND SlDcM.ID_Dv = 0 AND SlDcD.ID_KhoX = {id_kho} AND SlDcD.ID_Hang = {id_hang} 
        GROUP BY SlDcD.ID_KhoX, SlDcD.ID_Hang, DmH.Ma_Hang, DmH.Ma_Tong 

        UNION ALL 
        SELECT SlDcD.ID_KhoN AS ID_Kho, SlDcD.ID_Hang, DmH.Ma_Hang, ISNULL(DmH.Ma_Tong,SPACE(25)) AS Ma_Tong, 
        SUM(SlDcD.So_Luong) AS Sl_Cky, CAST(0 AS money) AS So_Luong 
        FROM SlDcD 
        LEFT JOIN SlDcM ON SlDcD.ID      = SlDcM.ID 
        LEFT JOIN DmKho ON SlDcD.ID_KhoN = DmKho.ID 
        LEFT JOIN DmH   ON SlDcD.ID_Hang = DmH.ID 
        LEFT JOIN DmNh  ON DmH.ID_Nhom   = DmNh.ID 
        WHERE SlDcM.Sngay >= '{dau_nam}' AND SlDcM.Sngay <= '{sngay}' AND SlDcM.ID_Dv = 0 AND SlDcD.ID_KhoN = {id_kho} AND SlDcD.ID_Hang = {id_hang}
        GROUP BY SlDcD.ID_KhoN, SlDcD.ID_Hang, DmH.Ma_Hang, DmH.Ma_Tong 

        ) AS Dt_Hang 
        WHERE Sl_Cky<>0 OR So_Luong<>0 
        GROUP BY ID_Kho, ID_Hang, Ma_Hang, Ma_Tong 
        """
        conn = self.env['ttb.tools'].get_mssql_connection()
        df = pd.read_sql(query, conn)
        sl_ton = df['SL_Ton'].iloc[0] if not df.empty else 0.0
        if pd.isna(sl_ton):
            sl_ton = 0.0

        return sl_ton
