var check = "";
var DATA_LUONG = [];
var TOTAL_COLUMNS_LUONG = [
    {
        column: 'NGAYCT',
        summaryType: "count",
        displayFormat: '{0} dòng',
    },
    {
        column: 'TTVND',
        summaryType: "sum",
        valueFormat: mFormat,
        displayFormat: '{0}',
    },
    {
        column: 'TTVND_TT',
        summaryType: "sum",
        valueFormat: mFormat,
        displayFormat: '{0}',
    }

]

var ds = [
    {
        "Key": "TaiKhoanKeToan",
        "ExcelColumn": "",
        "TK_NO": "",
        "TK_CO": "334",
    },
    {
        "Key": "TongLuong",
        "ExcelColumn": "",
        "TK_NO": "",
        "TK_CO": "334",
    },
    {
        "Key": "DN_KPCD",
        "ExcelColumn": "",
        "TK_NO": "",
        "TK_CO": "3382",
    },
    {
        "Key": "DN_BHXH",
        "ExcelColumn": "",
        "TK_NO": "",
        "TK_CO": "3383",
    },
    {
        "Key": "DN_BHYT",
        "ExcelColumn": "",
        "TK_NO": "",
        "TK_CO": "3384",
    },
    {
        "Key": "DN_BHTN",
        "ExcelColumn": "",
        "TK_NO": "",
        "TK_CO": "3385",
    },

    {
        "Key": "NLD_DP",
        "ExcelColumn": "",
        "TK_NO": "334",
        "TK_CO": "",
    },
    {
        "Key": "NLD_BHXH",
        "ExcelColumn": "",
        "TK_NO": "334",
        "TK_CO": "3383",
    },
    {
        "Key": "NLD_BHYT",
        "ExcelColumn": "",
        "TK_NO": "334",
        "TK_CO": "3384",
    },
    {
        "Key": "NLD_BHTN",
        "ExcelColumn": "",
        "TK_NO": "334",
        "TK_CO": "3385",
    },
    {
        "Key": "NLD_ThueTNCN",
        "ExcelColumn": "",
        "TK_NO": "334",
        "TK_CO": "3335",
    },
    {
        "Key": "TamUng",
        "ExcelColumn": "",
        "TK_NO": "334",
        "TK_CO": "1111",
    },
    {
        "Key": "ThucLinh",
        "ExcelColumn": "",
        "TK_NO": "334",
        "TK_CO": "1111",
    },
];

var currentCFG = [];
var currentCFG_ChiTiet = [{ "Key": "nhập tên phòng ban/bộ phận", "TkNo": "" }]; 

var dgCFGLuong, dgPhongBanBoPhan;

function openModalChiTiet() {
    showModal("mCauHinhChiTietTKNO");
}
var dsDanhSachCauHinh;

var dgDanhSachCauHinh;
function initCtrlLuong() {
    $.ajax({
        type: "POST",
        dataType: "json",
        url: '/Luong/LoadCauHinhLuong',
        data: {
            MaSoThue: MST,
        },
        success: function (data) {
            if (data.status == 1) {
                dsDanhSachCauHinh = JSON.parse(data.obj);
                initCtrlLuong2();
                
            }
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(textStatus);
            console.log(errorThrown);
            console.log(jqXHR);
            goTohome(jqXHR.responseText);

        }
    });

}


