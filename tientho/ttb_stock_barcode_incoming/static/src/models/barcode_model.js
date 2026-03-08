import { _t } from "@web/core/l10n/translation";
import { escape } from "@web/core/utils/strings";
import BarcodeModel from "@stock_barcode/models/barcode_model";
import BarcodePickingModel from '@stock_barcode/models/barcode_picking_model';
import { ConfirmationDialog, AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { patch } from "@web/core/utils/patch";
import { markup } from "@odoo/owl";
import { user } from '@web/core/user';
import { logStockBarcode } from "../barcode_logger_utils";

patch(BarcodeModel.prototype, {

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
    async deleteLine(line) {
        // Hiển thị popup thông báo thay vì xóa dòng
        this.dialogService.add(AlertDialog, {
            title: _t("Không cho phép xóa"),
            body: _t("Không thể xóa dòng sản phẩm. Chỉ có thể đặt số lượng về 0."),
            confirmLabel: _t("Đã hiểu"),
        });
    },

    async processBarcode(barcode, options={}) {
        await logStockBarcode('scan', barcode, this.record.id);
        return await super.processBarcode(...arguments)
    },
});

patch(BarcodePickingModel.prototype, {
    // Thêm biến instance để lưu thời gian bắt đầu
    setup() {
        super.setup();
        this.scanStartTime = null;
    },
    lineCanBeDeleted(line) {
        return true;
    },
    get isReturnPicking() {
        return !!(this.record && this.record.ttb_return_request_id);
    },
    get isPickOrPack() {
        if (!this.record || !this.record.pickup_status) return false;
        return ['picking', 'packing'].includes(this.record.pickup_status);
    },

    get isRestrictedMode() {
        if (!this.record) return false;

        if (this.isReturnPicking) return true;

        const type = this.record.picking_type_code;

        return ['outgoing', 'internal'].includes(type);
    },

    get pageLines() {
        // Lấy danh sách gốc
        let lines = super.pageLines;

        // Log trạng thái cờ
        const isRestricted = this.isRestrictedMode;
        const isReturn = this.isReturnPicking;

        // Chỉ in log 1 lần để đỡ spam (check nếu lines > 0)
        if (lines.length > 0 && Math.random() < 0.05) {
             console.log(`[TTB Filter Status] Restricted: ${isRestricted}, Return: ${isReturn}, UserID: ${user.userId}`);
        }

        // Logic lọc
        if (isRestricted && isReturn) {
            const currentUserId = user.userId;

            lines = lines.filter(line => {
                // 1. Dòng mới (chưa lưu) -> Luôn hiện
                if (!line.id) {
                    return true;
                }

                // 2. Dòng đã lưu -> Check chủ sở hữu
                let lineOwnerId = null;

                if (line.create_uid) {
                    // Xử lý cả trường hợp mảng [ID, Name] hoặc số ID
                    lineOwnerId = Array.isArray(line.create_uid) ? line.create_uid[0] : line.create_uid;
                }

                // [LOG QUAN TRỌNG] Kiểm tra từng dòng xem tại sao nó hiện/ẩn
                // Chỉ bật log này nếu thấy nghi ngờ

                console.log("[TTB Line Check]", {
                    product: line.product_id.display_name,
                    lineOwnerId: lineOwnerId,
                    myUserId: currentUserId,
                    isMatch: lineOwnerId === currentUserId
                });


                // So sánh (Dùng == để so sánh lỏng tránh lệch kiểu int/string)
                if (lineOwnerId == currentUserId) {
                    return true;
                }

                return false; // Ẩn dòng của người khác
            });
        }

        return lines;
    },

    async deleteLine(line) {
        if (this.isRestrictedMode) {
            // Thay thế this.notification bằng Dialog để tránh lỗi
            this.dialogService.add(AlertDialog, {
                title: _t("Cảnh báo"),
                body: _t("Không cho phép xóa sản phẩm trong phiếu này!"),
                confirmLabel: _t("Đóng"),
            });
            return;
        }
        await super.deleteLine(line);
    },

    async _processBarcode(barcode) {
        let targetModel = this.resModel || 'stock.picking';
        let targetResId = this.resId || false;

        if (this.record) {
            await this.orm.call(
                'stock.picking',
                'update_inventory_start_time',
                [this.resId]
            );
            if (this.isReturnPicking && this.record.ttb_return_request_id) {
                targetModel = 'ttb.return.request';
                targetResId = Array.isArray(this.record.ttb_return_request_id)
                              ? this.record.ttb_return_request_id[0]
                              : this.record.ttb_return_request_id;
            }
            else if (this.record.picking_type_code === 'inventory_counting') {

                targetModel = 'inventory.counting';
            }
        }

        if (this.isReturnPicking || (this.isRestrictedMode && this.isPickOrPack)) {

            const products = await this.orm.call('product.product', 'search_read', [
                ['|', '|', '|', 
                 ['barcode', '=', barcode], 
                 ['barcode_vendor', '=', barcode],
                 ['barcode_k', '=', barcode],
                 ['default_code', '=', barcode]
                ], 
                ['id', 'display_name']
            ], { limit: 1 });

            if (products && products.length > 0) {
                const product = products[0];


                console.log(`🔍 [TTB Check] Checking product: ${product.display_name} (ID: ${product.id})`);

                // Bước 2: CHECK SERVER-SIDE (Thay thế cho move_ids.some client-side)
                // Hỏi server: "Có dòng stock.move nào trong phiếu này chứa sản phẩm này không?"
                const isMoveExist = await this.orm.call('stock.move', 'search_count', [[
                    ['picking_id', '=', this.resId],  // Trong phiếu hiện tại
                    ['product_id', '=', product.id],  // Đúng sản phẩm vừa quét
                    ['state', '!=', 'cancel']         // Không tính dòng đã hủy
                ]]);

                console.log(`🔍 [TTB Check] Result in Demand (stock.move): ${isMoveExist}`);

                if (isMoveExist === 0) {

                    this.dialogService.add(AlertDialog, {
                        title: _t("Sai sản phẩm"),
                        body: _t(`Sản phẩm '${product.display_name}' không có trong danh sách cần xử lý!`),
                        confirmLabel: _t("Đã hiểu"),
                    });
                    return;
                }
            }
        }

        // --- Logic cũ của Trả hàng ---
        if (this.isReturnPicking) {
             return super._processBarcode(barcode);
        }

        // --- Logic cũ của Kiểm kê ---
        try {
            // Ghi lại thời gian nếu đây là lần quét đầu tiên
            if (!this.scanStartTime) {
                this.scanStartTime = new Date();
                console.log("Đang ghi thời gian bắt đầu:", this.scanStartTime);

                // Đảm bảo orm đã sẵn sàng
                if (!this.orm) {
                    console.error("ORM không có sẵn!");
                    return await super._processBarcode(barcode);
                }

                // Format date to match Odoo's expected format: YYYY-MM-DD HH:MM:SS
                const formattedDate = this.scanStartTime.toISOString().replace('T', ' ').split('.')[0];

                // Lưu thời gian bắt đầu kiểm kê vào Odoo
                await this.orm.write("stock.picking", [this.resId], {
                    inventory_scan_start_time: formattedDate,
                });

                // Tải lại bản ghi để xác minh rằng dữ liệu đã được lưu
                // await this.reload();
            }

            await super._processBarcode(barcode);
            await this.save();
        } catch (error) {
            console.error("Lỗi khi xử lý barcode:", error);
            await super._processBarcode(barcode);
        }
    },

    _createLine(data) {
        if (this.isReturnPicking || (this.isRestrictedMode && this.isPickOrPack)) {
            const product = data.product;
            
            // Kiểm tra an toàn ID sản phẩm trong move_ids
            const inDemand = this.record.move_ids.some(m => {
                 const mPid = Array.isArray(m.product_id) ? m.product_id[0] : m.product_id;
                 return mPid === product.id;
            });
            
            if (!inDemand) {
                return undefined; // Hủy tạo dòng
            }
        }
        const line = super._createLine(data);

        if (line && this.isRestrictedMode && this.isReturnPicking) {
            line.create_uid = user.userId;

            // Đánh dấu dòng đã thay đổi để Odoo lưu lại khi save()
            this._markLineAsDirty(line);
            this.save();
        }

        return line;
    },

    // -------------------------------------------------------------------------
    // CÁC HÀM KHÁC GIỮ NGUYÊN
    // -------------------------------------------------------------------------
    lineCanBeDeleted(line) { return true; },

    _findLine(barcodeData) {
        if (this.isReturnPicking) return super._findLine(barcodeData);
        if (this.record.picking_type_code != 'inventory_counting') return super._findLine(barcodeData);
        return super._findLine(barcodeData);
    },

    _shouldCreateLineOnExceed(line) {
        if (this.isRestrictedMode) return false;
        if (this.isReturnPicking) {
            return false;
        }

        if (this.record.picking_type_code != 'inventory_counting') {
            return super._shouldCreateLineOnExceed(line);
        }
        return false;
    },

    _sortingMethod(l1, l2) {
        if (this.record.picking_type_code != 'inventory_counting') {
            return super._sortingMethod(...arguments)
        }
        return 0;
    },

    displayLineQtyDemand(line) {
        if (this.record.picking_type_code != 'inventory_counting') {
            return super.displayLineQtyDemand(...arguments)
        }
        return false
    },

    // Copy lại source code của base và sửa lại để tìm ra line cũ
    _findLine(barcodeData) {

        if (this.isReturnPicking) {
            console.log("[TTB_RETURN_MERGE] scan", {
            barcode: barcodeData?.barcode,
            product: barcodeData?.product?.display_name,
            product_id: barcodeData?.product?.id,
            currentLines: (this.pageLines || []).map(l => ({
                pid: l.product_id?.id, qty_done: l.qty_done, vid: l.virtual_id
            })),
        });

            const { lot, lotName, product } = barcodeData;
            const quantPackage = barcodeData.package;
            const dataLotName = lotName || (lot && lot.name) || false;

            // ưu tiên selected line trước
            let pageLines = [...(this.pageLines || [])];
            if (this.selectedLineVirtualId) {
                const idx = pageLines.findIndex(l => l.virtual_id == this.selectedLineVirtualId);
                if (idx > -1) {
                    const selected = pageLines[idx];
                    pageLines.splice(idx, 1);
                    pageLines.unshift(selected);
                }
            }

            for (const line of pageLines) {
                if (!line.product_id || line.product_id.id !== product.id) {
                    continue;
                }

                // Nếu có package thì match package
                if (quantPackage && (!line.package_id || line.package_id.id !== quantPackage.id)) {
                    continue;
                }

                // Nếu hàng tracking thì match lot/serial (để tránh gộp sai)
                const lineLotName = this.getlotName ? this.getlotName(line) : false;
                if (line.product_id.tracking !== "none") {
                    if (!this._canOverrideTrackingNumber(line, dataLotName)) {
                        continue;
                    }
                    // nếu có lotName scan vào thì phải trùng
                    if (dataLotName && lineLotName && dataLotName !== lineLotName) {
                        continue;
                    }
                }

                // Check user ownership
                if (line.create_uid) {
                    const lineUserId = Array.isArray(line.create_uid) ? line.create_uid[0] : line.create_uid;
                    if (lineUserId !== user.userId) {
                        continue;
                    }
                }

                if (this._lineCannotBeTaken && this._lineCannotBeTaken(line)) {
                    continue;
                }

                // QUAN TRỌNG: với phiếu trả, hễ match product (và lot/package nếu có) thì trả về line này
                // để Odoo cộng dồn vào đây, KHÔNG tạo line mới.
                console.log("[TTB_RETURN_MERGE] reuse line", {
                product_id: product.id,
                virtual_id: line.virtual_id,
                qty_done: line.qty_done,
            });

                return line;
            }

            // Không tìm thấy line cũ => trả về null để tạo line mới
            return null;
        }

        if (this.record.picking_type_code != 'inventory_counting') {
            return super._findLine(barcodeData)
        }

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

});
