
var dgToKhaiHQ;
var RET_OBJ_HQ, ORG_RET_OBJ_HQ;
var txtTyGiaToKhai;
var dgNgayTyGia;
var dNganHang = ["- Ngân hàng -","ABBANK", "ACB", "AGRIBANK", "VCCB", "BIDV", "CBBANK", "DONGA", "EXIMBANK", "GPBANK", "HDBANK", "HLBANK", "HSBC", "KIENLONGBANK", "LIENVIETPOSTBANK", "MBBANK", "OCB", "PGBANK", "PVCOMBANK", "SACOMBANK", "SCB", "SHB", "TECHCOMBANK", "TPBANK", "VIB", "VIETCOMBANK", "VIETINBANK"];
var dNgoaiTe = ["USD", "JPY", "EUR", "CHF", "GBP", "AUD", "SGD", "CAD", "HKD", "THB", "KRW", "SEK", "DKK", "NOK", "CNY", "RUB", "MYR", "SAR", "KWD", "INR"];
var TOTAL_COLUMNS_TOKHAIHAIQUAN = [
    {
        column: 'NGAYCT',
        summaryType: "count",
        displayFormat: '{0} dòng',
    },
    {
        column: 'TTUSD',
        summaryType: "sum",
        valueFormat: mFormat2,
        displayFormat: '{0}',
    },
    {
        column: 'TTVND',
        summaryType: "sum",
        valueFormat: mFormat2,
        displayFormat: '{0}',
    },
    {
        column: 'TTVND_TT',
        summaryType: "sum",
        valueFormat: mFormat2,
        displayFormat: '{0}',
    }
];
var cboNganHangTyGia, cboNganHangNgoaiTe, dtNgayTyGia;

function ajaxDoiTyGia() {
    var nganHang = cboNganHangTyGia.option("value");
    //console.log(nganHang, ngoaiTe, ngay)
    $("#giaTriTyGia").html(" _______ ");


    $.ajax({
        type: "GET",
        dataType: "json",
        url: `/LayTyGia/SaveNganHang/${MST}/${nganHang}`,

        success: function (data) {
          //  console.log("tessttest")
           ajaxGetTyGia()
        },
        error: function (jqXHR, textStatus, errorThrown) {
            WaitModalToKhaiHaiQuan(0);
            console.log(jqXHR);
            goTohome(jqXHR.responseText);

        }
    });
}
var DATA_TYGIA;
function ajaxGetTyGia() {

    $("#waitTyGia").show();
    var nganHang = cboNganHangTyGia.option("value");
    var lst = [];
    var lst2 = [];

    for (let i in RET_OBJ_HQ) {
        let r = RET_OBJ_HQ[i];
        if (lst.indexOf(r["SOCT"])<0) {
            lst.push(r["SOCT"]);
            lst2.push({
                'SoToKhai': r["SOCT"],
                'LoaiToKhai': r["LCTG"] == 'PNKNK' ? "V" : "R",
                'LoaiNgoaiTe': r["LOAI_NT"],
                'Ngay': r["NGAYCT"]
            });
        }
    }
    DATA_TYGIA = [];
    console.log(lst2);
    $.ajax({
        type: "POST",
        dataType: "json",
        url: `/LayTyGia`,
        data: {
            "NganHang": nganHang,
            "ThongTinToKhai": lst2
        },
        success: function (data) {
            $("#waitTyGia").hide();
            $("#dgNgayTyGia").show();
            if (data.status == 1) {
                DATA_TYGIA = data.obj;
                dgNgayTyGia.option("dataSource", DATA_TYGIA);
            }
            else {
                dAlert(data.message);
            }
        },
        error: function (jqXHR, textStatus, errorThrown) {
            WaitModalToKhaiHaiQuan(0);
            console.log(jqXHR);
            goTohome(jqXHR.responseText);

        }
    });

}

