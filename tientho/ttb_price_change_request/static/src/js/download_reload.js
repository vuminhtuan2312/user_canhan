/** @odoo-module **/

import { registry } from "@web/core/registry";
import { download } from "@web/core/network/download";

// Đăng ký action mới vào registry
registry.category("actions").add("action_download_and_reload", async (env, action) => {
    const url = action.params.url;

    if (url) {

        await download({
            url: url,
            data: {},
        });
    }
    await env.services.action.doAction({
        type: "ir.actions.client",
        tag: "reload",
    });
});