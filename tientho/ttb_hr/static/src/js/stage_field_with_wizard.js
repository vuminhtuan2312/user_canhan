/** @odoo-module **/

import { StatusBarDurationField } from "@mail/views/fields/statusbar_duration/statusbar_duration_field";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class StatusBarDurationShowPopUp extends StatusBarDurationField {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
    }

    getAllItems() {
        // Lấy thứ tự từ widget gốc
        const items = super.getAllItems();
        // Đảo ngược lại thứ tự nếu đang bị ngược
        return items.slice().reverse();
    }

    async selectItem(item) {
        // Nếu đang ở stage hiện tại thì không làm gì
        if (item.value === this.props.value) return;

        // Kiểm tra có template_id không (dựa vào record data)
        const applicantId = this.props.record.resId;
        const newStageId = item.value;

        try {
            // Gọi hàm open_change_stage_wizard trên server
            const action = await this.orm.call(
                "hr.applicant",
                "open_change_stage_wizard",
                [[applicantId], newStageId]
            );
            if (action) {
                // Nếu có action, mở wizard pop-up
                await this.actionService.doAction(action, {
                    onClose: async () => {
                        // Sau khi đóng wizard, reload lại record
                        await this.props.record.model.load();
                    },
                });
                return;
            }
        } catch (error) {
            this.notification.add(error.message, { type: "danger" });
            return;
        }

        // Nếu không có wizard, thực hiện chuyển stage như bình thường
        return super.selectItem(item);
    }
}

// Lấy cấu hình gốc của statusbar_duration
const originalStatusBarDuration = registry.category("fields").get("statusbar_duration");

// Đăng ký widget mới với cấu hình hoàn toàn giống widget gốc
registry.category("fields").add("statusbar_duration_show_pop_up", {
    component: StatusBarDurationShowPopUp,
    displayName: originalStatusBarDuration.displayName,
    supportedTypes: originalStatusBarDuration.supportedTypes,
    fieldDependencies: originalStatusBarDuration.fieldDependencies,
    // Đảm bảo kế thừa tất cả các thuộc tính khác
    ...originalStatusBarDuration,
    // Override lại component để sử dụng class mới
    component: StatusBarDurationShowPopUp,
});
