/** @odoo-module **/

import BarcodeQuantModel from '@stock_barcode/models/barcode_quant_model';
// import { session } from '@web/session';
import { _t } from "@web/core/l10n/translation";
// import { rpc } from "@web/core/network/rpc";

export default class BarcodeInventoryResultModel extends BarcodeQuantModel {

    _getName() {
        return _t("Kiểm kê");
    }

    get displayAddProductButton() {
        return false;
    }

    // get barcodeInfo() {
    //     return {
    //         class: 'scan_src',
    //         message: _t("Quét sản phẩm trong PID"),
    //         icon: 'sign-out',
    //     };
    // }
    _getResultLineData(id){
        const smlData = this.cache.getRecord('inventory.result.lines', id);
        smlData.dummy_id = smlData.dummy_id && Number(smlData.dummy_id);
        return smlData;
    }

    // like updateLineQty
    updateLineQtyAppendDigit(virtualId, digit = 0) {
        this.actionMutex.exec(() => {
            const line = this.pageLines.find(l => l.virtual_id === virtualId);
            this.updateLine(line, {append_digit: digit});
            this.trigger('update');
        });
    }

    _updateLineQty(line, args) {
        if (args.append_digit !== undefined) {
            line.inventory_quantity = (line.inventory_quantity || 0) * 10 + args.append_digit;
            if (line.inventory_quantity > 0) {
                args.inventory_quantity_set = true;
            }
            return
        }
        return super._updateLineQty(line, args)
    }

    _createLinesState() {
        const lines = [];
        for (const id of Object.keys(this.cache.dbIdCache['inventory.result.lines']).map(id => Number(id))) {
            const inventory_result = this.cache.getRecord('inventory.result.lines', id);
            const smlData = this._getResultLineData(id);
            lines.push(smlData);
        }
        return lines;
    }

//    async _processLocation(barcodeData)  {
//        await super._processLocation(...arguments)
//        if (this.scanHistory[0]?.match && this.scanHistory[0]?.stopped) {
//            this.trigger("turn_off_camera");
//        }
//    }

    async _createNewLine(params) {
        const newLine = await super._createNewLine(...arguments);
        if (newLine) {
            this.trigger("turn_off_camera");

            // Khi tạo mới dòng kiểm kê thì để số lượng bằng 0 thay vì 1
            newLine.inventory_quantity = 0;
            // newLine.inventory_quantity_set = false;
        }
        return newLine;
    }

    _getFieldToWrite() {
        return [
            'quantity_count',
        ];
    }

    /**
     * Apply quantity set on counted quants.
     * @returns {Promise}
     */
    async _apply() {
        await this.save();
        const linesToApply = this.pageLines.filter(line => line.inventory_quantity_set);
        const lineIds = linesToApply.map(line => line.id);
        const action = await this.orm.call("inventory.result.lines", "action_validate", [lineIds]);
        const notifyAndGoAhead = res => {
            if (res && res.special) { // Do nothing if come from a discarded wizard.
                return this.trigger('refresh');
            }
            this.notification(_t("The inventory adjustment has been validated"), { type: "success" });
            this.trigger('history-back');
        };
        // if (action && action.res_model) {
        //     return this.action.doAction(action, { onClose: notifyAndGoAhead });
        // }
        notifyAndGoAhead();
    }

}
