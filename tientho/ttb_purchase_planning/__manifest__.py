{
    "name": "TTB Purchase Planning",
    "summary": "Lập kế hoạch mua hàng dạng lưới",
    "category": "Purchase",
    "license": "LGPL-3",
    "depends": ["base", "purchase", "stock", "web", "ttb_stock"],
    "data": [
        "security/ir.model.access.csv",
        "views/purchase_grid_action.xml",
        "views/purchase_grid_menu.xml",
        "views/purchase_grid_wizard_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "web/static/lib/luxon/luxon.js",
            "ttb_purchase_planning/static/src/components/purchase_grid_view.js",
            "ttb_purchase_planning/static/src/components/supplier_selection_popup.js",
            "ttb_purchase_planning/static/src/xml/purchase_grid_view.xml",
            "ttb_purchase_planning/static/src/xml/supplier_selection_popup.xml",
        ],
    },
    "installable": True,
    "application": True,
}