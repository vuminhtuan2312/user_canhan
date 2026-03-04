{
    'name': 'Đồng bộ đơn hàng hệ thống auggest',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'summary': "Lấy đơn hàng từ hệ thống auggest và sinh ra đơn pos",
    'depends': ['base', 'point_of_sale', 'ttb_stock', 'ttb_tools', 'uom'],
    'data': [
        'security/ir.model.access.csv',
        'data/cron.xml',
        'views/pos_order.xml',
        'views/pos_order_line.xml',
        'views/log_qr_transaction.xml',
        'views/account_tax.xml',
        'views/order_pivot.xml'
    ],
    'assets': {
    },
    "license": "LGPL-3",
}
