{
    'name': 'Quét mã kiểm kê - Thêm quét mã vào form view',
    'version': '18.0.0.1',
    'category': 'Tools',
    'summary': "Quy trình kho",
    'depends': ['base', 'stock_barcode', 'ttb_stock', 'ttb_stock_barcode_kiem_ke'],
    'data': [
        'views/barcode_inventory_session.xml',
        'views/experimental_kiemke.xml',
        'views/menu.xml',

        'wizards/thi_nghiem_wizard.xml',

        'security/ir.model.access.csv'
    ],
    'assets': {
        'web.assets_backend': [
            'ttb_inventory_barcode_kiem_ke/static/src/**/*',
        ],
    },
    'license': 'LGPL-3',
}
