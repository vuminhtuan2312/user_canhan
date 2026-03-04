/** @odoo-module **/

console.log('>>> purchase_grid_view.js loaded');

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
const { DateTime } = luxon;

export class PurchaseGridView extends Component {
    static props = {
        action: { type: Object, optional: true },
        actionId: { type: Number, optional: true },
        updateActionState: { type: Function, optional: true },
        className: { type: String, optional: true },
        resId: { type: [Number, String], optional: true },
        globalState: { type: Object, optional: true },
    };

    setup() {
        super.setup();
        console.log('>>> PurchaseGridView setup called');
        
        this.orm = useService("orm");
        this.action = useService("action");
        
        // Khởi tạo state
        this.state = useState({
            products: [], // [{id, name, code}]
            branch_id: null,
            branch_name: "",
            mch_id: null,
            mch_name: "",
            past_cycles: 0,
            future_cycles: 0,
            mch: [],
            periods: [],
            current_period: "", // Kỳ hiện tại
            data: {}, // {product_id: {period: {opening, in, out, closing}}}
            // State cho popup chọn nhà cung cấp
            showSupplierPopup: false,
            suppliers: [], // Danh sách nhà cung cấp
            selectedSuppliers: {}, // {product_id: supplier_id}
            purchaseQuantities: {}, // {product_id: quantity}
            wizard_id: null, // ID của wizard instance
        });
        
        // Lấy context từ props.action (từ wizard) hoặc currentAction
        console.log('>>> Props:', this.props);
        console.log('>>> Props.action:', this.props.action);
        
        if (this.props.action && this.props.action.context) {
            console.log('>>> Props action context found:', this.props.action.context);
            this.processContext(this.props.action.context);
        } else {
            console.log('>>> No props action context, trying currentAction');
            const currentAction = this.env.services.action.currentAction;
            console.log('>>> CurrentAction:', currentAction);
            
            if (currentAction && currentAction.context) {
                console.log('>>> CurrentAction context found:', currentAction.context);
                this.processContext(currentAction.context);
            } else {
                console.log('>>> No context found anywhere');
            }
        }
    }

    processContext(context) {
        console.log('>>> Processing context:', context);
        
        if (context.default_product_ids && context.default_product_ids.length > 0) {
            console.log('>>> Processing context data...');
            // Lưu danh sách sản phẩm vào state
            this.state.products = context.default_product_ids.map((id, idx) => ({
                id: id,
                name: context.default_product_names[idx] || '',
                code: context.default_product_codes[idx] || '',
            }));
            this.state.branch_id = context.default_branch_id || null;
            this.state.branch_name = context.default_branch_name || '';
            this.state.mch_id = context.default_mch_id || null;
            this.state.mch_name = context.default_mch_name || '';
            this.state.past_cycles = context.default_past_cycles || 0;
            this.state.future_cycles = context.default_future_cycles || 0;
            this.state.mch = [];

            console.log('>>> Products:', this.state.products);
            console.log('>>> Past cycles:', this.state.past_cycles);
            console.log('>>> Future cycles:', this.state.future_cycles);

            // Tính periods (tuần)
            const today = DateTime.now().startOf("week");
            const periods = [];
            for (let i = -this.state.past_cycles; i <= this.state.future_cycles; i++) {
                const start = today.plus({ weeks: i });
                const end = start.plus({ days: 6 });
                periods.push(`${start.toFormat("dd/MM")} - ${end.toFormat("dd/MM")}`);
            }
            this.state.periods = periods;
            // Xác định kỳ hiện tại
            this.state.current_period = `${today.toFormat("dd/MM")} - ${today.plus({ days: 6 }).toFormat("dd/MM")}`;
            console.log('>>> Periods:', this.state.periods);
            console.log('>>> Current period:', this.state.current_period);

            // Khởi tạo data cho từng sản phẩm
            if (context.data) {
                this.state.data = context.data;
            } else {
                // chỉ fallback khi không có data từ backend
                this.state.data = {};
                for (const product of this.state.products) {
                    let opening = 0; // Giá trị mặc định là 0
                    this.state.data[product.id] = {};
                    for (let i = 0; i < this.state.periods.length; i++) {
                        const period = this.state.periods[i];
                        this.state.data[product.id][period] = {
                            opening: opening,
                            in: 0,
                            out: 0,
                            closing: opening,
                        };
                        opening = this.state.data[product.id][period].closing;
                    }
                }
            }
            
            // Thử khôi phục dữ liệu từ localStorage
            this.loadDataFromStorage();
            
            console.log('>>> Data initialized:', this.state.data);
        } else {
            console.log('>>> No product_ids in context, initializing empty state');
            // Khởi tạo state mặc định nếu không có sản phẩm
            this.state.products = [];
            this.state.branch_id = null;
            this.state.branch_name = context.default_branch_name || '';
            this.state.mch_id = null;
            this.state.mch_name = context.default_mch_name || '';
            this.state.past_cycles = context.default_past_cycles || 2;
            this.state.future_cycles = context.default_future_cycles || 3;
            this.state.mch = [];
            this.state.periods = [];
            // Xác định kỳ hiện tại
            const today = DateTime.now().startOf("week");
            this.state.current_period = `${today.toFormat("dd/MM")} - ${today.plus({ days: 6 }).toFormat("dd/MM")}`;
            this.state.data = {};
        }
    }

