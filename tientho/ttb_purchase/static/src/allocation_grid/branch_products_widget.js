/** @odoo-module **/

import { Component, onWillUpdateProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class GoodsDistributionWidget extends Component {
    static template = "ttb_purchase.GoodsDistributionWidget";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        // Khởi tạo dữ liệu mặc định
        this.branches = [];
        this.poLines = []; // Đổi từ products sang poLines
        this.poLineTotals = new Map(); // Đổi từ productTotals sang poLineTotals
        this.grandTotal = 0;

        this.processData();
        onWillUpdateProps(() => {
            this.processData();
        });
    }

    get records() {
        return this.props.record.data[this.props.name]?.records || [];
    }

    processData() {
    const records = this.records;

    // Kiểm tra nếu không có dữ liệu
    if (records.length === 0) {
        this.branches = [];
        this.poLines = [];
        this.poLineTotals = new Map();
        this.grandTotal = 0;
        return;
    }

    // Tạo map để nhóm dữ liệu theo branch_id
    const branchMap = new Map();
    const uniquePoLinesMap = new Map(); // Dùng Map thay vì Set để tránh vấn đề so sánh reference

    records.forEach(record => {
        const branchId = record.data.branch_id;
        const branchCode = record.data.branch_code || '';
        const poLineId = record.data.po_line_id;
        const productId = record.data.product_id;
        const defaultCode = record.data.default_code;
        const actualQty = record.data.actual_qty || 0;

        if (!branchId || !poLineId || !productId) {
            console.log('Skip record - missing branchId, poLineId or productId:', { branchId, poLineId, productId, record: record.data });
            return;
        }
        if (!Array.isArray(branchId) || !Array.isArray(poLineId) || !Array.isArray(productId)) {
            console.log('Skip record - branchId, poLineId or productId is not array:', { branchId, poLineId, productId, record: record.data });
            return;
        }
        if (branchId.length < 1 || poLineId.length < 1 || productId.length < 1) {
            console.log('Skip record - empty array:', { branchId, poLineId, productId, record: record.data });
            return;
        }

        const branchKey = branchId[0];
        const poLineKey = poLineId[0];

        // === TẠO URL ẢNH TỪ TRƯỜNG Binary prd_image ===
        let prdImageUrl = null;
        if (record.data.prd_image) {
            // record.resModel/resId là model + id của dòng one2many: goods.distribution.ticket.line
            const model = record.resModel || 'goods.distribution.ticket.line';
            const id = record.resId;
            if (id) {
                prdImageUrl = `/web/image/${model}/${id}/prd_image`;
            }
        }

        // Lưu unique poLines vào Map
        if (!uniquePoLinesMap.has(poLineKey)) {
            uniquePoLinesMap.set(poLineKey, {
                poLineId: poLineId,
                productId: productId,
                prdImageUrl: prdImageUrl,   // LƯU URL ảnh
                defaultCode: defaultCode,
            });
        }

        if (!branchMap.has(branchKey)) {
            branchMap.set(branchKey, {
                branch: branchId,
                branchCode: branchCode,  // LƯU MÃ CƠ SỞ
                poLines: new Map()
            });
        }

        branchMap.get(branchKey).poLines.set(poLineKey, {
            poLine: poLineId,
            qty: actualQty,
            record: record
        });
    });

    // Chuyển đổi thành array và sắp xếp
    this.branches = Array.from(branchMap.values()).sort((a, b) => {
        const nameA = a.branch && a.branch[1] ? a.branch[1] : '';
        const nameB = b.branch && b.branch[1] ? b.branch[1] : '';
        return nameA.localeCompare(nameB);
    });

    // Chuyển uniquePoLinesMap thành array và sắp xếp theo tên sản phẩm
    this.poLines = Array.from(uniquePoLinesMap.values()).sort((a, b) => {
        const nameA = a.productId && a.productId[1] ? a.productId[1] : '';
        const nameB = b.productId && b.productId[1] ? b.productId[1] : '';
        return nameA.localeCompare(nameB);
    });

    // Tính tổng cho từng dòng đơn mua hàng
    this.poLineTotals = new Map();
    this.poLines.forEach(poLineData => {
        const poLineKey = poLineData.poLineId[0];
        let total = 0;
        this.branches.forEach(branch => {
            const poLineDataInBranch = branch.poLines.get(poLineKey);
            if (poLineDataInBranch) {
                total += poLineDataInBranch.qty;
            }
        });
        this.poLineTotals.set(poLineKey, total);
    });

    // Tính tổng tổng
    this.grandTotal = Array.from(this.poLineTotals.values()).reduce((sum, total) => sum + total, 0);

    // Debug log
    console.log('ProcessData result:', {
        branchesCount: this.branches.length,
        poLinesCount: this.poLines.length,
        branches: this.branches,
        poLines: this.poLines
    });
}

    async updateQuantity(branchId, poLineId, newQuantity) {
        try {
            const records = this.records;

            // Tìm record tương ứng
            const record = records.find(r => {
                const rBranchId = r.data.branch_id;
                const rPoLineId = r.data.po_line_id;

                return rBranchId && rPoLineId &&
                       rBranchId[0] === branchId[0] &&
                       rPoLineId[0] === poLineId[0];
            });

            if (record) {
                // Cập nhật giá trị
                const parsedQuantity = parseFloat(newQuantity) || 0;

                await record.update({ actual_qty: parsedQuantity });

                // Lưu record cha
                await this.props.record.save();

                // Cập nhật lại dữ liệu
                this.processData();
                this.render();
            }
        } catch (error) {
            console.error('Error updating quantity:', error);
        }
    }

    getPoLineQuantity(branchId, poLineId) {
        if (!branchId || !poLineId) return 0;

        const branch = this.branches.find(b =>
            b.branch && b.branch[0] === branchId[0]
        );

        // poLineId có thể là array hoặc object với poLineId property
        const poLineKey = Array.isArray(poLineId) ? poLineId[0] : poLineId.poLineId[0];

        if (branch && branch.poLines.has(poLineKey)) {
            return branch.poLines.get(poLineKey).qty;
        }
        return 0;
    }

    getBranchName(branch) {
        return branch && branch[1] ? branch[1] : '';
    }

    getBranchCode(branchObj) {
        // branchObj là object từ this.branches có cấu trúc: { branch: [id, name], branchCode: 'XXX', poLines: Map }
        return branchObj && branchObj.branchCode ? branchObj.branchCode : '';
    }

    getPoLineName(poLineData) { // Đổi từ getProductName - nhận vào object hoặc array
        // Nếu là object có productId property (từ uniquePoLinesMap)
        if (poLineData && poLineData.productId) {
            return poLineData.productId[1] || '';
        }
        // Nếu là array (backward compatibility)
        if (Array.isArray(poLineData)) {
            return poLineData[1] || '';
        }
        return '';
    }

    getPoLineDefaultCode(poLineData) {
        // Lấy default_code từ object uniquePoLinesMap
        if (poLineData && Object.prototype.hasOwnProperty.call(poLineData, "defaultCode")) {
            return poLineData.defaultCode || '';
        }
        return '';
    }

    getPoLineImage(poLineData) {
        // Lấy URL ảnh đã build sẵn
        if (poLineData && Object.prototype.hasOwnProperty.call(poLineData, "prdImageUrl")) {
            return poLineData.prdImageUrl || '';
        }
        return '';
    }
}

registry.category("fields").add("goods_distribution_widget", {
    component: GoodsDistributionWidget,
    supportedTypes: ["one2many"],
});
