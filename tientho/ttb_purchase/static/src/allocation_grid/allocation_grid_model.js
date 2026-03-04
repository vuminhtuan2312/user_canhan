/** @odoo-module */

import { serializeDate } from "@web/core/l10n/dates";
import { GridDataPoint, GridModel, GridRow } from "@web_grid/views/grid_model";
import { Domain } from "@web/core/domain";

export class AllocationGridRow extends GridRow {
    getGrandMax() {
        return parseFloat(this.valuePerFieldName['order_id'][1]);
    }
}

export class AllocationGridDataPoint extends GridDataPoint {
    /**
     * @override
     */
    async _searchMany2oneColumns(domain, readonlyField) {
        const fieldsToFetch = ["id", "display_name"];
        if (readonlyField) {
            fieldsToFetch.push(readonlyField);
        }
        const columnField = this.fieldsInfo[this.columnFieldName];
        const columnRecords = await this.orm.searchRead(
            columnField.relation,
            domain || [],
            fieldsToFetch,{context:this.searchParams.context}
        );
        return columnRecords.map((read) => Object.values(read));
    }
}

export class AllocationGridModel extends GridModel {
     static DataPoint = AllocationGridDataPoint;
     static Row = AllocationGridRow;
}