function getTyGia(p) {
    if (p == 0) {
        if (RET_OBJ_HQ.length > 0) {
            RET_OBJ_HQ = JSON.parse(ORG_RET_OBJ_HQ);
            dgToKhaiHQ.option("dataSource", RET_OBJ_HQ);
            dgToKhaiHQ.refresh();
        }
    }
    else if (p == 1) {
        if (RET_OBJ_HQ.length > 0) {
            var t = JSON.parse(ORG_RET_OBJ_HQ);
            for (let i in RET_OBJ_HQ) {
                if (RET_OBJ_HQ[i].DIENGIAI.indexOf("Nhập kho theo tờ khai số ") == 0
                ||
                    RET_OBJ_HQ[i].DIENGIAI.indexOf("Xuất khẩu theo tờ khai số ") == 0
                ) {
                    let n = RET_OBJ_HQ[i].NGAYCT.substring(0, 10)
                    let stk = RET_OBJ_HQ[i].SOCT
                    var rate = DATA_TYGIA.filter(p => p.Ngay == n && p.SoToKhai == stk)[0].TyGia;
                    if (rate>0) {
                        console.log(rate);
                        RET_OBJ_HQ[i].TYGIA = rate;
                        RET_OBJ_HQ[i].TTVND = t[i].TTUSD * rate;
                        RET_OBJ_HQ[i].TTVND_TT = t[i].TTUSD * rate;
                    }
                    
                }
            }
            dgToKhaiHQ.option("dataSource", RET_OBJ_HQ);
            dgToKhaiHQ.refresh();
        }
    }
    hideModal("mLayTyGia")
}
function initCtrlToKhaiHaiQuan() {
    let helpLink = '';// createHelpLink(1)
    $("#ctrlToKhaiHaiQuan").html(`
        <div class="row gy-2 mt-1 ">
            <div class="col-sm-8 mt-2 col-12 d-flex justify-content-start">
                <input type="file" id="uploadToKhaiHaiQuan"  multiple  style="display:none;" accept=".xls, .xlt, .xlsx" />

                <button type="button" class="btn btn-primary  btn-sm" id="btnUploadToKhaiHaiQuan"
                    data-toggle="tooltip" title=""
                ><em class="icon ni ni-upload"></em>&nbsp;Upload File Excel Tờ khai Hải quan</button>
                &nbsp;&nbsp;&nbsp; &nbsp;&nbsp;&nbsp; 
                <div id="infoToKhai" class='d-flex justify-content-left' >
                    <button type="button" id="btnLayTyGiaNganHang" class='btn btn-sm btn-dark'>Cập nhật tỷ giá từ ngân hàng</button>
                </div>
            </div>
            <div class="col-sm-4 mt-2 col-12 d-flex justify-content-end">
                <button type="button" class="btn btn-danger btn-dim btn-sm" id="btnKetXuatToKhai"><em class="icon ni ni-download"></em>&nbsp;Kết xuất</button>
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                <button type="button" class="btn btn-dark  btn-sm" id="btnHuongDanSuDungToKhai"><em class="icon ni ni-help"></em></button>
            </div>

        </div>
        <div class="row mt-2">
            <div id="dgToKhaiHQ" class="datagrid">
            </div>
        </div>
    `);
   
    $("#btnLayTyGiaNganHang").unbind().on("click", function () {
        $.ajax({
            type: "GET",
            dataType: "json",
            url: `/LayTyGia/LoadNganHang/${MST}`,

            success: function (data) {
                if (RET_OBJ_HQ && RET_OBJ_HQ.length > 0) {

                    let maNganHang = data.obj;
                    let bodyHtml = `


                            <div class='row' >
                                    <div class='col-12' style='color:#b10606;font-weight:bold'>
                                    Tỷ giá được lấy từ https://webtygia.com. Bạn nên so sánh với tỷ giá từ ngân hàng để đảm bảo tính chính xác.
                                    </div>
                                    <div class='col-4 mt-1'>
                                        <div id='cboNganHangTyGia'></div>
                                    </div>
                                    <div class='col-4 '>
                                        <div id='cboNganHangNgoaiTe'></div>
                                    </div>
                                     <div class='col-4 '>
                                    </div>
                           
                                    <div class='col-12 mt-2' >
                                        <div class = 'alert alert-primary text-center mt-1 mb-1' id='waitTyGia' >
                                            <div class="spinner-border " role="status">
                                                  <span class="visually-hidden"></span>
                                            </div><br/>
                                            Nibot đang lấy tỷ giá ngân hàng<br/>
                                            Vui lòng chờ trong giây lát!<br/>
                                        </div>
                                        <div id='dgNgayTyGia' class='datagrid' style='display:none'></div>
                                    </div>
                                    <hr/>
                                    </div>
                                    
                                    <div class='col-12 mt-2 d-flex justify-content-between'>
                                        <button class='btn  btn-dim btn-primary' onClick='getTyGia(0)'>Áp dụng tỷ giá gốc của tờ khai</button> 
                                        <button class='btn  btn-dim btn-danger' onClick='getTyGia(1)'>Áp dụng tỷ giá của lưới dữ liệu</button> 
                                    </div> 
                                    <div class='col-12 mt-2 text-danger'>
                                    * Bạn có thể điền giá trị tỷ giá vào ô tỷ giá trong lưới dữ liệu. Rồi bấm 'Áp dụng tỷ giá của lưới dữ liệu' để Nibot cập nhật theo tỷ giá mong muốn.
                                    </div> 
                                </div>
                        `

                    let btnHtml = '';

                    createModal("mLayTyGia", "Lấy tỷ giá ngân hàng", bodyHtml, btnHtml);
                    
                    cboNganHangTyGia = $("#cboNganHangTyGia").dxSelectBox({
                        dataSource: dNganHang,
                        value: maNganHang,
                        label: "Ngân hàng",
                        searchEnabled: true, // Enable searching
                        labelMode: "floating",
                        onValueChanged(e) {
                            ajaxDoiTyGia()
                        }
                    }).dxSelectBox("instance");
             

                    dgNgayTyGia = $("#dgNgayTyGia").dxDataGrid({
                        dataSource: DATA_TYGIA,
                        height: 300,
                        paging: {
                            enabled: false // Disable paging
                        },
                        editing: {
                            allowUpdating: true,
                            mode: 'cell',
                        },
                        columnAutoWidth:true,
                        columns: [
                            {
                                dataField: "SoToKhai", caption: "Số TK",
                                allowEditing: false,
                            },
                            {
                                dataField: "LoaiToKhai", caption: "Loại TK",
                                width:60,
                                allowEditing: false,
                            },
                            {
                                dataField: "LoaiTyGia", caption: "Loại T.giá",
                                allowEditing: false,
                                width: 80,
                            },
                            {
                                dataField: "Ngay", caption: "Ngày", dataType: "date", format: "dd/MM/yyyy",
                                allowEditing: false,
                                width: 80,
                            },
                            {
                                dataField: "NgoaiTe", caption: "N.Tệ",
                                allowEditing: false,
                                width: 70,
                            },
                            {
                                dataField: "TyGia", caption: "Tỷ giá", format: mFormat2,
                                allowEditing: true,

                            },
                        ],
                        allowColumnReordering: true,
                        rowAlternationEnabled: true,
                        showBorders: true,
                        showColumnLines: true,
                        showRowLines: true,
                        rowAlternationEnabled: true,
                        columnAutoWidth: true,
                  
                    }).dxDataGrid("instance")
           
                    showModal("mLayTyGia");
                    ajaxGetTyGia();
                }
                else {
                    dAlert("Chưa có dữ liệu tờ khai nên không thể mở form lấy tỷ giá!")
                    return;
                }
          
            },
            error: function (jqXHR, textStatus, errorThrown) {
                WaitModalToKhaiHaiQuan(0);
                console.log(jqXHR);
                goTohome(jqXHR.responseText);

            }
        });

    })


    $("#btnHuongDanSuDungToKhai").on("click", function () {
        let bodyHtml = `
                <div class='row' >
                    <div class='col-12'>
                         <p>
                            1. Upload file Excel Tờ khai Hải quan
                            2. Nibot sẽ tạo ra các dòng dữ liệu cho bạn.<br />
                            3. Nhấn Kết xuất để tải file Excel và Import vào Sổ chứng từ gốc trong Smart Pro
                        </p>
                        <hr/>
                        <a class='fs-18px fw-bold text-danger' href='https://www.youtube.com/watch?v=Na3XVQ8S7is' target='_blank'>HDSD Đọc tờ khai hải quan</a>
                    </div>
                </div>
        `
        let btnHtml = '';

        createModal("mHelpToKhai", "HDSD Đọc Tờ khai Hải quan", bodyHtml, btnHtml);
        showModal("mHelpToKhai");

    })
 
    $("#tabToKhaiHaiQuan").height($("#tabHD").height())

    $("#btnUploadToKhaiHaiQuan").unbind().on('click', function () {
        $("#uploadToKhaiHaiQuan").click();
    })

   // COLUMNS = [...COL_1, ...COL_3];

    dgToKhaiHQ = $("#dgToKhaiHQ").dxDataGrid({
        dataSource: [],
        columns: [
            { dataField: "LCTG", caption: "LCTG", },
            { dataField: "SR_HD", caption: "SR_HD", },
            { dataField: "SO_HD", caption: "SO_HD", },
            { dataField: "NGAY_HD", caption: "NGAY_HD", format: 'dd/MM/yyyy', dataType: "date", },
            { dataField: "SOCT", caption: "SOCT", },
            { dataField: "NGAYCT", caption: "NGAYCT", format: 'dd/MM/yyyy', dataType: "date", },
            { dataField: "DIENGIAI", caption: "DIENGIAI", width: 300, },
            { dataField: "TKNO", caption: "TKNO", },
            { dataField: "MADTPNNO", caption: "MADTPNNO", },
            { dataField: "MADMNO", caption: "MADMNO", },
            { dataField: "TKCO", caption: "TKCO", },
            { dataField: "MADTPNCO", caption: "MADTPNCO", },
            { dataField: "TENDM", caption: "TENDM", width: 200, },
            { dataField: "DONVI", caption: "DONVI", },
            { dataField: "LUONG", caption: "LUONG", format: mFormat2, width: 80, },
            { dataField: "DGUSD", caption: "DGUSD", format: mFormat2, width: 80, },
            { dataField: "TTUSD", caption: "TTUSD", format: mFormat2, width: 80, },
            { dataField: "TYGIA", caption: "TYGIA", format: mFormat2, width: 80, },
            { dataField: "LOAI_NT", caption: "LOAI_NT",  width: 80, },
            { dataField: "DGVND", caption: "DGVND", format: mFormat2, width: 80, },
            { dataField: "TTVND", caption: "TTVND", format: mFormat2, width: 150, },
            { dataField: "TS_NK", caption: "TS_NK", },
            { dataField: "TNK_USD", caption: "TNK_USD", format: mFormat2, width: 80, },
            { dataField: "TNK_VND", caption: "TNK_VND", format: mFormat2, width: 80, },
            { dataField: "HDVAT", caption: "HDVAT", },
            { dataField: "TKTHUE", caption: "TKTHUE", },
            { dataField: "TS_GTGT", caption: "TS_GTGT", },
            { dataField: "THUEVND", caption: "THUEVND", format: mFormat2, width: 80, },
            { dataField: "THUEUSD", caption: "THUEUSD", format: mFormat2, width: 80, },
            { dataField: "TTVND_TT", caption: "TTVND_TT", format: mFormat2, width: 150, },
            { dataField: "TTUSD_TT", caption: "TTUSD_TT", format: mFormat2, width: 150, },
            { dataField: "MATHANG", caption: "MATHANG", width: 200, },
            { dataField: "MAKH", caption: "MAKH", },
            { dataField: "TENKH", caption: "TENKH", },
            { dataField: "MS_DN", caption: "MS_DN", },
            { dataField: "DIACHI", caption: "DIACHI", },
            { dataField: "DIACHI_NGD", caption: "DIACHI_NGD", },
            { dataField: "KHACHHANG", caption: "KHACHHANG", },
            { dataField: "ID_NGHIEPVU", caption: "ID_NGHIEPVU", },
            { dataField: "GHICHU", caption: "GHICHU", },

            { dataField: "GUID", caption: "GUID", },

        ],
       // height: $("#dg").height() + 50,
        showOperationChooser: false,
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
        summary:  {
            totalItems:  TOTAL_COLUMNS_TOKHAIHAIQUAN
        },
        paging: {
            enabled: false
        },
        onExporting: function (e) {
            e.cancel = true;
            var i = exportToKhaiHaiQuan(e);
            if (i == 1)
                e.cancel = false;
        },

    }).dxDataGrid("instance");

    $("#btnKetXuatToKhai").unbind().on("click", function () {
        dgToKhaiHQ.option("summary.totalItems", []);
        setTimeout(function () {
            dgToKhaiHQ.exportToExcel();
        }, 300)
    });

    $("#uploadToKhaiHaiQuan").unbind().on("change", function () {
        WaitModalToKhaiHaiQuan(1);
        uploadFileToKhaiHaiQuan();


    });

    setTimeout(function () {
        $('input[type="text"]').attr('autocomplete', 'off');
        let h = calc_height("#dgToKhaiHQ") - 10;
        dgToKhaiHQ.option("height", h);
    }, 200);
}




