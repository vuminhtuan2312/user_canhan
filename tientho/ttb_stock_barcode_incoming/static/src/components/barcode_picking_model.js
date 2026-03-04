/** @odoo-module **/
import BarcodeModel from '@stock_barcode/models/barcode_picking_model';
import { patch } from '@web/core/utils/patch';

patch(BarcodeModel.prototype, {

    askBeforeNewLinesCreation(product) {
        if (this.record?.picking_type_code === 'inventory_counting') {
            return false;   // Không bao giờ hỏi
        }
        return super.askBeforeNewLinesCreation(product);
    },

    async _onExit() {

        // 1️⃣ Inventory counting → bỏ split
        if (this.record?.picking_type_code === 'inventory_counting') {
            console.log("🟡 Bỏ qua split_uncompleted_moves cho inventory_counting");
            return;
        }

        // 2️⃣ Phiếu trả hàng → auto save
        if (this.record?.ttb_return_request_id) {
            await this.save();
            return;
        }

        // 3️⃣ Các loại khác → chạy split
        return this.orm.call("stock.move", "split_uncompleted_moves", [this.moveIds]);
    },


    async _setUser() {
        if (this.record?.picking_type_code !== 'inventory_counting') {
            super._setUser();
        } else {
            await this.orm.call('stock.picking', 'log_inventory_skip', [this.record.id]);
        }
    },
    shouldSplitLine(line) {
        if (this.record?.ttb_return_request_id) {
            return false;
        }
        return super.shouldSplitLine(line);
    },
    _getMoveLineData(id) {
        const smlData = super._getMoveLineData(id);
        // Fix hiển thị x/all cho phiếu trả hàng
        if (this.record?.ttb_return_request_id) {
            if (smlData.move_id) {
                const move = this.cache.getRecord('stock.move', smlData.move_id);
                if (move) {
                    // Gán reserved_uom_qty bằng tổng nhu cầu của move để hiển thị x/all
                    smlData.reserved_uom_qty = move.product_uom_qty;
                }
            }
        }
        return smlData;
    },
    // createNewLine(params) {
    //
    //     const product = params.fieldsParams.product_id;
    //
    //     if (this.askBeforeNewLinesCreation(product)) {
    //
    //         const productName =
    //             (product.code ? `[${product.code}] ` : "") +
    //             product.display_name;
    //
    //         if (!this.config.barcode_allow_extra_product) {
    //             const message = _t(
    //                 "The product %s should not be picked in this operation.",
    //                 productName
    //             );
    //             this.notification(message, { type: "danger" });
    //             return false;
    //         }
    //
    //         // 🔥 Popup chỉ có nút Close (ẩn confirm)
    //         return new Promise(resolve => {
    //
    //             this.dialogService.add(ConfirmationDialog, {
    //                 title: _t("Not allowed"),
    //                 body: _t(
    //                     "Scanned product %s is not reserved for this transfer.",
    //                     productName
    //                 ),
    //                 cancelLabel: _t("Close"),
    //                 cancel: () => resolve(false),
    //             });
    //
    //         });
    //     }
    //
    //     return super.createNewLine(...arguments);
    // }
});
