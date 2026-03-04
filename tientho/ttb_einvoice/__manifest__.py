{
    'name': 'Tiến Thọ - Hóa đơn điện tử',
    'version': '18.0.0.1',
    'category': 'Tools',
    'summary': "Quy trình hóa đơn điện tử",
    'depends': ['base', 'api_call_base', 'ttb_sale', 'ttb_product', 'ttb_sync_sale_augges', 'ttb_purchase', 'base_view_inheritance_extension', 'ttb_stock', 'l10n_vn', 'point_of_sale', 'accountant'],
    'data': [
        # data always first
        'data/ir_sequence.xml',

        # group -> access -> rule
        'security/ir.model.access.csv',
        'security/ir_rule.xml',

        # reports

        # wizards

        # views
        'views/einvoice_service.xml',
        'views/einvoice_serial.xml',
        'views/pos_order.xml',
        'views/account_move.xml',
        'views/account_move_line_views.xml',

        # menu always last
        'views/menu.xml',
    ],
    'license': 'LGPL-3',
}
