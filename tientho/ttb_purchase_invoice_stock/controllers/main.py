from odoo import http
from odoo.http import request
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class EinvoiceRequestController(http.Controller):
    def _get_pos_order_from_invoice_number(self, invoice_number):
        """ Tìm pos.order dựa trên số hóa đơn bán lẻ """
        if not invoice_number:
            return None
        # id_augges là trường lưu số hóa đơn bán lẻ trên pos.order
        return request.env['pos.order'].sudo().search([('id_augges', '=', invoice_number)], limit=1)

    @http.route('/get-invoice-info', type='http', auth='public')
    def get_invoice_info(self, **kwargs):
        """
        Hiển thị form yêu cầu HĐĐT.
        Hàm này chủ yếu xử lý việc hiển thị trang ban đầu và các trang kết quả (success, error).
        """
        invoice_number = kwargs.get('inv_num')
        pos_order = self._get_pos_order_from_invoice_number(invoice_number)

        values = {
            'invoice_number': invoice_number,
            'error': kwargs.get('error'),
            'message': kwargs.get('message'),
            'order_info': {},
        }

        # Nếu có pos_order, điền thông tin vào form
        if pos_order:
            values['order_info'] = {
                'customer_name': pos_order.partner_name or '',
                'customer_vat': pos_order.partner_vat or '',
                'customer_address': pos_order.partner_address or '',
                'customer_email': pos_order.partner_email or '',
                'customer_phone': pos_order.partner_phone or '',
                'invoice_number': pos_order.id_augges,
                'code_qhns': pos_order.code_qhns,
            }

        return request.render('ttb_purchase_invoice_stock.einvoice_request_form_template', values)

    @http.route('/submit-invoice-info', type='http', auth='public', csrf=False, methods=['POST'])
    def submit_invoice_info(self, **post):
        """
        Xử lý dữ liệu form do người dùng gửi.
        - Cho phép cập nhật lại thông tin.
        - Giữ lại dữ liệu đã nhập nếu có lỗi.
        """
        _logger.info(f"Đã nhận yêu cầu gửi thông tin hóa đơn điện tử với dữ liệu: {post}")
        invoice_number = post.get('invoice_number')

        # Chuyển đổi trạng thái hộp kiểm thành organization_type
        # is_state_agency = 'is_state_agency' in post
        # if is_state_agency:
        #     organization_type = 'co_quan_nha_nuoc'
        # else:
        #     organization_type = 'don_vi_hanh_chinh_su_nghiep'

        # Chuẩn bị sẵn `values` để render lại form nếu có lỗi, giữ lại dữ liệu người dùng nhập
        values_on_error = {
            'invoice_number': invoice_number,
            'error': None,
            'message': None,
            'order_info': {
                'customer_name': post.get('customer_name', ''),
                'customer_vat': post.get('customer_vat', ''),
                'customer_address': post.get('customer_address', ''),
                'customer_email': post.get('customer_email', ''),
                'customer_phone': post.get('customer_phone', ''),
                'code_qhns': post.get('code_qhns', ''),
                'invoice_number': invoice_number,
                # 'organization_type': organization_type,
            }
        }

        # Tìm kiếm hoặc đồng bộ để lấy đơn hàng
        pos_order = self._get_pos_order_from_invoice_number(invoice_number)
        if not pos_order:
            _logger.info(f"Không tìm thấy hóa đơn {invoice_number}. Thực hiện đồng bộ theo yêu cầu.")
            try:
                request.env['ttb.sync.augges'].sudo().sync_orders_from_mssql_create_ngay_in(
                    augges_ids=[invoice_number],
                    create_order=datetime.now().date()
                )
                pos_order = self._get_pos_order_from_invoice_number(invoice_number)
                if pos_order:
                    _logger.info(f"Tìm thấy hóa đơn {invoice_number} sau khi đồng bộ thành công.")
                else:
                    _logger.warning(f"Không thể tìm thấy hóa đơn {invoice_number} ngay cả sau khi đồng bộ.")
            except Exception as e:
                _logger.error(f"Lỗi khi thực hiện đồng bộ theo yêu cầu cho hóa đơn {invoice_number}: {e}")
                pass

        # === KIỂM TRA LỖI ===
        # 1. Lỗi: Không tìm thấy đơn hàng sau khi đã thử đồng bộ
        if not pos_order:
            _logger.warning(f"Kết quả cuối cùng: Không tìm thấy hóa đơn {invoice_number}.")
            values_on_error['message'] = 'not_found'
            return request.render('ttb_purchase_invoice_stock.einvoice_request_form_template', values_on_error)

        # 2. Lỗi: Đã hết hạn yêu cầu
        expiration_minutes = int(request.env['ir.config_parameter'].sudo().get_param(
            'ttb_purchase_invoice_stock.einvoice_expiration_time_minutes', 75))
        expiration_seconds = expiration_minutes * 60
        if pos_order.date_order and (datetime.now() - pos_order.date_order).total_seconds() > expiration_seconds:
            values_on_error['error'] = 'expired'
            return request.render('ttb_purchase_invoice_stock.einvoice_request_form_template', values_on_error)

        # Luôn thực hiện cập nhật (cho phép sửa thông tin đã gửi)
        customer_vat = post.get('customer_vat')
        # if is_state_agency:
        #     customer_vat = ''

        update_data = {
            'partner_name': post.get('customer_name'),
            'partner_vat': customer_vat,
            'partner_address': post.get('customer_address'),
            'partner_email': post.get('customer_email'),
            'partner_phone': post.get('customer_phone'),
            'code_qhns': post.get('code_qhns'),
            'is_personalized_invoice': True,
            'is_invoice_origin': True,
        }
        try:
            pos_order.write(update_data)
            _logger.info(f"Cập nhật thông tin hóa đơn thành công cho đơn hàng {pos_order.name} với dữ liệu: {update_data}")
        except Exception as e:
            _logger.error(f"Lỗi khi ghi dữ liệu vào đơn hàng {pos_order.name}: {e}. Dữ liệu đã gửi: {post}")
            values_on_error['error'] = 'update_failed'
            return request.render('ttb_purchase_invoice_stock.einvoice_request_form_template', values_on_error)

        # Chuyển hướng về trang thành công
        redirect_url = f"/get-invoice-info?inv_num={invoice_number}&message=success"
        return request.redirect(redirect_url)

    # API Endpoint cho Augges
    @http.route('/einvoice/request/create', type='json', auth='public', methods=['POST'], csrf=False)
    def create_einvoice_request(self, **kwargs):
        invoice_number = kwargs.get('invoice_number') # Augges sẽ gửi số hóa đơn
        if not invoice_number:
            return {'error': 'Missing invoice_number'}

        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = f"{base_url}/get-invoice-info?inv_num={invoice_number}"
        
        return {'url': url}
