/** @odoo-module **/
import { rpc } from "@web/core/network/rpc";

/**
 * Hàm log dùng chung - không cần truyền orm
 */
export async function logStockBarcode(log_type, barcode, resId, extra) {
    return await rpc('/stock_barcode/log_barcode_data', {
            log_type: log_type,
            barcode: barcode,
            res_id: resId || false,
            extra: extra || {}
        })
}
