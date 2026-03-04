/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import BarcodePickingModel from "@stock_barcode/models/barcode_picking_model";

patch(BarcodePickingModel.prototype, {
    /**
     * Update SL không đạt cho 1 line.
     * Chỉ chạy khi phiếu là phiếu hàng trả lại (có ttb_return_request_id).
     *
     * @param {number} virtualId  virtual_id của line
     * @param {number} delta      lượng cộng/trừ (thường là +1 hoặc -1)
     */

    get isReturnPicking() {
        // record = stock.picking record loaded by barcode
        return Boolean(this.record.ttb_return_request_id);
    },
    updateLineRejectQty(virtualId, delta = 1) {

        if (!this.record || !this.record.ttb_return_request_id) {
            return;  // Không phải phiếu trả lại → không làm gì
        }

        this.actionMutex.exec(() => {
            const line = this.pageLines.find(l => l.virtual_id === virtualId);
            if (!line) {
                return;
            }
            const demand = this.getQtyDemand(line) || 0;
            const done = this.getQtyDone(line) || 0;
            const current = line.reject_qty || 0;

            // Tính số mới
            let next = current + delta;
            if (next < 0) {
                next = 0;
            }

            if (next === current) {
                return;
            }

            if (next > done) {
                next = done;
            }

            line.reject_qty = next;
            this._markLineAsDirty(line);
            this.trigger("update");
        });
    },

    // Ghi thêm field reject_qty khi save
    _getFieldToWrite() {
    const fields = super._getFieldToWrite();
    if (!fields.includes("reject_qty")) {
        fields.push("reject_qty");
        }
        return fields;
    }
});
