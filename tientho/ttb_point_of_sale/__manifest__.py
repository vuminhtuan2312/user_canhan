{
    'name': 'Điểm bán hàng Customize',
    'version': '18.0.0.2',
    'category': 'Sale',
    'summary': "Customize điểm bán hàng",
    'depends': ['base', 'point_of_sale', 'ttb_stock', 'sale', 'ttb_purchase'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'views/ttb_report_pos.xml',
        'views/pos_order_line_views.xml',
        'wizard/ttb_change_ncc_wizard.xml',
        'views/wizard_coverage_month.xml',
        'views/wizard_coverage_week.xml',
        'views/wizard_purchase_delivery.xml',
        'views/report_coverage_month.xml',
        'views/report_coverage_week.xml',
        'views/report_purchase_delivery.xml',
        'views/ttb_report_pos_action.xml',
        'views/product_template.xml',
        'views/product_category.xml',
        'views/ttb_report_points_card.xml',
        'views/report_customer_identification.xml',
        'views/menu.xml'
    ],
    'assets': {
    },
    'license': 'LGPL-3',
}