/** @odoo-module **/

import { registry } from "@web/core/registry";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import { ListRenderer } from "@web/views/list/list_renderer";
import { useState } from "@odoo/owl";

/**
 * Custom List Renderer với tính năng search
 */
export class NibotListRenderer extends ListRenderer {
    setup() {
        super.setup();
        this.state = useState({
            searchValue: "",
        });
    }

    /**
     * Lọc records dựa trên searchValue
     */
    get filteredRecords() {
        const searchValue = this.state.searchValue.toLowerCase().trim();
        if (!searchValue) {
            return this.props.list.records;
        }

        return this.props.list.records.filter(record => {
            // Tìm kiếm theo số hóa đơn
            const invoiceNo = record.data.ttb_vendor_invoice_no || "";
            if (String(invoiceNo).toLowerCase().includes(searchValue)) {
                return true;
            }

            // Tìm kiếm theo ký hiệu hóa đơn
            const invoiceCode = record.data.ttb_vendor_invoice_code || "";
            if (String(invoiceCode).toLowerCase().includes(searchValue)) {
                return true;
            }

            // Tìm kiếm theo mã số thuế
            const vat = record.data.ttb_vendor_vat || "";
            if (String(vat).toLowerCase().includes(searchValue)) {
                return true;
            }

            // Tìm kiếm theo số tiền (chuyển sang string để so sánh)
            const priceUnit = String(record.data.ttb_price_unit || "");
            if (priceUnit.includes(searchValue)) {
                return true;
            }

            // Tìm kiếm theo ngày hóa đơn
            const invoiceDate = record.data.ttb_vendor_invoice_date || "";
            if (String(invoiceDate).toLowerCase().includes(searchValue)) {
                return true;
            }

            return false;
        });
    }

    /**
     * Override displayedRecords để trả về filtered records
     * Đây là property được template sử dụng để render
     */
    get displayedRecords() {
        return this.filteredRecords;
    }

    /**
     * Override getRowsToDisplay để đảm bảo chỉ render filtered records
     * Method này được ListRenderer sử dụng trong template
     */
    getRowsToDisplay() {
        return this.filteredRecords;
    }

    /**
     * Xử lý thay đổi input search
     */
    onSearchInput(ev) {
        this.state.searchValue = ev.target.value;
    }

    /**
     * Xóa nội dung search
     */
    clearSearch() {
        this.state.searchValue = "";
    }
}

NibotListRenderer.template = "ttb_purchase_invoice_stock.NibotListRenderer";

/**
 * Custom X2Many Field với ListRenderer có search
 */
export class NibotX2ManyField extends X2ManyField {
    static components = {
        ...X2ManyField.components,
        ListRenderer: NibotListRenderer
    };

    setup() {
        super.setup();
    }

    get isMany2Many() {
        return this.props.type === "many2many";
    }
}

/**
 * Định nghĩa field descriptor
 */
export const nibotX2ManyField = {
    ...x2ManyField,
    component: NibotX2ManyField,
    additionalClasses: [...x2ManyField.additionalClasses || [], "o_field_one2many"],
};

// Đăng ký widget với tên "nibot_one2many"
registry.category("fields").add("nibot_one2many", nibotX2ManyField);
