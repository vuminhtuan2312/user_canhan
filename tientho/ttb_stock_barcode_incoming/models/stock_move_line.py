# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    similar_product_codes = fields.Text(
        string="Mã sản phẩm tương tự",
        help=_("Nhập hoặc quét nhiều mã"),
    )
    diff_qty = fields.Float(
        string="Lệch",
        related="move_id.diff_qty",
        store=True,
        readonly=True
    )
    diff_kk_than_hkl2 = fields.Float(
        string="Lệch KK so với HKL2",
        help="Số lượng kiểm kê trừ số lượng kiểm kê lần 2",
        readonly=True,
    )
    diff_kk_than_hkl1 = fields.Float(
        string="Lệch KK so với HKL1",
        help="Số lượng kiểm kê trừ số lượng hậu kiểm lần 1",
        readonly=True,
    )
    duplicate_picking = fields.Text(
        string="Mã phiếu trùng",
        help="Danh sách mã phiếu trùng sản phẩm trong lần kiểm kê này",
        readonly=True,
    )

    reject_qty = fields.Float(
        string="Số lượng không đạt",
        default=0.0,
        help="Số lượng sản phẩm không đạt chất lượng trên dòng này."
    )

    ttb_required_qty = fields.Float(
        related="move_id.ttb_required_qty",
        string="SL nhặt yêu cầu",
        readonly=True,
        store=False,
    )

    reason_diff = fields.Char(
        string="Lý do lệch",
        help="Lý do dẫn đến sự chênh lệch số lượng trên dòng này."
    )
    def _get_fields_stock_barcode(self):
        return super()._get_fields_stock_barcode() + [
            'create_uid',
            'reject_qty',
            'ttb_required_qty',
        ]