    async onAddProduct() {
        console.log('>>> Opening product selection wizard...');
        // Mở wizard, lấy kết quả
        const res = await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "purchase.grid.wizard",
            views: [[false, "form"]],
            target: "new",
        });
        console.log('>>> Wizard result:', res);
        
        if (res && res.context && res.context.default_product_ids) {
            console.log('>>> Processing wizard result...');
            // Lấy dữ liệu từ context
            this.state.products = res.context.default_product_ids.map((id, idx) => ({
                id: id,
                name: res.context.default_product_names[idx] || '',
                code: res.context.default_product_codes[idx] || '',
            }));
            this.state.branch_id = res.context.default_branch_id || null;
            this.state.branch_name = res.context.default_branch_name || '';
            this.state.mch_id = res.context.default_mch_id || null;
            this.state.mch_name = res.context.default_mch_name || '';
            this.state.past_cycles = res.context.default_past_cycles || 0;
            this.state.future_cycles = res.context.default_future_cycles || 0;
            this.state.mch = [];

            // Tính periods (tuần)
            const today = DateTime.now().startOf("week");
            const periods = [];
            for (let i = -this.state.past_cycles; i <= this.state.future_cycles; i++) {
                const start = today.plus({ weeks: i });
                const end = start.plus({ days: 6 });
                periods.push(`${start.toFormat("dd/MM")} - ${end.toFormat("dd/MM")}`);
            }
            this.state.periods = periods;
            // Xác định kỳ hiện tại
            this.state.current_period = `${today.toFormat("dd/MM")} - ${today.plus({ days: 6 }).toFormat("dd/MM")}`;

            // Khởi tạo data cho từng sản phẩm
            if (res.context.data) {
                this.state.data = res.context.data;
            } else {
                // fallback nếu không có data từ backend (chỉ dùng cho test)
                this.state.data = {};
                for (const product of this.state.products) {
                    let opening = 0; // Giá trị mặc định là 0
                    this.state.data[product.id] = {};
                    for (let i = 0; i < this.state.periods.length; i++) {
                        const period = this.state.periods[i];
                        this.state.data[product.id][period] = {
                            opening: opening,
                            in: 0,
                            out: 0,
                            closing: opening,
                        };
                        opening = this.state.data[product.id][period].closing;
                    }
                }
            }
            
            // Thử khôi phục dữ liệu từ localStorage
            this.loadDataFromStorage();
            
            console.log('>>> Grid updated with products:', this.state.products);
        } else {
            console.log('>>> No valid result from wizard');
        }
    }

    onInput(ev, product_id, period, field) {
        const value = parseFloat(ev.target.value) || 0;
        this.state.data[product_id][period][field] = value;
        this.recomputeClosing(product_id);
        
        // Tự động lưu dữ liệu khi có thay đổi
        this.saveDataToStorage();
    }

    recomputeClosing(product_id) {
        let prev_closing = null;
        for (const period of this.state.periods) {
            if (prev_closing !== null) {
                this.state.data[product_id][period].opening = prev_closing;
            }
            this.state.data[product_id][period].closing = this.state.data[product_id][period].opening + this.state.data[product_id][period].in - this.state.data[product_id][period].out;
            prev_closing = this.state.data[product_id][period].closing;
        }
    }

    // Lưu dữ liệu vào localStorage
    saveDataToStorage() {
        const storageKey = `purchase_grid_${this.state.branch_id}_${this.state.current_period}`;
        const dataToSave = {
            products: this.state.products,
            branch_id: this.state.branch_id,
            branch_name: this.state.branch_name,
            past_cycles: this.state.past_cycles,
            future_cycles: this.state.future_cycles,
            periods: this.state.periods,
            current_period: this.state.current_period,
            data: this.state.data,
            timestamp: new Date().toISOString()
        };
        localStorage.setItem(storageKey, JSON.stringify(dataToSave));
        console.log('>>> Data saved to localStorage:', storageKey);
    }

    // Khôi phục dữ liệu từ localStorage
    loadDataFromStorage() {
        const storageKey = `purchase_grid_${this.state.branch_id}_${this.state.current_period}`;
        const savedData = localStorage.getItem(storageKey);
        if (savedData) {
            try {
                const data = JSON.parse(savedData);
                // Đảm bảo data được khởi tạo trước khi khôi phục
                if (this.state.products.length > 0 && this.state.periods.length > 0) {
                    // Chỉ khôi phục data cho các sản phẩm và kỳ hiện tại
                    const restoredData = data.data || {};
                    for (const product of this.state.products) {
                        if (!this.state.data[product.id]) {
                            this.state.data[product.id] = {};
                        }
                        for (const period of this.state.periods) {
                            if (restoredData[product.id] && restoredData[product.id][period]) {
                                this.state.data[product.id][period] = {
                                    ...this.state.data[product.id][period],
                                    ...restoredData[product.id][period]
                                };
                            }
                        }
                    }
                    console.log('>>> Data loaded from localStorage:', storageKey);
                    return true;
                }
            } catch (error) {
                console.error('>>> Error loading data from localStorage:', error);
            }
        }
        return false;
    }

    // Xóa dữ liệu đã lưu
    clearSavedData() {
        const storageKey = `purchase_grid_${this.state.branch_id}_${this.state.current_period}`;
        localStorage.removeItem(storageKey);
        
        // Reset data về giá trị mặc định
        for (const product of this.state.products) {
            let opening = 0; // Giá trị mặc định là 0
            for (const period of this.state.periods) {
                this.state.data[product.id][period] = {
                    opening: opening,
                    in: 0,
                    out: 0,
                    closing: opening,
                };
                opening = this.state.data[product.id][period].closing;
            }
        }
        
        console.log('>>> Saved data cleared and reset to default');
    }

    // Method mở popup chọn nhà cung cấp
    async onCreatePurchaseOrder() {
        console.log('>>> Opening supplier selection popup...');
        
        // Test kết nối backend trước
        const testResult = await this.testBackendConnection();
        console.log('>>> Backend test result:', testResult);
        
        // Tạo wizard instance cho get_suppliers
        const wizardId = await this.orm.create('purchase.grid.wizard', [{
            product_ids: this.state.products.map(p => p.id),
            branch_id: this.state.branch_id,
            past_cycles: this.state.past_cycles,
            future_cycles: this.state.future_cycles,
        }]);
        console.log('>>> Wizard ID created:', wizardId);
        
        // Lấy danh sách nhà cung cấp từ backend
        const suppliers = await this.orm.call(
            'purchase.grid.wizard',
            'get_suppliers',
            [wizardId]
        );
        console.log('>>> Suppliers from backend:', suppliers);
        this.state.suppliers = suppliers;
        
        // Lưu wizard_id để sử dụng sau
        this.state.wizard_id = wizardId;
        
        // Tính số lượng cần mua cho từng sản phẩm (lấy từ kỳ hiện tại)
        this.state.purchaseQuantities = {};
        for (const product of this.state.products) {
            const currentData = this.state.data[product.id] && this.state.data[product.id][this.state.current_period];
            this.state.purchaseQuantities[product.id] = currentData ? currentData.in : 0;
        }
        console.log('>>> Purchase quantities calculated:', this.state.purchaseQuantities);
        
        // Reset selected suppliers
        this.state.selectedSuppliers = {};
        
        // Hiển thị popup
        this.state.showSupplierPopup = true;
        console.log('>>> Show supplier popup:', this.state.showSupplierPopup);
        console.log('>>> Suppliers loaded:', this.state.suppliers);
        console.log('>>> Purchase quantities:', this.state.purchaseQuantities);
        console.log('>>> Products:', this.state.products);
    }

    // Method đóng popup
    onCloseSupplierPopup() {
        this.state.showSupplierPopup = false;
    }

    // Method thay đổi nhà cung cấp cho sản phẩm
    onSupplierChange(productId, supplierId) {
        this.state.selectedSuppliers[productId] = parseInt(supplierId) || null;
    }

    // Method kiểm tra đã chọn đủ nhà cung cấp chưa
    hasAllSuppliersSelected() {
        for (const product of this.state.products) {
            if (this.state.purchaseQuantities[product.id] > 0 && !this.state.selectedSuppliers[product.id]) {
                return false;
            }
        }
        return true;
    }

    // Method xác nhận tạo đơn mua hàng
    async onConfirmCreatePurchaseOrder() {
        console.log('>>> Creating purchase orders...');
        console.log('>>> Branch ID:', this.state.branch_id);
        console.log('>>> Selected Suppliers:', this.state.selectedSuppliers);
        console.log('>>> Purchase Quantities:', this.state.purchaseQuantities);
        
        try {
            // Nhóm sản phẩm theo nhà cung cấp
            const supplierGroups = {};
            for (const product of this.state.products) {
                const supplierId = this.state.selectedSuppliers[product.id];
                const quantity = this.state.purchaseQuantities[product.id];
                
                if (supplierId && quantity > 0) {
                    if (!supplierGroups[supplierId]) {
                        supplierGroups[supplierId] = [];
                    }
                    supplierGroups[supplierId].push({
                        product_id: product.id,
                        quantity: quantity,
                    });
                }
            }
            
            console.log('>>> Supplier Groups:', supplierGroups);
            
            // Gọi method backend để tạo đơn mua hàng
            const purchaseOrderIds = await this.orm.call(
                'purchase.grid.wizard',
                'create_po_simple',
                [this.state.wizard_id, this.state.branch_id, supplierGroups]
            );
            
            console.log('>>> Purchase Order IDs:', purchaseOrderIds);
            
            // Kiểm tra lỗi từ backend
            if (purchaseOrderIds && purchaseOrderIds.error) {
                throw new Error(purchaseOrderIds.error);
            }
            
            // Đóng popup
            this.state.showSupplierPopup = false;
            
            // Hiển thị thông báo thành công
            if (purchaseOrderIds && purchaseOrderIds.length > 0) {
                // Hiển thị thông báo thành công
                alert(`Đã tạo thành công ${purchaseOrderIds.length} đơn mua hàng!`);
                
                // Thử mở danh sách đơn mua hàng vừa tạo
                try {
                    await this.action.doAction({
                        type: 'ir.actions.act_window',
                        name: 'Purchase Orders',
                        res_model: 'purchase.order',
                        view_mode: 'list,form',
                        domain: [['id', 'in', purchaseOrderIds]],
                        target: 'current',
                    });
                } catch (actionError) {
                    console.error('>>> Error opening purchase orders:', actionError);
                    // Nếu không mở được action, ít nhất đã tạo thành công
                }
            }
            
        } catch (error) {
            console.error('>>> Error creating purchase orders:', error);
            console.error('>>> Error details:', error.message, error.stack);
            // Hiển thị thông báo lỗi
            alert('Có lỗi xảy ra khi tạo đơn mua hàng: ' + error.message);
        }
    }

    // Method test kết nối backend
    async testBackendConnection() {
        try {
            // Tạo wizard instance trước
            const wizardId = await this.orm.create('purchase.grid.wizard', [{
                product_ids: this.state.products.map(p => p.id),
                branch_id: this.state.branch_id,
                past_cycles: this.state.past_cycles,
                future_cycles: this.state.future_cycles,
            }]);
            
            const result = await this.orm.call(
                'purchase.grid.wizard',
                'test_method',
                [wizardId]
            );
            console.log('>>> Test result:', result);
            return result;
        } catch (error) {
            console.error('>>> Test error:', error);
            return null;
        }
    }
}

PurchaseGridView.template = "ttb_purchase_planning.PurchaseGridView";
registry.category("actions").add("purchase_grid_view", PurchaseGridView);