/** @odoo-module **/

import { Component } from "@odoo/owl";

export class SupplierSelectionPopup extends Component {
    static props = {
        isVisible: { type: Boolean },
        products: { type: Array },
        suppliers: { type: Array },
        selectedSuppliers: { type: Object },
        quantities: { type: Object },
        onClose: { type: Function },
        onSupplierChange: { type: Function },
        onConfirm: { type: Function },
        hasAllSuppliersSelected: { type: Function },
    };

    static template = "ttb_purchase_planning.SupplierSelectionPopup";

    onClose() {
        this.props.onClose();
    }

    onSupplierChange(productId, supplierId) {
        this.props.onSupplierChange(productId, supplierId);
    }

    onConfirm() {
        this.props.onConfirm();
    }

    hasAllSuppliersSelected() {
        return this.props.hasAllSuppliersSelected();
    }
} 