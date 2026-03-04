{
    'name': 'API Kết Nối ZNS',
    'version': '18.0.0.1',
    'category': 'Applications/Tools',
    'depends': [
        'api_call_base', 'point_of_sale', 'ttb_product', 'ttb_stock',
        ],
    'data': [
        'data/ttb_connect_zns_data.xml',
        'data/cron_send_zns.xml',

        'security/ir.model.access.csv',
        'wizards/create_template_wizard_views.xml',
        'views/condition_to_send_zns_views.xml',
        'views/zns_send_views.xml',
        'views/period_campaign_views.xml',
        'views/webhook_response_views.xml',
        'views/zalo_shop_config.xml',
        'views/zalo_template_views.xml',
        'views/store_list_views.xml',
        'views/bizfly_table_views.xml',
        'views/pos_order_filter_views.xml',
        'views/zns_api_code_error_views.xml',
        'views/menu_views.xml',

    ],
    'license': 'LGPL-3',
}
