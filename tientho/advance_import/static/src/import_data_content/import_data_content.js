import { ImportDataContent } from "@base_import/import_data_content/import_data_content";
import { ImportDataCheckBox } from "@advance_import/import_data_checkbox/import_data_checkbox";
import { patch } from "@web/core/utils/patch";

patch(ImportDataContent, {
    components: {
        ...ImportDataContent.components,
        ImportDataCheckBox
    }
})