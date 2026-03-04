/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { _t } from "@web/core/l10n/translation";

export class MultiFileViewer extends Component {
    setup() {
        this.orm = useService("orm");
        this.state = useState({
            currentIndex: 0,
        });

        onWillUpdateProps((nextProps) => {
            // Khi props thay đổi, danh sách file có thể thay đổi độ dài.
            // Cần tính toán lại files từ nextProps để clamp currentIndex.
            // Tuy nhiên, vì getter this.files phụ thuộc vào this.props (hiện tại),
            // nên ta cần giả lập tính toán trên nextProps, hoặc đơn giản là để render cycle xử lý
            // và ta check clamp ở ngay đầu render hoặc getter.

            // Tốt nhất: Cứ để props update. currentIndex sẽ được clamp trong các getter access 
            // HOẶC clamp nó ngay đây dự trên length của nextProp data.

            const nextFieldValue = nextProps.record.data[nextProps.name];
            let nextLength = 0;
            if (nextFieldValue && Array.isArray(nextFieldValue.records)) {
                // Filter thô sơ để ước lượng length, chính xác thì nên dùng logic giống getter
                // Nhưng ở đây ta chỉ cần đảm bảo index không crash.
                // Thực tế, ta có thể clamp index ngay khi access 'currentFile'
                nextLength = nextFieldValue.records.length;
            }

            if (this.state.currentIndex >= nextLength) {
                this.state.currentIndex = Math.max(0, nextLength - 1);
            }
        });
    }

    get files() {
        const props = this.props;
        const fieldValue = props.record.data[props.name];

        // Get expected attachment_type
        let expectedType = null;
        // Logic lấy attachment_type tương tự cũ
        if (props.record.context?.default_attachment_type) {
            expectedType = props.record.context.default_attachment_type;
        } else if (props.context?.default_attachment_type) {
            expectedType = props.context.default_attachment_type;
        } else {
            const typeMap = {
                'supplier_payment_bill_ids': 'supplier_payment_bill',
                'supplier_shipping_bill_ids': 'supplier_shipping_bill',
                'wire_transfer_ids': 'wire_transfer',
                'goods_inspection_ids': 'goods_inspection',
                'goods_receipt_ids': 'goods_receipt',
                'other_attachment_ids': 'other',
            };
            expectedType = typeMap[props.name];
        }

        if (!fieldValue || !Array.isArray(fieldValue.records)) {
            return [];
        }

        return fieldValue.records
            .filter(record => {
                const recordType = record.data.attachment_type;
                if (expectedType && recordType && recordType !== expectedType) {
                    return false;
                }
                return true;
            })
            .map(record => {
                const isSaved = Number.isInteger(record.resId);
                const mimetype = record.data.mimetype || 'application/pdf';
                let url = null;

                if (isSaved) {
                    url = `/web/content/advance.request.attachment/${record.resId}/file_data`;
                } else if (record.data.file_data) {
                    url = `data:${mimetype};base64,${record.data.file_data}`;
                }

                return {
                    id: record.resId,
                    name: record.data.name || 'File',
                    mimetype: mimetype,
                    attachment_type: record.data.attachment_type,
                    url: url
                };
            });
    }

    get currentFile() {
        const files = this.files;
        if (files.length === 0) return null;
        // Safety check index everytime
        if (this.state.currentIndex >= files.length) {
            return files[files.length - 1];
        }
        return files[this.state.currentIndex];
    }

    get totalFiles() {
        return this.files.length;
    }

    get hasFiles() {
        return this.files.length > 0;
    }

    get canGoPrevious() {
        return this.state.currentIndex > 0;
    }

    get canGoNext() {
        return this.state.currentIndex < this.files.length - 1;
    }

    get fileUrl() {
        if (!this.currentFile) return null;
        return this.currentFile.url;
    }

