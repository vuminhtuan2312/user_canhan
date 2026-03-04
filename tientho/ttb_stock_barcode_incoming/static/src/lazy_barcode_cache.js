/** @odoo-module **/

import LazyBarcodeCache from '@stock_barcode/lazy_barcode_cache';

import { patch } from "@web/core/utils/patch";

patch(LazyBarcodeCache.prototype, {
   /**
   * @override
   * Với sản phẩm hỗ trợ các trường default_code, barcode_k, ma_vach_k
   */
   setCache(cacheData) {
      super.setCache(...arguments);
      for (const model in cacheData) {
         if (model !== 'product.product') { continue; }
         const records = cacheData[model];
         // Adds the model's key in the cache's DB.
         if (!this.dbIdCache.hasOwnProperty(model)) {
             this.dbIdCache[model] = {};
         }
         if (!this.dbBarcodeCache.hasOwnProperty(model)) {
             this.dbBarcodeCache[model] = {};
         }
         // // Adds the record in the cache.
         // const barcodeField = 'default_code'
         // for (const record of records) {
         //    const barcodeFields = ['default_code', 'barcode_vendor', 'barcode_k'];

         //    for (const barcodeField of barcodeFields) {
         //          // Todo: ktra record có trường barcodeField
         //          // TODO2: barcode_k là trường chứa nhiều mã cách nhau bởi dấu phẩy
         //          const barcode = record[barcodeField];
         //          if (!this.dbBarcodeCache[model][barcode]) {
         //             this.dbBarcodeCache[model][barcode] = [];
         //          }
         //          if (!this.dbBarcodeCache[model][barcode].includes(record.id)) {
         //             this.dbBarcodeCache[model][barcode].push(record.id);
         //             if (this.nomenclature && this.nomenclature.is_gs1_nomenclature && this.gs1LengthsByModel[model]) {
         //                 this._setBarcodeInCacheForGS1(barcode, model, record);
         //             }
         //          }
         //     }
         // }

         // Adds the record in the cache.
         const barcodeFields = ['default_code', 'barcode_vendor', 'barcode_k'];
         const extraBarcodes = [];

         for (const record of records) {
             for (const field of barcodeFields) {
                 let barcodes = [];

                 // Nếu là barcode_k thì tách theo dấu phẩy
                 if (field === 'barcode_k') {
                     if (record[field]) {
                         barcodes = record[field]
                             .split(",")
                             .map(b => b.trim())      // loại bỏ space thừa
                             .filter(b => b.length);  // bỏ rỗng
                     }
                 } else {
                     if (record[field]) {
                         barcodes = [record[field]];
                     }
                 }
                 for (const b of barcodes) {
                    if (b.length === 12) {
                        extraBarcodes.push('0' + b);
                    }
                 }
                    barcodes.push(...extraBarcodes);  // thêm vào danh sách gốc
                 for (const barcode of barcodes) {
                     if (!this.dbBarcodeCache[model][barcode]) {
                         this.dbBarcodeCache[model][barcode] = [];
                     }
                     if (!this.dbBarcodeCache[model][barcode].includes(record.id)) {
                         this.dbBarcodeCache[model][barcode].push(record.id);
                         if (this.nomenclature && this.nomenclature.is_gs1_nomenclature && this.gs1LengthsByModel[model]) {
                             this._setBarcodeInCacheForGS1(barcode, model, record);
                         }
                     }
                 }
             }
         }
      }
   }

});
