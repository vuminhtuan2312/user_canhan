# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ShelfLocation(models.Model):
    _name = "shelf.location"
    _description = "Danh mục của quầy kệ"

    name = fields.Char(string="Quầy kệ", required=True)
    picking_type_id = fields.Many2one(
        "stock.picking.type",
        string="Loại hoạt động",
        domain="[('code', '=', 'inventory_counting')]",
    )
    mch_category_id = fields.Many2one(
        "product.category",
        string="MCH2",
    )
    description = fields.Text(string="Mô tả")
    active = fields.Boolean(string="Hoạt động", default=True)
    category_level_id = fields.Many2one(
        'product.category',
        string="MCH2",
        help="Danh mục cấp của quầy kệ",
        domain=[('category_level', '=', 2)],
    )
    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Shelf Location must be unique.'),
    ]
