/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("actions").add("reload_with_notification", async (env, action) => {
    const { message, type = "warning" } = action.params || {};

    // Lưu thông báo vào sessionStorage trước khi reload
    sessionStorage.setItem("pending_notification", JSON.stringify({ message, type }));

    // Reload trang
    window.location.reload();
});

// Sau khi reload xong, kiểm tra và hiển thị thông báo nếu có
const pending = sessionStorage.getItem("pending_notification");
if (pending) {
    sessionStorage.removeItem("pending_notification");
    const { message, type } = JSON.parse(pending);

    // Chờ khởi động xong rồi mới hiện thông báo
    setTimeout(() => {
        const notifService = owl.Component.env?.services?.notification;
        if (notifService) {
            notifService.add(message, { type, sticky: true });
        }
    }, 1000);
}