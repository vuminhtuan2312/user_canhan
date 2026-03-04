/** @odoo-module **/

// import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
// import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { registry } from "@web/core/registry";
// import { useBus, useService } from "@web/core/utils/hooks";
// import { Component, onWillStart, useState } from "@odoo/owl";
// import { ManualBarcodeScanner } from "../components/manual_barcode";
// import { standardActionServiceProps } from "@web/webclient/actions/action_service";
// import { url } from '@web/core/utils/urls';

import { MainMenu } from '@stock_barcode/main_menu/main_menu'

export class ProductMainMenu extends MainMenu {
    static template = "ttb_product_barcode.MainMenu";

    async _onBarcodeScanned(barcode) {
        const res = await rpc('/product_barcode/scan_from_main_menu', { barcode });
        if (res.action) {
            this.playSound("success");
            return this.actionService.doAction(res.action);
        }
        this.notificationService.add(res.warning, { type: 'danger' });
    }

}

registry.category('actions').add('product_barcode_main_menu', ProductMainMenu);
