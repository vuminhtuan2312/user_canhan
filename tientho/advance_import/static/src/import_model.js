import { BaseImportModel } from "@base_import/import_model";
// import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(BaseImportModel.prototype, {
    async init() {
        await super.init(...arguments);

        // ✅ Thêm `create_only` (mặc định false, không có label/options)
        this.importOptionsValues.create_only = {
            value: false,
        };

        this.importOptionsValues.update_only = {
            value: false,
        };

        // ✅ Thêm `in_background` (mặc định false)
        this.importOptionsValues.in_background = {
            value: false,
        };

        this.importOptionsValues.relate_fields = {
            value: {}
        };

        this.importOptionsValues.skip_row_error = {
            value: false,
        };
        this.importOptionsValues.commit_per_record = {
            value: false,
        };
    },

    get importOptions() {
//        const options = super.importOptions;
        const tempImportOptions = {
          import_skip_records: [],
          import_set_empty_fields: [],
          fallback_values: {},
          name_create_enabled_fields: {},
          linking: {},
          check_for_duplicates: [],
        };
        for (const [name, option] of Object.entries(this.importOptionsValues)) {
            tempImportOptions[name] = option.value;
        }
        for (const key in this.fieldsToHandle) {
            const value = this.fieldsToHandle[key];
            if (value) {
                if (value.optionName === "import_skip_records") {
                    tempImportOptions.import_skip_records.push(key);
                } else if (value.optionName === "import_set_empty_fields") {
                    tempImportOptions.import_set_empty_fields.push(key);
                } else if (value.optionName === "name_create_enabled_fields") {
                    tempImportOptions.name_create_enabled_fields[key] = true;
                } else if (value.optionName === "fallback_values") {
                    tempImportOptions.fallback_values[key] = value.value;
                }
                if (value.optionName === "linking") {
                    tempImportOptions.linking[key] = value.value;
                }
                if (value.optionName === "check_for_duplicates") {
                    tempImportOptions.check_for_duplicates.push(key);
                }
                if (value.optionName === "remove_from_check_for_duplicates") {
                    const index = tempImportOptions.check_for_duplicates.indexOf(key);
                    if (index > -1) {
                        tempImportOptions.check_for_duplicates.splice(index, 1);
                    }
                }
            }
        }
        this._importOptions = tempImportOptions;
        return tempImportOptions;
    },
});
