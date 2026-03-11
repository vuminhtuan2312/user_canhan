{
    'name': 'Tiến Thọ - Kho vận',
    'version': '18.0.0.1',
    'category': 'Tools',
    'summary': "Quy trình kho",
    'depends': ['base', 'stock', 'base_view_inheritance_extension', 'ttb_product', 'stock', 'ttb_base', 'sale_stock', 'purchase_stock', 'ps_search_one2many_many2many'],
    'data': [
        # data always first
        'data/ir_sequence.xml',
        'data/ir_cron_data.xml',
        'data/cron.xml',

        # group -> access -> rule
        'security/groups.xml',
        'security/ir.model.access.csv',
        'security/ir_rule.xml',

        # reports
        'reports/report_layout.xml',
        'reports/report_deliveryslip.xml',

        # wizards

        # views
        'views/branch.xml',
        'views/stock_warehouse.xml',
        'views/res_users.xml',
        'views/stock_picking.xml',
        'views/stock_move.xml',
        'views/inventory_session.xml',
        'views/stock_location.xml',
        'views/inventory_result.xml',
        'views/config_invoice.xml',
        'views/stock_transfer_request.xml',
        'views/stock_consume_request.xml',
        'views/barcode_change.xml',
        'views/product_product.xml',

        # menu always last
        'views/menu.xml',
    ],
    'license': 'LGPL-3',
}
