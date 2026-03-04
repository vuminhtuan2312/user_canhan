{
    'name': 'HR - Tiến Thọ Book',
    'version': '18.0.0.2',
    'category': 'Tools',
    'summary': "HR",
    'depends': ['base', 'hr', 'website_hr_recruitment', 'ttb_approval', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/hr_recruitment_stage.xml',
        'views/res_users.xml',
        'views/hr_employee.xml',
        'views/hr_job.xml',
        'wizard/views/form_swap_status.xml',
        'wizard/views/applicant_change_stage_wizard_views.xml',
        'views/recruitment_requirements.xml',
        'views/plan_of_recruitment_template.xml',
        'views/menu_item.xml',
        'views/hr_job.xml',
        'views/hr_applicant.xml',
        'views/mail_notification_light_custom.xml',

        'wizard/views/evaluation_form_layout.xml',
        'wizard/views/evaluation_form_document_wizard.xml',
        'wizard/views/evaluation_form_wizard.xml',
        'wizard/views/applicant_refuse_reason.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ttb_hr/static/src/**/*.js',
            'ttb_hr/static/src/**/*.xml',
        ],
    },

    'license': 'LGPL-3',
}
