/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Many2ManyBinaryField } from "@web/views/fields/many2many_binary/many2many_binary_field";
import { useService } from "@web/core/utils/hooks"; // Cần import hook này

export class Many2ManyBinaryCamera extends Many2ManyBinaryField {
    setup() {
        super.setup();
        // Nếu cần thêm logic khởi tạo, thêm ở đây
    }
    // Chỉ định component này sẽ sử dụng template XML mới của chúng ta
    static template = "ps_search_one2many_many2many.Many2ManyBinaryCamera";

    // Phương thức setup() được gọi một lần khi component được khởi tạo.
    // Chúng ta cần ghi đè nó để đảm bảo có thể truy cập được fileUploader.
    // Tuy nhiên, vì Many2ManyBinaryField đã gọi nó rồi, chúng ta chỉ cần
    // đảm bảo gọi đúng phương thức upload sau này.

    onClickAdd(ev) {
        ev.preventDefault();

        const fileInput = document.createElement("input");
        fileInput.type = "file";
        fileInput.accept = "image/*";
        fileInput.capture = "environment";
        fileInput.multiple = true;

        fileInput.onchange = async () => {
            if (!fileInput.files || fileInput.files.length === 0) {
                return;
            }

            const filesToUpload = [];
            for (const originalFile of fileInput.files) {
                const newFilename = `camera_capture_${Date.now()}.jpg`;
                const newFile = new File([originalFile], newFilename, { type: originalFile.type });
                filesToUpload.push(newFile);
            }

            if (filesToUpload.length > 0) {
                await this.onFileUploaded(filesToUpload);
            }
        };

        fileInput.click();
    }

    async onFileUploaded(files) {
        const resId = this.props.record.resId;
        const parentVirtualId = this.props.record._virtualId || this.props.record.virtualId;
        const list = this.props.record.data[this.props.name];
        for (const file of files) {
            if (file.error) {
                return this.notification.add(file.error, {
                    title: 'Uploading error',
                    type: 'danger',
                });
            }
            // 1. Upload file lên server, lấy attachment id
            const attachmentId = await this.uploadFileToServer(file);
            // 2. Add vào many2many
            if (resId) {
                await list.addAndRemove({ add: [attachmentId] });
            } else if (parentVirtualId) {
                await list.addAndRemove({ add: [attachmentId], virtualId: parentVirtualId });
            } else {
                this.notification.add('Không xác định được record để lưu file!', { type: 'danger' });
            }
        }
    }

    async uploadFileToServer(file) {
        // Lấy service ORM
        const orm = this.orm || (this.env && this.env.services && this.env.services.orm) || useService("orm");
        // Đọc file thành base64
        const base64 = await this.fileToBase64(file);
        // Gửi lên server tạo attachment
        const attachmentId = await orm.call("ir.attachment", "create", [{
            name: file.name,
            datas: base64,
            res_model: this.props.record.resModel,
            res_id: this.props.record.resId || 0,
        }]);
        return attachmentId;
    }

    fileToBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => {
                // Remove the prefix "data:*/*;base64,"
                const base64 = reader.result.split(",")[1];
                resolve(base64);
            };
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    }
}

// Lấy đối tượng đăng ký của widget gốc
const many2manyBinaryField = registry.category("fields").get("many2many_binary");

// Đăng ký widget mới
registry.category("fields").add("many2many_binary_camera", {
    ...many2manyBinaryField,
    component: Many2ManyBinaryCamera,
});