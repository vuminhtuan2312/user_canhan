from odoo import api, fields, models, _, SUPERUSER_ID


class InOutInvoiceMaper(models.Model):
    _name = 'ttb.inout.invoice.mapper'
    _description = 'Đối soát số lượng dòng hoá đơn đầu vào và đầu ra'

    in_line_id = fields.Many2one('ttb.nimbox.invoice.line', 'Dòng hoá đơn đầu vào', index=True, auto_join=True)
    in_product_id = fields.Many2one('product.sale.item', 'Sản phẩm đầu vào', related='in_line_id.buy_product_id')
    in_line_price = fields.Float('Đơn giá dòng đầu vào', related='in_line_id.dongia_excluded_tax')
    in_product_price = fields.Float('Đơn giá đầu vào', related='in_product_id.price')
    
    out_line_id = fields.Many2one('tax.output.invoice.line', 'Dòng hoá đơn đầu ra', index=True, auto_join=True)
    out_product_id = fields.Many2one('product.sale.item', 'Sản phẩm đầu ra', related='out_line_id.product_id')
    out_line_price = fields.Float('Đơn giá dòng đầu ra', related='out_line_id.price_unit')
    
    quantity = fields.Float('Số lượng')
    in_quantity = fields.Float('Số lượng dòng đầu vào', related='in_line_id.soluong')
    out_quantity = fields.Float('Số lượng dòng đầu ra', related='out_line_id.quantity')

    version = fields.Integer('Phiên bản')
    version_time = fields.Datetime('Thời điểm lưu version')
    active = fields.Boolean(default=True)
    diff_rate = fields.Float('Tỉ lệ tương hợp')

    buy_product_level = fields.Char(string='MCH tương hợp', related='out_line_id.buy_product_level', store=True)

    in_price_total = fields.Float('Thành tiền đầu vào', compute='compute_in_price_total', store=True)
    @api.depends('in_line_id', 'quantity')
    def compute_in_price_total(self):
        for rec in self:
            if rec.in_line_id.soluong != 0:
                rec.in_price_total = (rec.in_line_id.thanhtien_exclude_tax * rec.quantity) / rec.in_line_id.soluong
            else:
                rec.in_price_total = 0

class InOutInvoiceMaperHistory(models.Model):
    _name = 'ttb.inout.invoice.mapper.history'
    _inherit = 'ttb.inout.invoice.mapper'
    _description = 'Đối soát số lượng dòng hoá đơn đầu vào và đầu ra history'


