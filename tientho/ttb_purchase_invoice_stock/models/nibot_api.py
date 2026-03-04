from odoo import api, fields, models, _
from odoo import tools
from odoo.exceptions import UserError
from datetime import datetime, date, timedelta
import base64
import zlib
import json
from urllib.parse import urlencode
import xml.etree.ElementTree as ET
from odoo.addons.ttb_tools.ai.product_similar_matcher import get_vectors_json as convert_string_to_vectors

import logging
_logger = logging.getLogger(__name__)

GUID_GOI = 'eea4cb7d-01f8-4743-ac97-8fcc161415e6'
# Hàm kiểm tra và chuyển đổi số (để tránh lỗi ValueError)
def to_float(value):
    return float(value) if value and value.replace('.', '', 1).isdigit() else 0

class TtbNibotApi(models.Model):
    _name = 'ttb.nibot.api'
    _description = 'Tương tác với Nibot sử dụng http request và cookie'

    name = fields.Char('Tên')
    base_url = fields.Char('Url gốc', default='https://nibot4.com:3939/')
    masothue = fields.Char('Mã số thuế')
    cookie = fields.Char('Cookie (token)')
    enable_ban_ra = fields.Boolean('Đồng bộ HĐ bán ra', default=False)
    enable_mua_vao = fields.Boolean('Đồng bộ HĐ mua vào', default=False)
    is_get_pdf = fields.Boolean('Lấy file pdf', default=True)
    batch_day_number = fields.Integer('Số ngày chia batch khi lấy hoá đơn', default=1)
    active = fields.Boolean(default=True)

    date_start = fields.Date('Đồng bộ từ ngày')
    date_end = fields.Date('Đồng bộ đến ngày')

    date_current = fields.Date('Ngày đang đồng bộ')
    # state = fields.Selection([('auto', 'Đồng bộ theo lịch'), ('manual', 'Đang đồng bộ tay')])

    def split_date_from_to(self, date_from=False, date_to=False, batch_day_number=None):
        if isinstance(date_from, str):
            try:
                date_from = datetime.strptime(date_from, "%Y-%m-%d").date()
            except ValueError:
                raise ValueError(f"Định dạng ngày không hợp lệ: {date_from}")
        if isinstance(date_to, str):
            try:
                date_to = datetime.strptime(date_to, "%Y-%m-%d").date()
            except ValueError:
                raise ValueError(f"Định dạng ngày không hợp lệ: {date_to}")
        # loaihd = "MUA_VAO"
        # date_from = date(2025, 5, 1)
        date_to_local = date_to or fields.Date.today()
        date_to_run = date_from or fields.Date.today()

        if batch_day_number is None:
            batch_day_number = self.batch_day_number

        result = []
        while date_to_run <= date_to_local:
            start_date = date_to_run
            if batch_day_number > 0:
                end_date = min(date_to_local, start_date + timedelta(days=batch_day_number-1))
            else:
                end_date = date_to_local
            date_to_run = end_date + timedelta(days=1)

            result.append((start_date, end_date))

        return result

    def call_api(self, url_path, payload, method='POST', type='json'):
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
          'Cookie': self.cookie,
        }

        url = self.base_url + url_path
        return self.env['api_call.base']._call_api(
            url,
            params = payload,
            headers=headers,
            method=method,
            type=type
        )

    def get_invoice(self, date_from, date_to=False, loaihd="MUA_VAO", more_params={}):
        if isinstance(date_from, str):
            try:
                date_from = datetime.strptime(date_from, "%Y-%m-%d").date()
            except ValueError:
                raise ValueError(f"Định dạng ngày không hợp lệ: {date_from}")
        if isinstance(date_to, str):
            try:
                date_to = datetime.strptime(date_to, "%Y-%m-%d").date()
            except ValueError:
                raise ValueError(f"Định dạng ngày không hợp lệ: {date_to}")

        url_path = 'QLHD/TRACUU'
        payload = (
            f"TuNgay={date_from.strftime('%Y-%m-%d')}"
            f"&DenNgay={date_to.strftime('%Y-%m-%d')}"
            f"&MaSoThue={self.masothue}"
            f"&LoaiHD={loaihd}"
            f"&TrangThaiHD={more_params.get('trang_thai', '')}"
            f"&KyHieuHD={more_params.get('ky_hieu', '')}"
            f"&SoHD={more_params.get('so_hoa_don', '')}"
            f"&ThongTin={more_params.get('thong_tin', '')}"
            f"&TrangThaiDuyet={more_params.get('trang_thai_duyet', '')}"
            f"&KetQuaKiemTra={more_params.get('ket_qua_kiem_tra', '')}"
            f"&Type={more_params.get('type', 'dsp')}"
            f"&LocFile=&CheckMaHang=1&IsPdf=false"
        )
        result = self.call_api(url_path, payload) or {}
        # if result.get('message') == 'ZString':
            # _logger.info('Gặp lỗi ZString')
            # raise UserError('Gặp lỗi ZString')

        if not isinstance(result, dict) or 'obj' not in result:
            raise UserError('Lỗi gọi api. Nội dung: %s' % str(result))
        
        # return result['obj']
        message = result.get('message', '')
        obj_data = result.get('obj')
        final_data = None

        # 2. Xử lý logic giải nén nếu message chứa "ZString"
        if message and "ZString" in message:
            try:
                _logger.info("Phát hiện dữ liệu nén ZString, đang tiến hành giải nén...")
                
                # Bước 1: Giải mã Base64 sang mảng byte (tương đương atob)
                compressed_bytes = base64.b64decode(obj_data)
                
                # Bước 2: Giải nén (Inflate) (tương đương pako.inflate)
                # zlib.decompress mặc định xử lý được định dạng của pako/zlib
                decompressed_bytes = zlib.decompress(compressed_bytes)
                
                # Bước 3: Chuyển mảng byte về chuỗi UTF-8 và parse JSON (tương đương JSON.parse)
                final_data = json.loads(decompressed_bytes.decode('utf-8'))
                
            except Exception as e:
                _logger.error("Lỗi giải mã ZString: %s", str(e))
                raise UserError(f"Không thể giải nén dữ liệu từ hệ thống. Chi tiết: {str(e)}")
        else:
            # Trường hợp không phải ZString, lấy dữ liệu trực tiếp như JS (else { DATA = data.obj; })
            final_data = obj_data

        return final_data

    def get_pdf(self, id_nibot):
        if not id_nibot: return False
        try:
            url_path = f'QLHD/TaiFile/pdf/{self.masothue}/{id_nibot}'
            pdf_content = self.with_context(disable_api_log=True).call_api(url_path, {}, 'GET', 'file')
            if pdf_content:
                return base64.b64encode(pdf_content)
        except:
            _logger.info('Không thể tải file PDF từ Nibot, có thể do không có quyền truy cập hoặc không tồn tại file PDF, id_nibot: %s' % id_nibot)
        return False

    def get_xml(self, id_nibot):
        if not id_nibot: return False
        try:
            url_path = f'Download/XML/nd-{id_nibot}'
            xml_content = self.with_context(disable_api_log=True).call_api(url_path, {}, 'GET', 'file')
            if xml_content:
                return xml_content.decode('utf-8')
        except:
            _logger.info('Không thể tải file XML từ Nibot, có thể do không có quyền truy cập hoặc không tồn tại file XML, id_nibot: %s' % id_nibot)
        return False

    def dong_bo_hoa_don_tong_quat(self, date_from, date_to=False):
        url_path = 'QLHD/DongBoHoaDonTongQuat'
        payload = (
            f"TuNgay={date_from.strftime('%Y-%m-%d')}"
            f"&DenNgay={date_to.strftime('%Y-%m-%d')}"
            f"&MaSoThue={self.masothue}"
            f"&GuidGoi={GUID_GOI}"
            f"&LoaiDongBo=GOV"
            f"&PhamViDongBo=MUA_VAO"
        )

        chung_thuc_tai_khoan = self.call_api('QLHD/ChungThucTaiKhoan', payload)
        if not chung_thuc_tai_khoan:
            raise UserError('Chứng thực tài khoản thất bại. Nội dung lỗi: %s', str(chung_thuc_tai_khoan))
        result = self.call_api(url_path, payload)

        # Kiểm tra kết quả tổng quát (Tránh exception tầng 1)
        if not isinstance(result, dict) or not result.get('obj'):
            _logger.info('Không nhận được dữ liệu "obj" từ API Nimbox')
            return False

        # Kiểm tra cấu trúc sâu bên trong (Tránh exception tầng 2: result['obj'][0]['obj'])
        # Sử dụng next() hoặc check len để an toàn với list
        obj_list = result.get('obj')
        if not isinstance(obj_list, list) or len(obj_list) == 0:
            _logger.info('Dữ liệu "obj" không phải là danh sách hoặc rỗng')
            return False

        list_ids = []
        for invoice in result['obj'][0]['obj']['listDongBo']:
            if 'J' in invoice['Type'] or 'X' in invoice['Type']:
                list_ids.append(invoice['Id'])
                _logger.info('Cần đồng bộ về nibot hoá đơn: %s', invoice['Id'])

        if list_ids:
            payload_nibot_dict = {
                'lstId[]': list_ids,
                'MaSoThue': self.masothue,
                'GuidGoi': GUID_GOI
            }
            generated_payload_string = urlencode(payload_nibot_dict, doseq=True)
            self.call_api('QLHD/DongBoLaiHoaDon', generated_payload_string)

    def get_xml_quantity_count(self, xml_data):
        # Khởi tạo biến để lưu tổng số lượng
        tong_so_luong = 0

        try:
            # 1. Đọc và phân tích chuỗi XML
            root = ET.fromstring(xml_data)

            # 2. Tìm tất cả các thẻ có tên là 'SLuong'
            # XPath './/SLuong' sẽ tìm thẻ 'SLuong' ở bất kỳ đâu trong cây XML
            danh_sach_so_luong = root.findall('.//SLuong')

            # 3. Duyệt qua từng thẻ tìm được và cộng dồn giá trị
            for so_luong_tag in danh_sach_so_luong:
                if so_luong_tag.text:
                    # Chuyển đổi nội dung text của thẻ sang số và cộng vào tổng
                    tong_so_luong += to_float(so_luong_tag.text)

            # 4. In kết quả
            # print(f"Đã tìm thấy {len(danh_sach_so_luong)} mặt hàng.")
            # print(f"Tổng số lượng hàng hóa là: {tong_so_luong}")

            return int(tong_so_luong)

        except ET.ParseError as e:
            _logger.info(f"Lỗi khi đọc XML: {e}")
        except (ValueError, TypeError) as e:
            _logger.info(f"Lỗi khi chuyển đổi số lượng get_xml_quantity_count: {e}")

        return 0

    def get_xml_hvtnmhang(self, xml_data):
        try:
            root = ET.fromstring(xml_data)
            # 1. Ưu tiên lấy <HVTNMHang>
            hvtnm_tags = root.findall('.//HVTNMHang')
            hvtnm_values = [tag.text.strip() for tag in hvtnm_tags if tag.text]

            if hvtnm_values:
                return ", ".join(hvtnm_values)

            # 2. Nếu không có <HVTNMHang>, lấy <Ten> trong NDHDon -> NMua
            ten_tags = root.findall('.//NDHDon/NMua/Ten')
            ten_values = [tag.text.strip() for tag in ten_tags if tag.text]

            if ten_values:
                return ", ".join(ten_values)

        except Exception as e:
            _logger.info(f"Lỗi khi đọc XML: {e}")
        return ""

    def get_xml_dia_chi_nmhang(self, xml_data):
        """Lấy địa chỉ người mua: NDHDon -> NMua -> DChi"""
        try:
            root = ET.fromstring(xml_data)

            dchi_tags = root.findall('.//NDHDon/NMua/DChi')
            dchi_values = [tag.text.strip() for tag in dchi_tags if tag.text]
            if dchi_values:
                return ", ".join(dchi_values)

        except Exception as e:
            _logger.info(f"Lỗi khi đọc XML: {e}")

        return ""

    def get_xml_ma_nmhang(self, xml_data):
        """Lấy địa chỉ người mua: NDHDon -> NMua -> MKHang"""
        try:
            root = ET.fromstring(xml_data)

            dchi_tags = root.findall('.//NDHDon/NMua/MKHang')
            dchi_values = [tag.text.strip() for tag in dchi_tags if tag.text]
            if dchi_values:
                return ", ".join(dchi_values)

        except Exception as e:
            _logger.info(f"Lỗi khi đọc XML: {e}")

        return ""

    def get_xml_thuesuat(self, xml_data):
        """
        Lấy tất cả các mức thuế suất (TSuat) có trong tổng hợp thanh toán của hóa đơn
        và trả về dưới dạng chuỗi (ví dụ: '8%', '10%').
        """
        if not xml_data:
            return "" # Trả về chuỗi rỗng nếu không có dữ liệu XML
            
        try:
            root = ET.fromstring(xml_data)
            
            # 1. Tìm tất cả các thẻ TSuat nằm trong khối tổng hợp thuế
            tax_rate_tags = root.findall('.//TToan/THTTLTSuat/LTSuat/TSuat')
            
            # 2. Trích xuất giá trị text, loại bỏ khoảng trắng
            tax_rates = [tag.text.strip() for tag in tax_rate_tags if tag.text]
            
            # 3. Lấy các giá trị duy nhất
            unique_tax_rates = sorted(list(set(tax_rates)))
            
            # ⚡️ 4. Định dạng kết quả thành chuỗi cách nhau bằng dấu phẩy
            return ", ".join(unique_tax_rates)

        except ET.ParseError as e:
            # Xử lý lỗi khi phân tích XML
            _logger.info(f"Lỗi khi phân tích XML trong get_xml_thuesuat: {e}")
        except Exception as e:
            # Xử lý các lỗi khác
            _logger.info(f"Lỗi không xác định trong get_xml_thuesuat: {e}")

        return ""

    def get_xml_invoice_line(self, xml_data):
        # Khởi tạo biến lưu giá trị các invoice line
        if xml_data:
            invoice_line = []

            try:
                # 1. Đọc và phân tích chuỗi XML
                root = ET.fromstring(xml_data)

                # 2. Tìm tất cả các thẻ có tên là 'HHDVu'
                # XPath './/HHDVu' sẽ tìm thẻ 'HHDVu' ở bất kỳ đâu trong cây XML
                invoie_line_list = root.findall('.//HHDVu')

                # 3. Duyệt qua từng thẻ tìm được và cộng dồn giá trị
                for hhdvu in invoie_line_list:
                    tensp = hhdvu.findtext('THHDVu', default='').strip() if hhdvu.findtext('THHDVu') else ''
                    soluong = hhdvu.findtext('SLuong', default='').strip() if hhdvu.findtext('SLuong') else ''
                    donvi = hhdvu.findtext('DVTinh', default='').strip() if hhdvu.findtext('DVTinh') else ''
                    dongia = hhdvu.findtext('DGia', default='').strip() if hhdvu.findtext('DGia') else ''

                    # ⚡️ Lấy Thành tiền trước thuế
                    thanhtien = hhdvu.findtext('ThTien', default='').strip()
                    
                    # ⚡️ Lấy Thuế suất
                    thuesuat = hhdvu.findtext('TSuat', default='').strip()

                    # ⚡️ Lấy Tỉ lệ chiết khấu
                    ti_le_chiet_khau = hhdvu.findtext('TLCKhau', default='0').strip()
                    
                    # ⚡️ Lấy Số tiền chiết khấu
                    so_tien_chiet_khau = hhdvu.findtext('STCKhau', default='0').strip()
                    
                    # Tính chất
                    tchat = hhdvu.findtext('TChat', default='').strip()
                    
                    invoice_line.append({
                        'tensp': tensp if tensp else None,
                        'soluong': to_float(soluong),
                        'donvi': donvi if donvi else None,
                        'dongia': to_float(dongia),

                        # ⚡️ Thêm trường mới
                        'thanhtien': to_float(thanhtien),
                        'thuesuat': thuesuat if thuesuat else None,
                        # ⚡️ Thêm trường mới
                        'ti_le_chiet_khau': to_float(ti_le_chiet_khau),
                        'so_tien_chiet_khau': to_float(so_tien_chiet_khau),
                        'tchat': tchat,
                    })
                return invoice_line

            except ET.ParseError as e:
                _logger.info(f"Lỗi khi đọc XML: {e}")
            except (ValueError, TypeError) as e:
                _logger.info(f"Lỗi khi chuyển đổi số lượng get_xml_invoice_line: {e}")

        return None

    def get_xml_tthdlquan(self, xml_data):
        """
        Lấy thông tin hóa đơn liên quan từ thẻ TTHDLQuan
        """
        try:
            root = ET.fromstring(xml_data)
            # Tìm thẻ TTHDLQuan (Thông tin hóa đơn liên quan)
            tthdlq_tag = root.find('.//TTHDLQuan')
            if tthdlq_tag is not None:
                return {
                    'shd': tthdlq_tag.findtext('SHDCLQuan'),   # Số hóa đơn liên quan
                    'khhd': tthdlq_tag.findtext('KHHDCLQuan'), # Ký hiệu hóa đơn liên quan
                    'ngay': tthdlq_tag.findtext('NLHDCLQuan'), # Ngày hóa đơn liên quan
                    'loai': tthdlq_tag.findtext('LHDCLQuan'),  # Loại (1: Thay thế, 2: Điều chỉnh...)
                }
        except Exception as e:
            _logger.info(f"Lỗi khi parse TTHDLQuan: {e}")
        return False

    def get_xml_tthdlquan_id(self, xml_data):
        related_info = self.get_xml_tthdlquan(xml_data)
        target_invoice = self.env['ttb.nimbox.invoice']
        if related_info:
            # Tìm hóa đơn gốc trong hệ thống dựa trên Số hóa đơn và Ký hiệu
            target_invoice = self.env['ttb.nimbox.invoice'].search([
                ('ttb_vendor_invoice_no', '=', related_info.get('shd')),
                ('ttb_vendor_invoice_code', '=', related_info.get('khhd')),
                ('ttb_vendor_invoice_date', '=', related_info.get('ngay')),
            ], limit=1)
            
        return target_invoice

    def sync_invoice(self, date_from, date_to=False, loaihd='MUA_VAO', nibot=False, more_params={}):
        for date_from, date_to in self.split_date_from_to(date_from, date_to):
            self.sync_invoice_one_day(date_from, date_to, loaihd, nibot, more_params)
    
    def sync_invoice_one_day(self, date_from, date_to=False, loaihd='MUA_VAO', nibot=False, more_params={}):    
        _logger.info('sync nibot %s, from: %s, to: %s', self.name, date_from, date_to)
        
        if nibot:
            self.dong_bo_hoa_don_tong_quat(date_from, date_to)

        invoices = self.get_invoice(date_from, date_to, loaihd, more_params=more_params)
        i = 0
        list_invoice = []
        for res in invoices:
            i += 1
            id_nibot = res['id']
            _logger.info('Đồng bộ nibot %s/%s, id %s', i, len(invoices), id_nibot)

            old = self.env['ttb.nimbox.invoice'].sudo().search([('id_nibot', '=', id_nibot)])
            if old: 
                _logger.info('Đã tồn tại nibot id %s', id_nibot)
                continue

            old = self.env['ttb.nimbox.invoice'].sudo().search([
                ('ttb_vendor_vat', '=', res['mst2']),
                ('ttb_vendor_invoice_code', '=', res['khhd']),
                ('ttb_vendor_invoice_no', '=', res['so']),
                ('ttb_vendor_invoice_date', '=', res['ngay']),
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
            if self.is_get_pdf or self.env.context.get('nibot_get_pdf'):
                vals['pdf_file'] = self.get_pdf(res['id'])

            xml_content = self.get_xml(res['id'])
            vals['xml_content'] = xml_content
            quantity_count = self.get_xml_quantity_count(xml_content)
            vals['count_product'] = str(quantity_count)
            vals['hvtnmhang'] = self.get_xml_hvtnmhang(xml_content)
            vals['dia_chi_nmhang'] = self.get_xml_dia_chi_nmhang(xml_content)
            vals['ma_nmhang'] = self.get_xml_ma_nmhang(xml_content)
            vals['change_invoice_id'] = self.get_xml_tthdlquan_id(xml_content)

            #lấy thông tin chi tiết từng dòng hoá đơn
            invoice_lines = self.get_xml_invoice_line(xml_content)
            if invoice_lines:
                vals['nimbox_line_ids'] = [(0, 0, line) for line in invoice_lines]

            _logger.info('Tạo mới nibot id %s', id_nibot)
            invoice = self.env['ttb.nimbox.invoice'].with_context(nibot_disable_auto_map_po=True).create(vals)
            # invoice.find_and_apply_purchase()
            list_invoice.extend(invoice.nimbox_line_ids.ids)
            self.env.cr.commit()

        try:
            invoice_line = self.env['ttb.nimbox.invoice.line'].browse(list_invoice)
            ai_vectors = convert_string_to_vectors(invoice_line.mapped('tensp'))
            for index, line in enumerate(invoice_line):
                line.write({
                    'ai_vector_name': ai_vectors[index]
                })
            _logger.info(f'Đã vector hóa tên sản phẩm cho {len(invoice_line)} dòng hóa đơn chi tiết')
        except UserError as e:
            _logger.info('Lỗi khi vector hóa tên sản phẩm %s', e)

    def sync_write_pdf(self, date_from, date_to=False, field_list=['pdf_file']):
        return self.sync_invoice_write(date_from, date_to, field_list)


    def sync_invoice_write(self, date_from, date_to=False, field_list=['pdf_file'], fields_check_emtpy=[], more_params={}):
        for date_from, date_to in self.split_date_from_to(date_from, date_to):
            self.sync_invoice_write_one_day(date_from, date_to, field_list, fields_check_emtpy, more_params)

    def sync_invoice_write_one_day(self, date_from, date_to=False, field_list=['pdf_file'], fields_check_emtpy=[], more_params={}):
        _logger.info('Đồng bộ cập nhật nibot %s, from: %s, to: %s', self.name, date_from, date_to)

        invoices = self.get_invoice(date_from, date_to, more_params=more_params)
        i = 0
        for res in invoices:
            i += 1
            id_nibot = res['id']
            _logger.info('Đồng bộ nibot %s/%s, id %s', i, len(invoices), id_nibot)

            old = self.env['ttb.nimbox.invoice'].sudo().search([('id_nibot', '=', id_nibot)])
            
            if not old:
                old = self.env['ttb.nimbox.invoice'].sudo().search([
                    ('ttb_vendor_vat', '=', res['mst2']),
                    ('ttb_vendor_invoice_code', '=', res['khhd']),
                    ('ttb_vendor_invoice_no', '=', res['so']),
                    ('ttb_vendor_invoice_date', '=', res['ngay']),
                ])
            if not old:
                _logger.info('Không tìm được hoá đơn %s', id_nibot)
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

            for record in old:
                # Không có field nào rỗng thì bỏ qua không xử lý
                if fields_check_emtpy and all(record[field_check] for field_check in fields_check_emtpy):
                    continue

                vals_update = {key: vals[key] for key in field_list if key in vals and record[key] != vals[key]}
                
                if 'pdf_file' in field_list:
                    vals_update['pdf_file'] = self.get_pdf(res['id'])

                if {'xml_content', 'count_product', 'hvtnmhang', 'dia_chi_nmhang', 'ma_nmhang', 'nimbox_line_ids', 'change_invoice_id'} & set(field_list):
                    xml_content = self.get_xml(res['id'])
                    if 'xml_content' in field_list:
                        vals_update['xml_content'] = xml_content
                    
                    if 'count_product' in field_list:
                        quantity_count = self.get_xml_quantity_count(xml_content)
                        vals_update['count_product'] = str(quantity_count)

                    #lấy thông tin chi tiết từng dòng hoá đơn
                    if 'nimbox_line_ids' in field_list:
                        invoice_lines = self.get_xml_invoice_line(xml_content) or []
                        vals_update['nimbox_line_ids'] = [(5, 0, 0)] + [(0, 0, line) for line in invoice_lines]
                    
                    if 'hvtnmhang' in field_list:
                        vals_update['hvtnmhang'] = self.get_xml_hvtnmhang(xml_content)
                    if 'dia_chi_nmhang' in field_list:
                        vals_update['dia_chi_nmhang'] = self.get_xml_dia_chi_nmhang(xml_content)
                    if 'ma_nmhang' in field_list:
                        vals_update['ma_nmhang'] = self.get_xml_ma_nmhang(xml_content)
                    if 'thuesuat' in field_list:
                        vals_update['thuesuat'] = self.get_xml_thuesuat(xml_content)
                    if 'change_invoice_id' in field_list:
                        vals_update['change_invoice_id'] = self.get_xml_tthdlquan_id(xml_content)

                if vals_update:
                    _logger.info('Cập nhật nibot id %s', id_nibot)
                    record.write(vals_update)

            self.env.cr.commit()

    def sync_today(self, nibot=False):
        self.sync_invoice(date_from=fields.Date.today(), date_to=fields.Date.today(), nibot=nibot)  
