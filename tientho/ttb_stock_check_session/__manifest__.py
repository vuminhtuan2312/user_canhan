{
    'name': 'Stock Check Session',
    'version': '18.0.0.1',
    'summary': 'Quản lý phiên kiểm tồn bằng mã vạch',
    'category': 'Inventory',
    'depends': ['base', 'product', 'ttb_stock', 'ps_search_one2many_many2many', 'ttb_kpi'],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'data/ir_sequence_data.xml',
        'data/cron.xml',
        'views/check_inventory_wizard_view.xml',
        'views/stock_check_view.xml',
        'views/add_qty_wizard.xml',
        'views/sgk_book.xml',
        'views/adjust_mch5_wizard.xml',
        'views/add_stock_wizard.xml',
        'views/kvc_inventory_session.xml',
        'views/kvc_inventory_config.xml',
        'views/check_kvc_inventory_wizard.xml',
        'views/add_qty_kvc_wizard.xml',
        'views/stock_check_sgk_book.xml',
        'views/stock_check_sgk_book_wizard.xml',
        'views/add_qty_sgk_book_wizard.xml',
        'views/menu.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'ttb_stock_check_session/static/src/css/stock_check.css',
        ],
    },
    'license': 'LGPL-3'
}
