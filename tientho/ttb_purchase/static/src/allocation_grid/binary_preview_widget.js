/** @odoo-module **/

import { registry } from "@web/core/registry";
import { BinaryField } from "@web/views/fields/binary/binary_field";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, onWillUpdateProps, useState, onWillDestroy } from "@odoo/owl";
import { FileUploader } from "@web/views/fields/file_handler";
import { isBinarySize } from "@web/core/utils/binary";
import { url } from "@web/core/utils/urls";

const IMAGE_MIME = "image/*";
const PDF_MIME = "application/pdf";

export class BinaryPreviewWidget extends BinaryField {
    static template = "ttb_purchase.BinaryPreviewWidget";
    static components = { FileUploader };
    static props = {
        ...standardFieldProps,
        acceptedFileExtensions: { type: String, optional: true },
        fileNameField: { type: String, optional: true },
    };
    static defaultProps = { acceptedFileExtensions: "*" };

    setup() {
        super.setup();
        this.objectUrl = null;
        this.state = useState({
            fileType: null,
            previewSrc: null,
            loading: false,
        });
        this.loadPreview(this.props);

        onWillUpdateProps((nextProps) => {
            const nextValue = this.getRawValue(nextProps);
            const currentValue = this.getRawValue(this.props);
            if (nextValue !== currentValue || nextProps.record.resId !== this.props.record.resId) {
                this.loadPreview(nextProps);
            }
        });

        onWillDestroy(() => this.revokeObjectUrl());
    }

    getRawValue(props) {
        return props.record.data[props.name];
    }

    getFileValue(props) {
        const value = this.getRawValue(props);
        if (!value || isBinarySize(value)) {
            return null;
        }
        return value;
    }

    buildDataUrl(fileType, base64Value) {
        const mime = fileType === "pdf" ? PDF_MIME : IMAGE_MIME;
        return `data:${mime};base64,${base64Value}`;
    }

    async loadPreview(props) {
        const base64Value = this.getFileValue(props);

        if (base64Value) {
            const fileType = this.determineFileType(base64Value);
            this.revokeObjectUrl();
            this.state.previewSrc = this.buildDataUrl(fileType, base64Value);
            this.state.fileType = fileType;
            return;
        }

        if (props.record.resId && this.getRawValue(props)) {
            await this.fetchPreviewFromServer(props);
            return;
        }

        this.revokeObjectUrl();
        this.state.previewSrc = null;
        this.state.fileType = null;
    }

    async fetchPreviewFromServer(props) {
        try {
            this.state.loading = true;
            const contentUrl = url("/web/content", {
                model: props.record.resModel,
                field: props.name,
                id: props.record.resId,
            });
            const response = await fetch(contentUrl);
            if (!response.ok) {
                throw new Error("Không thể tải file");
            }
            const blob = await response.blob();
            this.revokeObjectUrl();
            this.objectUrl = URL.createObjectURL(blob);
            this.state.previewSrc = this.objectUrl;
            this.state.fileType = this.getFileTypeFromMime(blob.type);
        } catch (error) {
            console.error("Binary preview error:", error);
            this.state.previewSrc = null;
            this.state.fileType = null;
        } finally {
            this.state.loading = false;
        }
    }

    getFileTypeFromMime(mime) {
        if (mime === PDF_MIME) {
            return "pdf";
        }
        if (mime && mime.startsWith("image/")) {
            return "image";
        }
        return "unknown";
    }

    determineFileType(value) {
        try {
            const bytes = Uint8Array.from(atob(value), (c) => c.charCodeAt(0));
            if (bytes[0] === 0x25 && bytes[1] === 0x50 && bytes[2] === 0x44 && bytes[3] === 0x46) {
                return "pdf";
            }
            if (bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff) return "image";
            if (bytes[0] === 0x89 && bytes[1] === 0x50 && bytes[2] === 0x4e && bytes[3] === 0x47) return "image";
            if (bytes[0] === 0x47 && bytes[1] === 0x49 && bytes[2] === 0x46 && bytes[3] === 0x38) return "image";
            if (bytes[0] === 0x52 && bytes[1] === 0x49 && bytes[2] === 0x46 && bytes[3] === 0x46 &&
                bytes[8] === 0x57 && bytes[9] === 0x45 && bytes[10] === 0x42 && bytes[11] === 0x50) {
                return "image";
            }
        } catch (error) {
            console.error("determineFileType", error);
        }
        return "unknown";
    }

    revokeObjectUrl() {
        if (this.objectUrl) {
            URL.revokeObjectURL(this.objectUrl);
            this.objectUrl = null;
        }
    }

    get previewSrc() {
        return this.state.previewSrc;
    }

    get fileType() {
        return this.state.fileType;
    }

    async update({ data, name }) {
        const result = await super.update({ data, name });
        await this.loadPreview(this.props);
        return result;
    }
}

export const binaryPreviewField = {
    component: BinaryPreviewWidget,
    supportedTypes: ["binary"],
    extractProps: ({ attrs, options }) => ({
        acceptedFileExtensions: options.accepted_file_extensions,
        fileNameField: attrs.filename,
    }),
};

registry.category("fields").add("binary_preview_ticket", binaryPreviewField);