class InOutProductMaper(models.Model):
    _name = 'ttb.inout.product.mapper'
    _description = 'Map hoá đơn đầu vào với các sản phẩm đầu ra'
    _order = 'ttb_vendor_invoice_date asc, nimbox_invoice_id asc, in_line_id asc'

    version = fields.Integer('Phiên bản')
    version_time = fields.Datetime('Thời điểm lưu version')
    active = fields.Boolean(default=True)

    in_line_id = fields.Many2one('ttb.nimbox.invoice.line', 'Dòng hoá đơn đầu vào', index=True, auto_join=True)
    nimbox_invoice_id = fields.Many2one('ttb.nimbox.invoice', string='Hóa đơn Nibot', related='in_line_id.nimbox_invoice_id', store=True, auto_join=True)
    ttb_vendor_invoice_date = fields.Date(string='Ngày hóa đơn NCC', related="nimbox_invoice_id.ttb_vendor_invoice_date", store=True)
    in_line_id_2 = fields.Many2one('ttb.nimbox.invoice.line', 'Dòng hoá đơn đầu vào 2', related='in_line_id', help='Khai báo trường ảo để export')
    in_line_id_3 = fields.Many2one('ttb.nimbox.invoice.line', 'Dòng hoá đơn đầu vào 3', related='in_line_id', help='Khai báo trường ảo để export')
    out_product_id = fields.Many2one('product.sale.item', 'Sản phẩm đầu ra', index=True, auto_join=True)
    quantity = fields.Float('Số lượng')

    thanhtien = fields.Float(string='Thành tiền (trước thuế)')
    so_tien_chiet_khau = fields.Float(string='Số tiền chiết khấu')
    tien_thue = fields.Float('Tiền thuế')
    thanhtien_exclude_tax = fields.Float('Thành tiền trước thuế')

    # A: Hiển thị trên sổ
    column_a = fields.Char('Hiển thị trên sổ', default='2')
    # B: Hình thức mua hàng
    column_b = fields.Char('Hình thức mua hàng', default='0')
    # C: Phương thức thanh toán
    column_c = fields.Char('Phương thức thanh toán', default='0')
    # D: Nhận kèm hóa đơn
    column_d = fields.Char('Nhận kèm hóa đơn', default='1')
    # E: Ngày hạch toán (*)
    column_e = fields.Char('Ngày hạch toán (*)')
    # F: Ngày chứng từ (*)
    column_f = fields.Char('Ngày chứng từ (*)')
    # G: Số phiếu nhập (*)
    column_g = fields.Char('Số phiếu nhập (*)', compute='compute_column_g')
    def compute_column_g(self):
        prefix = self.env['ir.config_parameter'].sudo().get_param('ttb_invoice_custom.misa_in_invoice_prefix', default='tth_')
        for rec in self:
            inv = rec.in_line_id.nimbox_invoice_id
            ttb_branch_id = inv.in_branch_id or inv.ttb_branch_id
            is_active = 1 if inv.total_soluong_used > 0 else 0
            rec.column_g = f'{prefix}{is_active}_{ttb_branch_id.id}_{inv.id}'
    # H: Số chứng từ thanh toán
    column_h = fields.Char('Số chứng từ thanh toán')
    # I: Mã nhà cung cấp
    column_i = fields.Char('Mã nhà cung cấp')
    # J: Tên nhà cung cấp
    column_j = fields.Char('Tên nhà cung cấp')
    # K: Người giao hàng
    column_k = fields.Char('Người giao hàng')
    # L: Diễn giải
    column_l = fields.Char('Diễn giải', compute='compute_column_l')
    def compute_column_l(self):
        for rec in self:
            ttb_branch_id = rec.in_line_id.nimbox_invoice_id.in_branch_id or rec.in_line_id.nimbox_invoice_id.ttb_branch_id
            inv = rec.in_line_id.nimbox_invoice_id
            is_change = 1 if inv.manual_import else 0
            is_ho = 1 if inv.in_branch_id else 0
            dien_giai = f'b_{ttb_branch_id.id}_n_{inv.ttb_vendor_invoice_code}_t_{inv.ttb_vendor_invoice_no}_v_{inv.ttb_vendor_vat}_ty_{inv.total_soluong_used}_i_{is_change}_h{is_ho}_e'

            rec.column_l = dien_giai
    
    # M: NV mua hàng
    column_m = fields.Char('NV mua hàng')
    # N: Loại tiền
    column_n = fields.Char('Loại tiền')
    # O: Tỷ giá
    column_o = fields.Char('Tỷ giá')
    # P: Mã hàng (*)
    column_p = fields.Char('Mã hàng (*)')
    # Q: Tên hàng
    column_q = fields.Char('Tên hàng')
    # R: Kho
    column_r = fields.Char('Kho')
    ttb_branch_id = fields.Many2one(string='Cở sở', comodel_name='ttb.branch', compute='compute_ttb_branch_id')
    @api.depends('in_line_id')
    def compute_ttb_branch_id(self):
        for rec in self:
            rec.ttb_branch_id = rec.in_line_id.nimbox_invoice_id.in_branch_id or rec.in_line_id.nimbox_invoice_id.ttb_branch_id

    # S: Hàng hóa giữ hộ/bán hộ
    column_s = fields.Char('Hàng hóa giữ hộ/bán hộ')
    # T: TK kho (*)
    column_t = fields.Char('TK kho (*)', default='1561')
    # U: TK công nợ/TK tiền (*)
    column_u = fields.Char('TK công nợ/TK tiền (*)', default='331')
    # V: Đối tượng
    column_v = fields.Char('Đối tượng')
    # W: ĐVT
    column_w = fields.Char('ĐVT')
    # X: Số lượng
    column_x = fields.Char('Số lượng')
    # Y: Đơn giá
    column_y = fields.Char('Đơn giá')
    # Z: Thành tiền
    column_z = fields.Char('Thành tiền')

    # --- 2. Từ cột AA đến AZ (column_aa đến column_az) ---

    # AA: Thành tiền quy đổi
    column_aa = fields.Char('Thành tiền quy đổi')
    # AB: Tỷ lệ CK
    column_ab = fields.Char('Tỷ lệ CK')
    # AC: Tiền chiết khấu
    column_ac = fields.Char('Tiền chiết khấu')
    # AD: Tiền chiết khấu quy đổi
    column_ad = fields.Char('Tiền chiết khấu quy đổi')
    # AE: Phí hàng về kho/Chi phí mua hàng
    column_ae = fields.Char('Phí hàng về kho/Chi phí mua hàng')
    # AF: % thuế GTGT
    column_af = fields.Char('% thuế GTGT')
    thuesuat = fields.Char(string='Thuế suất GTGT', compute='compute_thuesuat')
    def compute_thuesuat(self):
        for rec in self:
            thuesuat = (rec.in_line_id.thuesuat or '').strip()
            if not thuesuat:
                thuesuat = rec.in_line_id.nimbox_invoice_id.thuesuat or ''
            thuesuat = str(thuesuat).replace(' ', '').lower()

            if 'khac' in thuesuat:
                rec.thuesuat = '8'
            else:
                rec.thuesuat = {
                    '0%': '0',
                    '0': '0',
                    '5%': '5',
                    '5': '5',
                    '8%': '8',
                    '8': '8',
                    '10%': '10',
                    '10': '10',
                    'kct': 'KCT',
                    'kkknt': 'KKKNT',
                    'khac:08.00%': '8',
                    'khac': '8',
                }.get(thuesuat, '0')

    # AG: Tỷ lệ tính thuế (Thuế suất KHAC)
    column_ag = fields.Char('Tỷ lệ tính thuế (Thuế suất KHAC)')
    # AH: Tiền thuế GTGT
    column_ah = fields.Char('Tiền thuế GTGT')
    # AI: Tiền thuế GTGT quy đổi
    column_ai = fields.Char('Tiền thuế GTGT quy đổi')
    # AJ: TKĐƯ thuế GTGT
    column_aj = fields.Char('TKĐƯ thuế GTGT')
    # AK: TK thuế GTGT
    column_ak = fields.Char('TK thuế GTGT', default='1331')
    # AL: Ngày hóa đơn
    column_al = fields.Char('Ngày hóa đơn')
    # AM: Số hóa đơn
    column_am = fields.Char('Số hóa đơn')
    # AN: Nhóm HHDV mua vào
    column_an = fields.Char('Nhóm HHDV mua vào', default='1')
    # AO: Mã NCC
    column_ao = fields.Char('Mã NCC')
    # AP: Tên NCC
    column_ap = fields.Char('Tên NCC')
    # AQ: Mã số thuế NCC
    column_aq = fields.Char('Mã số thuế NCC')
    # AR: Địa chỉ NCC
    column_ar = fields.Char('Địa chỉ NCC')
    # AS: Phí trước hải quan
    column_as = fields.Char('Phí trước hải quan')
    # AT: Giá tính thuế NK
    column_at = fields.Char('Giá tính thuế NK')
    # AU: % thuế NK
    column_au = fields.Char('% thuế NK')
    # AV: Tiền thuế NK
    column_av = fields.Char('Tiền thuế NK')
    # AW: TK thuế NK
    column_aw = fields.Char('TK thuế NK')
    # AX: % thuế TTĐB
    column_ax = fields.Char('% thuế TTĐB')
    # AY: Tiền thuế TTĐB
    column_ay = fields.Char('Tiền thuế TTĐB')
    # AZ: TK thuế TTĐB (Cột số 52)
    column_az = fields.Char('TK thuế TTĐB')

    def unlink(self):
        for rec in self:
            out_lines = self.env['ttb.inout.invoice.mapper'].search([
                ('in_line_id', '=', rec.in_line_id.id),
                ('out_line_id.product_id.misa_product_id', '=', rec.out_product_id.id),
            ])

            for line in out_lines:
                self.env['tax.manual.choice'].create({
                    'choice_type': 'delete',
                    'in_line_id': rec.in_line_id.id,
                    'out_line_id': line.out_line_id.id,
                })

                rec.in_line_id.write({
                    'soluong_used': rec.in_line_id.soluong_used + line.quantity,
                })
                line.unlink()

        return super(InOutProductMaper, self).unlink()

class InOutProductMaperMisa(models.Model):
    _name = 'ttb.inout.product.mapper.history'
    _inherit = 'ttb.inout.product.mapper'
    _description = 'Map hoá đơn đầu vào với các sản phẩm đầu ra history'

class InProductOutProductMapper(models.Model):
    _name = 'ttb.inproduct.outproduct.mapper'
    _description = 'Map sản phẩm đầu vào với sản phẩm đầu ra'

    in_product_id = fields.Many2one('product.sale.item', 'Sản phẩm đầu vào', index=True, auto_join=True)
    out_product_id = fields.Many2one('product.sale.item', 'Sản phẩm đầu ra', index=True, auto_join=True)
    quantity = fields.Float('Số lượng')
