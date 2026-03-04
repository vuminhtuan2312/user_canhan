{
    'name': 'Tiến Thọ - Quy trình phê duyệt',
    'version': '18.0.0.1',
    'category': 'Tools',
    'summary': "Quy trình phê duyệt",
    'depends': ['base', 'hr'],
    'data': [
        'data/mail_template.xml',
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'views/approval_process.xml',
        'views/approval_rule.xml',
        'views/approval_line.xml',

        # always last
        'views/menu.xml',
    ],
    'license': 'LGPL-3',
}
