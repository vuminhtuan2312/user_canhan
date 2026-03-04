# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import UserError

class Base(models.AbstractModel):
    _inherit = 'base'

    def export_data(self, fields_to_export, *args, **kwargs):
        """
        Chỉ cho export nếu model hiện tại nằm trong danh sách cho phép
        """
        if self.env.is_superuser():
            return super().export_data(fields_to_export, *args, **kwargs)

        allowed_models = self.env['ir.model.access']._get_allowed_models_export()
        if self._name in {
            'ttb.happy.call',
            'res.partner',
            'ttb.transaction',
            'helpdesk.ticket'
        } and self._name not in allowed_models:
            raise UserError(_("Bạn không có quyền xuất dữ liệu, vui lòng liên hệ quản trị viên"))

        # Gọi luồng chuẩn của Odoo
        return super().export_data(fields_to_export, *args, **kwargs)
