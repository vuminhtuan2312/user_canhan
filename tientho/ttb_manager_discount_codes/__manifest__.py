{
    'name': 'Quản lý mã ưu đãi',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Quản lý và cấp mã ưu đãi theo quản lý nhà sách',
    'depends': ['base', 'ttb_kpi'],
    'data': [
        'security/ir.model.access.csv',
        'views/ttb_voucher_type_views.xml',
        'views/ttb_voucher_views.xml',
        'views/ttb_voucher_request_views.xml',
        'wizard/ttb_voucher_wizard_views.xml',
        'views/menu.xml',
    ],
    'license': 'LGPL-3',
}