    get isPDF() {
        if (!this.currentFile) return false;
        const mimetype = this.currentFile.mimetype || '';
        return mimetype.includes('pdf');
    }

    get isImage() {
        if (!this.currentFile) return false;
        const mimetype = this.currentFile.mimetype || '';
        return mimetype.includes('image');
    }

    onPrevious() {
        if (this.canGoPrevious) {
            this.state.currentIndex--;
        }
    }

    onNext() {
        if (this.canGoNext) {
            this.state.currentIndex++;
        }
    }

    onDownload() {
        if (!this.currentFile) return;
        const link = document.createElement('a');
        link.href = this.fileUrl;
        link.download = this.currentFile.name;
        link.click();
    }

    async onAddFile() {
        // Trigger file input
        const input = document.createElement('input');
        input.type = 'file';
        input.multiple = true;
        input.accept = '*/*';

        input.onchange = async (e) => {
            const files = Array.from(e.target.files);
            if (files.length === 0) return;

            // Xác định attachment_type
            let attachmentType = null;
            if (this.props.record.context?.default_attachment_type) {
                attachmentType = this.props.record.context.default_attachment_type;
            } else if (this.props.context?.default_attachment_type) {
                attachmentType = this.props.context.default_attachment_type;
            } else {
                const typeMap = {
                    'supplier_payment_bill_ids': 'supplier_payment_bill',
                    'supplier_shipping_bill_ids': 'supplier_shipping_bill',
                    'wire_transfer_ids': 'wire_transfer',
                    'goods_inspection_ids': 'goods_inspection',
                    'goods_receipt_ids': 'goods_receipt',
                    'other_attachment_ids': 'other',
                };
                attachmentType = typeMap[this.props.name];
            }

            if (!attachmentType) {
                alert('Lỗi: Không xác định được loại chứng từ');
                return;
            }

            // Đọc tất cả các file
            const commands = [];

            for (const file of files) {
                const base64Data = await new Promise((resolve) => {
                    const reader = new FileReader();
                    reader.onload = (e) => resolve(e.target.result.split(',')[1]);
                    reader.readAsDataURL(file);
                });

                commands.push([0, 0, {
                    attachment_type: attachmentType,
                    name: file.name,
                    file_data: base64Data,
                    mimetype: file.type || 'application/octet-stream',
                }]);
            }

            if (commands.length > 0) {
                await this.props.record.update({
                    [this.props.name]: commands
                });
            }
        };

        input.click();
    }

    async onDeleteFile() {
        if (!this.currentFile) return;

        // Confirm deletion
        if (!confirm(`Bạn có chắc muốn xóa file "${this.currentFile.name}"?`)) {
            return;
        }

        const currentFileId = this.currentFile.id;

        // Delete from One2many field using array operation [2, id]
        await this.props.record.update({
            [this.props.name]: [[2, currentFileId]]
        });

        // Không cần splice thủ công nữa vì onWillUpdateProps sẽ gọi loadFiles với nextProps
        // logic loadFiles sẽ tự động cập nhật lại state.files dựa trên dữ liệu mới nhất từ Odoo
    }
}

MultiFileViewer.template = "ttb_purchase.MultiFileViewer";
MultiFileViewer.props = {
    ...standardFieldProps,
    context: { type: Object, optional: true },
};

export const multiFileViewer = {
    component: MultiFileViewer,
    supportedTypes: ["one2many"],
    extractProps: ({ attrs, field, record }) => {
        // Extract context from attrs and merge with record context
        const attrContext = attrs.context ?
            (typeof attrs.context === 'string' ?
                JSON.parse(attrs.context.replace(/'/g, '"')) :
                attrs.context
            ) : {};

        console.log('extractProps called:', {
            attrs,
            field,
            attrContext,
            recordContext: record?.context,
        });

        return {
            readonly: attrs.readonly,
            context: attrContext,
        };
    },
};

registry.category("fields").add("multi_file_viewer", multiFileViewer);

