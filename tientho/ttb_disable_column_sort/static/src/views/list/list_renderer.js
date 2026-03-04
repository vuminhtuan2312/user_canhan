/** @odoo-module **/

import { registry } from "@web/core/registry";
import { ListRenderer } from "@web/views/list/list_renderer";
import { listView } from "@web/views/list/list_view";

export class TtbDisableColumnSortListRenderer extends ListRenderer {
    onClickSortColumn(column) {
        return;
    }
};

export const TtbDisableColumnSortListView = {
    ...listView,
    Renderer: TtbDisableColumnSortListRenderer,
};

registry.category("views").add("ttb_disable_comlumn_list_view", TtbDisableColumnSortListView);