async function uploadFileLuong() {
    var files = document.getElementById("uploadBangLuong").files;
    if (files.length > 0) {
        var countUpload = files.length;
        var kq = await readUploadedFiles(files);
        $.ajax({
            type: "POST",
            dataType: "json",
            url: '/Luong/UploadBangLuong/',
            data: {
                DataUpload: JSON.stringify(kq),
                MaSoThue: MST
            },
            success: function (data) {
                if (data.status == 99) {
                    var kq = data.obj;
                    if (kq.lstLuong.length > 0) {
                        DATA_LUONG = kq.lstLuong;
                        dgDataLuong.option("dataSource", DATA_LUONG);
                        if (DATA_LUONG.length > 0) {
                            var k1 = DATA_LUONG.filter(p => p.TKCO.indexOf("334") >= 0);
                            var k2 = DATA_LUONG.filter(p => p.TKNO.indexOf("334") >= 0);
                            let sumCo = 0;
                            let sumNo = 0;
                            for (let j in k1) {
                                sumCo += k1[j].TTVND;
                            }
                            for (let j in k2) {
                                sumNo += k2[j].TTVND;
                            }
                            let tk = k1[0].TKCO;
                            let op = '';
                            if (sumNo == sumCo) {
                                op = "<span class='text-primary'> = </span>"
                            }
                            else if (sumNo > sumCo) {
                                op = "<span class='text-danger'> > </span>"
                            }
                            else if (sumNo < sumCo) {
                                op = "<span class='text-danger'> < </span>"
                            }

                            msg = `<span class='badge bg-dark'>Tài khoản ${tk}</span>&nbsp;&nbsp;&nbsp;&nbsp; <b>${fmt(sumNo)}</b><small>(nợ)</small>  ${op}  <b>${fmt(sumCo)}</b><small>(có)</small>`
                            $("#lblKiemTraTaiKhoan").html(msg);
                        }
                    }
                    if (kq.errMessage != "") {
                        let msg = "";
                        let msgTuyNhien = '';
                        if (DATA_LUONG.length > 0) {
                            msg = "<div class='alert alert-primary'><b>NIBOT đã phân tích file thành công và tạo được " + DATA_LUONG.length + " cho bạn.</b></div> ";
                            msgTuyNhien = "Tuy nhiên, trong những dữ liệu bạn upload lên cũng tồn tại 1 số lỗi như sau:<br/>";
                        }

                        msg += `<div class='alert alert-danger'>${msgTuyNhien} ${kq.errMessage}</div>`;
                        if (msg.indexOf("Tên sheet đặt theo nguyên tắc") >= 0) {
                            msg += "<div class='alert alert-info'> * Chú ý: về cảnh báo lỗi 'tên sheet không đúng quy định', nếu Sheet đó không có dữ liệu về Lương thì bạn có thể bỏ qua lỗi này, không cần quan tâm!</div>"

                        }

                        let bodyHtml = `
                                <div class='row' >
                                    <div class='col-12'>
                                          ${msg}
                                    </div>
                                </div>
                        `
                        let btnHtml = '';

                        createModal("mKetQuaXuLyLuong", "Kết quả xử lý", bodyHtml, btnHtml);
                        showModal("mKetQuaXuLyLuong");

                    }
                }
            },
            error: function (jqXHR, textStatus, errorThrown) {
                WaitModalSaoKe(0);
                console.log(jqXHR);
                goTohome(jqXHR.responseText);

            }
        });
        setTimeout(function () {

            $("#uploadNganHang").val("");


        }, 200)


    }
}


