{
    'name': 'Tiến Thọ - SQL Augges',
    'version': '18.0.0.2',
    'category': 'Tools',
    'summary': "SQL Augges - Xuất nhập kho Augges",
    'depends': ['base', 'stock', 'ttb_tools'],
    'data': [
        'security/ir.model.access.csv',

        # 'views/view_xuat_nhap_kho_augges.xml',
        'views/view_xuat_nhap_kho.xml',
        
        'wizards/view_xuat_nhap_kho_augges_wizard.xml',
    ],
    'license': 'LGPL-3',
}
