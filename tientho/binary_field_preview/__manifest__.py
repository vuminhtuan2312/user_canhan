{
    'name': 'Binary Field Attachment Preview',
    'version': '18.0.0.1',
    'category': 'Tools',
    'summary': 'Preview attachments for binary fields',
    'depends': ['base', 'web'],
    'assets': {
        'web.assets_backend': [
            'binary_field_preview/static/src/js/binary_field_preview.js',
            'binary_field_preview/static/src/xml/binary_field_preview.xml',
            'binary_field_preview/static/src/js/many2many_pdf_preview.js',
            'binary_field_preview/static/src/xml/many2many_pdf_preview.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
