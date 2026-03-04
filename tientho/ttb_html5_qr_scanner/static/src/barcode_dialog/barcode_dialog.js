/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { pick } from "@web/core/utils/objects";
import { Component, useState, onWillStart } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { CustomBarcodeVideoScanner } from "@ttb_html5_qr_scanner/barcode_dialog/barcode_video_scanner";
import { BarcodeDialog } from "@web/core/barcode/barcode_dialog"

export class CustomBarcodeDialog extends Component {
    static template = "ttb_html5_qr_scanner.BarcodeDialog";
    static components = {
        CustomBarcodeVideoScanner,
        Dialog,
    };
    static props = {
        facingMode: { type: String, optional: true },
        close: { type: Function },
        onResult: { type: Function },
        onError: { type: Function },
        // delayBetweenScan for ZXing
        delayBetweenScan: { type: Number, optional: true },
    };

    setup() {
        this.state = useState({
            zxingScannerSupported: isBarcodeScannerSupported(), // For the Zxing path
            errorMessage: _t("Check your browser permissions."),
            activeScannerType: "html5", // Start with html5
            isLoading: true, // Show loading indicator initially
        });

        this.propsToPassToScanner = pick(this.props, "facingMode", "delayBetweenScan");

        onWillStart(() => {
            // This is just to ensure the state is set correctly before first render attempt
            this.state.isLoading = false;
        });
    }
    onChangeScannerType(ev) {
        switch(ev.target.value) {
            case 'barcode':
                this.state.activeScannerType = "zxing";
                break;
            case 'qrcode':
                this.state.activeScannerType = "html5";
                break;
        }
    }

    onScannerResult(result) {
        this.props.onResult(result);
        this.props.close();
    }

    onHtml5ScannerError(error) {
        console.warn("HTML5 QR Scanner failed, attempting fallback to ZXing/Native:", error);
        this.state.errorMessage = _t("HTML5 scanner failed: %(message)s. Trying fallback...", { message: error.message });
        // Check if ZXing is supported before switching
        if (this.state.zxingScannerSupported) {
            this.state.activeScannerType = "zxing";
        } else {
            // If ZXing also not supported, then it's a final error
            this.state.errorMessage = _t("HTML5 scanner failed and fallback is not available. Error: %(message)s", { message: error.message });
            this.props.onError(new Error(this.state.errorMessage)); // Propagate final error
            this.props.close();
        }
    }

    onZxingScannerError(error) {
        console.error("ZXing/Native Scanner failed:", error);
        this.state.zxingScannerSupported = false; // Mark zxing as failed
        this.state.errorMessage = _t("Fallback scanner also failed: %(message)s", { message: error.message });
        this.props.onError(new Error(this.state.errorMessage)); // Propagate final error
        this.props.close();
    }
}

export async function scanBarcode(env, facingMode = "environment") {
    return new Promise((resolve, reject) => {
        env.services.dialog.add(CustomBarcodeDialog, {
            facingMode,
            onResult: resolve,
            onError: reject,
            delayBetweenScan: 500, // Example delay for ZXing if it's used
        });
    });
}

export function isBarcodeScannerSupported() {
    return Boolean(browser.navigator.mediaDevices && browser.navigator.mediaDevices.getUserMedia);
}
