/** @odoo-module **/

const { Component, useComponent } = owl;
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";

/**
 * Systray item allowing to toggle the voip DialingPanel.
 */
export class EnLoginAsSystrayItem extends Component {
    setup() {
        this.action = useService('action');
    }
    /**
     * Toggle the dialing panel.
     */
    onClick() {
        this.action.doAction('en_login_as.wizard_login_as_action')
    }
}
EnLoginAsSystrayItem.template = "en_login_as.SystrayItem";

export const systrayItem = {
    Component: EnLoginAsSystrayItem,
    isDisplayed: (env) => user.isSystem,
};

registry.category("systray").add("EnLoginAsSystrayItem", systrayItem, { sequence: 1 });
