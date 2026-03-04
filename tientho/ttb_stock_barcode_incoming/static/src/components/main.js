/** @odoo-module **/

import MainComponent from '@stock_barcode/components/main';
import { patch } from "@web/core/utils/patch";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

patch(MainComponent.prototype, {
    async onOpenAccountantForm() {
        await this.env.model.save();
        this.env.model.openAccountantForm();
    },

    // Thêm method tính tổng số lượng
    getTotalQuantity() {
        const lines = this.env.model.pageLines || [];
        return lines.reduce((sum, line) => {
            const raw = line.qty_done ?? 0;
            const qty = Number(raw) || 0;
            return sum + qty;
        }, 0);
    },
    getMinProductToCheck() {
        return this.env.model.record.min_products_to_check || 0;
    },
    async onClickRefresh() {
        window.location.reload()
        this.env.services.notification.add("Dữ liệu đã được làm mới.");
    },
    async onMoveProductDuplicate() {
        await this.env.model.save();
        const recordId = this.env.model.resId;
        await this.orm.call("stock.picking", "action_move_product_duplicate", [recordId]);

        // Gọi lại hàm refresh
        await this.onClickRefresh();
    },
});
