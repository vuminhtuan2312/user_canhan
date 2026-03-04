//2024-08-08 08:30

var TOTAL_COLUMNS_DN = [{
    column: 'tin',
    summaryType: "count",
    displayFormat: '{0} MST',
}];
var COLUMNS_DN = [
    { dataField: "tin", headerCellTemplate: "Mã số thuế", caption: "Mã số thuế" },
    { dataField: "norm_name", headerCellTemplate: "Tên DN", caption: "Tên DN" },
    { dataField: "econ_name", headerCellTemplate: "Loại hình DN", caption: "Loại DN" },
    //{ dataField: "tran_addr", headerCellTemplate: "Địa chỉ", caption: "Địa chỉ" },
    { dataField: "nd_diachi", headerCellTemplate: "Địa chỉ", caption: "Địa chỉ" },
    //{ dataField: "nd_nguoidaidien", headerCellTemplate: "Người đại diện", caption: "Người đại diện" },
    //{ dataField: "tran_tel", headerCellTemplate: "Điện thoại", caption: "Điện thoại" },
    { dataField: "pay_taxo_name", headerCellTemplate: "CQT quản lý", caption: "CQT quản lý", },
    { dataField: "regi_date", headerCellTemplate: "Ngày đăng ký", caption: "Ngày đăng ký", dataType: "date", format: 'dd/MM/yy', },
    { dataField: "tu_ngay", headerCellTemplate: "Ngày thay đổi thông tin gần nhất", caption: "Ngày thay đổi thông tin gần nhất", dataType: "date", format: 'dd/MM/yy', },
    //{ dataField: "den_ngay", headerCellTemplate: "Ngày ngừng HĐ", caption: "Ngày ngừng HĐ", dataType: "date", format: 'dd/MM/yy', },
    { dataField: "cong_van", headerCellTemplate: "Công Văn", caption: "Công Văn" },
    { dataField: "statusName", headerCellTemplate: "Tình trạng", caption: "Tình trạng" },
];


var TOTAL_COLUMNS_CN = [{
    column: 'SoGiayTo',
    summaryType: "count",
    displayFormat: '{0}',
}];

var COLUMNS_CN = [
    { dataField: "SoGiayTo", headerCellTemplate: "CMND/CCCD", caption: "CMND/CCCD" },
    
    { dataField: "TenNguoiNopThue", headerCellTemplate: "Tên người nộp thuế", caption: "Tên người nộp thuế" },

    { dataField: "LoaiGiayTo", headerCellTemplate: "Loại giấy tờ", caption: "Loại giấy tờ" },
    { dataField: "MaSoThue", headerCellTemplate: "MST", caption: "MST" },
    { dataField: "CoQuanThue", headerCellTemplate: "CQT", caption: "CQT" },
    { dataField: "NgayCap", headerCellTemplate: "Ngày cấp", caption: "Ngày cấp" },
    { dataField: "TrangThai", headerCellTemplate: "Trạng thái", caption: "Trạng thái" },
];



function ExportDSMST() {
    dgTraCuuThongTin.exportToExcel();
}

function isnum(val) {
    return /^\d+$/.test(val);
}

function MSTHopLe(mst) {
    mst = mst.trim();
    const pattern = /^(?:\d{10}|\d{10}-\d{3})$/;
    return pattern.test(mst);
}

function GiayToHopLe(str) {
    return isnum(str) && (str.length == 9 || str.length == 12 || str.length == 10 || str.length == 14 );
}


function TraCuuDSGiayToCaNhan() {

    let dsMST = $("#txtDSGiayToCaNhan").val().split("\n");
    if (dsMST.length > 0) {
        let dataMST = [];
        for (let i = 0; i < dsMST.length; i++) {
            let giayTo = dsMST[i].trim();
            if (GiayToHopLe(giayTo) && dataMST.indexOf(giayTo) == -1) {
                dataMST.push(giayTo);
            }
        }
        if (dataMST.length > 0) {
            hideModal("mTraCuuCN");
            TraCuuMST("CN", dataMST);


        }
        else {
            dAlert("Không có dữ liệu để tra cứu", "Thông báo");
        }
    }

}

function TraCuuDSMST(TXT_ALL) {
    var dsMST;
    if (TXT_ALL) {
        dsMST = TXT_ALL.split("\n");
        TXT_ALL = '';
    }
    else {
        dsMST = $("#txtDSMST").val().split("\n");
    }
    if (dsMST.length > 0) {
        let dataMST = [];
        for (let i = 0; i < dsMST.length; i++) {
            let mst = dsMST[i].trim();
            if (MSTHopLe(mst) && dataMST.indexOf(mst) == -1) {
                dataMST.push(mst);
            }
        }
        if (dataMST.length > 0) {
            hideModal("mTraCuuDN");
            hideModal("mTraCuuCN");
            TraCuuMST("DN",dataMST);
        }
        else {
            dAlert("Không có dữ liệu để tra cứu", "Thông báo");
        }
    }

}

