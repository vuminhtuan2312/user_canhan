{
    'name': 'Hủy hàng – Đề xuất & Quy trình',
    'version': '18.0.1.0.0',
    'summary': 'Quản lý đề xuất hủy hàng, nhặt, điều chuyển VP và hủy kho',
    'category': 'Inventory',
    'author': 'TTB',
    'depends': ['base', 'mail', 'product', 'purchase', 'stock', 'ttb_stock', 'ttb_approval', 'ttb_stock_barcode_incoming'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/menu.xml',
        'views/cancel_views.xml',
    ],
    'installable': True,
}
