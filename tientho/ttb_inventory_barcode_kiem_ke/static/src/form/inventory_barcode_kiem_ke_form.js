/** @odoo-module */

import { FormRenderer } from '@web/views/form/form_renderer';
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { useService } from '@web/core/utils/hooks';
import { markup, onWillStart } from "@odoo/owl";

export class KiemKeBarcodeFormRenderer extends FormRenderer {
    setup() {
        super.setup(...arguments);
        this.barcodeService = useService('barcode');
        this.dialogService = useService("dialog");
        this.orm = useService("orm");
    }
}