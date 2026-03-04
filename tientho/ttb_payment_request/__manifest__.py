{
    'name': 'TTB: Đề Xuất Thanh Toán cho Đơn Mua Hàng',
    'version': '18.0.1.0.0',
    'category': 'Purchases',
    'summary': 'Quản lý đề xuất thanh toán cho đơn mua hàng (tạm ứng và tất toán).',
    'description': """
Module này cho phép người dùng tạo và quản lý các phiếu đề xuất thanh toán trực tiếp từ đơn mua hàng.
Module được thiết kế để xử lý các luồng thanh toán tạm ứng và thanh toán tất toán, cung cấp một quy trình phê duyệt có cấu trúc.

Tính năng chính:
- Tạo Đề xuất Thanh toán từ Đơn Mua hàng.
- Hỗ trợ nhiều loại thanh toán (ví dụ: Tạm ứng, Tất toán).
- Luồng phê duyệt cho các đề xuất.
- Liên kết giữa đề xuất thanh toán và hóa đơn nhà cung cấp.
    """,
    'author': 'Tiến Thọ Book',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',

    # Các module phụ thuộc cần thiết để module này hoạt động
    'depends': [
        'base',
        'ttb_purchase',
        'account',
    ],

    # Các file dữ liệu, view luôn được tải
    'data': [
        # Các file security phải được tải trước
        'security/ir.model.access.csv',
        # 'security/payment_request_security.xml',
        # Các file view
        # 'views/payment_request_views.xml',
        # 'views/order_views.xml', # Kế thừa view để thêm nút trên đơn mua hàng
        'views/menu_views.xml',
        'views/ttb_payment_request_views.xml',
        'data/ir_sequence.xml',
        'views/account_payment_views.xml',
        'views/purchase_order_views.xml',
        'wizard/payment_request_selector_views.xml', 
        'reports/payment_request_report.xml', 
    ],

    'installable': True,
    'application': True,
    'auto_install': False,
}