
var txtQD_TimKiem;
var dgQuyDoi;
var DATA_QD;
function initCtrlQuyDoi() {
    txtQD_TimKiem = $("#txtQD_TimKiem").dxTextBox({
        placeholder: 'nhập thông tin cần tìm'
    }).dxTextBox("instance");

    $("#helpQuyDoi").html(createHelpLink("DON_VI_TINH"))

    $("#helpQuyDoi").html(
        `
            <div class='d-flex justify-content-end'> 
                <a  href='https://www.youtube.com/watch?v=xmz0_3ZCUaU&ab_channel=VanNhatNguyen' target='_blank'><em class=" fw-bold text-danger icon ni ni-youtube" style='font-size:32px'></em> </a> 
                <a  style='background-image: linear-gradient(45deg, #f70bc7, #5700b1);-webkit-background-clip: text; background-clip: text;color: transparent;margin-top:7px;font-weight:bold;' href='https://www.youtube.com/watch?v=xmz0_3ZCUaU&ab_channel=VanNhatNguyen' target='_blank'>&nbsp;&nbsp;Video HDSD chức năng Quy đổi&nbsp;&nbsp;</a>
            </div>
        `
    )
    setTimeout(function () {
        $('input[type="text"]').attr('autocomplete', 'off');
    }, 200);
}

function prepareObjectQuyDoi() {
    try {
        var searchObj = {
            'KeywordQuyDoi': txtQD_TimKiem.option("value").trim(),
            'MaSoThue': MST,
        };
        return searchObj;

    } catch (e) {
        var searchObj = {
            'KeywordQuyDoi': '',
            'MaSoThue': MST,
        };
        return searchObj;
    }
    
}
function SearchQuyDoi() {

    let searchObj = prepareObjectQuyDoi();
    $.ajax({
        type: "POST",
        dataType: "json",
        url: '/QLHD/QuyDoi',
        data: searchObj,
        success: function (data) {
            DATA_QD = data;
            dspDataQuyDoi();
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR);
            goTohome(jqXHR.responseText);

        }
    });
}



function KetXuatQuyDoi() {
    $("#dgQuyDoiExport").show();
    dgQuyDoiExport = $("#dgQuyDoiExport").dxDataGrid({
        dataSource: DATA_QD,
        onContentReady: function (e) {
            dgQuyDoiExport.exportToExcel();
        },
        export: {
            fileName: 'Quy Đổi ĐVT - ' + MST
        },
        height: 1,
        wordWrapEnabled: true,
        allowColumnReordering: true,
        rowAlternationEnabled: true,
        showBorders: true,
        filterRow: { visible: true },
        showColumnLines: true,
        showRowLines: true,
        rowAlternationEnabled: true,
        columnAutoWidth: true,
        noDataText: "Không có dữ liệu",
        repaintChangesOnly: true,
        scrolling: {
            columnRenderingMode: 'virtual',
            useNative: false,
            renderAsync: true,
            showScrollbar: "always"
        },
      
        columns: [
            {
                dataField: "MaHang", caption: "Mã hàng", width: 200
            },
            {
                dataField: "TenHang", caption: "Tên hàng", width: 500
            },
            {
                dataField: "Dvt", caption: "ĐVT Gốc (hóa đơn)"
            },
            {
                dataField: "DvtquyDoi", caption: "ĐVT Đích (Quy Đổi)"
            },
            {
                dataField: "SoLuongQuyDoi", caption: "Số lượng quy đổi"
            },
            
        ]
    }).dxDataGrid("instance");
    setTimeout(function () {
        $("#dgQuyDoiExport").hide();

        clearAutoCompleted();
    }, 200)

}


function XoaTatCaQuyDoi() {
    var result = DevExpress.ui.dialog.confirm("Hệ thống sẽ xóa tất cả hàng hóa thỏa điều kiện tìm kiếm.<br/>Xóa rồi sẽ không phục hồi lại được vì thế bạn nên Export ra 1 bản trước khi xóa.<br/><b>Bạn đã chắc cú chưa?</b>", "XÓA TOÀN BỘ HÀNG HÓA");
    result.done(function (dialogResult) {
        if (dialogResult) {

            let searchObj = prepareObjectQuyDoi();
            searchObj.IsXoa = true;
            loadingQuyDoi(true, "Đang xóa Hàng Hóa<br/>Vì thế nên vui lòng chờ đợi")
            $.ajax({
                type: "POST",
                dataType: "json",
                url: '/QLHD/QuyDoi',
                data: searchObj,
                success: function (data) {
                    if (data.status == 1) {
                        dAlert("Xóa quy đổi thành công", "Thông báo")
                        SearchQuyDoi();
                    }
                    else {
                        dAlert(data.message, "Lỗi đồng bộ")
                        SearchQuyDoi();

                    }
                    loadingQuyDoi(false)


                },
                error: function (jqXHR, textStatus, errorThrown) {
                    console.log(jqXHR);
                    loadingQuyDoi(false)
                    goTohome(jqXHR.responseText);

                }
            });
        }

    });
}


