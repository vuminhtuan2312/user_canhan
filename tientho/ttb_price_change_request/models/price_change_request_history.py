# -*- coding: utf-8 -*-
from odoo import fields, models

class TtbPCRUpdateHistory(models.Model):
    _name = "ttb.pcr.update.history"
    _description = "Lịch sử cập nhật giá Augges"
    _order = "create_date desc"

    request_id = fields.Many2one("ttb.price.change.request", required=True, ondelete="cascade", index=True)
    request_line_id = fields.Many2one("ttb.price.change.request.line", ondelete="cascade", index=True)
    product_id = fields.Many2one("product.product", required=True, index=True)
    augges_id = fields.Integer(string="Augges ID", index=True)

    price_level = fields.Selection([
        ("sale", "Giá bán"),
        ("bl", "BL"),
        ("bb1", "BB1"),
        ("bb2", "BB2"),
        ("bb3", "BB3"),
        ("bb4", "BB4"),
        ("bb5", "BB5"),
        ("bb6", "BB6"),
    ], required=True, index=True)

    old_value = fields.Float("Giá cũ")
    new_value = fields.Float("Giá mới")
    updated_value = fields.Float("Giá đọc lại sau cập nhật")

    state = fields.Selection([
        ("pending", "Chờ"),
        ("success", "Thành công"),
        ("skipped", "Bỏ qua"),
        ("mismatch", "Không khớp"),
        ("error", "Lỗi"),
    ], default="pending", index=True)

    message = fields.Char("Thông tin")
    updated_by = fields.Many2one("res.users", default=lambda self: self.env.user, readonly=True)
    updated_at = fields.Datetime(default=fields.Datetime.now, readonly=True)
