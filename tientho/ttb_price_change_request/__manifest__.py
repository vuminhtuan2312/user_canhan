# -*- coding: utf-8 -*-
{
    "name": "TTB - Phiếu yêu cầu thay đổi giá",
    "summary": "Quy trình tạo - duyệt - xuất file cập nhật Augges cho yêu cầu thay đổi giá",
    "version": "1.0",
    "author": "TTB",
    "depends": ["base", "mail", "product", 'purchase', 'stock', 'ttb_stock', "ttb_approval", "ttb_tools"],
    "data": [
        "security/ir.model.access.csv",
        "security/security.xml",
        "data/sequence.xml",
        "data/cron.xml",
        'reports/price_label_report.xml',
        'reports/ttb_label_wizard_report.xml',
        "views/price_change_request_views.xml",
        "views/label_print_order_views.xml",
        "views/price_change_request_history.xml",
        "views/product_pricelist_views.xml",
        "wizard/product_label_layout.xml",
    ],
    'assets': {
            'web.assets_backend': [
                'ttb_price_change_request/static/src/**/*.js',
            ],
        },
    "application": True,
}