function dspDataQuyDoi() {
    if (dgQuyDoi) {
        dgQuyDoi.option("dataSource", DATA_QD);
        dgQuyDoi.refresh();
    }
    else {

        var TOTAL_COLUMNS_QD = [{
            column: 'MaHang',
            summaryType: "count",
            displayFormat: '{0} hàng hóa',
        }
        ];


        var COLUMNS_QD = [
            {
                dataField: "MaHang", headerCellTemplate: "Mã hàng"
            },
            {
                dataField: "TenHang", headerCellTemplate: "Tên hàng"
            },
            {
                dataField: "Dvt", headerCellTemplate: "ĐVT Gốc<br/>(Hóa Đơn)"
            },
            {
                dataField: "DvtquyDoi", headerCellTemplate: "ĐVT Đích<br/>(Quy Đổi)"
            },
            {
                dataField: "SoLuongQuyDoi", headerCellTemplate: "Số lượng quy đổi"
            },
        ];

        dgQuyDoi = $("#dgQuyDoi").dxDataGrid({
            dataSource: DATA_QD,
            repaintChangesOnly: true,
            scrolling: {
                columnRenderingMode: 'virtual',
                useNative: false,
                renderAsync: true,
                showScrollbar: "always"
            },
            editing: {
                mode: "batch",
                allowUpdating: true,
                allowDeleting: true,

                useIcons: true,
                useKeyboard: true,
                startEditAction: "click",
                editMode: "cell",
                selectTextOnEditStart: true,
                highlightChanges: true,
                repaintChangesOnly: true,
            },
            keyboardNavigation: {
                enterKeyAction: 'moveFocus',
                enterKeyDirection: 'column',
                editOnKeyPress: true,
            },
            onToolbarPreparing: function (e) {
                e.toolbarOptions.items.unshift({
                    location: "after",
                    widget: "dxButton",
                    options: {
                        icon: "add",
                        hint: "Thêm Quy đổi ĐVT (Alt+N)",
                        onClick: function () {
                            OpenModalThemQuyDoi ();
                        }
                    }
                });
            },
            showBorders: true,
            paging: {
                enabled: true,
                pageSize: 100,
                pageIndex: 0    // Shows the second page
            },
            height: $("#dg").height(),
            wordWrapEnabled: true,
            allowColumnReordering: true,
            rowAlternationEnabled: true,
            showBorders: true,
            filterRow: { visible: true },
            showColumnLines: true,
            showRowLines: true,
            rowAlternationEnabled: true,
            columnAutoWidth: true,
            noDataText: "Không có dữ liệu",
            pager: {
                showPageSizeSelector: true,
                allowedPageSizes: [50, 100, 150, 200],
                showNavigationButtons: true,
                showInfo: true,
                infoText: " Tổng cộng: {2} hàng hóa - Trang {0}/{1}"
            },
            columnFixing: {
                enabled: true
            },
            summary: {
                totalItems: TOTAL_COLUMNS_QD
            },
            columns: COLUMNS_QD,

            onSaving(e, i) {
                let changes = e.changes;
                e.promise = true;

                if (changes.length > 0) {

                    let updateData = [];
                    for (let k in changes) {
                        let type = changes[k].type;
                        let dataChanges = changes[k].data;
                        if (type == "update") {
                            let dataOrgs = JSON.parse(JSON.stringify(changes[k].key));
                            for (let key in dataChanges)
                                dataOrgs[key] = dataChanges[key];
                            dataOrgs["Loai"] = "update";
                            updateData.push(dataOrgs);
                        }
                        else if (type == "remove") {
                            let dataOrgs = JSON.parse(JSON.stringify(changes[k].key));
                            for (let key in dataChanges)
                                dataOrgs[key] = dataChanges[key];

                            dataOrgs["Loai"] = "delete";
                            updateData.push(dataOrgs);
                        }
                    }
                    console.log(updateData)

                    $.ajax({
                        type: "POST",
                        dataType: "json",
                        url: '/QLHD/QuyDoi/Update',
                        data: {
                            quyDoi: updateData
                        },
                        success: function (data) {
                            if (data.status == 1) {
                                dAlert("Hoan hô. Đã cập nhật xong", "Thông báo")
                            }
                            else {
                                dAlert(data.message, "Thông báo");
                                SearchQuyDoi();
                            }

                        },
                        error: function (jqXHR, textStatus, errorThrown) {
                            console.log(jqXHR);
                            goTohome(jqXHR.responseText);

                        }
                    });


                }
                else {
                    e.cancel = true;
                    $(".dx-icon-edit-button-cancel").click();
                    e.promise = null;
                }
            },
        }).dxDataGrid("instance");


    }
}



