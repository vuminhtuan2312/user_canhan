///** @odoo-module **/
//
//import { registry } from "@web/core/registry";
//import { Component } from "@odoo/owl";
//import { useService } from "@web/core/utils/hooks";
//import { standardFieldProps } from "@web/views/fields/standard_field_props";
//
//const fieldRegistry = registry.category("fields");
//
//class FieldClickableNumber extends Component {
//    static template = "ttb.FieldClickableNumber";
//    static props = { ...standardFieldProps };
//
//    setup() {
//        this.orm = useService("orm");
//        this.action = useService("action");
//    }
//
//    /** Lấy raw value ổn định từ record -> fallback sang props.value -> 0 */
//    get rawValue() {
//        const name = this.props.name;
//        const rec  = this.props.record;
//        let val =
//            (rec && rec.data && Object.prototype.hasOwnProperty.call(rec.data, name) ? rec.data[name] : undefined);
//        if (val === undefined && rec && rec.values && Object.prototype.hasOwnProperty.call(rec.values, name)) {
//            val = rec.values[name];
//        }
//        if (val === undefined) {
//            val = this.props.value;
//        }
//        // Chuẩn hoá về number
//        if (typeof val === "string" && val !== "") {
//            const n = Number(val);
//            return Number.isNaN(n) ? 0 : n;
//        }
//        return (typeof val === "number") ? val : 0;
//    }
//
//    async onClick(ev) {
//        ev.preventDefault();
//        ev.stopPropagation();
//
//        const rec = this.props.record;
//        const resId = rec?.resId;
//        const resModel = rec?.resModel;
//        if (!resModel || !resId) return; // hàng tổng/nhóm không có id
//
//        const fieldName = this.props.name;
//        const method =
//            (this.props.options && this.props.options.method) ||
//            `action_open_${fieldName}`;
//
//        const ctx = rec.context || {};
//        const action = await this.orm.call(resModel, method, [resId], { context: ctx });
//        if (action) {
//            await this.action.doAction(action);
//        }
//    }
//}
//
//fieldRegistry.add("ttb_clickable_number", {
//    component: FieldClickableNumber,
//    supportedTypes: ["integer", "float", "monetary"],
//});
/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

const fieldRegistry = registry.category("fields");

class FieldClickableNumber extends Component {
  static template = "ttb.FieldClickableNumber";
  static props = { ...standardFieldProps };

  setup() {
    this.orm = useService("orm");
    this.action = useService("action");
  }

  get rawValue() {
    const name = this.props.name;
    const rec  = this.props.record;
    let v = rec?.data?.[name];
    if (v === undefined) v = rec?.aggregates?.[name];
    if (v === undefined) v = rec?.groupData?.[name];
    if (v === undefined) v = this.props.value;
    if (v === undefined || v === null || v === false) return 0;
    if (typeof v === "string") {
      const n = Number(v.replace(/[\s,]/g, ""));
      return Number.isFinite(n) ? n : 0;
    }
    return typeof v === "number" ? v : 0;
  }

  _actionToUrl(action) {
    const q = new URLSearchParams();
    // có id action thì ưu tiên
    if (action.id) q.set("action", action.id);
    if (action.res_model) q.set("model", action.res_model);

    // xác định view_type
    let viewType = "list";
    if (action.view_mode) {
      viewType = action.view_mode.split(",")[0];
    } else if (action.views && action.views.length && action.views[0][1]) {
      viewType = action.views[0][1];
    }
    q.set("view_type", viewType);

    if (action.res_id) q.set("id", action.res_id);
    if (action.domain) q.set("domain", JSON.stringify(action.domain));
    if (action.context) q.set("context", JSON.stringify(action.context));
    return `/web#${q.toString()}`;
  }

  async onClick(ev) {
    ev.preventDefault();
    ev.stopPropagation();

    const rec = this.props.record;
    const resId = rec?.resId;
    const resModel = rec?.resModel;
    if (!resModel || !resId) return; // hàng tổng/nhóm không drill-down theo resId

    const fieldName = this.props.name;
    const method =
      (this.props.options && this.props.options.method) ||
      `action_open_${fieldName}`;

    const openInNew = !!(this.props.options && this.props.options.new_tab);

    // 👉 MỞ TRƯỚC 1 TAB RỖNG để tránh bị chặn popup
    let preWin = null;
    if (openInNew) {
      preWin = window.open("", "_blank");
      if (!preWin) {
        // bị chặn hoàn toàn (popup blocker) -> fallback mở trong tab hiện tại
        // hoặc hiện toast hướng dẫn cho phép popup tại site này
        // return; // nếu muốn dừng hẳn
      }
    }

    // Gọi server lấy action
    const action = await this.orm.call(resModel, method, [resId], {
      context: rec.context || {},
    });
    if (!action) {
      if (preWin) preWin.close();
      return;
    }

    if (openInNew && preWin) {
      preWin.location = this._actionToUrl(action);
      return;
    }

    // Mặc định: mở trong tab hiện tại
    await this.action.doAction(action);
  }
}

fieldRegistry.add("ttb_clickable_number", {
  component: FieldClickableNumber,
  supportedTypes: ["integer", "float", "monetary"],
});

