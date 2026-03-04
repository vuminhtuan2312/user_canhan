{
    'name': "Login as",
    'summary': "Login vào user khác để support. Odoo 18.0",
    'description': """
        Login bằng user/password admin trước. Xong xuôi rồi mới có tính năng cho phép chọn user cần login
        Tham khảo module https://apps.odoo.com/apps/modules/16.0/oi_login_as/
    """,
    'version': "1.0.0",
    "license": "LGPL-3",
    'author': "Mr.Tran",
    'category': "Tools",
    'data': [
        'wizard/wizard_login_as_views.xml',
        'security/ir.model.access.csv',
    ],
    'assets': {
        'web.assets_backend': [
            'en_login_as/static/src/js/systray_item.js',
            'en_login_as/static/src/xml/*.xml',
        ],
    },
    'demo': [],
    'depends': [],
    'installable': True,
}
