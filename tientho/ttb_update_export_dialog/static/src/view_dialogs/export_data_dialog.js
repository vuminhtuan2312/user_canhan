/** @odoo-module **/

import { ExportDataDialog } from "@web/views/view_dialogs/export_data_dialog";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(ExportDataDialog.prototype, {
    onDraggingEnd(item, target) {
        this.enterTemplateEdition();
        super.onDraggingEnd(...arguments);
    },

    onAddItemExportList(fieldId) {
        this.enterTemplateEdition();
        super.onAddItemExportList(...arguments);
    },

    onRemoveItemExportList(fieldId) {
        this.enterTemplateEdition();
        super.onRemoveItemExportList(...arguments);
    },

    async onUpdateExportTemplate() {
         const id = this.state.templateId;
         await this.orm.write(
             "ir.exports",
                [id],
                {
                     export_fields: [
                      [5],
                      ...this.state.exportList.map((field) => [
                         0,
                         0,
                         {
                             name: field.id,
                         },
                     ]),
                 ],
                 resource: this.props.root.resModel,
                },
             { context: this.props.context }
         );
         this.state.isEditingTemplate = false;
         this.notification.add(_t("Templated updated"), {
                 type: "success",}
         );
    }
})