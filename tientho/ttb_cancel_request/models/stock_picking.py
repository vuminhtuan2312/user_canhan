from odoo import models, fields, api
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    cancel_request_id = fields.Many2one('cancel.request', string='Đề xuất hủy hàng', readonly=True)

    # Trường bổ sung cho Phiếu hủy hàng
    cancel_minutes = fields.Binary(string='Biên bản hủy', attachment=True)
    cancel_photo = fields.Binary(string='Ảnh hủy hàng', attachment=True)

    def button_validate(self):
        # Override để kiểm tra điều kiện bắt buộc
        for record in self:
            if record.cancel_request_id and record.picking_type_code == 'outgoing':
                # Đây là bước hủy hàng cuối cùng
                if not record.cancel_minutes or not record.cancel_photo:
                    raise UserError("Bắt buộc phải tải lên Biên bản hủy và Ảnh hủy hàng trước khi hoàn tất.")

        res = super().button_validate()

        # Logic sau khi validate thành công
        for record in self:
            if record.cancel_request_id and record.state == 'done':
                record._sync_cancel_request()

        return res

    def _sync_cancel_request(self):
        req = self.cancel_request_id

        # Mapping move lines to request lines
        for move in self.move_ids_without_package:
            # Tìm dòng tương ứng trên request
            req_line = req.line_ids.filtered(lambda l: l.product_id == move.product_id)
            if req_line:
                qty_done = move.quantity

                # Update SL dựa trên trạng thái request hiện tại hoặc loại picking
                if req.state == 'wait_pick':
                    # Picking nhặt hàng xong
                    req_line.qty_picked = qty_done
                elif req.state == 'wait_transfer':
                    # Picking chuyển VP xong
                    req_line.qty_office_received = qty_done
                elif req.state == 'wait_cancel':
                    # Picking hủy xong
                    req_line.qty_cancelled = qty_done

        # Chuyển trạng thái Request
        if req.state == 'wait_pick':
            req.state = 'wait_transfer'
            req._create_picking(step='transfer')  # Tự động tạo phiếu điều chuyển VP

        elif req.state == 'wait_transfer':
            req.state = 'wait_approve'
            # Dừng ở đây, đợi người dùng bấm Duyệt

        elif req.state == 'wait_cancel':
            req.state = 'done'