async function uploadFileToKhaiHaiQuan() {
    var files = document.getElementById("uploadToKhaiHaiQuan").files;
    if (files.length > 0) {
        RET_OBJ_HQ = [];
        ORG_RET_OBJ_HQ = "";
        var countUpload = files.length;
        var kq = await readUploadedFiles(files);
     

        $.ajax({
            type: "POST",
            dataType: "json",
            url: '/ToKhaiHaiQuan/Upload/',
            data: {
                DataUpload: JSON.stringify(kq),
                MaSoThue: MST
            },
            success: function (data) {
                if (data.status == 1) {
                    WaitModalToKhaiHaiQuan(0);
                    dAlert(data.message);
                    if (data.obj) {
                        let result = data.obj;
                        for (let i in result) {
                            var r = result[i];
                            if (r["LTS_GTGT"] && r["LTS_GTGT"] == "KCT") {
                                r["TS_GTGT"] = "KCT";
                            }
                        }


                        RET_OBJ_HQ = result;
                        ORG_RET_OBJ_HQ = JSON.stringify(result);
                        dgToKhaiHQ.option("dataSource", result);
                        if (result.length>0) {
                    //        txtTyGiaToKhai.option("value", RET_OBJ_HQ[0].TYGIA)
                        }
                    }
                    else {
                        dgNH.option("dataSource", []);
                        txtNganHang.option("value", "");
                    }
                }
                else {
                    WaitModalToKhaiHaiQuan(2, data);
                }
            },
            error: function (jqXHR, textStatus, errorThrown) {
                WaitModalToKhaiHaiQuan(0);
                console.log(jqXHR);
                goTohome(jqXHR.responseText);

            }
        });
        setTimeout(function () { $("#uploadNganHang").val(""); }, 200)


    }
}
function WaitModalToKhaiHaiQuan(i, data) {
    if (i == 0) {
        setTimeout(function () {
            $("#mWaitToKhaiHaiQuan").modal("hide");
            $("#mWaitToKhaiHaiQuan").remove();
            $(".modal-backdrop").remove();
        }, 200);
    }
    else if (i == 1) {

        let bodyHtml = `
   
            <div class='row' >
                <div class='col-12'>
                    <div class = 'alert alert-primary text-center mt-1 mb-1'>
                        <div class="spinner-border " role="status">
                              <span class="visually-hidden"></span>
                        </div><br/>
                        Nibot đang phân tích nội dung file Excel<br/>
                        Vui lòng chờ trong giây lát!<br/>
                    </div>
                </div>
            </div>
        `
        let btnHtml = '';

        createModal("mWaitToKhaiHaiQuan", "Xử lý File Tờ Khai Hải Quan", bodyHtml, btnHtml);
        showModal("mWaitToKhaiHaiQuan")
    }
    else if (i == 2) {
        let msg = "";
        if (data.status == -99) {
            // khong dung dinh dang template
            msg = `<p >${data.message}</p>`;
        }
        if (data.status == -3) {
            // khong dung dinh dang template
            msg = `File template không đúng định dạng chuẩn của Nibot. Để chắc chắn, bạn hãy tải lại file template mới nhất.<br/><br/> <a class='text-bold fw-bold fs-18px' href='/TEMPLATES/NiBot_SaoKeNganHang.xlsx'> TẢI EXCEL TEMPLATE SAO KÊ</a>
                <br/><br/>
                <p class='text-start'>
                    <a href='https://www.youtube.com/watch?v=eUXtjtfIvaY' class='text-danger fw-bold fs-18px' target='_blank'>HDSD EXCEL TEMPLATE SAO KÊ</a>
                    <br/>
                    <a class='fs-16px fw-bold text-dark' href='https://www.youtube.com/watch?v=7cG0-kAQlTg' target='_blank'> HDSD chức năng Sao Kê Ngân Hàng</a>
                </p>
    
            `;
        }
        else if (data.status == -2) {
            // khong dung dinh dang template
            msg = `Nibot không phân tích được nội dung file. Lý do: file sao kê tải về từ ngân hàng có chứa htm.<br/><br/>
                  <p class='text-start'>
                    1. <a href='https://www.youtube.com/watch?v=0y0jFZfomqg' target='_blank' class='text-danger fw-bold fs-18px'>HƯỚNG DẪN KHẮC PHỤC LỖI FILE CÓ CHỨA HTM</a>
                    <br/>
                    2. <a class='fs-16px fw-bold text-dark' href='https://www.youtube.com/watch?v=7cG0-kAQlTg' target='_blank'> HDSD chức năng Sao Kê Ngân Hàng</a><br/>
                    3. <a class='fs-16px fw-bold text-dark' href='https://www.youtube.com/watch?v=eUXtjtfIvaY' target='_blank'> HDSD Template Sao Kê</a>

                </p>
            `;
        }
        else if (data.status == -1) {
            msg = ` ${data.message}
                   <br/>
                     <p  class='fw-bold mt-2 text-secondary'>
                    Hoặc bạn có thể tải file <a class='fs-18px' href='/TEMPLATES/NiBot_SaoKeNganHang.xlsx'> EXCEL TEMPLATE SAO KÊ</a> này về để Import Sao Kê.</span></p>
                    <br/><br/>
                    <p class='text-start'>
                    1. <a href='https://www.youtube.com/watch?v=eUXtjtfIvaY' class='text-danger fw-bold fs-18px' target='_blank'>HDSD EXCEL TEMPLATE SAO KÊ</a>
                    <br/><br/>
                    2. <a class='fs-16px fw-bold text-dark' href='https://www.youtube.com/watch?v=7cG0-kAQlTg' target='_blank'> HDSD chức năng Sao Kê Ngân Hàng</a>
                    </p>
            `
        }
        let bodyHtml = `
   
            <div class='row' >
                <div class='col-12'>
                    <div class = 'alert alert-secondary text-center mt-1 mb-1' style='line-height:25px'>
                     ${msg}
                    </div>
                </div>
            </div>
        `
        let btnHtml = '';

        createModal("mWaitToKhaiHaiQuan", "Xử lý Tờ khai hải quan", bodyHtml, btnHtml);
        showModal("mWaitToKhaiHaiQuan");


    }
}