function ImportQuyDoi() {
    $("#importFileQuyDoi").unbind().on("change", function () {
        var dataImport = [];
        var fileUpload = $("#importFileQuyDoi").prop('files')[0];
        if (fileUpload) {
            var isXlsx = fileUpload.name.toLowerCase().indexOf(".xlsx") > 0;

            if (typeof (FileReader) != "undefined") {
                const wb = new ExcelJS.Workbook();
                const reader = new FileReader()
                var lstKey = [];
                var strMSG = "";
                reader.readAsArrayBuffer(fileUpload)
                reader.onload = () => {
                    const buffer = reader.result;
                    wb.xlsx.load(buffer).then(workbook => {
                        workbook.eachSheet((sheet, id) => {
                            sheet.eachRow((row, rowIndex) => {
                                let data = row.values;
                                try {
                                    if (data.length > 2 && rowIndex > 1) {
                                        let maHang = getExcelData(data, 1);
                                        let tenHang = getExcelData(data, 2);
                                        let dvt = getExcelData(data, 3);
                                        let dvtQuyDoi = getExcelData(data, 4);
                                        let soLuongQuyDoi = 0;
                                        try {
                                            soLuongQuyDoi = parseFloat(getExcelData(data,5));
                                        }
                                        catch {
                                            strMSG += "Dòng " + rowIndex + ", " + tenHang + ": Số lượng quy đổi sai định dạng<br/>";
                                            soLuongQuyDoi = 0;
                                        }

                                        var dataHang = {
                                            "MaHang": maHang.toString().trim(),
                                            "TenHang": tenHang.toString().trim(),
                                            "DVT": dvt.toString().trim(),
                                            "DVTQuyDoi": dvtQuyDoi.toString().trim(),
                                            "SoLuongQuyDoi": soLuongQuyDoi,
                                            "MaSoThue": MST,
                                        };
                                        if (data.MaHang && data.DVT && data.DVTQuyDoi && data.MaHang && soLuongQuyDoi <= 0) {
                                            strMSG += "Dòng "+rowIndex+", Dữ liệu không đúng định dạng - "+JSON.stringify(dataHang)+"<br/>"
                                           
                                        }
                                        else {
                                            //hoa mai
                                            //MAI TRUONG DINH anhtienane247
                                            var key = (MST == "0302797984" || MST == "0402130175" ) ? dataHang.MaHang + "_" + dataHang.TenHang + "_" + dataHang.DVT : dataHang.MaHang + "_" + dataHang.DVT;
                                            //var key = dataHang.MaHang + "_" + dataHang.TenHang + "_" + dataHang.DVT;
                                            if (lstKey.indexOf(key) == -1) {
                                                dataImport.push(dataHang);
                                                lstKey.push(key);
                                            }
                                            else {
                                                strMSG += "Dòng " + rowIndex + ", Dữ liệu bị trùng với dòng trước đó - " + JSON.stringify(dataHang)+"<br/>"
                                            }
                                        }
                                    }
                                }
                                catch (err) {
                                    console.log(data);
                                    console.log(err);
                                    dAlert("File dữ liệu import bị lỗi định dạng", "Lỗi định dạng")
                                    return;
                                }
                            });
                        })
                    }).then(function () {
                        $("#importFileQuyDoi").val("");
                   
                        if (!isXlsx) {
                            strMSG = "File Excel không đúng định dạng XLSX (Office 2007 trở lên)";
                        }
                        if (strMSG == "") {
                            if (dataImport.length > 0) {
                                ImportQuyDoiChiTiet(dataImport);
                            }
                            else {
                                dAlert("Không đọc được dữ liệu trong file Excel.<br/>Hãy chắc rằng file Excel có dữ liệu và đúng định dạng XLSX thực sự (Office 2007 trở lên).", "Lỗi");
                            }
                        }
                        else
                            dAlert(strMSG, "Lỗi")

                    });
                }
            }

        }
    });

    $("#importFileQuyDoi").click();

}



function ImportQuyDoiChiTiet(array) {
    impX = array.length;
    impC = 0;

    var lstChunks = chunks(150, array);
    aj_importQD(lstChunks, 0, lstChunks.length);
}


function aj_importQD(lst, b, e) {
    if (b == e) {
        SearchQuyDoi();
        dAlert("Import ĐVT Quy Đổi thành công", "Thông báo")
        loadingQuyDoi(false)
    }
    else {
        $.ajax({
            type: "POST",
            dataType: "json",
            url: '/QLHD/QuyDoi/Import',
            data: {
                quyDoi: lst[b]
            },
            success: function (data) {
                console.log(data);
                if (data.status == 1) {
                    impC = impC + lst[b].length;
                    loadingQuyDoi(true, "Đang import được " + impC + "/" + impX + " hàng hóa")
                    b++;
                    aj_importQD(lst, b, e)

                }
                else {
                    dAlert(data.message, "Thông báo")
                    loadingQuyDoi(false)
                    goTohome(jqXHR.responseText);

                    return;
                }

            },
            error: function (jqXHR, textStatus, errorThrown) {
                console.log(jqXHR);
                b++;
            }
        });
    }
}

function loadingQuyDoi(isShow, status) {

    if (isShow) {
        $("#statusImportQuyDoi").html(
            `<div class = 'alert alert-success text-center'>
                <div class="spinner-border " role="status">
                  <span class="visually-hidden">đang import ...</span>
                </div>
            <div class='mt-2'>
            ${status}   
            </div>
        </div>`
        ).show();
    }
    else {
        $("#statusImportQuyDoi").hide();
    }

}
