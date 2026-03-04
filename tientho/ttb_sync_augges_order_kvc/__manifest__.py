{
    'name': 'TTB Sync Augges Order KVC -> BizCRM (Skeleton)',
    'version': '18.0.1.0.0',
    'summary': 'Filter Augges POS orders with ticket group (Ma_Tong=VE) and prepare BizCRM push (hourly cron).',
    'category': 'Sales/Point of Sale',
    'author': 'TTB',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'point_of_sale',
        'ttb_sync_sale_augges',
        'api_call_base',
        'ttb_tools',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
    ],
    'installable': True,
    'application': True,
}
