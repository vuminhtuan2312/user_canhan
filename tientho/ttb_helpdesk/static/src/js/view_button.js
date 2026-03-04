import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { ViewButton } from "@web/views/view_button/view_button";
import { pick } from "@web/core/utils/objects";

patch(ViewButton.prototype, {
    setup() {
        super.setup();
        if ("voip" in this.env.services) {
            // FIXME: this is only because otherwise @web tests would fail.
            // This is one of the major pitfalls of patching.
            this.voip = useService("voip");
            this.callService = useService("voip.call");
            this.userAgent = useService("voip.user_agent");
        }
    },
    onClick(ev) {
        if (this.props.clickParams.name !== "make_phone_call") {
            return super.onClick(...arguments);
        }
        if (this.props.tag === "a") {
            ev.preventDefault();
        }
        if (!this.voip?.canCall) {
            return;
        }
        if (this.props.onClick) {
            return this.props.onClick();
        }
        var self = this;
        this.env.onClickViewButton({
            clickParams: this.clickParams,
            getResParams: () =>
                pick(
                    this.props.record || {},
                    "context",
                    "evalContext",
                    "resModel",
                    "resId",
                    "resIds"
                ),
            beforeExecute: () => this.dropdownControl.close(),
        }).then(function () {
            const fieldName = 'partner_phone';
            const { record } = self.props;
            self.userAgent.makeCall({
                phone_number: record.data[fieldName],
                res_id: record.resId,
                res_model: record.resModel,
            });
        });
    }
});
