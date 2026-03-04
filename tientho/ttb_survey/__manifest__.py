{
    'name': 'Surveys - Tiến Thọ Book',
    'version': '18.0.0.1',
    'category': 'Tools',
    'summary': "Custom survey phục vụ checklist An ninh và PCCC",
    'depends': ['base', 'survey'],
    'data': [
        'views/survey_templates.xml',
        # 'views/survey_user_input_line_view.xml',
        'views/survey_question_view.xml',
        'views/survey_user_views.xml'
    ],
    'assets': {
        'survey.survey_assets': [
            # ('include', 'survey.survey_assets'),
            'ttb_survey/static/src/js/survey_form.js',
        ],
    },
    'license': 'LGPL-3',
}
