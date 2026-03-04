{
    'name': 'Tiến Thọ - API',
    'version': '18.0.0.1',
    'category': 'Tools',
    'summary': "Quy trình API",
    'depends': ['base'],
    'data': [
        # data always first
        'data/ir_sequence.xml',

        # group -> access -> rule
        'security/ir.model.access.csv',
        'security/ir_rule.xml',

        # reports

        # wizards

        # views
        'views/api_call_log.xml',
    ],
    'license': 'LGPL-3',
}
