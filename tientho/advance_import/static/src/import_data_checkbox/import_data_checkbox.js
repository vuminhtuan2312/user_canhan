import { ImportDataContent } from "@base_import/import_data_content/import_data_content";
import { Component, useState, onWillStart } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

export class ImportDataCheckBox extends Component {
    static template = "ImportDataCheckBox";
    static props = {
        fieldInfo: { type: Object },
        onOptionChanged: { type: Function },
    }
    setup() {
        super.setup();
        this.rpc = rpc;
        this.state = useState({
            isLinking: false,
            availableFields: {},
            selectField: ''
        });
    }

    async onLinkingChecked(ev) {
        this.state.isLinking = !this.state.isLinking;
        if (this.state.isLinking) {
            const fields = await rpc(`/web/dataset/call_kw/${this.props.fieldInfo.comodel_name}/fields_get`, {
                                                model: this.props.fieldInfo.comodel_name,
                                                method: "fields_get",
                                                args: [],
                                                kwargs: {},
                                            });
            if (fields) {
                this.state.availableFields[this.props.fieldInfo.fieldPath] = fields;
                this.state.selectedField = this.props.fieldInfo.fieldPath;
            }
        } else {
            this.state.selectedField = '';
            delete this.state.availableFields[this.props.fieldInfo.fieldPath];
        }
    }

    onOptionChecked(ev) {
        if (ev.target.checked) {
            this.props.onOptionChanged(
                ev.target.value,
                ev.target.value,
                this.props.fieldInfo.fieldPath
            );
        } else {
            const value = {
                fallback_values: 'prevent',
                field_model: this.props.fieldInfo.comodel_name || this.props.fieldInfo.model_name,
                field_type: this.props.fieldInfo.type,
            }
            this.props.onOptionChanged(
                "fallback_values",
                value,
                this.props.fieldInfo.fieldPath,
            );
        }
    }

    onLinkingSelectionChanged(ev) {
        if (this.state.selectedField) {
            const value = {
                linking_via_field: ev.target.value,
                field_model: this.props.fieldInfo.comodel_name
            };
            this.props.onOptionChanged("linking", value, this.props.fieldInfo.fieldPath);
        } else {
            const value = {
                fallback_values: 'undo_linking',
                field_model: this.props.fieldInfo.comodel_name,
                field_type: this.props.fieldInfo.type,
            }
            this.props.onOptionChanged(
                "fallback_values",
                value,
                this.props.fieldInfo.fieldPath,
            );
        }
    }
    onCheckForDuplicatesChecked(ev) {
        if (ev.target.checked) {
            this.props.onOptionChanged(
                ev.target.value,
                ev.target.value,
                this.props.fieldInfo.fieldPath
            );
        } else {
            this.props.onOptionChanged(
                "remove_from_check_for_duplicates",
                "remove_from_check_for_duplicates",
                this.props.fieldInfo.fieldPath
            );
        }
    }
}
