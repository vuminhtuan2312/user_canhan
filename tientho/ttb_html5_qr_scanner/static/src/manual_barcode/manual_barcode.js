import { CustomBarcodeDialog } from '@ttb_html5_qr_scanner/barcode_dialog/barcode_dialog';
import { Component, onMounted, useRef, useState } from "@odoo/owl";
import { BarcodeInput } from "@stock_barcode/components/manual_barcode"

export class CustomManualBarcodeScanner extends CustomBarcodeDialog {
    static template = "ttb_html5_qr_scanner.ManualBarcodeScanner";
    static components = {
        ...CustomBarcodeDialog.components,
        BarcodeInput,
    };
}