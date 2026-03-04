import base64
import xml.dom.minidom
from datetime import date, timedelta, datetime

from odoo import api, fields, models, _, SUPERUSER_ID
from odoo import tools
from odoo.exceptions import UserError
from odoo.addons.ttb_tools.ai.product_similar_matcher import get_candidate
from odoo.addons.ttb_tools.ai.product_similar_matcher import get_vectors_json as convert_string_to_vectors

import logging
_logger = logging.getLogger(__name__)

class TtbNimboxInvoice(models.Model):
    _name = 'ttb.nimbox.invoice'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Hóa đơn hệ thống Nimbox'
    _rec_name = 'ten_hien_thi'

    ttb_vendor_invoice_no = fields.Char(string='Số hóa đơn NCC', copy=False, required=True, tracking=True)
    ttb_vendor_invoice_code = fields.Char(string='Ký hiệu hóa đơn NCC', copy=False, required=True, tracking=True)
    ttb_price_unit = fields.Float(string='Số tiền nimbox', copy=False, tracking=True)
    ttb_vendor_name = fields.Char(string='Tên NCC', copy=False, tracking=True)
    ttb_vendor_vat = fields.Char(string='MST NCC', copy=False, required=True, tracking=True)
    ttb_vendor_invoice_date = fields.Date(string='Ngày hóa đơn NCC', copy=False, tracking=True)
    list_product = fields.Char(string='Danh sách sản phẩm nimbox', copy=False)
    count_product = fields.Char(string='Số lượng sản phẩm nimbox', copy=False)
    state = fields.Selection(string='Trạng thái', selection=[('not_matching', 'Không hợp lệ'), ('many_po', 'Có nhiều PO'), ('amout_vat', 'Trùng tiền và MST'), ('not_matching_amout', 'Không khớp số tiền'),('waiting', 'Chờ xác nhận'),('done', 'Đã khớp')], default='not_matching', readonly=True, copy=False, tracking=True)
    po_ids = fields.Many2many(comodel_name='purchase.order', string='Đơn mua hàng', relation='ttb_nimbox_invoice_purchase_rel', copy=False, tracking=True)
    domain_po_ids = fields.Binary(string='Lọc PO', compute='_compute_po_ids')
    picking_ids = fields.One2many(string='Điều chuyển', copy=False, comodel_name='stock.picking', inverse_name='ttb_nimbox_invoice_id')
    po_map_ids = fields.Many2many(comodel_name='purchase.order', relation='ttb_nimbox_invoice_po_ref', column1="ttb_nimbox_id", column2="po_id", string='Đơn PO cùng số tiền', compute='_compute_po_map_ids', precompute=False)
    po_map_vat_ids = fields.Many2many(comodel_name='purchase.order', relation='ttb_nimbox_invoice_po_vat_ref', column1="ttb_nimbox_id", column2="po_id", string='Đơn PO cùng mã số thuế', compute='_compute_po_map_vat_ids', precompute=False)
    # Todo: Store=True
    ttb_total_price_unit = fields.Float(string='Tổng tiền đơn hàng', compute='_compute_price_unit')
    count_ttb_product = fields.Integer(string='Tổng số lượng sản phẩm đơn hàng', compute='_compute_ttb_product_ids', store=True)
    ttb_product_ids = fields.Many2many(comodel_name='product.product', string='Sản phẩm đơn hàng', compute='_compute_ttb_product_ids', store=True)
    ttb_branch_id = fields.Many2one(string='Cở sở', comodel_name='ttb.branch', required=False)
    active = fields.Boolean(default=True)
    delivery_count = fields.Integer(compute='_compute_delivery_count', string='Số điều chuyển')

    id_nibot = fields.Char('UUID Nibot', tracking=True)
    _sql_constraints = [
        ('id_nibot_unique', 'UNIQUE(id_nibot)', 'ID Nibot (UUID) đã tồn tại trong hệ thống!'),
    ]

    tien_c_thue = fields.Float('Tiền C.Thuế', tracking=True)
    tien_thue = fields.Float('Tiền Thuế', tracking=True)
    thuesuat = fields.Char(string='Thuế suất GTGT')
    tien_ck_tm = fields.Float('Tiền CK.TM', tracking=True)
    tien_phi = fields.Float('Tiền Phí', tracking=True)
    trang_thai_hd = fields.Char('Trạng thái HĐ', tracking=True)
    pdf_file = fields.Binary(string="File PDF Hóa đơn", attachment=True)
    status_mapping = fields.Boolean(string='Trạng thái khớp PO', default=False, tracking=True,
                                    help="phiếu mới tạo sẽ có trạng thái False, khi đồng bộ với phiếu nhận hàng sẽ chuyển thành True.")
    nimbox_line_ids = fields.One2many('ttb.nimbox.invoice.line','nimbox_invoice_id', string='Chi tiết hóa đơn', copy=False, tracking=True)
    hvtnmhang = fields.Char('Họ tên NMH')
    dia_chi_nmhang = fields.Char('Địa chỉ NMH')
    ma_nmhang = fields.Char('Mã NMH')
    xml_content = fields.Text('XML')
    # Trường compute dùng để hiển thị đã định dạng
    formatted_xml_display = fields.Text(
        string="XML Hiển thị đẹp",
        compute='_compute_formatted_xml_display',
        store=False # Không cần lưu database, chỉ để hiển thị
    )

    @api.depends('xml_content')
    def _compute_formatted_xml_display(self):
        for record in self:
            if not record.xml_content:
                record.formatted_xml_display = ""
                continue
            try:
                # 1. Parse chuỗi XML gốc. Cần strip() để loại bỏ khoảng trắng thừa đầu cuối gây lỗi parse.
                dom = xml.dom.minidom.parseString(record.xml_content.strip())

                # 2. Sử dụng toprettyxml để định dạng.
                # Tham số indent="    " chính là yêu cầu thụt vào 4 khoảng trắng của bạn.
                pretty_xml_str = dom.toprettyxml(indent="    ")

                # 3. (Tùy chọn) minidom đôi khi tạo ra các dòng trống thừa thãi giữa các tag.
                # Đoạn code này giúp làm sạch các dòng trống đó để nhìn gọn hơn.
                cleaned_lines = [line for line in pretty_xml_str.split('\n') if line.strip()]
                formatted_xml = '\n'.join(cleaned_lines)

                record.formatted_xml_display = formatted_xml

            except Exception as e:
                # Nếu chuỗi XML gốc bị lỗi cú pháp, hiển thị thông báo lỗi thay vì làm crash server
                record.formatted_xml_display = f"Lỗi định dạng XML: {str(e)}\nVui lòng kiểm tra lại nội dung XML gốc."

    is_line_exclude_tax = fields.Boolean('Line trước thuế', compute='compute_total_thanhtien_va_thue', store=True)
    line_exclude_tax  = fields.Selection([
        ('1', '1: Tiền C.Thuế = Tổng thành tiền'),
        ('2', '2: Tiền C.Thuế = Tổng thành tiền - Tổng chiết khấu'),
        ('3', '3: Tiền C.Thuế = Tổng thành tiền - Tổng chiết khấu theo tỉ lệ'),
        ('4', '4: Tiền C.Thuế = Tổng thành tiền - Chiết khấu cả đơn'),
        ('5', '5: Tiền C.Thuế = Tổng thành tiền - Chiết khấu cả đơn - Tổng chiết khấu'),
        ('6', '6: Tiền C.Thuế = Tổng thành tiền - Chiết khấu tổng đơn - Tổng chiết khấu theo tỉ lệ'),

        ('7', '7: Tiền C.Thuế = Tổng thành tiền - tien_thue'),
        ('8', '8: Tiền C.Thuế = Tổng thành tiền - Tổng chiết khấu - tien_thue'),
        ('9', '9: Tiền C.Thuế = Tổng thành tiền - Tổng chiết khấu theo tỉ lệ - tien_thue'),
        ('10', '10: Tiền C.Thuế = Tổng thành tiền - Chiết khấu cả đơn - tien_thue'),
        ('11', '11: Tiền C.Thuế = Tổng thành tiền - Chiết khấu cả đơn - Tổng chiết khấu - tien_thue'),
        ('12', '12: Tiền C.Thuế = Tổng thành tiền - Chiết khấu tổng đơn - Tổng chiết khấu theo tỉ lệ - tien_thue'),
        ('0', '0: Không phải 12 trường hợp trên'),
    ], string="Cách tính tiền trước thuế", compute="compute_total_thanhtien_va_thue", store=True)
    total_thanhtien = fields.Float('Tổng thành tiền', compute='compute_total_thanhtien_va_thue', store=True)
    total_diff = fields.Float('Tổng số tiền lệch', compute='compute_total_thanhtien_va_thue', store=True)

    @api.depends('tien_c_thue', 'nimbox_line_ids', 'nimbox_line_ids.thanhtien', 'nimbox_line_ids.so_tien_chiet_khau')
    def compute_total_thanhtien_va_thue(self):
        def compare_float(f1, f2):
            if f1 == 0 and f2 == 0: return False
            maxf12 = max(abs(f1), abs(f2))
            return abs((f1-f2) / maxf12) < 0.000003

        for rec in self:
            line_exclude_tax = '0'
            discount = ('2', '3', '4')

            line_normal = rec.nimbox_line_ids.filtered(lambda line: (line.tchat or '').strip() not in discount)
            line_chiet_khau_tong_don = rec.nimbox_line_ids.filtered(lambda line: (line.tchat or '').strip() in discount)

            sum_thanhtien = sum(line_normal.mapped('thanhtien') or [])
            sum_so_tien_chiet_khau = sum(line_normal.mapped('so_tien_chiet_khau') or [])
            sum_ti_le_chiet_khau = sum([((line.ti_le_chiet_khau or 0) * (line.thanhtien or 0)) / 100 for line in line_normal])

            sum_chiet_khau_tong_don = sum(line_chiet_khau_tong_don.mapped('thanhtien') or [])

            if   compare_float(rec.tien_c_thue, sum_thanhtien):
                line_exclude_tax = '1'
            elif compare_float(rec.tien_c_thue, sum_thanhtien - sum_so_tien_chiet_khau):
                line_exclude_tax = '2'
            elif compare_float(rec.tien_c_thue, sum_thanhtien - sum_ti_le_chiet_khau):
                line_exclude_tax = '3'
            elif compare_float(rec.tien_c_thue, sum_thanhtien - sum_chiet_khau_tong_don):
                line_exclude_tax = '4'
            elif compare_float(rec.tien_c_thue, sum_thanhtien - sum_so_tien_chiet_khau - sum_chiet_khau_tong_don):
                line_exclude_tax = '5'
            elif compare_float(rec.tien_c_thue, sum_thanhtien - sum_ti_le_chiet_khau - sum_chiet_khau_tong_don):
                line_exclude_tax = '6'

            # if rec.ttb_vendor_vat in ['0100110207', '0100110207-001']:
            #     total = sum(rec.nimbox_line_ids.mapped('thanhtien') or [])
            # else:
            #     total = sum(rec.nimbox_line_ids.mapped('thanhtien') or []) - sum(rec.nimbox_line_ids.mapped('so_tien_chiet_khau'))

            rec.total_thanhtien = sum_thanhtien
            rec.total_diff = (rec.tien_c_thue or 0) - sum_thanhtien
            rec.line_exclude_tax = line_exclude_tax
            rec.is_line_exclude_tax = compare_float(sum_thanhtien, rec.tien_c_thue)


    def reconcil_money_invoice_m2(self):
        for rec in self:
            if not rec.nimbox_line_ids: continue

            discount = ('2', '3', '4')
            line_normal = rec.nimbox_line_ids.filtered(lambda line: (line.tchat or '').strip() not in discount)
            sum_thanhtien = sum(line_normal.mapped('thanhtien') or [])
            if sum_thanhtien == 0: continue

            for line in line_normal[:-1]:
                rate = line.thanhtien / sum_thanhtien
                thanhtien_exclude_tax = round(rate * rec.tien_c_thue)
                sum_thanhtien_exclude_tax += thanhtien_exclude_tax
                
                dongia_excluded_tax = thanhtien_exclude_tax / line.soluong if line.soluong else line.dongia
                line.write({
                    'thanhtien_exclude_tax': thanhtien_exclude_tax,
                    'dongia_excluded_tax': dongia_excluded_tax
                })

            line = line_normal[-1]
            thanhtien_exclude_tax = round(rec.tien_c_thue - sum_thanhtien_exclude_tax)
            dongia_excluded_tax = thanhtien_exclude_tax / line.soluong if line.soluong else line.dongia
            line.write({
                'thanhtien_exclude_tax': thanhtien_exclude_tax,
                'dongia_excluded_tax': dongia_excluded_tax
            })

            # sum_thanhtien_exclude_tax = 0

            # lines = rec.nimbox_line_ids.sorted(key=lambda l: l.soluong)
            # for line in lines[:-1]:
            #     soluong = line.soluong if line.soluong != 0 else 1
            #     # line.dongia = line.thanhtien_exclude_tax / soluong
            #     if rec.is_line_exclude_tax:
            #         if rec.ttb_vendor_vat in ['0100110207', '0100110207-001']:
            #             thanhtien_exclude_tax = line.thanhtien
            #         else:
            #             thanhtien_exclude_tax = line.thanhtien - line.so_tien_chiet_khau
            #     else:
            #         thue = line.get_thuesuat_integer()
            #         if rec.ttb_vendor_vat in ['0100110207', '0100110207-001']:
            #             thanhtien_exclude_tax = round(line.thanhtien / (1 + thue/100))
            #         else:
            #             thanhtien_exclude_tax = round((line.thanhtien - line.so_tien_chiet_khau) / (1 + thue/100))

            #     line.write({
            #         'thanhtien_exclude_tax': thanhtien_exclude_tax
            #     })
            #     sum_thanhtien_exclude_tax += thanhtien_exclude_tax

            # line = lines[-1]
            # soluong = line.soluong if line.soluong != 0 else 1
            # line.write({
            #     # 'dongia': line.thanhtien_exclude_tax / soluong,
            #     'thanhtien_exclude_tax': rec.tien_c_thue - sum_thanhtien_exclude_tax,
            # })

    def action_view_pdf(self):
        self.ensure_one()
        if self.pdf_file:
            view_id = self.env.ref('ttb_purchase_invoice_stock.view_nimbox_invoice_pdf_preview').id
            return {
                'type': 'ir.actions.act_window',
                'name': 'Xem trước PDF',
                'res_model': 'ttb.nimbox.invoice',
                'res_id': self.id,
                'view_mode': 'form',
                'view_id': view_id,
                'target': 'new',
                'context': self.env.context,
            }
        return False

    ten_hien_thi = fields.Char(string='Tên hiển thị', compute='_compute_ten_hien_thi', store=True,)

    @api.depends('ttb_vendor_invoice_no', 'ttb_vendor_invoice_code', 'ttb_vendor_invoice_date')
    def _compute_ten_hien_thi(self):
        for rec in self:
            rec.ten_hien_thi = f"{rec.ttb_vendor_invoice_no} - {rec.ttb_vendor_invoice_code} - {rec.ttb_vendor_invoice_date}"


    def call_api(self, url, payload, cookie, method='POST', type='json'):
        # url = "https://nibot4.com:3939/QLHD/TraCuu"

        # payload = "TuNgay=2023-02-01&DenNgay=2023-03-28&MaSoThue=0108881480&LoaiHD=BAN_RA&TrangThaiHD=&KyHieuHD=&SoHD=&ThongTin=&TrangThaiDuyet=&KetQuaKiemTra=&Type=dsp&LocFile=&CheckMaHang=1&IsPdf=false"
        headers = {
          'accept': 'application/json, text/javascript, */*; q=0.01',
          'accept-language': 'en-US,en;q=0.9,vi;q=0.8',
          'cache-control': 'no-cache',
          'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
          'origin': 'https://nibot4.com:3939',
          'pragma': 'no-cache',
          'priority': 'u=1, i',
          # 'referer': 'https://nibot4.com:3939/QLHD/0108881480/eea4cb7d-01f8-4743-ac97-8fcc161415e6',
          'sec-ch-ua': '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
          'sec-ch-ua-mobile': '?0',
          'sec-ch-ua-platform': '"macOS"',
          'sec-fetch-dest': 'empty',
          'sec-fetch-mode': 'cors',
          'sec-fetch-site': 'same-origin',
          'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
          'x-requested-with': 'XMLHttpRequest',
          # 'Cookie': '_ga=GA1.1.1408018217.1749490418; nibot43939=wNOHniJTNrA8Q0%2BiKdFk5JCYm8Ip40q1afkqjqX1ua%2BPgEtcQ0cHvEwf%2F%2FCUdVCW; NangDongSession=CfDJ8Orb%2BHz1G%2FRMh8kZYho01NseOmsg3V8F7J9f5uX%2Bg6P400h7k3zBg1I3HKFkSxI4UtQOyHJNcvHL%2BQSfBwRHqp1%2BWSsBMO16NeNxHshHRWwGx8lvB1ocgewthmfUco5mdY71LxiUPrl%2B0Ls5PQFB9KOq6WOp3jXkwX5wNqQs4QZu; _ga_WP13T16MX2=GS2.1.s1749518647$o2$g1$t1749518840$j46$l0$h0'
          'Cookie': cookie,
        }

        return self.env['api_call.base']._call_api(
            url,
            params = payload,
            headers=headers,
            method=method,
            type=type
        )

    def find_and_apply_purchase(self):
        for invoice in self:
            po_ids = self.env['purchase.order'].sudo().search([
                ('picking_ids.ttb_vendor_invoice_code', '=', invoice.ttb_vendor_invoice_code),
                ('picking_ids.ttb_vendor_invoice_no', '=', invoice.ttb_vendor_invoice_no),
                ('picking_ids.ttb_vendor_invoice_date', '=', invoice.ttb_vendor_invoice_date),
                ('picking_ids.partner_id.vat', '=', invoice.ttb_vendor_vat),
                # ('picking_ids.amount_total', '=', invoice.ttb_price_unit),
            ])

            po_ids = po_ids.filtered(lambda po: any(picking.amount_total == invoice.ttb_price_unit for picking in po.picking_ids))
            if po_ids:
                invoice.write({
                    'po_ids': po_ids,
                    'state': 'waiting'
                })
                # Chưa xác nhận, để review trước xong xác nhận bằng job. Khi đã ổn định thì xác nhận luôn
                if not self.env.context.get('nibot_pending_action_confirm'): invoice.action_confirm()


    def sync_invoice(self, cookie, masothue, date_from, date_to=False, loaihd='MUA_VAO'):
        def generate_payloads_per_day():
            # masothue = "0110683327"
            # loaihd = "MUA_VAO"
            date_to1 = date_to or fields.Date.today()
            date_from1 = date_from

            payloads = []

            # date_from = date(2025, 5, 1)
            while date_from1 <= date_to1:
                start_date = date_from1
                end_date = date_from1  # mỗi ngày là một payload

                payload = (
                    f"TuNgay={start_date.strftime('%Y-%m-%d')}"
                    f"&DenNgay={end_date.strftime('%Y-%m-%d')}"
                    f"&MaSoThue={masothue}"
                    f"&LoaiHD={loaihd}"
                    f"&TrangThaiHD=&KyHieuHD=&SoHD=&ThongTin=&TrangThaiDuyet="
                    f"&KetQuaKiemTra=&Type=dsp&LocFile=&CheckMaHang=1&IsPdf=false"
                )

                payloads.append(payload)
                date_from1 += timedelta(days=1)

            return payloads


        url = "https://nibot4.com:3939/QLHD/TraCuu"
        # payload = "TuNgay=2023-02-01&DenNgay=2023-04-28&MaSoThue=0108881480&LoaiHD=BAN_RA&TrangThaiHD=&KyHieuHD=&SoHD=&ThongTin=&TrangThaiDuyet=&KetQuaKiemTra=&Type=dsp&LocFile=&CheckMaHang=1&IsPdf=false"

        for payload in generate_payloads_per_day():
            result = self.call_api(url, payload, cookie)
            if result.get('message') == 'ZString':
                _logger.info('Gặp lỗi ZString')
                continue

            if not isinstance(result, dict) or 'obj' not in result:
                raise UserError('Lỗi gọi api. Nội dung: %s' % str(result))
            for res in result['obj']:
                id_nibot = res['id']
                _logger.info('Đồng bộ nibot, id %s', id_nibot)

                old = self.sudo().search([('id_nibot', '=', id_nibot)])
                if old:
                    _logger.info('Đã tồn tại nibot id %s', id_nibot)
                    continue

                old = self.sudo().search([
                    ('ttb_vendor_vat', '=', res['mst2']),
                    ('ttb_vendor_invoice_code', '=', res['khhd']),
                    ('ttb_vendor_invoice_no', '=', res['so']),
                ])
                if old:
                    old.write({'id_nibot': id_nibot})
                    _logger.info('Đã tồn tại (hoá đơn import tay) nibot id %s', id_nibot)
                    continue

                vals = {
                    'id_nibot': res['id'],
                    'ttb_vendor_vat': res['mst2'],
                    'ttb_vendor_name': res['dtpn2'],
                    'ttb_vendor_invoice_date': res['ngay'],
                    'ttb_vendor_invoice_code': res['khhd'],
                    'ttb_vendor_invoice_no': res['so'],
                    'tien_c_thue': res['tct'],
                    'tien_thue': res['tt'],
                    'tien_ck_tm': res['tck'],
                    'tien_phi': res['tp'],
                    'ttb_price_unit': res['ttt'],
                    'trang_thai_hd': res['tthhd'],
                }
                try:
                    url_pdf = f'https://nibot4.com:3939/QLHD/TaiFile/pdf/{masothue}/{id_nibot}'
                    pdf_content = self.with_context(disable_api_log=True).call_api(url_pdf, {}, cookie, 'GET', 'file')
                    if pdf_content:
                        pdf_base64 = base64.b64encode(pdf_content)
                        vals['pdf_file'] = pdf_base64
                except:
                    _logger.info('Không thể tải file PDF từ Nibot, có thể do không có quyền truy cập hoặc không tồn tại file PDF, id_nibot: %s' % id_nibot)
                    pass

                _logger.info('Tạo mới nibot id %s', id_nibot)
                invoice = self.with_context(nibot_disable_auto_map_po=True).create(vals)
                invoice.find_and_apply_purchase()

                self.env.cr.commit()


    @api.depends('picking_ids')
    def _compute_delivery_count(self):
        for rec in self:
            rec.delivery_count = len(rec.picking_ids)

    @api.depends('po_ids')
    def _compute_ttb_product_ids(self):
        for rec in self:
            productes = rec.po_ids.order_line.filtered(lambda x: x.qty_received > 0).mapped('product_id')
            rec.ttb_product_ids = productes.ids
            rec.count_ttb_product = len(productes)

    @api.depends('po_ids', 'po_ids.received_amount_total', 'po_ids.count_ttb_product')
    # Todo: Store=True
    def _compute_price_unit(self):
        for rec in self:
            rec.ttb_total_price_unit = sum(rec.po_ids.mapped('received_amount_total'))

    @api.depends('ttb_price_unit', 'state')
    def _compute_po_map_ids(self):
        for rec in self:
            po_ids = self.sudo().search([('id', '!=', rec.id)]).mapped('po_ids').ids
            po_map_ids = False
            if rec.state != 'done':
                difference_amount = float(self.env['ir.config_parameter'].sudo().get_param('ttb_purchase_invoice_stock.difference_amount', 0))
                min_ttb_price_unit = max(rec.ttb_price_unit - difference_amount, 0)
                max_ttb_price_unit = rec.ttb_price_unit + difference_amount
                po_map_ids = self.env['purchase.order'].search([('id', 'not in', po_ids), ('ttb_type', '=', 'sale'),
                                                                ('received_amount_total','>=', min_ttb_price_unit),
                                                                ('received_amount_total','<=', max_ttb_price_unit),
                                                                ('is_create_picking', '=', False), ('count_ttb_product', '>', 0)])
            rec.po_map_ids = po_map_ids

    @api.depends('ttb_vendor_vat', 'state')
    def _compute_po_map_vat_ids(self):
        for rec in self:
            po_ids = self.sudo().search([('id', '!=', rec.id)]).mapped('po_ids').ids
            po_map_vat_ids = False
            if rec.state != 'done' and rec.ttb_vendor_vat:
                po_map_vat_ids = self.env['purchase.order'].search([('id', 'not in', po_ids), ('ttb_type', '=', 'sale'), ('ttb_vat', '=ilike', rec.ttb_vendor_vat), ('count_ttb_product', '>', 0), ('is_create_picking', '=', False)])

            # po_map_vat_ids = self.env['purchase.order'].search([], limit=10)
            # Update độ lệch tiền để sắp xếp
            # Thiện bỏ logic cũ đã không còn dùng đến. Lệnh SQL này có thể ảnh hưởng hiệu năng hệ thống
            # if po_map_vat_ids:
            #     po_map_vat_ids_str = str(po_map_vat_ids.ids).replace('[', '(').replace(']', ')')
            #     query = f"""
            #     UPDATE purchase_order
            #     SET difference_amount = ABS(received_amount_total - {rec.ttb_price_unit})
            #     WHERE id in {po_map_vat_ids_str}
            #     """
            #     self.env.cr.execute(query)
            rec.po_map_vat_ids = po_map_vat_ids

    @api.model
    def ttb_vendor_invoice_no_lstrip(self, val):
        if not val:
            return f''
        return val.replace(" ", "").lstrip('0')

    @api.depends('ttb_vendor_invoice_no', 'ttb_vendor_invoice_code', 'ttb_vendor_vat')
    def _compute_po_ids(self):
        for rec in self:
            ttb_vendor_invoice_no = self.ttb_vendor_invoice_no_lstrip(rec.ttb_vendor_invoice_no)
            rec.domain_po_ids = [('ttb_vendor_invoice_no_lstrip', '=ilike', ttb_vendor_invoice_no),
                                 ('ttb_vendor_invoice_code', '=ilike', rec.ttb_vendor_invoice_code),
                                 ('ttb_vat', '=ilike', rec.ttb_vendor_vat), ('count_ttb_product', '>', 0), ('is_create_picking', '=', False)]

    def button_not_matching(self):
        self.write({'state': 'not_matching'})

    def action_confirm(self):
        for rec in self.with_context(no_check_document=True):
             if not rec.po_ids:
                 raise UserError('Chưa có đơn mua hàng, vui lòng nhập đơn mua hàng')
             else:
                for po in rec.po_ids:
                    if po.is_create_picking: continue
                    rec._create_picking(po)
                rec.state = 'done'

    def auto_map_po(self):
        for rec in self:
            po_ids = self.sudo().search([('id', '!=', rec.id)]).mapped('po_ids').ids
            difference_amount = float(self.env['ir.config_parameter'].sudo().get_param('ttb_purchase_invoice_stock.difference_amount', 0))
            min_ttb_price_unit = max(rec.ttb_price_unit - difference_amount, 0)
            max_ttb_price_unit = rec.ttb_price_unit + difference_amount
            ttb_vendor_invoice_no = self.ttb_vendor_invoice_no_lstrip(rec.ttb_vendor_invoice_no)
            purchases = self.env['purchase.order'].sudo().search([('ttb_vendor_invoice_no_lstrip', '=ilike', ttb_vendor_invoice_no),
                                                                  ('ttb_type', '=', 'sale'),
                                                                  ('ttb_vendor_invoice_code', '=ilike', rec.ttb_vendor_invoice_code),
                                                                  ('ttb_vat', '=ilike', rec.ttb_vendor_vat), ('received_amount_total','>=', min_ttb_price_unit),
                                                                  ('received_amount_total','<=', max_ttb_price_unit), ('is_create_picking', '=', False),
                                                                  ('count_ttb_product', '>', 0)])
            if len(purchases) == 1:
                rec.po_ids = purchases.ids
                # if purchases[0].is_create_picking: continue
                # rec._create_picking(purchases)
                rec.state = 'waiting'
            elif len(purchases) >= 2:
                rec.po_ids = purchases.ids
                rec.state = 'many_po'
            else:
                purchases = self.env['purchase.order'].sudo().search([('id', 'not in', po_ids),
                                                                      ('ttb_type', '=', 'sale'),
                                                                      ('ttb_vendor_invoice_no_lstrip', '=ilike', ttb_vendor_invoice_no),
                                                                      ('ttb_vat', '=ilike', rec.ttb_vendor_vat),
                                                                      ('ttb_vendor_invoice_code', '=ilike', rec.ttb_vendor_invoice_code),
                                                                      ('is_create_picking', '=', False), ('count_ttb_product', '>', 0)])
                if len(purchases) == 1:
                    rec.po_ids = purchases.ids
                    rec.state = 'not_matching_amout'
                elif len(purchases) >= 2:
                    rec.po_ids = purchases.ids
                    rec.state = 'many_po'
                else:
                    purchases = self.env['purchase.order'].sudo().search([('id', 'not in', po_ids), ('ttb_vat', '=ilike', rec.ttb_vendor_vat),
                                                                          ('ttb_type', '=', 'sale'),
                                                                          ('received_amount_total','>=', min_ttb_price_unit),
                                                                          ('received_amount_total','<=', max_ttb_price_unit),
                                                                          ('is_create_picking', '=', False),
                                                                          ('count_ttb_product', '>', 0)])
                    if purchases:
                        rec.po_ids = purchases[0].ids
                        rec.state = 'amout_vat'

    def button_auto_map_po(self):
        self_auto = self.search([('state', '=', 'not_matching'), ('po_ids', '=', False)])
        self_auto.auto_map_po()

    def _create_picking(self, purchase):
        StockPicking = self.env['stock.picking']
        for order in purchase:
            warehouse_id = order.ttb_branch_id.vat_warehouse_id
            if not warehouse_id:
                raise UserError('Không tìm thấy Kho HDT, vui lòng kiểm tra cấu hình cơ sở')
            picking_type_id = warehouse_id.in_type_id
            location_dest_id = picking_type_id.default_location_dest_id
            location_id = picking_type_id.default_location_src_id
            if any(product.type == 'consu' for product in order.order_line.product_id):
                move_line = []
                for line in order.order_line.filtered(lambda x: x.qty_received > 0):
                    move_line.append((0, 0, {'name': line.product_id.name,
                                             'product_id': line.product_id.id,
                                             'date': line.order_id.effective_date or fields.Datetime.now(),
                                             'product_uom_qty': line.qty_received,
                                             'product_uom': line.product_uom.id,
                                             'location_id': location_id.id,
                                             'location_dest_id': location_dest_id.id,
                                             }))

                res = {'picking_type_id': picking_type_id.id,
                        'partner_id': order.partner_id.id,
                        'user_id': False,
                        'date': order.date_order,
                        'origin': order.name,
                        'location_dest_id':location_dest_id.id,
                        'location_id':location_id.id,
                        'company_id': order.company_id.id,
                        'state': 'draft',
                        'move_ids': move_line,
                        'ttb_vendor_invoice_no': self.ttb_vendor_invoice_no_lstrip(self.ttb_vendor_invoice_no),
                        'ttb_vendor_invoice_code': self.ttb_vendor_invoice_code,
                        'ttb_nimbox_invoice_id': self.id,
                       }
                picking = StockPicking.with_user(SUPERUSER_ID).create(res)
                picking.action_confirm()
                picking.with_context(skip_sms=True, cancel_backorder=True).button_validate()
            value = {'is_create_picking': True, 'ttb_accountant_accept': 'ok'}
            if order.ttb_vendor_invoice_no_lstrip != self.ttb_vendor_invoice_no_lstrip(self.ttb_vendor_invoice_no):
                value['ttb_vendor_invoice_no'] = self.ttb_vendor_invoice_no
            if order.ttb_vendor_invoice_code != self.ttb_vendor_invoice_code:
                value['ttb_vendor_invoice_code'] = self.ttb_vendor_invoice_code
            order.write(value)
        return True

    def action_view_pickings(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Điều chuyển'),
            'res_model': 'stock.picking',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.picking_ids.ids)],
            'context': dict(self._context, create=False, edit=False, delete=False)
        }
        if self.delivery_count == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.picking_ids.id
            })
        return action

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        if not self.env.context.get('nibot_disable_auto_map_po'): res.auto_map_po()
        return res

    def unlink(self):
        for rec in self:
            if rec.state == 'done':
                raise UserError(f"Không thể xoá phiếu Đã khớp, vui lòng kiểm tra lại")
        return super().unlink()

    def button_apply_nimbox(self):
        if self.status_mapping == True:
            raise UserError('Hóa đơn đã bị khóa. Vui lòng kiểm tra lại hóa đơn.')
        res_id = self._context.get('res_id', False)
        if res_id:
            stock_picking = self.env['stock.picking'].browse(res_id)
            if stock_picking.exists():
                if stock_picking.has_invoice == True:
                    raise UserError(
                        "Bạn đã chọn hóa đơn không đi cùng hàng nên sẽ không thể chọn hóa đơn cho đơn hàng. Vui lòng kiểm tra lại.")
                # Thêm hóa đơn đỏ vào phiếu nhập kho
                pdf_attachments = []
                for invoice in self:
                    if invoice.pdf_file:
                        # Tạo attachment cho mỗi PDF nếu chưa có
                        attachment = self.env['ir.attachment'].create({
                            'name': invoice.ten_hien_thi or 'Hóa đơn Nimbox',
                            'type': 'binary',
                            'datas': invoice.pdf_file,
                            'res_model': 'stock.picking',
                            'res_id': stock_picking.id,
                            'mimetype': 'application/pdf',
                        })
                        pdf_attachments.append(attachment.id)

                if pdf_attachments:
                    # Lấy các attachment PDF đã có
                    existing_ids = stock_picking.nimbox_pdf_files.ids or []
                    # Gộp và loại bỏ trùng lặp
                    all_ids = list(set(existing_ids + pdf_attachments))
                    stock_picking.nimbox_pdf_files = [(6, 0, all_ids)]
                po_ids = self.ids
                if stock_picking.invoice_ids:
                    po_ids = list(set(stock_picking.invoice_ids.ids + po_ids))
                stock_picking.write({'invoice_ids': [(6, 0, po_ids)]})

                # Thêm PO vào hóa đơn đỏ
                if stock_picking.purchase_id:
                    purchase_ids = stock_picking.purchase_id.ids
                    if self.po_ids:
                        purchase_ids = list(set(self.po_ids.ids + purchase_ids))
                    self.write({'po_ids': [(6, 0, purchase_ids)]})

                # Kiểm tra số tiền chênh lệch để quyết định có cần khóa hóa đơn Nibot không cho chọn nữa không
                params = self.env['ir.config_parameter'].sudo()
                if not params.get_param('ttb_invoice.money_difference'):
                    params.set_param('ttb_invoice.money_difference', '50000')
                money_difference = float(params.get_param('ttb_invoice.money_difference', 50000))
                nibot_ids = []
                # 1PO nhiều hóa đơn => đổi trạng thái hóa đơn không được chọn nữa
                if len(stock_picking.invoice_ids.ids) + len(stock_picking.purchase_id.invoice_nibot_ids.ids) > 1:
                    for invoice in stock_picking.invoice_ids:
                        nibot_ids.append(invoice.id)
                    invoice_nibot_ids = self.env['ttb.nimbox.invoice'].search([('id', 'in', nibot_ids)])
                    for line in invoice_nibot_ids:
                        line.write({'status_mapping': True})
                # 1 hóa đơn nhiều PO hoặc 1 PO 1 hóa đơn => check tiền giữa PO và hóa đơn => đổi trạng thái hóa đơn không được chọn nữa
                else:
                    received_amount_total = 0.0
                    invoice_amount_total = self.ttb_price_unit
                    purchase_orders = self.env['purchase.order'].browse(self.po_ids.ids)
                    nibot_ids.append(self.id)
                    for purchase in purchase_orders:
                        received_amount_total = received_amount_total + purchase.received_amount_total
                    received_amount_total = received_amount_total +  self._context.get('total', 0)
                    if (invoice_amount_total - money_difference < received_amount_total):
                        invoice_nibot_ids = self.env['ttb.nimbox.invoice'].search([('id', 'in', nibot_ids)])
                        for line in invoice_nibot_ids:
                            line.write({'status_mapping': True})

    def check_result_compare(self, po_dict, invoice_dict, candidate_names):
        notice = ""
        for key, value in po_dict.items():
            if not candidate_names:
                notice += f'Thừa {value[0]} {value[1]}.\n'
                continue
            max_index, max_score = get_candidate(key, candidate_names)
            if float(max_score) >= 0.8:
                best_match = candidate_names.pop(max_index)
                result = po_dict[key][0] - invoice_dict[best_match][0]
                if result > 0:
                    notice += f'Thừa {result} {po_dict[key][1]}.\n'
                elif result < 0:
                    notice += f'Thiếu {abs(result)} {po_dict[key][1]}.\n'
            else:
                notice += f'Thiếu {value[0]} {value[1]}.\n'
        return notice

    def gen_invoice_dict_po_dict(self, purchase_orders, invoices):
        po_dict = {}
        invoice_dict = {}
        if len(purchase_orders) > 1:
            for line in invoices.nimbox_line_ids:
                if line.ai_vector_name in invoice_dict:
                    qty_invoice = invoice_dict[line.ai_vector_name][0] + line.soluong
                    invoice_dict[line.ai_vector_name] = [qty_invoice, line.tensp]
                else:
                    invoice_dict[line.ai_vector_name] = [line.soluong, line.tensp]
            for po in purchase_orders:
                for line in po.order_line:
                    if line.product_id.product_tmpl_id.ai_vector in po_dict:
                        qty_po = po_dict[line.product_id.product_tmpl_id.ai_vector][0] + line.qty_received
                        po_dict[line.product_id.product_tmpl_id.ai_vector] = [qty_po, line.name]
                    else:
                        po_dict[line.product_id.product_tmpl_id.ai_vector] = [line.qty_received, line.name]
        else:
            for po in purchase_orders.order_line:
                if po.product_id.product_tmpl_id.ai_vector in po_dict:
                    qty_po = po_dict[po.product_id.product_tmpl_id.ai_vector][0] + po.qty_received
                    po_dict[po.product_id.product_tmpl_id.ai_vector] = [qty_po, po.name]
                else:
                    po_dict[po.product_id.product_tmpl_id.ai_vector] = [po.qty_received, po.name]
            for line in invoices:
                for rec in line.nimbox_line_ids:
                    if rec.ai_vector_name in invoice_dict:
                        qty_invoice = invoice_dict[rec.ai_vector_name][0] + rec.soluong
                        invoice_dict[rec.ai_vector_name] = [qty_invoice, rec.tensp]
                    else:
                        invoice_dict[rec.ai_vector_name] = [rec.soluong, rec.tensp]

        return po_dict, invoice_dict

    def compare_quantity_invoice(self, purchase_orders):
        # 1 hóa đơn nhiều po
        if len(purchase_orders) > 1:
            nimbox_id = purchase_orders[0].invoice_nibot_ids
            if not nimbox_id.nimbox_line_ids:
                res = purchase_orders.write({
                    'notice': 'Hóa đơn không có thông tin chi tiết của các sản phẩm'
                })
                return res
            po_dict, invoice_dict = self.gen_invoice_dict_po_dict(purchase_orders, nimbox_id)
        # 1 po nhiều hóa đơn hoặc 1 hóa đơn
        else:
            invoice_no_line = purchase_orders.invoice_nibot_ids.filtered(lambda ni: not ni.nimbox_line_ids)
            if invoice_no_line:
                notice = f'Hóa đơn '
                for rec in invoice_no_line:
                    notice += f'{rec.ttb_vendor_invoice_no} '
                notice += f'không có thông tin chi tiết các sản phẩm'
                res = purchase_orders.write({
                    'notice': notice
                })
                return res
            po_dict, invoice_dict = self.gen_invoice_dict_po_dict(purchase_orders, purchase_orders.invoice_nibot_ids)
        ai_vector_invoice = list(invoice_dict.keys())
        notice_check = self.check_result_compare(po_dict, invoice_dict, ai_vector_invoice)
        purchase_orders.sudo().write({
            'notice': notice_check
        })

    def hdt_sp_not_created(self, normal_sp_list, hdt_sp_list):
        result = []
        for line in normal_sp_list:
            if not line in hdt_sp_list:
                result.append(line)
        return self.env['stock.picking'].search([('name', 'in', result), ('state', '=', 'done')])



    def button_apply_nimbox_purchase(self):
        if self.status_mapping == True:
            raise UserError('Hóa đơn đã bị khóa. Vui lòng kiểm tra lại hóa đơn.')
        res_id = self._context.get('res_id', False)
        if res_id:
            nimbox = self.env['purchase.order'].browse(res_id)
            _logger.info(f'Người dùng ghép hóa đơn có id ({self.id}) cho PO {nimbox.name}')
            qty_received = sum(line.qty_received for line in nimbox.order_line if line.qty_received > 0)
            params = self.env['ir.config_parameter'].sudo()
            if not params.get_param('ttb_invoice.money_difference'):
                params.set_param('ttb_invoice.money_difference', '50000')
            money_difference = float(params.get_param('ttb_invoice.money_difference', 50000))
            if nimbox.exists() and qty_received > 0:
                #Dâng tồn khi có hóa đơn và đã co nhâp kho
                normal_sp = self.env['stock.picking'].search([('origin', '=', nimbox.name)])
                total_sp = self.env['stock.picking'].search([('origin', 'ilike', nimbox.name)])
                hdt_sp = total_sp - normal_sp
                if not len(normal_sp) == len(hdt_sp):
                    normal_sp_list = [invoice.name for invoice in normal_sp]
                    hdt_sp_list = [invoice.origin.partition('/')[2] for invoice in hdt_sp]
                    hdt_need_create = self.hdt_sp_not_created(normal_sp_list, hdt_sp_list)
                    stock_picking = self.env['stock.picking']
                    for line in hdt_need_create:
                        stock_picking.insert_hdt_invoice(line)

                pdf_attachments = []
                for invoice in self:
                    if invoice.pdf_file:
                        # Tạo attachment cho mỗi PDF nếu chưa có
                        attachment = self.env['ir.attachment'].create({
                            'name': invoice.ten_hien_thi or 'Hóa đơn Nimbox',
                            'type': 'binary',
                            'datas': invoice.pdf_file,
                            'res_model': 'purchase.order',
                            'res_id': nimbox.id,
                            'mimetype': 'application/pdf',
                        })
                        pdf_attachments.append(attachment.id)

                if pdf_attachments:
                    # Lấy các attachment PDF đã có
                    existing_ids = nimbox.nimbox_pdf_files.ids or []
                    # Gộp và loại bỏ trùng lặp
                    all_ids = list(set(existing_ids + pdf_attachments))
                    nimbox.nimbox_pdf_files = [(6, 0, all_ids)]

                # Thêm PO vào hóa đơn đỏ
                purchase_ids = nimbox.ids
                if self.po_ids:
                    purchase_ids = list(set(self.po_ids.ids + purchase_ids))
                self.write({'po_ids': [(6, 0, purchase_ids)]})

                # Kiểm tra số tiền chênh lệch để quyết định có cần khóa hóa đơn Nibot không cho chọn nữa không
                invoice_amount_total = 0.0
                invoice_qty_total = 0
                received_qty_total = 0
                received_amount_total = 0.0
                nibot_ids = []
                # 1 PO nhiều hóa đơn
                if len(nimbox.invoice_nibot_ids.ids) > 1:
                    purchase_orders = nimbox
                    received_amount_total = nimbox.received_amount_total
                    for invoice in nimbox.invoice_nibot_ids:
                        invoice_amount_total = invoice_amount_total + invoice.ttb_price_unit
                        invoice_qty_total = invoice_qty_total + int(invoice.count_product)
                        nibot_ids.append(invoice.id)
                    for line in nimbox.order_line:
                        received_qty_total = received_qty_total + line.qty_received
                    invoice_nibot_ids = self.env['ttb.nimbox.invoice'].search([('id', 'in', nibot_ids)])
                    _logger.info(f'Hóa đơn {self.id} được ghép với PO {nimbox.name} và chuyển trạng thái status_mapping = True cho các hóa đơn {invoice_nibot_ids}')
                    invoice_nibot_ids.write({'status_mapping': True})
                # 1 hóa đơn nhiều PO hoặc 1 PO 1 hóa đơn
                else:
                    invoice_amount_total = self.ttb_price_unit
                    invoice_qty_total = int(self.count_product)
                    purchase_orders = self.env['purchase.order'].search([('invoice_nibot_ids', 'in', self.ids)])
                    for purchase in purchase_orders:
                        received_amount_total = received_amount_total + purchase.received_amount_total
                        for line in purchase.order_line:
                            received_qty_total = received_qty_total + line.qty_received
                    _logger.info(f'Hóa đơn {self.id} được ghép với PO {nimbox.name} và chuyển trạng thái status_mapping = True cho các hóa đơn {self}')
                    if (invoice_amount_total - money_difference < received_amount_total):
                        self.write({'status_mapping': True})

                # Kiểm tra tiền và số lượng hóa đơn với PO
                if not params.get_param('ttb_invoice.invoice_difference'):
                    params.set_param('ttb_invoice.invoice_difference', '5')
                if abs(received_amount_total - invoice_amount_total) <= float(params.get_param('ttb_invoice.invoice_difference', 5)):
                    for purchase in purchase_orders:
                        purchase.sudo().write({
                            'compare_invoice': 'matching',
                            'alert_po': False
                        })
                        purchase.picking_ids.update_augges_invoice(auto_create=False)
                        # purchase.update_augges_invoice_info()
                else:
                    if received_qty_total != invoice_qty_total:
                        for purchase in purchase_orders:
                            purchase.sudo().write({
                                'compare_invoice': 'quantity',
                            })
                        config_value = self.env['list.po.need.check'].search(
                            [('need_check', '=', True), ('purchase_id', '=', res_id)])
                        if not config_value:
                            self.env['list.po.need.check'].create({
                                'purchase_id': res_id,
                            })
                    else:
                        for purchase in purchase_orders:
                            purchase.sudo().write({
                                'compare_invoice': 'money',
                            })
            else:
                received_amount_total = 0.0
                if self.po_ids:
                    for line in self.po_ids:
                        received_amount_total += line.received_amount_total
                received_amount_total += nimbox.amount_total
                if self.ttb_price_unit - money_difference < received_amount_total:
                    # Nếu số tiền hóa đơn Nibot đã khớp với PO thì đánh dấu trạng thái khớp
                    self.write({'status_mapping': True})

                # Thêm PO và hóa đơn đỏ
                purchase_ids = nimbox.ids
                if self.po_ids:
                    purchase_ids = list(set(self.po_ids.ids + purchase_ids))
                self.write({'po_ids': [(6, 0, purchase_ids)]})

            return {
                'name': _('Xác nhận đẩy lên Augges'),
                'type': 'ir.actions.act_window',
                'res_model': 'push.augges.confirm.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_purchase_id': nimbox.id,
                }
            }

    def cron_update_data_vector_for_invoice_line(self, start_date, end_date):
        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError(f"Định dạng ngày không hợp lệ: {start_date}")
        try:
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError(f"Định dạng ngày không hợp lệ: {end_date}")

        try:
            invoice = self.env['ttb.nimbox.invoice'].search([('ttb_vendor_invoice_date', '>=', start_date),
                                                             ('ttb_vendor_invoice_date', '<=', end_date)])
            list_invoice =[]
            for rec in invoice:
                if rec.nimbox_line_ids:
                    list_invoice.extend(rec.nimbox_line_ids.ids)
            invoice_line = self.env['ttb.nimbox.invoice.line'].browse(list_invoice)
            _logger.info(f'Có {len(invoice_line)} dòng hóa đơn chi tiết đầu vào')
            _logger.info('Bắt đầu mã hóa')
            ai_vectors = convert_string_to_vectors(invoice_line.mapped('tensp'))
            _logger.info('Bắt đầu gắn vector mã hóa cho dòng tương ứng')
            for index, line in enumerate(invoice_line):
                if not line.ai_vector_name:
                    line.write({
                        'ai_vector_name': ai_vectors[index]
                    })
            _logger.info(f'Đã vector hóa tên sản phẩm cho {len(invoice_line)} dòng hóa đơn chi tiết')
        except UserError as e:
            _logger.info('Lỗi khi vector hóa tên sản phẩm %s', e)

    # 1. Thêm trường nối đến hóa đơn gốc
    change_invoice_id = fields.Many2one(
        comodel_name='ttb.nimbox.invoice', 
        string='Hóa đơn gốc bị điều chỉnh/thay thế',
        help="Hóa đơn gốc liên quan dựa trên thông tin thẻ TTHDLQuan"
    )

    def action_update_related_invoice_from_xml(self):
        """
        Hàm dùng để cập nhật riêng trường change_invoice_id khi đã có sẵn xml_content
        """
        for record in self:
            if record.xml_content:
                # Gọi logic tìm kiếm invoice liên quan từ XML
                # Tìm hóa đơn gốc trong hệ thống dựa trên Số hóa đơn và Ký hiệu
                record.change_invoice_id = self.env['ttb.nibot.api'].get_xml_tthdlquan_id(record.xml_content)


