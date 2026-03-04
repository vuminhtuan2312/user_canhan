{
    'name':'TTB - MASTER DATA theo SKU',
    'version': '18.0.0.1',
    'summary': 'Master data theo SKU và Vendor',
    'category': 'Tools',
    'depends': ['base', 'ttb_product', 'ttb_kpi'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_master_views.xml',
        'views/vendor_master_views.xml',
        'views/product_template.xml',
        'views/menu.xml'
    ],
    'license': 'LGPL-3',

}
