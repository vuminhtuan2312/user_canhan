/** @odoo-module **/

import LazyBarcodeCache from '@stock_barcode/lazy_barcode_cache';

import { patch } from "@web/core/utils/patch";

patch(LazyBarcodeCache.prototype, {

    /**
     * Đoạn code thêm mã barcode copy từ hàm setCache super
     */
    addBarcode(model, record, barcode) {
        if (!this.dbBarcodeCache[model][barcode]) {
            this.dbBarcodeCache[model][barcode] = [];
        }
        if (!this.dbBarcodeCache[model][barcode].includes(record.id)) {
            this.dbBarcodeCache[model][barcode].push(record.id);
            if (this.nomenclature && this.nomenclature.is_gs1_nomenclature && this.gs1LengthsByModel[model]) {
                this._setBarcodeInCacheForGS1(barcode, model, record);
            }
        }
    },

    addExtraBarcode(model, record, barcodes) {
        // 1. Hàm kiểm tra tính hợp lệ của mã EAN-13
        const isValidEAN13 = (code) => {
            if (!/^\d{13}$/.test(code)) return false;

            let sum = 0;
            for (let i = 0; i < 12; i++) {
                // Vị trí lẻ (1, 3, 5...) nhân 1, vị trí chẵn (2, 4, 6...) nhân 3
                sum += parseInt(code[i]) * (i % 2 === 0 ? 1 : 3);
            }

            const checkDigit = (10 - (sum % 10)) % 10;
            return checkDigit === parseInt(code[12]);
        };

        // 2. Duyệt qua danh sách barcode đầu vào
        for (let barcode of barcodes) {
            if (barcode.length === 12) {
                const potentialBarcode = '0' + barcode;

                // Kiểm tra 2 điều kiện:
                // - Phải là mã EAN-13 hợp lệ
                // - Chưa tồn tại trong cache của model này
                const isExisting = this.dbBarcodeCache[model] && this.dbBarcodeCache[model][potentialBarcode];

                if (isValidEAN13(potentialBarcode) && !isExisting) {
                    this.addBarcode(model, record, potentialBarcode);
                }
            }
        }
    },

    /**
     * Duyệt cache để tìm mã trùng và lưu vào this.duplicateBarcodes
     */
    _collectDuplicateBarcodes() {
        this.duplicateBarcodes = {};

        for (const model in this.dbBarcodeCache) {
            const modelCache = this.dbBarcodeCache[model];
            if (!modelCache) continue;

            for (const barcode in modelCache) {
                const recordIds = modelCache[barcode];
                
                // Nếu mã barcode này trỏ đến nhiều hơn 1 record ID
                if (recordIds && recordIds.length > 1) {

                    if (!this.duplicateBarcodes.hasOwnProperty(model)) {
                        this.duplicateBarcodes[model] = {}
                    }

                    this.duplicateBarcodes[model][barcode] = [...recordIds]
                }
            }

            // Log nhẹ ra console để dev kiểm soát (không gửi lên server)
            if (this.duplicateBarcodes[model]) {
                console.warn("⚠️ Phát hiện mã vạch trùng lặp trong Cache:", model, this.duplicateBarcodes[model]);
            }
        }
    },

    /**
     * @override
     * Với sản phẩm ngoài trường barcode hỗ trợ thêm các trường default_code, barcode_k, ma_vach_k
     * 3/3/2026 Thiện phát hiện ra lỗi sai và fix: Biến extraBarcodes được khai báo ngoài vòng for nên các sản phẩm sẽ dùng chéo mã của nhau
     */
    setCache(cacheData) {
        // Trường barcode của sản phẩm (và các model khác): Gọi super
        super.setCache(...arguments);

        // Các trường mở rộng còn lại
        const barcodeFields = ['default_code', 'barcode_vendor', 'barcode_k'];

        for (const model in cacheData) {
            if (model !== 'product.product') { continue; }

            const records = cacheData[model];
            for (const record of records) {
                for (const field of barcodeFields) {
                    if (!record[field]) { continue; }

                    let barcodes = [];
                    const field_value = record[field]

                    // Nếu là barcode_k thì tách theo dấu phẩy
                    if (field === 'barcode_k') {
                        barcodes = field_value
                            .split(",")
                            .map(b => b.trim())      // loại bỏ space thừa
                            .filter(b => b.length);  // bỏ rỗng
                    } else {
                        barcodes = [field_value];
                    }

                    for (const barcode of barcodes) {
                        this.addBarcode(model, record, barcode)
                    }

                    this.addExtraBarcode(model, record, barcodes)
                }
            }
        }

        this._collectDuplicateBarcodes();
    }

});
