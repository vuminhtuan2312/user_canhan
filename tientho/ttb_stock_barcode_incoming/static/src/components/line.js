/** @odoo-module **/
import { Component } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import LineComponent from "@stock_barcode/components/line";
import { logStockBarcode } from "../barcode_logger_utils";

// patch(LineComponent.prototype, {
//     addRejectQty(delta) {

//     // Chỉ phiếu có ttb_return_request_id (hàng trả lại) mới xử lý
//         const record = this.env.model.record;
//         if (!record || !record.ttb_return_request_id) {
//             return;
//         }
//         // Gọi vào model mới
//         this.env.model.updateLineRejectQty(this.line.virtual_id, delta);
//     },
// });

// export default class LineIncomingComponent extends Component {

//     addQuantity(quantity) {
//         console.log("🟢 LineIncomingComponent addQuantity", quantity);
//         this.env.model.updateLineQty(this.line.virtual_id, quantity);
//     }
// }
// const originalAddQuantity = LineComponent.prototype.addQuantity;

patch(LineComponent.prototype, {
    addRejectQty(delta) {

    // Chỉ phiếu có ttb_return_request_id (hàng trả lại) mới xử lý
        const record = this.env.model.record;
        if (!record || !record.ttb_return_request_id) {
            return;
        }
        // Gọi vào model mới
        this.env.model.updateLineRejectQty(this.line.virtual_id, delta);
    },

    async addQuantity(quantity) {
        await logStockBarcode('add', '', this.env.model.resId, {'message': {'quantity': quantity, 'line': {...this.line}, 'sub_model': 'stock.move.line'}})

        const res = await super.addQuantity(quantity);
        await this.env.model.save()

        return res;

        // if (this.line && this.env.model && this.env.model._markLineAsDirty) {
        //     this.env.model._markLineAsDirty(this.line);
        // }

        // if (this.env.model && this.env.model.save) {
        //     try {

        //         await this.env.model.save({
        //             stayInEdit: true,
        //             reload: false,
        //         });
        //     } catch (e) {
        //         console.warn("⚠️ Autosave failed:", e);
        //     }
        // }

        // if (this.line?.id && this.line?.product_id?.barcode) {
        //      const barcode = this.line.product_id.barcode;
        //      window.dispatchEvent(
        //         new CustomEvent("barcode_scanned", {
        //             detail: { barcode },
        //             bubbles: true,
        //         })
        //     );
        // }
    },

});
