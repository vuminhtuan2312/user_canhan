/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import { ListRenderer } from "@web/views/list/list_renderer";

class ResultCheckListRenderer extends ListRenderer {
	get getEmptyRowIds() {
		return [];
	}
	get canCreate() {
		return false;
	}
	get displayRowCreates() {
		return false;
	}
}

class One2ManyResultCheckField extends X2ManyField {
	static template = "web.X2ManyField";
	static components = {
		...X2ManyField.components,
		ListRenderer: ResultCheckListRenderer,
	};
}

// Reuse x2ManyField config, chỉ thay component và giới hạn one2many
const one2manyResultCheck = {
	...x2ManyField,
	component: One2ManyResultCheckField,
	displayName: _t("Relational table (no empty rows)"),
	supportedTypes: ["one2many"],
};

registry.category("fields").add("one2many_result_check", one2manyResultCheck);
