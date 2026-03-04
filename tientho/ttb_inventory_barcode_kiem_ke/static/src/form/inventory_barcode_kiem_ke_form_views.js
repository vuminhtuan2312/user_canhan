/** @odoo-module */

import { formView } from '@web/views/form/form_view';
import { registry } from "@web/core/registry";
import { KiemKeBarcodeFormRenderer } from "@ttb_inventory_barcode_kiem_ke/form/inventory_barcode_kiem_ke_form";
import { KiemKeBarcodeFormController } from "@ttb_inventory_barcode_kiem_ke/form/inventory_barcode_kiem_ke_form_controller";

export const kiemKeFormView = {
    ...formView,
    Renderer: KiemKeBarcodeFormRenderer,
    Controller: KiemKeBarcodeFormController,
}

registry.category("views").add("kiem_ke_form", kiemKeFormView);