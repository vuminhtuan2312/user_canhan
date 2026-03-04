/** @odoo-module **/

import { MainMenu } from "@stock_barcode/main_menu/main_menu";
import { CustomManualBarcodeScanner } from "@ttb_html5_qr_scanner/manual_barcode/manual_barcode";
import { patch } from "@web/core/utils/patch";

patch(MainMenu.prototype, {
    openManualBarcodeDialog() {
        let res;
        let rej;
        const promise = new Promise((resolve, reject) => {
            res = resolve;
            rej = reject;
        });
        this.dialogService.add(CustomManualBarcodeScanner, {
            facingMode: "environment",
            onResult: (barcode) => {
                this._onBarcodeScanned(barcode);
                res(barcode);
            },
            onError: (error) => rej(error),
        });
        promise.catch(error => console.log(error))
        return promise;
    }
})