function exportToKhaiHaiQuan(e) {

    let sheet = "NIBOT - ToKhaiHaiQuan " + MST + "_" + RET_OBJ_HQ[0].SOCT ;
    let fileName = sheet + ".xlsx";
    var workbook = new ExcelJS.Workbook();
    var worksheet = workbook.addWorksheet("KTSC");
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
                if (dtFieldName.indexOf("TTVND_TT") >= 0 || dtFieldName.indexOf("TTUSD_TT") >= 0 ||   dtFieldName.indexOf("TTVND") >= 0 || dtFieldName.indexOf("TTUSD") >= 0 || dtFieldName.indexOf("TYGIA") >= 0) {
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
        // Get the last row
        //var worksheet = workbook.getWorksheet("KTSC");
        //// Get the index of the last row
        //var lastRowIndex = worksheet.lastRow.number;
        //console.log(lastRowIndex)
        //// Remove the last row
        //worksheet.spliceRows(lastRowIndex, 1);

    }).then(function () {

        workbook.xlsx.writeBuffer().then(function (buffer) {
            saveAs(new Blob([buffer], { type: 'application/octet-stream' }), fileName);
        })

        setTimeout(function () {
            dgToKhaiHQ.option("summary.totalItems", TOTAL_COLUMNS_TOKHAIHAIQUAN);
        }, 200)

        return 1;
    });
}
