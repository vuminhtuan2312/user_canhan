# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

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

    def create(self, vals):
        """
        Kiểm kê: Log trường hợp nhập số lượng sản phẩm tại màn hình kiểm kê
        """
        is_log = 'hide_unlink_button' in self._context and 'force_fullfil_quantity' in self._context and 'scan_barcode_log_no_more' not in self._context
        if is_log:
            self = self.with_context(scan_barcode_log_no_more=True)

        res = super(StockMoveLine, self).create(vals)

        if is_log:
            self.env['scan.barcode.log'].create({
                'log_type': 'set',
                'res_id': res.picking_id,
                'message': 'vals:' + str(vals) + ', context:' + str(self._context),
            })

        return res

    def write(self, vals):
        """
        Kiểm kê: Log trường hợp nhập số lượng sản phẩm tại màn hình kiểm kê
        """
        is_log = 'hide_unlink_button' in self._context and 'force_fullfil_quantity' in self._context and 'scan_barcode_log_no_more' not in self._context
        if is_log:
            self = self.with_context(scan_barcode_log_no_more=True)
            self.env['scan.barcode.log'].create({
                'log_type': 'set',
                'res_id': self.picking_id[:1].id,
                'message': 'vals:' + str(vals) + ', context:' + str(self._context) + ',ids:' + str(self.picking_id.ids),
            })
        return super(StockMoveLine, self).write(vals)

    def unlink(self):
        """
        Kiểm kê: Không cho phép xoá sản phẩm tại màn hình kiểm kê
        """
        is_inventory_counting = 'hide_unlink_button' in self._context and 'force_fullfil_quantity' in self._context and 'scan_barcode_log_no_more' not in self._context
        if is_inventory_counting:
            raise UserError('Không xóa dòng sản phẩm. Hãy đặt số lượng về 0.')
        return super().unlink()

    def _get_fields_stock_barcode(self):
        return super()._get_fields_stock_barcode() + [
            'create_uid',
            'reject_qty',
            'ttb_required_qty',
        ]

    def unlink(self):
        valid_records = self.env['stock.move.line']
        for rec in self:
            try:
                # Kiểm tra xem rec hoặc rec.move_id có raise MissingError không
                _ = rec.move_id
                valid_records |= rec
            except Exception:
                _logger.info('Lỗi xoá bản ghi đã bị xoá stock_move_line')
                pass

        # Gọi unlink thực sự cho những record hợp lệ
        if valid_records:
            return super(StockMoveLine, valid_records).unlink()
        return True

