{
    'name': 'Patch Barcode Scanner',
    'version': '18.0.0.2',
    'category': 'Feature',
    'summary': "Patch Barcode Scanner - integrated Html5QR-Scanner along with ZXing",
    'depends': ['web', 'stock_barcode'],
    'data': [
    ],
    'assets': {
        'web.assets_backend': [
            'ttb_html5_qr_scanner/static/src/**/*',
        ]
    },
    'license': 'LGPL-3',
}