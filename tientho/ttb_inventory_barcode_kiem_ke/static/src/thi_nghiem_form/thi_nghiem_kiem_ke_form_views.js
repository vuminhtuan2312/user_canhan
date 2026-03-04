/** @odoo-module */

import { formView } from '@web/views/form/form_view';
import { registry } from "@web/core/registry";
import { ThiNgiemKiemKeFormRenderer } from "@ttb_inventory_barcode_kiem_ke/thi_nghiem_form/thi_nghiem_kiem_ke_form";
import { ThiNgiemKiemKeFormController } from "@ttb_inventory_barcode_kiem_ke/thi_nghiem_form/thi_nghiem_kiem_ke_form_controller";

export const thiNghiemKiemKeFormView = {
    ...formView,
    Renderer: ThiNgiemKiemKeFormRenderer,
    Controller: ThiNgiemKiemKeFormController,
}

registry.category("views").add("kiem_ke_thi_nghiem_form", thiNghiemKiemKeFormView);