function TraCuuMST(loai, array) {
    dgTraCuuThongTin.option("columns", loai == "DN" ? COLUMNS_DN : COLUMNS_CN);
    dgTraCuuThongTin.option("summary.totalItems", loai == "DN" ? TOTAL_COLUMNS_DN : TOTAL_COLUMNS_CN);
    dgTraCuuThongTin.option("export.fileName", loai == "DN" ? 'NIBOT - Tra cứu MST' : 'NIBOT - Tra cứu CMND-CCCD');

    CHUNKS_SIZE_MST = 30;

    DATA_TC = [];
    ttX = array.length;
    ttC = 0;
    if (ttX >= 400) {
        CHUNKS_SIZE_MST = 150;
    } else if (ttX >= 300) {
        CHUNKS_SIZE_MST = 100;
    }
    else if (ttX >= 100) {
        CHUNKS_SIZE_MST = 50;
    }

    var lstChunks = chunks(CHUNKS_SIZE_MST, array);
    beginTime = new Date();
    loadingTC(true, "Đang xử lý được 0 / " + ttX.toString() + " mã số thuế");
    aj_traCuuMST(loai,lstChunks, 0, lstChunks.length);
}


function aj_traCuuMST(loai, dataMST, b, e) {
    if (b == e) {
        endTime = new Date();
        let tgian = ((endTime - beginTime) / 1000);
        if (tgian > 5) {
            dAlert("Xử lý xong. Thời gian xử lý " + ((endTime - beginTime) / 1000) + " giây", "Thông báo");
        }
        loadingTC(false);
        return;
    }

    
    let url = (loai == "DN") ? '/QLHD/TraCuuMST' : '/QLHD/TraCuuMSTCaNhan/';
    let loaiGT = (loai == "DN") ? ' mã số thuế' : ' CMND/CCCD';
    $.ajax({
        type: "POST",
        dataType: "json",
        url: url,
        data: {
            "lstMST": dataMST[b]
        },
        success: function (data) {
            if (data.status == 1) {
                if (data.obj != null) {
                    ttC += data.obj.length;
                    DATA_TC = DATA_TC.concat(data.obj);
                    dgTraCuuThongTin.option("dataSource", DATA_TC);
                    dgTraCuuThongTin.refresh();

                    loadingTC(true, "Đang xử lý được " + ttC.toString() + " / " + ttX.toString() + loaiGT);
                }
                b++;
                aj_traCuuMST(loai,dataMST, b, e)
            }
            else {
                dAlert(data.message, "Thông báo")
            }
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR);
            goTohome(jqXHR.responseText);
        }
    });
}

function showModalTraCuu(loai) {
    if (loai == 'DN') {
        let bodyHtml = `
            <p>Nhập danh sách MST vào đây, mỗi mã số thuế là 1 dòng. Nibot sẽ tự động loại bỏ MST không đúng định dạng và khử trùng nếu có.</p>
            <textarea id="txtDSMST" class="form-control" row=8></textarea>
        `
        let btnHtml = `
                <button class="btn btn-sm btn-primary" onclick = "TraCuuDSMST()" > <em class="icon ni ni-spark"></em>&nbsp;&nbsp;Tra cứu nhanh</button>
        `;

        createModal("mTraCuuDN", "Tra cứu thông tin DN dựa vào MST", bodyHtml, btnHtml);
        if (DATA_TC.length>0) {
            let str = '';
            for (let i in DATA_TC) {
                if (str != "") str += "\n";
                str += DATA_TC[i].mst;
            }
            $("#txtDSMST").val(str);
        }

        $("#txtDSMST").val()
        showModal("mTraCuuDN");
        setTimeout(function () {
            $("#txtDSMST").focus();
        }, 200);
    }
    else if (loai=='CN') {
        let bodyHtml = `
            <p id='txtLabelCN' class='mt-2'>Nhập mỗi CMND/CCCD/MST cá nhân là 1 dòng. Nibot sẽ tự động loại bỏ CMND/CCCD/MST cá nhân nếu không đúng định dạng và khử trùng nếu có.</p>
            <textarea id="txtDSGiayToCaNhan" class="form-control" row=8></textarea>
        `
        let btnHtml = '<button class="btn btn-sm btn-primary" onclick="TraCuuDSGiayToCaNhan()">Tra cứu</button>';
        createModal("mTraCuuCN", "Tra cứu MST cá nhân", bodyHtml, btnHtml);
        showModal("mTraCuuCN")
        setTimeout(function () {
            $("#txtDSGiayToCaNhan").focus();
        }, 200);
    }
}



