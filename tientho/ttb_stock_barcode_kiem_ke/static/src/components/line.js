/** @odoo-module **/

import LineComponent from "@stock_barcode/components/line";
import { patch } from "@web/core/utils/patch";

patch(LineComponent.prototype, {
    
    // like addQuantity
    addQuantityByDigit(digit) {
        this.env.model.updateLineQtyAppendDigit(this.line.virtual_id, digit);
    }

})
