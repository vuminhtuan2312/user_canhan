/** @odoo-module **/


import { registry } from "@web/core/registry";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";

export class PsSearchOption extends X2ManyField {
    onInputKeyUp(event) {
        let value = event.currentTarget.value.toLowerCase();
        let rows = document.querySelectorAll(".o_list_table tr");
        rows.forEach((row, index) => {
            if (index === 0) return;
            let isMatch = false;
            if (this.props.context['search_by'] !== undefined) {
                if (Array.isArray(this.props.context['search_by'])) {
                    for (const key of this.props.context['search_by']){
                        if (row.cells[key] === undefined) {
                            continue;
                        }
                        let text = row.cells[key].textContent.toLowerCase();
                        isMatch = text.includes(value);
                        if (isMatch === true) {
                            break;
                        }
                    }
                } else if (row[this.props.context['search_by']] !== undefined) {
                    let text = row.cells[this.props.context['search_by']].textContent.toLowerCase();
                    isMatch = text.includes(value);
                }
            } else {
                let text = row.textContent.toLowerCase();
                isMatch = text.includes(value);
            }
            row.style.display = isMatch ? "" : "none";
        });
    }
}

PsSearchOption.template = "PsSearchOptionTemplate";

export const SearchOption = {
    ...x2ManyField,
    component: PsSearchOption,
};

registry.category("fields").add("search_section_and_note_one2many", SearchOption);
