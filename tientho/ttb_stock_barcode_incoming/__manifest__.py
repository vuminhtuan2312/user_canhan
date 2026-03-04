{
    'name': 'TTB: Stock Barcode - Accounting Document',
    'version': '18.0.1.0.0',
    'summary': '''
        Adds a button to upload accounting documents from the barcode incoming screen.
        Dùng module này như là module kiểm kê.
        - Đẩy tồn xuống Augges khi xác nhận phiên kiểm kê
    ''',
    'author': 'Your Name',
    'category': 'Inventory/Barcode',
    'license': 'LGPL-3',
    'depends': [
        'stock_barcode', 'ttb_stock',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/cron_send_augges.xml',
        'data/ttb_stock_barcode_incoming_data.xml',

        #reports
        'views/product_zone_report_views.xml',
        'views/stock_picking_views.xml',
        'views/stock_warehouse_views.xml',
        'views/inventory_product_recheck_views.xml',
        'views/stock_move_line_views.xml',
        'views/stock_barcode_views.xml',
        'views/shelf_location_views.xml',
        'views/period_inventory_views.xml',
        'views/kvc_inventory_report_views.xml',
        'views/kvc_inventory_pivot_views.xml',
        'views/menu_items.xml',
        # wizard
        'wizard/create_recheck_inventory_wizard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ttb_stock_barcode_incoming/static/src/**/*',
        ],
    },
    'installable': True,
    'application': False,
}