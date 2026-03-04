/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import BarcodeModel from "@stock_barcode/models/barcode_picking_model";

// LƯU HÀM GỐC (BẮT BUỘC)
const originalUpdateLineQty = BarcodeModel.prototype.updateLineQty;

patch(BarcodeModel.prototype, {

    updateLineQty(lineVirtualId, qty) {
        console.log("🟢 PATCH updateLineQty CALLED", lineVirtualId, qty);

        // gọi logic gốc (update UI)
        const res = originalUpdateLineQty.call(this, lineVirtualId, qty);

        // 🔥 TÌM LINE ĐÚNG CÁCH (ODOO 18)
        let foundLine = null;
        for (const page of this.pages || []) {
            const line = page.lines.find(l => l.virtual_id === lineVirtualId);
            if (line) {
                foundLine = line;
                break;
            }
        }

        if (!foundLine || !foundLine.id) {
            console.warn("⚠️ Move line chưa có id (chưa save lần đầu)", foundLine);
            return res;
        }

        console.log("🔥 FORCE COMMAND UPDATE", foundLine.id, qty);

        // 🔥 PUSH COMMAND UPDATE (GIỐNG BARCODE FLOW)
        this.commands.push({
            operation: "UPDATE",
            record: foundLine,
            values: {
                qty_done: qty,
            },
        });

        // 🔥 SAVE → backend BẮT BUỘC write
        this.save({
            stayInEdit: true,
            reload: false,
        });

        return res;
    },

});
