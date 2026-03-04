/** @odoo-module */

import { gridView } from "@web_grid/views/grid_view";
import { AllocationGridModel } from "./allocation_grid_model";
import { AllocationGridRenderer } from "./allocation_grid_renderer";
import { registry } from "@web/core/registry";


export const allocationGridView = {
     ...gridView,
    Model: AllocationGridModel,
    Renderer: AllocationGridRenderer,
    searchMenuTypes: ["filter", "favorite"],
};

registry.category("views").add('ttb_allocation_grid', allocationGridView);
