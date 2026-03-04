{
    'name': 'Tiến Thọ - Bán hàng',
    'version': '18.0.0.1',
    'category': 'Tools',
    'summary': "Quy trình bán hàng",
    'depends': ['base', 'ttb_approval', 'ttb_product', 'sale_stock', 'base_view_inheritance_extension', 'sale_management', 'ttb_stock'],
    'data': [
        # data always first
        'data/ir_sequence.xml',

        # group -> access -> rule
        'security/ir.model.access.csv',
        'security/ir_rule.xml',

        # reports

        # wizards

        # views
        'views/sale_order.xml',

        # menu always last
        'views/menu.xml',
    ],
    'license': 'LGPL-3',
}
