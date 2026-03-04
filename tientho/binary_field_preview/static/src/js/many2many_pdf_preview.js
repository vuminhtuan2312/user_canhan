/** @odoo-module **/

import { Many2ManyBinaryField } from "@web/views/fields/many2many_binary/many2many_binary_field";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { useFileViewer } from "@web/core/file_viewer/file_viewer_hook";
import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

export class Many2ManyPDFPreview extends Many2ManyBinaryField {
    static props = {
        ...super.props, // Kế thừa tất cả các props từ class cha
        showPreview: { type: Boolean, optional: true }, // Khai báo prop mới
    };
    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.fileViewer = useFileViewer();
    }
    onClickPreviewPDF(ev, file, files) {
        ev.stopPropagation();
        const attachments = files.map(f => this.store.Attachment.insert({
            id: f.id,
            filename: f.name,
            name: f.name,
            mimetype: f.mimetype,
        }));
        const attachment = attachments.find(a => a.id === file.id);
        if (attachment) {
            this.fileViewer.open(attachment, attachments);
        }
    }
}

export const many2manyPDFPreview = {
    component: Many2ManyPDFPreview,
    supportedOptions: [
        {
            label: "Accepted file extensions",
            name: "accepted_file_extensions",
            type: "string",
        },
        {
            label: "Number of files",
            name: "number_of_files",
            type: "integer",
        },
    ],
    supportedTypes: ["many2many"],
    isEmpty: () => false,
    relatedFields: [
        { name: "name", type: "char" },
        { name: "mimetype", type: "char" },
    ],
    extractProps: ({ attrs, options }) => ({
        acceptedFileExtensions: options.accepted_file_extensions,
        className: attrs.class,
        numberOfFiles: options.number_of_files,
        // Nếu không được chỉ định, mặc định là false (không hiện).
        showPreview: options.show_preview || false,
    }),
};

registry.category("fields").add("many2many_pdf_preview", many2manyPDFPreview); 