{
    'name': 'Stock Picking Type Kanban Custom',
    'version': "18.0.0.0.0",
    'summary': 'Custom kanban view for stock picking type',
    'category': 'Warehouse',
    'author': 'Your Company',
    "license": "LGPL-3",
    'depends': ['stock_barcode', 'ttb_stock', 'ttb_purchase'],
    'data': [
        'views/stock_picking_type_kanban_custom.xml',
        'views/stock_picking_kanban_custom.xml',
        'views/stock_location.xml',
    ],
    'installable': True,
    'application': False,
} 