class NimboxInvoiceLine(models.Model):
    _name = 'ttb.nimbox.invoice.line'
    _description = 'Chi tiết hóa đơn Nibot'
    _order = 'id desc'

    nimbox_invoice_id = fields.Many2one(comodel_name='ttb.nimbox.invoice', string='Hóa đơn Nibot', ondelete='cascade', index=True, auto_join=True)
    tensp = fields.Char(string='Tên sản phẩm', index=True)
    soluong = fields.Float(string='Số lượng', )
    dongia = fields.Float(string='Đơn giá', )
    donvi = fields.Char(string='Đơn vị',)
    tchat = fields.Char(string='Tính chất')

    # ⚡️ Trường mới 1: Tỉ lệ chiết khấu theo dòng
    ti_le_chiet_khau = fields.Float(string='Tỷ lệ chiết khấu')

    # ⚡️ Trường mới 2: Số tiền chiết khấu theo dòng
    so_tien_chiet_khau = fields.Float(string='Số tiền chiết khấu')

    # ⚡️ Trường mới: Thuế suất GTGT
    thuesuat = fields.Char(string='Thuế suất GTGT')
    tien_thue = fields.Float('Tiền thuế')

    # ⚡️ Trường mới: Thành tiền (trước thuế)
    thanhtien = fields.Float(string='Thành tiền (nibot)')

    ai_vector_name = fields.Text(
        string='AI Vector',
        copy=False,
        help="Chuyển đổi tên sản phẩm sang dạng vector"
    )
