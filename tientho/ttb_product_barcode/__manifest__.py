{
    'name': 'Quét mã sản phẩm',
    'version': '18.0.0.1',
    'category': 'Inventory/Inventory',
    'summary': "This module allows you to update or create products from barcode",
    "license": "LGPL-3",
    'depends': ['stock_barcode', 'ttb_product'],
    'data': [
        'security/groups.xml',
    	'views/product_barcode_views.xml',
        'views/product_product_views.xml',
        'views/ttb_product_image_views.xml',
        'views/scan_barcode_log_views.xml',
        'views/ketoan_query_views.xml',
        'security/ir.model.access.csv',
    ],
    'assets': {
        'web.assets_backend': [
            'ttb_product_barcode/static/src/**/*.js',
            # 'ttb_product_barcode/static/src/**/*.scss',
            'ttb_product_barcode/static/src/**/*.xml',
        ]
    },
}
