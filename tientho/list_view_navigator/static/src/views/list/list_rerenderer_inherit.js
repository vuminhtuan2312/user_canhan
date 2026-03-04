/** @odoo-module **/

import { ListRenderer } from "@web/views/list/list_renderer";
import { patch } from "@web/core/utils/patch";

patch(ListRenderer.prototype, {
    onCellKeydownEditMode(hotkey, cell, group, record) {
        if (!hotkey.includes('arrowdown') && !hotkey.includes('arrowup')) {
            // Nếu không phải arrow up/down thì dùng hành vi gốc
            return super.onCellKeydownEditMode(...arguments)
        } else {
            const list = this.props.list;
            const index = list.records.indexOf(record);

            const navigateToCell = (futureRecord, direction) => {
                if (!futureRecord)
                    return;
                const futureCell = findFutureValueCell(cell, direction);
                if (futureCell) {
                    futureCell.click();
                }
            };

            if (hotkey === "arrowdown") {
                let futureRecord = (index + 1 >= 0 && index + 1 < list?.records?.length)
                    ? list.records[index + 1]
                    : undefined;
                if (this.topReCreate && index === 0) {
                    futureRecord = null;
                }
                if (!futureRecord && !this.canCreate) {
                    return;
                }
                navigateToCell(futureRecord, 'down');
            }

            if (hotkey === "arrowup") {
                let futureRecord = (index - 1 >= 0 && index - 1 < list?.records?.length)
                    ? list.records[index - 1]
                    : undefined;
                if (this.topReCreate && index === 0) {
                    futureRecord = null;
                }
                if (!futureRecord && !this.canCreate) {
                    return;
                }
                navigateToCell(futureRecord, 'up');
            }
        }
    },
});

function findFutureValueCell(cell, direction) {
    const row = cell.parentElement;
    const children = [...row.children];
    const index = children.indexOf(cell);

    let futureRow;
    if (direction === 'up') {
        futureRow = row.previousElementSibling;
    } else if (direction === 'down') {
        futureRow = row.nextElementSibling;
    }

    if (futureRow) {
        return (index >= 0 && index < futureRow.children?.length)
            ? futureRow.children[index]
            : undefined;
    }
    return null; // Trường hợp không có dòng tiếp theo
}
