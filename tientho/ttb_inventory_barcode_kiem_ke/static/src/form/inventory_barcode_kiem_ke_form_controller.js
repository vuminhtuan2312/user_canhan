/** @odoo-module */

import { FormController } from "@web/views/form/form_controller";
import { user } from "@web/core/user";
import { useBus, useService } from '@web/core/utils/hooks';
import { onMounted } from "@odoo/owl";
import { ManualBarcodeScanner } from "@stock_barcode/components/manual_barcode";

export class KiemKeBarcodeFormController extends FormController {
    static template = "ttb_inventory_barcode_kiem_ke.InventorySessionForm"
    setup() {
        super.setup(...arguments);
        this.barcodeService = useService('barcode');
        useBus(this.barcodeService.bus, 'barcode_scanned', (ev) => this._onBarcodeScannedHandler(ev.detail.barcode));
        onMounted(() => {
            document.activeElement.blur();
        });
    }

    openManualBarcodeDialog() {
            this.dialogService.add(ManualBarcodeScanner, {
                facingMode: "environment",
                onResult: (barcode) => {
                    this.barcodeService.bus.trigger("barcode_scanned", { barcode });
                },
                onError: () => {},
            });
    }

    async _onBarcodeScannedHandler(barcode) {
        const kwargs = { barcode, context: this.props.context };
        const res = await this.model.orm.call(this.props.resModel, 'filter_on_barcode', [], kwargs);
        if (res.action) {
            this.actionService.doAction(res.action);
        } else if (res.warning) {
            const params = { title: res.warning.title, type: 'danger' };
            this.model.notification.add(res.warning.message, params);
        }
    }
}