function initCtrlLuong2() {


    //<div class='col-4 fw-bold " style=' margin-bottom:5px' >
    //    < div style = 'float:right' >
    //        ${ createHelpLink('LUONG_DOANH_NGHIEP') }
    //            </div >
    //        </div >

    $("#ctrlLuong").html(`
        <form id="frmLuong" autocomplete="off">
        <div class='row mb-2'>
            <div class='col-8 fw-bold " style='margin-bottom:5px'>
                <a href='javascript:void(0)'  class='text-primary' id="btnCauHinhLuong"'>1. Cấu hình bảng Lương</a>&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;<a  href='javascript:void(0)' class='text-muted' ' href='javascript:void(0)' id="btnXuLyBangLuong">2. Xử lý bảng Lương</a>
            </div>
            <div class='col-4 fw-bold  d-flex justify-content-end text-end" style='margin-bottom:5px'>
                <button type="button" class="btn btn-dark  btn-sm" id="btnHuongDanSuDungLuong"><em class="icon ni ni-help"></em></button>
                
            </div>
        </div>
            <div id='divCauHinhLuong' class='row' style='display:none' >
                <div class='col-12'>
                    <div class='d-flex justify-content-start' style='display:none'>
                        <button type="button" class='btn btn-sm btn-primary' id='btnTaoMoiCauHinh' style='margin-right:15px;display:none'>Tạo mới 1 cấu hình Lương </button>
                        <button type="button" class='btn btn-sm btn-secondary' id='btnCancel' style='display:none;margin-right:15px'>Hủy</button>
                        <button type="button" class='btn btn-sm btn-danger' id='btnSave' style='display:none;margin-right:15px'>Lưu</button>&nbsp;&nbsp;&nbsp;
                    </div>
                    <div id='dgCauHinh' class='datagrid mt-2'></div>
                </div>
            </div>

             <div id='divXuLyBangLuong' class='row' style='display:none'>
                    <input type="file" id="uploadBangLuong" multiple style="display:none;" accept=".xls,.xlsx" />

                <div class='col-8 col-12 d-flex justify-content-between'>
                    <div class='d-flex justify-content-start'>
                        <button type="button" class='btn btn-sm btn-primary' id='btnUploadBangLuong' style='margin-right:15px' 
                    data-toggle="tooltip" title="Nibot hỗ trợ upload nhiều file Excel cùng lúc hoặc 1 file excel có nhiều sheet"><em class="icon ni ni-upload"></em>&nbsp;Upload file Excel bảng lương </button>
                        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<div id='lblKiemTraTaiKhoan' style='margin-top:5px;font-size:14pt'></div>
                    </div>
                    <div class='d-flex justify-content-end'>
                        <button type="button"  class="btn btn-danger btn-dim btn-sm" id="btnDownloadBangLuong"><em class="icon ni ni-download"></em>&nbsp;Kết xuất</button>
                    </div>
                    
                </div>
                <div class='col-12'>
                    <div id='dgDataLuong' class='datagrid mt-2'></div>
                </div>
            </div>
    </form>
    `);

    $("#btnHuongDanSuDungLuong").on("click", function () {
        let bodyHtml = `
                <div class='row' >
                    <div class='col-12'>
                         <p style='line-height:2.0rem'>
                            1. Cấu hình các cột tương ứng trên bảng lương ở mục Cấu hình bảng Lương<br/>
                            2. Upload file Excel Lương theo mẫu đã khai báo cấu hình ở mục Xử lý bảng Lương. Bạn có thể upload 1 lần nhiều file (tương ứng với từng tháng lương) hoặc 1 file có nhiều sheet (mỗi sheet tương ứng với 1 tháng lương).<br/>
                            3. Nibot phân tích bảng lương và trả về kết quả.<br/>
                            <div class='alert alert-info'>
                                - HDSD chức năng Lương DN:  <a class='fs-16px fw-bold text-danger' href='https://youtu.be/KRf1bfne4oI' target='_blank'>https://youtu.be/KRf1bfne4oI</a><br/>
                                <small class='text-danger'>Chú ý: từ phút 4:00 của viddeo nên xem kỹ</small><br/>
                                - Một số vấn đề cần lưu ý khi cấu hình bảng Lương:  <a class='fs-16px fw-bold text-danger' href='https://youtu.be/r9pHUv1UwvY' target='_blank'>https://youtu.be/r9pHUv1UwvY</a><br/>
                                - File Excel mẫu Lương trong video: <a class='fs-16px fw-bold text-danger' href='/TEMPLATES/FileLuongMau.xlsx' target='_blank'>FileLuongMau.xlsx</a><br/>
                                <small class='text-primary'>Bạn có thể sử dụng file lương mẫu để làm dữ liệu chuẩn cho công ty</small><br/>
                            </div>
                        <p>
                    </div>
                </div>
        `
        let btnHtml = '';

        createModal("mHelpNganHang", "Hướng dẫn sử dụng chức năng Lương DN", bodyHtml, btnHtml);
        showModal("mHelpNganHang");
        //option A
        $("#frmLuong").submit(function (e) {
            e.preventDefault();
        });
        setTimeout(function () {
            clearAutoCompleted();
        }, 200);
    });

    $("#btnDownloadBangLuong").on("click", function () {
        dgDataLuong.option("summary.totalItems", []);
        setTimeout(function () {
            dgDataLuong.exportToExcel();
        }, 300)
    });

    $("#btnUploadBangLuong").on("click", function () {
        $("#uploadBangLuong").click();
    })

  
    $("#btnCauHinhLuong").unbind().on('click', function () {
        $("#divCauHinhLuong").show();
        $("#divXuLyBangLuong").hide();
        $("#btnCauHinhLuong").addClass("text-primary").removeClass("text-muted")
        $("#btnXuLyBangLuong").removeClass("text-primary").addClass("text-muted")

    })

    $("#btnXuLyBangLuong").unbind().on('click', function () {
        $("#divCauHinhLuong").hide();
        $("#divXuLyBangLuong").show();
        $("#btnCauHinhLuong").removeClass("text-primary").addClass("text-muted")
        $("#btnXuLyBangLuong").addClass("text-primary").removeClass("text-muted")

    })
  
    $("#uploadBangLuong").unbind().on("change", function () {
        $("#lblKiemTraTaiKhoan").html('');

        uploadFileLuong();

        //var fileUpload = $("#uploadBangLuong").prop('files')[0];
        //if (fileUpload) {
        //    if (typeof (FileReader) != "undefined") {
        //        const reader = new FileReader()
        //        reader.readAsArrayBuffer(fileUpload)
        //        reader.onload = () => {
        //            const buffer = reader.result;
        //            var base64String = _arrayBufferToBase64(buffer);
        //            $.ajax({
        //                type: "POST",
        //                dataType: "json",
        //                url: '/Luong/UploadBangLuong/',
        //                data: {
        //                    Content: base64String,
        //                    FileName: fileUpload.name,
        //                    MaSoThue: MST
        //                },
        //                success: function (data) {

        //                    if (data.status == 1) {
        //                        DATA_LUONG = data.obj;
        //                        if (DATA_LUONG.length>0) {
        //                            var k1 = DATA_LUONG.filter(p => p.TKCO.indexOf("334") >= 0);
        //                            var k2 = DATA_LUONG.filter(p => p.TKNO.indexOf("334") >= 0);
        //                            let sumCo = 0;
        //                            let sumNo = 0;
        //                            for (let j in k1) {
        //                                sumCo += k1[j].TTVND;
        //                            }
        //                            for (let j in k2) {
        //                                sumNo += k2[j].TTVND;
        //                            }
        //                            let tk = k1[0].TKCO;
        //                            let op = '';
        //                            if (sumNo == sumCo) {
        //                                op = "<span class='text-primary'> = </span>"
        //                            }
        //                            else if (sumNo > sumCo) {
        //                                op = "<span class='text-danger'> > </span>"
        //                            }
        //                            else if (sumNo < sumCo) {
        //                                op = "<span class='text-danger'> < </span>"
        //                            }

        //                            msg = `<span class='badge bg-dark'>Tài khoản ${tk}</span>&nbsp;&nbsp;&nbsp;&nbsp; <b>${fmt(sumNo)}</b><small>(nợ)</small>  ${op}  <b>${fmt(sumCo)}</b><small>(có)</small>`
        //                            $("#lblKiemTraTaiKhoan").html(msg);
        //                        }


        //                        dgDataLuong.option("dataSource", DATA_LUONG);
        //                        dgDataLuong.refresh();
        //                    }
        //                    else {
        //                       dAlert(data.message)
        //                    }
        //                },
        //                error: function (jqXHR, textStatus, errorThrown) {
        //                    //WaitModalSaoKe(0);
        //                    console.log(jqXHR);
        //                }
        //            });
        //        }
        //    }
        //    setTimeout(function () { $("#uploadBangLuong").val(""); }, 200);
        //}
    });
    dgDataLuong = $("#dgDataLuong").dxDataGrid({
        dataSource: [],
        paging: {
            enabled: false
        },
        filterRow: { visible: true },
        showOperationChooser: false, 
        onExporting: function (e) {
            e.cancel = true;
            var i = exportBangLuong(e);
            if (i == 1)
                e.cancel = false;
        },
        columns: [
            {
                dataField: 'LCTG',
            },
            {
                dataField: 'NGAYCT',
                format: 'dd/MM/yyyy',
                dataType: "date",
            },
            {
                dataField: 'SOCT',
            },
            {
                dataField: 'DIENGIAI',
                width: 300,
            },
            {
                dataField: 'TKNO',
            },
            {
                dataField: 'MADTPNNO',
            },
            {
                dataField: 'TKCO',
            },
            {
                dataField: 'MADTPNCO',
            },
            {
                dataField: 'TTVND',
                format: mFormat,
                width: 150,
            },
            {
                caption: "TTVND_TT",
                dataField: 'TTVND_TT',

                format: mFormat,
                width: 150,

            },
            {
                dataField: 'ID_NGHIEPVU',
                caption: "ID_NGHIEPVU",
            },
            {
                dataField: 'GHICHU',
            },
            {
                dataField: 'GUID',
            },
        ],
        height: $("#dg").height(),
        showBorders: true,
        showColumnLines: true,
        showRowLines: true,
        columnAutoWidth: true,
        noDataText: "Không có dữ liệu",
        keyboardNavigation: {
            enterKeyAction: 'moveFocus',
            enterKeyDirection: 'column',
            editOnKeyPress: true,
        },
        summary: {
            totalItems: TOTAL_COLUMNS_LUONG
        }

    }).dxDataGrid("instance");


    dgCFGLuong = $("#dgCauHinh").dxDataGrid({
        dataSource: currentCFG,
        height: $("#dg").height(),
        sorting: false, // disable sorting
        showOperationChooser: false, 
        columns: [
            { dataField: "Key", allowEditing: false, width:200, },
            {
                height: 300,
                dataField: "ExcelColumn", caption: "Tiêu đề cột Excel",
                editorType: "dxTextArea",
                cellTemplate(container, options) {
                    let v = options.value;
                    while (v[v.length - 1] == "\n" || v[v.length - 1] == " ") {
                        v = v.substr(0, v.length - 1);
                    }
                    while (v[0] == " ") {
                        v = v.substr(1);
                    }
                    if (v.indexOf('"') == 0) {
                        v = v.substr(1);
                        v = v.substr(0, v.length - 1);
                    }
                    var r = ds.filter(p => p.Key == options.data.Key)[0];
                    r.ExcelColumn = v;

                    const text = v.replace(/\n/gi, "<br/>");

                    $("<div>" + text + "</div>").appendTo(container);
                },
            },
            {
                dataField: "TK_NO", caption: "TK Nợ", width: 400, 
            },
            {
                dataField: "TK_CO", caption: "TK Có", width: 400, 
            },
        ],
        onCellPrepared: function (e) {
            if (e.rowType === "data") {
                if (e.column.dataField === "TK_NO") {
                    if (e.data.Key == "TaiKhoanKeToan") {
                        var x = e.cellElement.find(".dx-texteditor-input");
                        x.remove();
                        $(x.prevObject[0]).html(`<a class='btn btn-sm  btn-dark' href='javascript:void(0)' onClick='openModalChiTiet()'>Cấu hình TK Nợ cho bộ phận/phòng ban</a>`);
                    }
                    else if (e.data.Key == "TongLuong" || e.data.Key == "DN_KPCD" || e.data.Key == "DN_BHXH" || e.data.Key == "DN_BHYT" || e.data.Key == "DN_BHTN") {
                        var x = e.cellElement.find(".dx-texteditor-input");
                        x.remove();
                        $(x).attr("disabled", true);
                        $(x.prevObject[0]).html("---TaiKhoanKeToan---")
                    }
                }
            }
        },
        onRowUpdating(e) {
            if (e.newData && (e.newData.TK_CO || e.newData.TK_NO)) {
                let keyCol = e.key.Key;
                let colsKey = ["NLD_BHXH", "NLD_BHYT", "NLD_BHTN", "NLD_ThueTNCN", "NLD_DP","TamUng", "ThucLinh", "TongLuong"];
                let v = "";
                let hasEdit3343341 = false;
                if (e.newData.TK_CO && (keyCol == "TaiKhoanKeToan" || keyCol == "TongLuong")) {
                    v = e.newData.TK_CO;
                    hasEdit3343341 = true
                }
                else if (e.newData.TK_NO && colsKey.indexOf(keyCol) >= 0) {
                    v = e.newData.TK_NO;
                    hasEdit3343341 = true
                }
                if (hasEdit3343341) {
                    currentCFG.filter(p => p.Key == 'TaiKhoanKeToan')[0].TK_CO = v;
                    currentCFG.filter(p => p.Key == 'TongLuong')[0].TK_CO = v;
                 //   currentCFG.filter(p => p.Key == 'NLD_DP')[0].TK_NO = v;
                    currentCFG.filter(p => p.Key == 'NLD_BHXH')[0].TK_NO = v;
                    currentCFG.filter(p => p.Key == 'NLD_BHYT')[0].TK_NO = v;
                    currentCFG.filter(p => p.Key == 'NLD_BHTN')[0].TK_NO = v;
                    currentCFG.filter(p => p.Key == 'NLD_ThueTNCN')[0].TK_NO = v;
                    currentCFG.filter(p => p.Key == 'TamUng')[0].TK_NO = v;
                    currentCFG.filter(p => p.Key == 'ThucLinh')[0].TK_NO = v;
                }

                if (e.newData.TK_CO && (keyCol.indexOf("DN_KPCD") >= 0  )) {
                    currentCFG.filter(p => p.Key == 'DN_KPCD')[0].TK_CO = e.newData.TK_CO;
               //     currentCFG.filter(p => p.Key == 'NLD_DP')[0].TK_CO = e.newData.TK_CO;
                }

                if (e.newData.TK_CO && keyCol.indexOf("BHXH") > 0) {
                    currentCFG.filter(p => p.Key == 'DN_BHXH')[0].TK_CO = e.newData.TK_CO;
                    currentCFG.filter(p => p.Key == 'NLD_BHXH')[0].TK_CO = e.newData.TK_CO;
                }
                if (e.newData.TK_CO && keyCol.indexOf("BHYT") > 0) {
                    currentCFG.filter(p => p.Key == 'DN_BHYT')[0].TK_CO = e.newData.TK_CO;
                    currentCFG.filter(p => p.Key == 'NLD_BHYT')[0].TK_CO = e.newData.TK_CO;
                }
                if (e.newData.TK_CO && keyCol.indexOf("BHTN") > 0) {
                    currentCFG.filter(p => p.Key == 'DN_BHTN')[0].TK_CO = e.newData.TK_CO;
                    currentCFG.filter(p => p.Key == 'NLD_BHTN')[0].TK_CO = e.newData.TK_CO;
                }
             

            }
        },

        showBorders: true,
        showColumnLines: true,
        showRowLines: true,
        columnAutoWidth: true,
        noDataText: "Không có dữ liệu",
        editing: {
            mode: 'cell', // 'batch' | 'cell' | 'form' | 'popup'
            allowUpdating: true,
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
    }).dxDataGrid("instance");


    $("#btnCancel").on("click", function () {
        dgCFGLuong = $("#dgCauHinh").dxDataGrid({
            dataSource: [],
            height: $("#dg").height(),
        }).dxDataGrid("instance");
        $("#btnCancel").hide();
        $("#btnSave").hide();
        $("#btnTaoMoiCauHinh").attr("disabled", false);
        $("#txtTenCfg").val("");

    })

    let bodyHtml = `
                <div class='row' >
                   <div class='col-12'>
                         <p class='text-dark'><b>Tên cấu hình lương</b></p>
                         <input type='text' class='form-control' id="txtTenCfg" placeholder='Cấu hình lương cho công ty ACBD'></input>
                        
                    </div>
                    <div class='col-12 mt-2'>
                       <button class='btn btn-danger ' id='btnLuuCauHinh'>LƯU</button>
                    </div>
                </div>
        `
    let btnHtml = '';

    createModal("mCauHinhLuong", "Tạo mới 1 cấu hình Lương", bodyHtml, btnHtml);
    
    $("#btnCancel").hide();
    $("#btnSave").hide();
    $("#btnTaoMoiCauHinh").attr("disabled", false);
    $("#txtTenCfg").val("");
    $("#btnLuuCauHinh").unbind().on("click", function () {
        let tenCauHinh = $("#txtTenCfg").val();
        if (tenCauHinh == "") {
            dAlert("Chưa nhập tên cấu hình.");
            return;
        }
        else {
            $.ajax({
                type: "POST",
                dataType: "json",
                url: '/Luong/LuuCauHinhLuong',
                data: {
                    TenCauHinh: $("#txtTenCfg").val(),
                    CauHinh: JSON.stringify( currerentCFG),
                    ChiTiet: JSON.stringify(currentCFG_ChiTiet),
                    MaSoThue: MST,
                },
                success: function (data) {
                    if (data.status == 1) {

                    }
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    hideModal(tenModal)
                    console.log(textStatus);
                    console.log(errorThrown);
                    console.log(jqXHR);
                    goTohome(jqXHR.responseText);

                }
            });

        }
    })
    let bodyHtml2 = `
                <div class='row' >
                    <div class='col-12'>
                        <div id="dgPhongBanBoPhan" class='datagrid'></div>
                    </div>
                    <div class='col-12 mt-2'>
                       <button class='btn btn-danger' id='btnDongChiTiet'>Đóng</button>
                    </div>
                </div>
        `

    createModal("mCauHinhChiTietTKNO", "Cấu hình TK Nợ cho Bộ Phận/Phòng Ban", bodyHtml2, '');
    $("#btnDongChiTiet").unbind().on("click", function () {
        hideModal("mCauHinhChiTietTKNO");
    })

    dgPhongBanBoPhan = $("#dgPhongBanBoPhan").dxDataGrid({
        dataSource: currentCFG_ChiTiet,
        showOperationChooser: false, 

        columns: [
            {
                dataField: "Key",
                caption: "Tên bộ phận/phòng ban",
            },
            {
                dataField: "TkNo",
                caption: "TK NỢ",
                width:60,
            },
        ],
        noDataText: "Không có dữ liệu",
        showBorders: true,
        showColumnLines: true,
        showRowLines: true,


        editing: {
            texts: {
                confirmDeleteMessage: "Bạn đã chắc cú chưa?",
                deleteRow: "Xóa",
                addRow: "Thêm mới",
                saveRowChanges: "Lưu",
                cancelRowChanges: "Hủy"
            },
            mode: 'cell', // 'batch' | 'cell' | 'form' | 'popup'
            allowAdding: true, // enable inserting new rows
            allowDeleting: true, // enable deleting rows
            allowUpdating: true, // enable updating rows
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
        height: 400,

    }).dxDataGrid("instance");

    $("#btnSave").on("click", function () {
        ///
        let errMsg = "";

        //if (currentCFG.filter(p => !p.ExcelColumn).length > 0){
        //    errMsg += "- Tiêu đề cột Excel phải điền đầy đủ, không được để trống<br/>";
        //}

        //if (currentCFG.filter(p => !p.TK_CO).length > 0) {
        //    errMsg += "- Tài khoản có phải điền đầy đủ, không được để trống<br/>";
        //}
        //if (currentCFG.filter(p => p.Key != "TaiKhoanKeToan" && p.Key != "TongLuong" && p.Key.indexOf("DN_")<0 &&  !p.TK_NO).length > 0) {
        //    errMsg += "- Tài khoản nợ phải điền đầy đủ, không được để trống";
        //}

        var k = currentCFG_ChiTiet.filter(p => p.Key == "nhập tên phòng ban/bộ phận" || p.Key == "" || p.Key == null).length;
        if (k > 0) errMsg += "- Tên bộ phận/phòng ban không được để trống<br/>";
        var k2 = currentCFG_ChiTiet.filter(p => !p.TkNo).length;
        if (k2 > 0) errMsg += "- TK Nợ của bộ phận/phòng ban không được để trống<br/>";
        
      
        if (errMsg!="") {
            dAlert(errMsg);
            return;
        }


        $.ajax({
            type: "POST",
            dataType: "json",
            url: '/Luong/LuuCauHinhLuong',
            data: {
                TenCauHinh: "",
                CauHinh: JSON.stringify(currentCFG),
                ChiTiet: JSON.stringify(currentCFG_ChiTiet),
                MaSoThue: MST,
            },
            success: function (data) {
                if (data.status == 1) {
                    
                    dAlert("Lưu thành công")
                    initCtrlLuong();
                }
                else {
                    dAlert(data.message);
                }
            },
            error: function (jqXHR, textStatus, errorThrown) {
             
                console.log(textStatus);
                console.log(errorThrown);
                console.log(jqXHR);
                goTohome(jqXHR.responseText);

            }
        });


        //showModal("mCauHinhLuong");
        //setTimeout(function () {
        //    $("#txtTenCfg").focus();
        //}, 100)

        
    })

    $("#btnTaoMoiCauHinh").on("click", function () {
        currentCFG = JSON.parse(JSON.stringify(ds));
        currentCFG_ChiTiet = [{ "Key": "nhập tên phòng ban/bộ phận", "TkNo": "" }]; 
        dgCFGLuong.option("dataSource", currentCFG);
        dgPhongBanBoPhan.option("dataSource", currentCFG_ChiTiet);
        $("#btnCancel").show();
        $("#btnSave").show();
        $("#btnTaoMoiCauHinh").attr("disabled",true);

       
    })

    setTimeout(function () {
        if (dsDanhSachCauHinh.length > 0) {
            let r = dsDanhSachCauHinh[dsDanhSachCauHinh.length - 1];
            let x = JSON.parse(r["CfgTongQuat"]);
            let cfgCreate = [];
            for (let i in ds) {
                var fullKey = ds[i].Key;
                var kq = x.filter(p => p.Key == fullKey);
                if (kq.length == 1) {
                    cfgCreate.push(kq[0])
                }
                else {
                    //if (fullKey == "NLD_DP") {
                    //    let dp = ds[i];
                    //    let kpcd = x.filter(p => p.Key == "DN_KPCD")[0];
                    //    let tongluong = x.filter(p => p.Key == "TongLuong")[0];
                    //    dp.TK_NO = tongluong.TK_CO;
                    //    dp.TK_CO = kpcd.TK_CO;
                    //    cfgCreate.push(dp);
                    //}
                }
            }

            currentCFG = cfgCreate;
            currentCFG_ChiTiet = JSON.parse(r["CfgChiTiet"]);

            




            dgCFGLuong.option("dataSource", currentCFG);
            dgPhongBanBoPhan.option("dataSource", currentCFG_ChiTiet);
            $("#btnTaoMoiCauHinh").hide();
            $("#btnCancel").html("Reload")
            $("#btnSave").show();
            $("#btnCancel").show();

            $("#btnCancel").unbind().on("click", function () {
                initCtrlLuong();

            })
            $("#btnCauHinhLuong").click();
            
          ///  $("#btnXuLyBangLuong").click();
        }
        else {
            $("#btnCauHinhLuong").click();
            $("#btnTaoMoiCauHinh").show();
        }

    }, 200);

    setTimeout(function () {
        $('input[type="text"]').attr('autocomplete', 'off');
    }, 200);

}


function exportBangLuong(e) {
    if (DATA_LUONG.length == 0) {
        return;
    }
    let t = DATA_LUONG[0].NGAYCT.substr(0,7);

    let sheet = "NIBOT - LƯƠNG " + MST + " - " + t;
    let fileName = sheet + ".xlsx";
    var workbook = new ExcelJS.Workbook();
    var worksheet = workbook.addWorksheet("KTSC_LUONG");
    var startRow = 1;
    var lastRow = 0;
    var selectedRow = false;
    if (datagrid.getSelectedRowsData().length > 0)
        selectedRow = true;

    DevExpress.excelExporter.exportDataGrid({
        component: e.component,
        worksheet: worksheet,
        topLeftCell: { row: startRow, column: 1 },
        selectedRowsOnly: selectedRow,
        customizeCell: function (options) {
            var gridCell = options.gridCell;
            var excelCell = options.excelCell;
            if (gridCell.rowType === 'header') {
                Object.assign(excelCell, {
                    font: { bold: true },
                    alignment: {
                        vertical: "middle",
                        horizontal: "center",
                        wrapText: true
                    },
                    fill: { type: 'pattern', pattern: 'solid', fgColor: { argb: 'ffebcc' } }
                });
            }

            Object.assign(excelCell, {
                alignment: { wrapText: true },
                border: {
                    top: { style: 'thin' },
                    left: { style: 'thin' },
                    bottom: { style: 'thin' },
                    right: { style: 'thin' }
                }
            });


            if (gridCell.rowType == 'data') {
                let dtFieldName = gridCell.column.dataField;
                if (dtFieldName.indexOf("TTVND") >= 0 || dtFieldName.indexOf("TTUSD") >= 0 || dtFieldName.indexOf("TYGIA") >= 0) {
                    excelCell.numFmt = '#,##0.00';
                    Object.assign(excelCell);

                }
                if (gridCell.column.dataField == "TKNO" || gridCell.column.dataField == "TKCO" || gridCell.column.dataField == "MADTPNNO" || gridCell.column.dataField == "MADTPNCO") {
                    excelCell.numFmt = '@';
                    Object.assign(excelCell);
                }

            }

        }
    }).then(function () {


    }).then(function () {

        workbook.xlsx.writeBuffer().then(function (buffer) {
            saveAs(new Blob([buffer], { type: 'application/octet-stream' }), fileName);
        })

        setTimeout(function () {
            dgDataLuong.option("summary.totalItems", TOTAL_COLUMNS_LUONG);
        }, 200)

        return 1;
    });
}