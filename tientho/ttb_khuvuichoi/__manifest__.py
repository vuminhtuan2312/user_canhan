# -*- coding: utf-8 -*-
{
    'name': "Quản lý Khu Vui Chơi (TTB)",
    'summary': """
        Module quản lý vận hành, phân công ca và công việc tại khu vui chơi
    """,
    'description': """
        Module mở rộng cho Odoo 18:
        - Quản lý nhân viên khu vui chơi
        - Phân công ca làm việc
        - Quản lý công việc vận hành và kiểm soát chất lượng
    """,
    'author': "TTB Dev Team",
    'website': "https://www.yourcompany.com",
    'category': 'Operations',
    'version': '18.0.1.0.0',
    'depends': [
        'base',
        'hr',
        'mail',
        'resource',
        'ttb_kpi',
        'ttb_helpdesk',
        # 'ttb_base', # Uncomment nếu có module base chứa ttb.branch/ttb.area gốc
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule.xml',

        # 'data/ttb_work_template.xml',
        'data/ir_cron.xml',
        'data/ir_config_parameter.xml',
        'data/sequences.xml',

        'views/menu_root.xml',
        'views/employee_dashboard.xml',
        'views/manager_dashboard.xml',
        'views/ttb_operational_task.xml',
        'views/ttb_shift_assignment.xml',
        # 'views/ttb_operational_check.xml',
        'views/ttb_post_audit.xml',
        'views/resource_calendar_views.xml',
        'views/report.xml',
        'views/ttb_work_template.xml',
        'views/ttb_pause_reason.xml',

        'wizard/audit_fail_wizard.xml',
        'wizard/task_delay_wizard.xml',
        'wizard/task_delay_report_wizard.xml',
        'wizard/task_delay_confirm_wizard.xml',

        # 'data/ttb_work_template.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ttb_khuvuichoi/static/src/js/tours/*.js',
            'ttb_khuvuichoi/static/src/js/*.js',
            'ttb_khuvuichoi/static/src/xml/*.xml',
            'ttb_khuvuichoi/static/src/scss/*.scss',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}