function initCtrlTraCuu() {
    $("#frmTraCuu").html(
        `
            <div class="row gy-2 mt-1" >
                <div class="mt-1 col-sm-8 col-12 d-flex justify-content-between justify-content-sm-start" style="margin-top: 10px !important;">
                    <button type="button"  class="w-240px btn btn-sm btn-dim btn-dark" onclick='showModalTraCuu("DN")'>
                        <em class="icon ni ni-building"></em>&nbsp;&nbsp; Tra cứu MST Doanh nghiệp
                    </button>
                    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                    <button type="button"  class="w-240px btn btn-sm btn-dim btn-dark" onclick='showModalTraCuu("CN")' >
                       <em class="icon ni ni-user"></em>&nbsp;&nbsp; Tra cứu MST Cá nhân
                    </button>
                    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                    <button type="button" id="btnExportExcel" class="w-240px btn btn-sm btn-primary" onclick="ExportDSMST()">
                        <em class="icon ni ni-download"></em>&nbsp;&nbsp;Xuất kết quả tra cứu ra Excel
                    </button>
                </div>
                <div class="col-sm-4 col-12 text-end" id="helpTTDN">
                    <a href='javascript:void(0)' onclick='openThamKhao()' class='text-danger' style='font-weight:bold'>Danh sách công văn rủi ro (tham khảo)</a>
                </div>
            </div>
            <div class="row">
                <div class="col-12  mt-1 mb-1">
                    <div class="statusImportTCDN" id="statusImportTCDN"></div>
                </div>
            </div>
            <div class="row">
                <div id="dgTraCuuThongTin" class="datagrid">
                </div>
            </div>
        `
    );

   // $("#helpTTDN").html(createHelpLink("TINH_TRANG_DOANH_NGHIEP"))

    
    dgTraCuuThongTin = $("#dgTraCuuThongTin").dxDataGrid({
        dataSource: DATA_TC,
        repaintChangesOnly: true,
        showOperationChooser: false, 
        export: {
            fileName: 'NIBOT - Tra cứu MST ',
        },
        noDataText: "Chưa có dữ liệu",
        scrolling: {
            columnRenderingMode: 'virtual',
            useNative: false,
            renderAsync: true,
            showScrollbar: "always"
        },

        keyboardNavigation: {
            enterKeyAction: 'moveFocus',
            enterKeyDirection: 'column',
            editOnKeyPress: true,
        },
        onRowPrepared(e) {
            if (e.rowType === "data") {
                if (e.data.tin) {
                    if (!e.data.statusName) {
                        $(e.rowElement).attr("style", "background:#f7e54f61;font-weight:bold;color:red");
                    }
                    else if (e.data.statusName.trim() != "NNT đang hoạt động (đã được cấp GCN ĐKT)") {
                        $(e.rowElement).attr("style", "background:#f7e54f61;font-weight:bold;color:red");
                    }
                }
                else {
                    if (e.data.TrangThai.toLowerCase().indexOf("đang hoạt động")<0) {
                        $(e.rowElement).attr("style", "background:#f7e54f61;font-weight:bold;color:red");
                    }
                }
                
            }
        },
        showBorders: true,
        paging: {
            enabled: true,
            pageSize: 100,
            pageIndex: 0    // Shows the second page
        },
        headerFilter: {
            visible: true,
        },
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
            infoText: " Tổng cộng: {2} - Trang {0}/{1}"
        },

        summary: {
            totalItems: TOTAL_COLUMNS_DN
        },

        columns: COLUMNS_DN,


    }).dxDataGrid("instance");

    ////////////////

    setTimeout(function () {
     
        $('input[type="text"]').attr('autocomplete', 'off');
        let h = calc_height("#dgTraCuuThongTin") - 10;
        dgTraCuuThongTin.option("height", h);
    }, 200);
}

var TXT_ALL = '';

function TraCuuMstTuHoaDon() {
    TXT_ALL = '';
    let dataMST = [];
    for (let j in DATA) {
        if (dataMST.indexOf(DATA[j].mst2) < 0)
            dataMST.push(DATA[j].mst2)
    }
    let txt = '';
    for (let j in dataMST) {
        txt += dataMST[j] + "\n";
    }

    TXT_ALL = txt.trim();

    $(".nav-link,.tab-pane").removeClass("active");
    $("#linkTC,#tabTC").addClass("active");

    if (isFirstClickTC) {
        initCtrlTraCuu();
        isFirstClickTC = false;
        setTimeout(function () {
            TraCuuDSMST(TXT_ALL)
        }, 200)
    }
    else {
        TraCuuDSMST(TXT_ALL)
    }
}


function loadingTC(isShow, status) {

    if (isShow) {
        $("#statusImportTCDN").html(
            `<div class = 'alert alert-success text-center'>
                <div class="spinner-border " role="status">
                  <span class="visually-hidden">đang import ...</span>
                </div>
                <div class='mt-2'>
                ${status}   
                </div>
            </div>
            `
        ).show();
    }
    else {
        $("#statusImportTCDN").hide();
    }

}
