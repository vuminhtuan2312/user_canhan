# -*- coding: utf-8 -*-
from odoo import models, fields, api

class StockMove(models.Model):
    _inherit = 'stock.move'

    stock_qty = fields.Float(string='Số lượng tồn lý thuyết', readonly=1, tracking=True)
    # Đè trường base thêm tracking
    quantity = fields.Float(tracking=True)
    diff_qty = fields.Float(string='Lệch', readonly=1, help='Số lượng kiểm kê trừ số lượng lý thuyết', tracking=True, store=True)    #
    diff_qty1 = fields.Float(string='Lệch', readonly=1, help='Số lượng kiểm kê trừ số lượng kiểm kê ở phiếu gốc')
    diff_qty_last = fields.Float(string='Lệch so với số đếm cuối', readonly=1, help='Số lượng đếm cuối trừ số tồn lý thuyết trước kiểm kê', default=0)
    quantity_qty_last = fields.Float(string='Số lượng đếm cuối', readonly=1, default=0)
    is_cong_don = fields.Boolean(string="Là Cộng dồn", default=False, help="Đánh dấu là cộng dồn xuống augges nếu không thì là ghi đè", store=True)
    reject_qty_total = fields.Float(compute="_compute_reject_total", store=True)
    achieved_qty = fields.Float(
        string="SL đạt",
        compute="_compute_achieved_qty",
        store=True,
    )

    ttb_required_qty = fields.Float(
        string="SL nhặt yêu cầu",
        help="Số lượng yêu cầu nhặt, nhập tay trên phiếu trả hàng"
    )

    @api.depends('move_line_ids.reject_qty')
    def _compute_reject_total(self):
        for move in self:
            move.reject_qty_total = sum(move.move_line_ids.mapped('reject_qty'))

    @api.depends('quantity', 'reject_qty_total', 'picked')
    def _compute_achieved_qty(self):
        for line in self:
            if not line.picked:
                line.achieved_qty = 0.0
            else:
                quantity = line.quantity or 0.0
                reject = line.reject_qty_total or 0.0
                # Không cho âm
                line.achieved_qty = max(quantity - reject, 0.0)
    # @api.depends('picking_id', 'picking_id.inventory_origin_id', 'picking_id.inventory_origin_id.move_ids_without_package', 'picking_id.move_ids_without_package', 'quantity')
    # def compute_diff_qty(self):
    #     for rec in self:
    #         if rec.picking_id and rec.picking_id.inventory_origin_id:
    #             inventory = rec.picking_id.inventory_origin_id
    #             line = inventory.move_ids_without_package.filtered(lambda l: l.product_id == rec.product_id)
    #             rec.diff_qty = abs(line.quantity - rec.quantity)
    #         else:
    #             rec.diff_qty = 0
    def prepare_augges_values(self, quantity=False, thanh_tien=False):
        if quantity is False:
            quantity = quantity
        if thanh_tien is False:
            thanh_tien = thanh_tien
        data = {
            'ID_Hang': self.product_id.augges_id,
            'Sl_Qd': quantity,
            'So_Luong': quantity,
            'So_LuongT': quantity,
            'Gia_Vat': self.ttb_price_unit,

            'Gia_Kvat': self.ttb_price_unit,
            'Gia_Qd': self.ttb_price_unit,
            'Don_Gia': self.ttb_price_unit,
            # 'T_Tien': self.ttb_price_unit * quantity,
            'Tyle_Ck': self.ttb_discount,
            'Ty_Gia': 0,
            'md': '',
            'No_Tk': '1561',
            'Co_Tk': '1551',
            'T_tien': thanh_tien,
            'T_tien1': thanh_tien,
        }

        return data

    # Thiện giữ lại đoạn code này không back lại
    def _create_backorder(self):
        if self.picking_id.picking_type_id.code != 'inventory_counting':
            return super()._create_backorder()
        return False

    def split_uncompleted_moves(self):
        if self.picking_id.ttb_return_request_id:
            return
        return super().split_uncompleted_moves()

    def _get_fields_stock_barcode(self):
        return super()._get_fields_stock_barcode() + [
            'ttb_required_qty',
        ]
    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)

        for move in moves:
            picking = move.picking_id
            if not picking:
                continue

            # 1️⃣ Chỉ áp dụng cho inventory_counting
            if picking.picking_type_code != 'inventory_counting':
                continue

            # 2️⃣ Chỉ khi chưa có thời gian
            if picking.inventory_scan_start_time:
                continue

            # 3️⃣ Nếu picking chỉ có đúng 1 move (chính move vừa tạo)
            if len(picking.move_ids_without_package) == 1:
                picking.inventory_scan_start_time = fields.Datetime.now()

        return moves
