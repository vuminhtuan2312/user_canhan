/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { escape } from "@web/core/utils/strings";
// import BarcodeModel from "@stock_barcode/models/barcode_model";
import BarcodePickingModel from '@stock_barcode/models/barcode_picking_model';
import { ConfirmationDialog, AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { patch } from "@web/core/utils/patch";
import { markup } from "@odoo/owl";
import { user } from '@web/core/user';
import { logStockBarcode } from "../barcode_logger_utils";

// Code lại ra một file mới vì code trước tệ ko sửa được

patch(BarcodePickingModel.prototype, {

    // todo: move to BarcodePickingModel
    get displayAccountantButton() {
        return this.record.picking_type_code == 'incoming';
    },

    async openAccountantForm(barcodeData=false) {
        return await this.action.doAction(
            "ttb_stock_barcode_incoming.ttb_stock_barcode_incoming_stock_picking_action",
            {
                additionalContext: {
                    "dialog_size": "medium",
                },
                props: {
                    resId: this.resId,
                },
            }
        );
    },
    
    // Log thông tin mỗi khi quét mã
    async processBarcode(barcode, options={}) {
        await logStockBarcode('scan', barcode, this.record.id);
        return await super.processBarcode(...arguments)
    },

	// Phiếu kiểm kê không cho xoá dòng
    async deleteLine(line) {
        if (this.record.picking_type_code == 'inventory_counting') {
            // Hiển thị popup thông báo thay vì xóa dòng
            return this.dialogService.add(AlertDialog, {
                title: _t("Không cho phép xóa"),
                body: _t("Không thể xóa dòng sản phẩm. Chỉ có thể đặt số lượng về 0."),
                confirmLabel: _t("Đã hiểu"),
            });
        }
        return await super.deleteLine(line)
    },

	// Phiếu kiểm kê không có số lượng yêu cầu nên không check điều kiện số quét so với số yêu cầu
	// Phiếu trả lại cũng không check vì có số lượng không đạt nữa nên có thể phải quét quá số lượng yêu cầu
	_shouldCreateLineOnExceed(line) {
        if (this.record.picking_type_code == 'inventory_counting') {
        	return false;
        }
        if (this.isReturnPicking) {
            return false;
        }
        return super._shouldCreateLineOnExceed(line);
    },

    // Phiếu kiểm kê hiển thị các dòng theo thứ tự sinh ra (tức là thứ tự quét)
    _sortingMethod(l1, l2) {
        if (this.record.picking_type_code == 'inventory_counting') {
            return 0;
        }
        return super._sortingMethod(...arguments)
    },

	// Hiện tại hiển thị Số đã quét/Số lượng yêu cầu nhưng với Phiếu kiểm kê chỉ hiển thị Số đã quét
	displayLineQtyDemand(line) {
        if (this.record.picking_type_code == 'inventory_counting') {
            return false
        }
        return super.displayLineQtyDemand(...arguments)
    },

	// Tự động lưu dữ liệu khi quét mã
	async _processBarcode(barcode) {
        const result = await super._processBarcode(barcode)
        // TODO: Lệnh save này khá nặng vừa lưu vừa load lại vừa refresh cache vừa gen lại màn hình. Cần tìm cách tối ưu
        await this.save()
        return result
    },

	// Khi đã quét 1 sản phẩm thì ẩn dòng điền sẵn
    // - Bỏ những dòng = 0 không phải của mình
    get pageLines() {
        // Lấy lines từ super (đã được filter package + sort)
        let lines = super.pageLines;

        // Nhóm index theo product_id.id để biết sản phẩm nào có nhiều dòng
        // Dùng Map để giữ thứ tự xuất hiện
        const productIndexMap = new Map(); // product_id.id → [index, ...]
        lines.forEach((line, index) => {
            const pid = line.product_id.id;
            if (!productIndexMap.has(pid)) {
                productIndexMap.set(pid, []);
            }
            productIndexMap.get(pid).push(index);
        });

        const currentUserId = user.userId;

        // Tập hợp các index cần loại bỏ
        const indicesToRemove = new Set();

        for (const [pid, indices] of productIndexMap) {
            // Chỉ xử lý sản phẩm có nhiều hơn 1 dòng
            if (indices.length <= 1) continue;

            for (const index of indices) {
                const line = lines[index];

                // Giữ lại nếu qty_done > 0
                if (line.qty_done > 0) continue;

                // qty_done = 0: giữ nếu chưa lưu (dòng mới trên client)
                if (!line.id) continue;

                // qty_done = 0, đã lưu: giữ nếu là của user hiện tại
                const lineOwnerId = Array.isArray(line.create_uid)
                    ? line.create_uid[0]
                    : line.create_uid;

                if (lineOwnerId == currentUserId) continue;

                // Còn lại: qty_done=0, đã lưu, không phải của user hiện tại → loại
                indicesToRemove.add(index);
            }

            // Đề phòng: nếu toàn bộ dòng của product bị loại, giữ lại 1 dòng
            // (trường hợp này hiếm nhưng cần an toàn)
            const remaining = indices.filter(i => !indicesToRemove.has(i));
            if (remaining.length === 0) {
                // Hoàn trả dòng bị xoá gần nhất (giữ thứ tự gốc)
                indicesToRemove.delete(indices[indices.length - 1]);
            }
        }
        console.log('line ẩn', indicesToRemove)

        // Filter giữ nguyên thứ tự, chỉ bỏ index trong set
        return indicesToRemove.size > 0
            ? lines.filter((_, index) => !indicesToRemove.has(index))
            : lines;
    },

	// Copy lại source code của base (_findLine) và sửa lại để tìm ra line cũ
    _findLine(barcodeData) {
        let foundLine = false;
        const {lot, lotName, product} = barcodeData;
        const quantPackage = barcodeData.package;
        const dataLotName = lotName || (lot && lot.name) || false;
        let pageLines = [...this.pageLines]
        // If a line is selected, unshift it to the first position to start the search by it
        if (this.selectedLineVirtualId) {
            const selectedLineIndex = pageLines.findIndex(line => line.virtual_id == this.selectedLineVirtualId);
            if (selectedLineIndex > -1) {
                pageLines.splice(selectedLineIndex, 1);
                pageLines.unshift(this.pageLines[selectedLineIndex]);
            }
        }
        for (const line of pageLines) {
            const lineLotName = this.getlotName(line);
            if (line.product_id.id !== product.id) {
                continue; // Not the same product.
            }
            if (quantPackage && (!line.package_id || line.package_id.id !== quantPackage.id)) {
                continue; // Not the expected package.
            }
            if (line.product_id.tracking !== "none" && !this._canOverrideTrackingNumber(line, dataLotName)) {
                continue; // Not the same lot.
            }
            if (line.product_id.tracking === 'serial') {
                if (this.getQtyDone(line) >= 1 && lineLotName) {
                    continue; // Line tracked by serial numbers with quantity & SN.
                } else if (dataLotName && this.getQtyDone(line) > 1) {
                    continue; // Can't add a SN on a line where multiple qty. was previously added.
                }
            }

            ///////////////////////////////
            // BẮT ĐẦU THAY ĐỔI SO VỚI BASE
            // Bỏ nguyên điều kiện này
            // if ((
            //         !dataLotName || !lineLotName || dataLotName !== lineLotName
            //     ) && (
            //         line.qty_done && line.qty_done >= line.reserved_uom_qty &&
            //         (line.product_id.tracking === "none" || lineLotName) &&
            //         line.id && (!this.selectedLine || line.virtual_id != this.selectedLine.virtual_id)
            //     )) {
            //         // Has enough quantity (and another lot is set if the line's product is tracked)
            //         // and the line wasn't explicitly selected.
            //         continue;
            // }
            // Thêm đk user_id
            if (line.create_uid && line.create_uid != user.userId) {
                continue;
            }
            // KẾT THÚC THAY ĐỔI SO VỚI BASE
            /////////////////////////////////

            if (this._lineCannotBeTaken(line)) {
                continue;
            }
            if (this._lineIsNotComplete(line)) {
                if (this.lineCanBeTakenFromTheCurrentLocation(line)) {
                    // Found a uncompleted compatible line, stop searching if it has the same location
                    // than the scanned one (or if no location was scanned).
                    foundLine = line;
                    if ((this.lineIsInTheCurrentLocation(line)) &&
                        (line.product_id.tracking === 'none' || !dataLotName || dataLotName === lineLotName)) {
                        // In case of tracked product, stop searching only if no
                        // LN/SN was scanned or if it's the same.
                        break;
                    }
                } else if (this.needSourceConfirmation && foundLine && !this._lineIsNotComplete(foundLine)) {
                    // Found a empty line in another location, we should take it but depending of
                    // the config, maybe we can't (location should be confirmed first).
                    // That said, we already found another line but if it's completed, forget we
                    // found it to avoid to create a new line in the current location because it's
                    // basicaly the same than increment the other line found in another location.
                    foundLine = false;
                    continue;
                }
            }
            // If all the previous checks were passed, the line can be considered
            // as the found line. That said, if another line was already found,
            // it can be tricky to know which one we want to prioritize.
            if (!foundLine) {
                // The line matches but there could be a better candidate, so keep searching.
                // If multiple lines can match, prioritises the one at the right location (if a
                // location source was previously selected) or the selected one if relevant.
                const currentLocationId = this.lastScanned.sourceLocation && this.lastScanned.sourceLocation.id;
                if (this.selectedLine && this.selectedLine.virtual_id === line.virtual_id && (
                    !currentLocationId || !foundLine || foundLine.location_id.id != currentLocationId)) {
                    foundLine = this.lineCanBeTakenFromTheCurrentLocation(line) ? line : foundLine;
                } else if (!foundLine || (currentLocationId &&
                        foundLine.location_id.id != currentLocationId &&
                        line.location_id.id == currentLocationId)) {
                    foundLine = this.lineCanBeTakenFromTheCurrentLocation(line) ? line : foundLine;
                }
            } else if (this._lineIsNotComplete(foundLine)) {
                // If previous line is not completed, no reason to prioritize the current one.
                continue;
            } else if (this._lineIsNotComplete(line)) {
                // If previous line is completed and current one is not, prioritize the current one.
                foundLine = line;
            } else if (this.lineIsSelected(line) ||
                (!this.lineIsSelected(foundLine) && this.lineBelongsToSelectedLine(line))
            ) {
                // If both previous found line and current line are completed, prioritize the
                // current one only if it's the selected line (or on of its sublines.)
                foundLine = line;
            }
        }
        return foundLine;
    },

    async validate() {
    // ===== POPUP 1: cảnh báo / hỏi kiểm tra lại =====
        const mismatchedProducts = await this.orm.call('stock.picking', 'get_products_with_inventory_mismatch', [this.record.id]);
        const check_product_inventory_origin = await this.orm.call('stock.picking', 'check_product_inventory_origin', [this.record.id]);

        let productListHtml = "";
        if (mismatchedProducts.length) {
            productListHtml = `
                <table class="table table-sm table-bordered mt-2">
                    <thead>
                        <tr>
                            <th>${_t("Sản phẩm")}</th>
                            <th class="text-end">${_t("Số đếm")}</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${mismatchedProducts.map(p => `
                            <tr>
                                <td>${escape(p.product_name)}</td>
                                <td class="text-end">${p.counted_quantity}</td>
                            </tr>
                        `).join("")}
                    </tbody>
                </table>
            `;
        }
        const firstConfirm = await new Promise((resolve) => {
            if (check_product_inventory_origin) {
                this.dialogService.add(ConfirmationDialog, {
                    title: _t("Cảnh báo"),
                    body: markup(`
                        <div class="text-danger">
                            ${escape(
                                _t("Một số sản phẩm có số đếm lệch so với tồn trên hệ thống. Bạn có muốn kiểm tra lại không?")
                            )}
                        </div>
                        ${productListHtml}
                    `),
                    confirmLabel: _t("Vẫn xác nhận"),
                    cancelLabel: _t("Có, muốn kiểm tra lại"),
                    confirm: () => resolve(true),
                    cancel: () => resolve(false),
                });
            } else {
                // Không có lệch tồn → cho đi tiếp luôn
                resolve(true);
            }
        });

        // Nếu người dùng chọn "Có, muốn kiểm tra lại" → dừng
        if (!firstConfirm) {
            return false;
        }

        // ===== LOGIC CŨ CỦA BẠN (GIỮ NGUYÊN) =====

        // Tính toán thời gian kiểm kê
        let durationText = "";
        if (this.scanStartTime) {
            const endTime = new Date();
            const duration = Math.floor((endTime - this.scanStartTime) / 1000);
            const minutes = Math.floor(duration / 60);
            const seconds = duration % 60;
            durationText = `${minutes} phút ${seconds} giây`;
        }

        const confirmMessage1 = _t(
            "Khi nhấn nút Xác nhận đã hoàn thành phiếu thì phiếu sẽ biến mất và bạn sẽ không thao tác được với phiếu nữa."
        );
        const confirmMessage2 = _t(
            "Hãy nhấn nút Tiếp tục làm việc với phiếu nếu bạn vẫn chưa hoàn thành."
        );
        const timeMessage = durationText
            ? _t("Thời gian thực hiện: %s", durationText)
            : "";

        return new Promise((resolve) => {
            this.dialogService.add(ConfirmationDialog, {
                body: markup(
                    `<div class="text-danger">${escape(confirmMessage1)}</div>
                     <div class="text-danger">${escape(confirmMessage2)}</div>
                     ${timeMessage ? `<div class="text-info mt-2">${escape(timeMessage)}</div>` : ""}`
                ),
                title: _t("Xác nhận đã hoàn thành"),
                confirmLabel: _t("Xác nhận đã hoàn thành phiếu"),
                cancelLabel: _t("Tiếp tục làm việc với phiếu"),
                confirm: async () => {
                    const result = await super.validate();
                    resolve(result);
                },
                cancel: () => resolve(false),
            });
        });
    }
})
