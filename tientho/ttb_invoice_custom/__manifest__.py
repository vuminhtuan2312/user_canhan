{
    'name': 'Invoice custom - Tiến Thọ Book',
    'version': '18.0.0.2',
    'category': 'Tools',
    'summary': "Invoice",
    "license": "LGPL-3",
    'depends': ['ttb_product', 'ttb_purchase_invoice_stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/action_tax_invoice_views.xml',
        'views/ttb_nimbox_invoice_line_views.xml',
        'views/product_sale_item_views.xml',
        'views/menus.xml',

    ],

    'license': 'LGPL-3',
}
