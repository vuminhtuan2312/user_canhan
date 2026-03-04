/** @odoo-module **/

import { BarcodeInput } from "@stock_barcode/components/manual_barcode";
import { patch } from "@web/core/utils/patch";

patch(BarcodeInput.prototype, {
    
    _onKeydown(ev) {
        super._onKeydown(ev);
        // Xoá trống mã cũ đã quét
        if (ev.key === "Enter" && this.state.barcode) {
            this.state.barcode = '';

            const input = ev.target;
            // chỉ thử trên Android (tùy chọn)
            const isAndroid = /Android/i.test(navigator.userAgent);
            if (!isAndroid) return;

            try {
                // blur + focus lại sau 30-120ms (thử chỉnh hiệu ứng)
                input.blur();
                setTimeout(() => {
                    input.focus();
                    // ép con trỏ về cuối chuỗi
                    const len = input.value ? input.value.length : 0;
                    try { input.setSelectionRange(len, len); } catch(e) {}
                    // đôi khi click() giúp bật keyboard
                    try { input.click(); } catch(e) {}
                }, 80);
            } catch (err) {
                console.error("force keyboard blur/focus error:", err);
            }
        }
    }

})
