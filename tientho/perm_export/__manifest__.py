{
    "name": "Kiểm soát quyền xuất dữ liệu",
    "summary": "Thêm quyền 'Export' trên model, cho phép ẩn nút 'Export' cho những người dùng không có quyền.",
    "version": "18.0.2.0.0",
    "license": "LGPL-3",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "views/ir_model_access.xml",
    ],
    "installable": True,
    "application": True,
}
