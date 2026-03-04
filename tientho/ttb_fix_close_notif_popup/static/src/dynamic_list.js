/** @odoo-module **/

import { DynamicList } from "@web/model/relational_model/dynamic_list";
import { patch } from "@web/core/utils/patch";

patch(DynamicList.prototype, {
    async leaveEditMode({ discard } = {}) {
        let editedRecord = this.editedRecord;
        if (editedRecord) {
            if (discard) {
                return super.leaveEditMode(...arguments);
            } else {
                if (editedRecord.isNew) {
                    this._removeRecords([editedRecord.id]);
                }
                return super.leaveEditMode(...arguments);
            }
        }
        return super.leaveEditMode(...arguments);
    }
})
