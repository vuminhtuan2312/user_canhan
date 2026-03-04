import { SoftphoneContainer } from "@voip/softphone/softphone_container";
import { UserAgent } from "@voip/core/user_agent_service";

import { xml } from "@odoo/owl";
import { user } from "@web/core/user";
import { patch } from "@web/core/utils/patch";

SoftphoneContainer.template = xml`
    <div class="o-voip-SoftphoneContainer" style="z-index: 2000;position: absolute;">
        <Softphone t-if="voip.softphone.isDisplayed"/>
    </div>
`;

patch(UserAgent.prototype, {
    /** @param {Object} data */
    async makeCall(data) {
        await super.makeCall(...arguments);
        var record_data = this.getDefaultRecordData()
        if (data.res_model === 'ttb.happy.call' && data.res_id) {
            record_data = data
            record_data.action_name = 'Happy call'
        } else {
            this.openRecord(record_data)
        }
    },

    async acceptIncomingCall() {
        await super.acceptIncomingCall(...arguments);
        this.openRecord(this.getDefaultRecordData())
    },

    async openRecord(data) {
        if (data.res_model) {
            const resModel = data.res_model;
            const resId = data.res_id;
            const viewId = await this.env.services.orm.call(resModel, "get_formview_id", [[resId]], {
                context: user.context,
            });
            this.env.services.action.doAction({
                type: "ir.actions.act_window",
                res_id: resId,
                res_model: resModel,
                views: [[viewId || false, "form"]],
                view_mode: "form",
                view_type: "form",
                target: "new",
                context: data.context || {},
                name: data.action_name
            });
        }
    },
    getDefaultRecordData() {
        var record_data = {
            res_id: false,
            res_model: 'ttb.transaction',
            action_name: 'Tương tác',
            context: {
                default_partner_phone: this.session.call.phoneNumber,
                default_user_id: this.env.uid,
                default_voip_call_id: this.session.call.id,
            }
        }
        if (this.session.call.partner.id) {
            record_data.context.default_partner_id = this.session.call.partner.id
        }
        return record_data
    }

});
