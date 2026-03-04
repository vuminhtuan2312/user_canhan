from odoo import api, fields, models, _, SUPERUSER_ID
from odoo import tools
from odoo.exceptions import UserError


class NimboxInvoiceLine(models.Model):
    _inherit = 'ttb.nimbox.invoice.line'
    _rec_name = 'buy_product_id'

    buy_product_id = fields.Many2one('product.sale.item', 'Sản phẩm đầu vào', index=True)
    out_line_ids = fields.One2many('ttb.inout.invoice.mapper', 'in_line_id', 'Các dòng hoá đơn bán ra')
    out_product_ids = fields.One2many('ttb.inout.product.mapper', 'in_line_id', 'Các sản phẩm bán ra')
    dongia_excluded_tax = fields.Float(string='Đơn giá trước thuế')
    thanhtien_exclude_tax = fields.Float('Thành tiền trước thuế', readonly=1)
    phanbo_thanh_tien_exclude_tax = fields.Float('Phân bổ thành tiền trước thuế', readonly=1)
    phanbo_tienthue = fields.Float('Phân bổ tiền thuế', readonly=1)
    soluong_used = fields.Float('Số lượng đã sử dụng', default=0)

    manual_import = fields.Boolean('Import thủ công', default=False)

    soluong_remain = fields.Float('Số lượng còn lại', compute='_compute_soluong_remain', store=True)
    @api.depends('soluong', 'soluong_used')
    def _compute_soluong_remain(self):
        for rec in self:
            rec.soluong_remain = rec.soluong - rec.soluong_used

    count_out_product = fields.Integer('Số sản phẩm ghép', help='Đánh dấu các dòng đầu vào bị ghép nhiều sản phẩm đầu ra', default=0)

    category_id_level_1 = fields.Many2one('product.category.training', 'MCH 1', index=True, related='buy_product_id.category_id_level_1', store=True, readonly=False, domain="[('category_level', '=', 1)]")
    category_id_level_2 = fields.Many2one('product.category.training', 'MCH 2', index=True, related='buy_product_id.category_id_level_2', store=True, readonly=False, domain="[('category_level', '=', 2)]")
    category_id_level_3 = fields.Many2one('product.category.training', 'MCH 3', index=True, related='buy_product_id.category_id_level_3', store=True, readonly=False, domain="[('category_level', '=', 3)]")
    category_id_level_4 = fields.Many2one('product.category.training', 'MCH 4', index=True, related='buy_product_id.category_id_level_4', store=True, readonly=False, domain="[('category_level', '=', 4)]")
    category_id_level_5 = fields.Many2one('product.category.training', 'MCH 5', index=True, related='buy_product_id.category_id_level_5', store=True, readonly=False, domain="[('category_level', '=', 5)]")

    donvi_rate = fields.Float('Đơn vị quy đổi', default=1)
    donvi_ban = fields.Char('Đơn vị bán')
    dongia_ban = fields.Float('Đơn giá bán')
    soluong_goc = fields.Float('Số lượng gốc', help='Số lượng gốc lấy từ hoá đơn thuế (nimbox)')

    invoice_date = fields.Date(string='Ngày hóa đơn', related='nimbox_invoice_id.ttb_vendor_invoice_date', store=True)
    ttb_branch_id = fields.Many2one(string='Cở sở', comodel_name='ttb.branch', related='nimbox_invoice_id.ttb_branch_id', store=True, index=True)
    in_branch_id = fields.Many2one(string='Cở sở được ghép', comodel_name='ttb.branch', related='nimbox_invoice_id.in_branch_id', store=True, index=True)
    price_unit = fields.Float('Giá nhập', related='buy_product_id.price', store=True, help='Đơn giá của sản phẩm đầu vào')
    phanbo_chietkhau = fields.Float('Phân bổ chiết khấu')

    # Một số trường phục vụ xử lý hoá đơn điều chỉnh
    im_hvtnmhang = fields.Char('Họ tên NMH (Import)')
    im_invoice_no = fields.Char(string='Số hóa đơn NCC (Import)', copy=False, required=True, tracking=True)
    im_invoice_code = fields.Char(string='Ký hiệu hóa đơn NCC (Import)', copy=False, required=True, tracking=True)
    
    def get_thuesuat_integer(self):
        thuesuat = (self.thuesuat or '').strip()
        if not thuesuat:
            thuesuat = self.nimbox_invoice_id.thuesuat or ''
        thuesuat = str(thuesuat).replace(' ', '').lower()
        thuesuat = {'0%': '0', '5%': '5', '8%': '8', '10%': '10', 'kct': 'KCT', 'kkknt': 'KKKNT'}.get(thuesuat,
                                                                                                      'KHAC')
        if thuesuat in ['KCT', 'KKKNT', 'KHAC']:
            thue = 0
        else:
            thue = int(thuesuat)
        return thue

    def reconcil_money_m3(self):
        for rec in self:
            if rec.soluong == 0 or not rec.out_product_ids: continue

            sum_tien_thue = sum_thanhtien_exclude_tax = sum_so_tien_chiet_khau = 0
            thue = rec.get_thuesuat_integer() / 100

            # Phân bổ hết số lượng vào dòng cuối nếu vẫn còn
            remain_quantity = rec.soluong - sum(rec.out_product_ids.mapped('quantity'))
            if remain_quantity > 0:
                rec.out_product_ids[-1].quantity += remain_quantity

            lines = rec.out_product_ids.sorted(key=lambda l: l.quantity)
            for line in lines[:-1]:
                rate = line.quantity / rec.soluong
                thanhtien_exclude_tax = round(rec.thanhtien_exclude_tax * rate)

                tien_thue = round(thanhtien_exclude_tax * thue)
                # so_tien_chiet_khau = round(rec.so_tien_chiet_khau * rate)

                sum_thanhtien_exclude_tax += thanhtien_exclude_tax
                sum_tien_thue += tien_thue
                # sum_so_tien_chiet_khau += so_tien_chiet_khau

                line.write({
                    'thanhtien_exclude_tax': thanhtien_exclude_tax,
                    'tien_thue': tien_thue,
                    # 'so_tien_chiet_khau': so_tien_chiet_khau,
                })

            line = lines[-1]
            thanhtien_exclude_tax = rec.thanhtien_exclude_tax - sum_thanhtien_exclude_tax
            tien_thue = (rec.thanhtien_exclude_tax * thue) - sum_tien_thue
            # so_tien_chiet_khau = rec.so_tien_chiet_khau - sum_so_tien_chiet_khau

            line.write({
                'thanhtien_exclude_tax': thanhtien_exclude_tax,
                'tien_thue': tien_thue,
                # 'so_tien_chiet_khau': so_tien_chiet_khau,
            })
