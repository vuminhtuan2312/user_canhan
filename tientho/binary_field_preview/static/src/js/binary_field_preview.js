/** @odoo-module **/

import { registry } from "@web/core/registry";
import { BinaryField } from "@web/views/fields/binary/binary_field";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { isBinarySize, toBase64Length } from "@web/core/utils/binary";
import { _t } from "@web/core/l10n/translation";
import { Component, xml } from "@odoo/owl";
import { useFileViewer } from "@web/core/file_viewer/file_viewer_hook";

export class BinaryFieldPreview extends BinaryField {
    static template = "binary_field_preview.BinaryFieldPreview";
    static components = { BinaryField };

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.fileViewer = useFileViewer();
        this.store = useService("mail.store");
    }

    static props = {
        ...standardFieldProps,
        acceptedFileExtensions: { type: String, optional: true },
        fileNameField: { type: String, optional: true },
    };

    static defaultProps = {
        acceptedFileExtensions: "*",
    };

    async openPreview() {
        const model = this.props.record.resModel;
        const fieldName = this.props.name;
        const recordId = this.props.record.resId;

        if (!model || !fieldName || !recordId) {
            console.error("Missing required information to fetch attachment");
            return;
        }

        try {
            const attachment = await this.orm.call(
                model,
                "get_attachment_preview",
                [model, fieldName, recordId]
            );
            if (attachment) {
                const attach = this.store.Attachment.insert({
                    id: attachment.id,
                    filename: attachment.name,
                    name: attachment.name,
                    mimetype: attachment.mimetype,
                });
                this.fileViewer.open(attach);
            } else {
                console.error("No valid attachment received");
            }
        } catch (error) {
            console.error("Error fetching attachment:", error);
        }
    }

    get fileName() {
        return (
            this.props.record.data[this.props.fileNameField] ||
            this.props.record.data[this.props.name] ||
            ""
        ).slice(0, toBase64Length(MAX_FILENAME_SIZE_BYTES));
    }
}

export const binaryFieldPreview = {
    component: BinaryFieldPreview,
    displayName: _t("File"),
    supportedOptions: [
        {
            label: _t("Accepted file extensions"),
            name: "accepted_file_extensions",
            type: "string",
        },
    ],
    supportedTypes: ["binary"],
    extractProps: ({ attrs, options }) => ({
        acceptedFileExtensions: options.accepted_file_extensions,
        fileNameField: attrs.filename,
    }),
};

registry.category("fields").add("binary_preview", binaryFieldPreview);