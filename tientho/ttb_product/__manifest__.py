{
    'name': 'Product Customize',
    'version': '18.0.0.2',
    'category': 'Sales/Sales',
    'summary': "Add category_code to product_category",
    'depends': ['base','product', 'account_reports'],
    'data': [
        'security/ir.model.access.csv',
        'data/cron.xml',
        'security/ir_rule.xml',

        'views/product_category_views.xml',
        'views/product_template_views.xml',
        'views/product_product.xml',
        'views/substitute_product_views.xml',
        'wizard/update_product_attribute_value_views.xml',

        # report
        'views/attribute_product_report.xml',
        'views/product_zone_report_views.xml',

        'views/product_mch_setter_views.xml',
        'views/product_nibot_views.xml',
        'views/product_category2_views.xml',
        'views/product_mch_setter2_views.xml',

        'views/product_stock_item_views.xml',
        'views/product_sale_item_views.xml',
        'views/product_matching_menus.xml',
        'views/season_type.xml',
        'views/training_data_views.xml',
        'views/product_merge_views.xml',
        'data/product_category_training_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ttb_product/static/src/**/*.js',
            'ttb_product/static/src/**/*.scss',
            'ttb_product/static/src/**/*.xml',
        ]
    },
    'license': 'LGPL-3',
}
