{
    "name": "Disable column sort",
    "version": "18.0.0.0.0",
    "summary": "Disable column sort list view.",
    "category": "Other",
    "depends": ["web"],
    "data": [
    ],
    'assets': {
        'web.assets_backend': [
            'ttb_disable_column_sort/static/src/views/list/list_renderer.js',
            'ttb_disable_column_sort/static/src/views/fields/x2many/x2many_field.js',
        ],
    },
    "license": "LGPL-3",
    "installable": True,
    "application": True,
    "auto_install": False,
}
