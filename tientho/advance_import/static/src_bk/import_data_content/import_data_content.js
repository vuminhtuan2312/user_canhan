import { ImportDataContent } from "@base_import/import_data_content/import_data_content";
// import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(ImportDataContent.prototype, {
    onRelationFieldInput(column, value) {
        column.selectedRelationField = value;
    },
});
