# -*- coding: utf-8 -*-
{
    'name': "server_manager_auto_backup",

    'summary': """ Quản lý backup server""",

    'description': """""",

    'author': "TT, ENC Company",
    'website': "https://entrustlab.com/",

    'category': 'Uncategorized',
    'version': '1.0',

    # any module necessary for this one to work correctly
    'depends': ['base', 'auth_oauth', 'web'],

    # always loaded
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'views/asset.xml',
        'views/groups.xml',
        'views/warning_box.xml',
        'views/server.xml',
        'views/ftp_host.xml',
        'views/next_cloud.xml',
        'views/auto_backup_config.xml',
        'views/action_update.xml',
        'views/menu.xml',
    ],
    'qweb': ['static/src/xml/control_panel.xml'],
}
