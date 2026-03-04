{
    'name': 'Tiến Thọ - Kho vận - Quét mã kiểm kê',
    'version': '18.0.0.1',
    'category': 'Tools',
    'summary': "Quy trình kho",
    'depends': ['base', 'stock_barcode', 'ttb_stock'],
    'data': [
        'data/data.xml',
        'security/ir.model.access.csv',

        'wizard/move_to_shelves_template.xml',

        'views/stock_warehouse.xml',
        'views/stock_picking.xml',
        'views/barcode_inventory_result.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'ttb_stock_barcode_kiem_ke/static/src/**/*.js',
            'ttb_stock_barcode_kiem_ke/static/src/**/*.scss',
            'ttb_stock_barcode_kiem_ke/static/src/**/*.xml',
        ],
    },
    'license': 'LGPL-3',
}
