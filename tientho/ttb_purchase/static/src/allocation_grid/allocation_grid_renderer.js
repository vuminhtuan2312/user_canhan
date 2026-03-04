/** @odoo-module */

import { GridRenderer } from "@web_grid/views/grid_renderer";
import { onWillStart } from "@odoo/owl";
import { useState, useExternalListener, reactive } from "@odoo/owl";
import { session } from "@web/session";

export class AllocationGridRenderer extends GridRenderer {
    static template = "ttb_purchase.AllocationGridRenderer";
}
