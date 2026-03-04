/** @odoo-module **/

import MainComponent from "@stock_barcode/components/main";
import BarcodeInventoryResultModel from "../models/barcode_inventory_result_model";
// import HeaderComponent from "./header";
// import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
// import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";
import { useState } from "@odoo/owl";
import { useBus } from "@web/core/utils/hooks";

patch(MainComponent.prototype, {
    setup() {
        super.setup();
        useBus(this.env.model, 'turn_off_camera', this.turnOffCamera.bind(this));
    },

    _getModel() {
        const { resId, resModel, rpc, notification, orm, action } = this;
        if (this.resModel === 'inventory.result.lines') {
            return new BarcodeInventoryResultModel(resModel, resId, { rpc, notification, orm, action });
        }
        return super._getModel(...arguments);
    },

    turnOffCamera() {
        this.state.cameraScannedEnabled = false;
    },

});

// MainComponent.components.Header = HeaderComponent;
