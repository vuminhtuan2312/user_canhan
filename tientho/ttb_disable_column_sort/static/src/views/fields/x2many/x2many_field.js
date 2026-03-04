/** @odoo-module **/

import { ListRenderer } from "@web/views/list/list_renderer";

const _super_onClickSortColumn = ListRenderer.prototype.onClickSortColumn;

ListRenderer.prototype.onClickSortColumn = function (column) {
    if (this.props.list.context?.disable_column_sort) {
        return;
    } else {
        return _super_onClickSortColumn.call(this, column);
    }
};
