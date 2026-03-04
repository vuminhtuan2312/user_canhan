/** @odoo-module */

import { FormController } from "@web/views/form/form_controller";
import { user } from "@web/core/user";
import { useBus, useService, useEffect } from '@web/core/utils/hooks';
import { _t } from "@web/core/l10n/translation";
import { onMounted, onWillStart } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { ManualBarcodeScanner } from "@stock_barcode/components/manual_barcode";

export class ThiNgiemKiemKeFormController extends FormController {
    static template = "ttb_inventory_barcode_kiem_ke.ThiNghiemKiemKeForm"
    setup() {
        super.setup(...arguments);
        this.actionService = useService("action");
        this.barcodeService = useService('barcode');
        this.sessionIsDone = false;
        useBus(this.barcodeService.bus, 'barcode_scanned', (ev) => this._onBarcodeScannedHandler(ev.detail.barcode));
        onWillStart(async () => {
            await this.renderProductList();
        });
        onMounted(() => {
            document.activeElement.blur();
        });
    }

    async renderProductList() {
        const productList = await this.orm.call(
            "experimental.kiemke",
            "get_product_by_session_id",
            [this.props.resId],
        )
        if (productList && productList.length) {
            this.productList = productList;
            this.expectedProduct = productList[0];
            console.log(productList);
        }
    }

    validateProduct({product, order_number}) {
        if (product === this.expectedProduct.product_id && order_number === this.expectedProduct.order_number)
            return true;
        return false;
    }

    openManualBarcodeDialog() {
        this.dialogService.add(ManualBarcodeScanner, {
            facingMode: "environment",
            onResult: (barcode) => {
                this.barcodeService.bus.trigger("barcode_scanned", { barcode });
            },
            onError: () => {},
        });
    }

    async _onBarcodeScannedHandler(barcode) {
        const kwargs = { barcode, context: this.props.context, id: this.props.resId};
        const res = await this.model.orm.call(this.props.resModel, 'filter_on_barcode', [], kwargs);
        if (res.product) {
            if (this.validateProduct({product: res.product, order_number: res.order_number})) {
                let index = this.productList.findIndex(el => el.order_number == this.expectedProduct.order_number);
                if (index < this.productList.length) {
                    this.expectedProduct = this.productList[index + 1]
                }
                const context = {};
                context['default_thi_nghiem_kiem_ke_line_id'] = res.stock_location_id;
                context["default_product_id"] = res.product;
                context["default_order_number"] = res.order_number;
                context["default_quantity"] = res.quantity;
                context["default_is_final_product"] = (res.order_number == this.productList[this.productList.length-1].order_number)

                this.actionService.doAction("ttb_inventory_barcode_kiem_ke.action_thi_nghiem_popup_form", {
                    additionalContext: context,
                });
            } else {
                this.model.notification.add(_t("Sản phẩm không đúng thứ tự cần kiểm kê. Vui lòng kiểm tra lại!"), {
                    title: _t("Warning"),
                })
            }


        } else if (res.warning) {
            const params = { title: res.warning.title, type: 'danger' };
            this.model.notification.add(res.warning.message, params);
        }
    }
}