import { CallService } from "@voip/core/call_service";
import { patch } from "@web/core/utils/patch";
import { browser } from "@web/core/browser/browser";

patch(CallService.prototype, {
    async start(call) {
        const [data] = await this.orm.call("voip.call", "start_call", [[call.id]]);
        this.store.Call.insert(data);
        call.timer = {};
        // Use the time from the client (rather than call.start_date) to avoid
        // clock skew with the server.
        const timerStart = luxon.DateTime.now();
        const computeDuration = () => {
            call.timer.time = Math.floor((luxon.DateTime.now() - timerStart) / 1000);
        };
        computeDuration();
        call.timer.interval = browser.setInterval(computeDuration, 1000);
    }
});
