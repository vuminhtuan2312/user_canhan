import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { Many2ManyTagsField, many2ManyTagsField } from "@web/views/fields/many2many_tags/many2many_tags_field";
import { registry } from "@web/core/registry";

export class Many2XAutocompleteUnlimit extends Many2XAutocomplete {
    static defaultProps = {
        ...Many2XAutocomplete.defaultProps,
        searchLimit: 2000,
    };
}

export class Many2ManyTagsFieldUnlimit extends Many2ManyTagsField {
    static components = {
        ...Many2ManyTagsField.components,
        Many2XAutocomplete: Many2XAutocompleteUnlimit,
    };
}
const many2ManyTagsFieldUnlimit = Object.assign(many2ManyTagsField, {component: Many2ManyTagsFieldUnlimit});
registry.category("fields").add("many2many_tags_unlimit", many2ManyTagsFieldUnlimit);
