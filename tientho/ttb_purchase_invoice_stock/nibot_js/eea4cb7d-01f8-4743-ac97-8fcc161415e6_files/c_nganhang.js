var dgNH;
var txtNganHang, txtTyGia;
var RET_OBJ;
var ORG_RET_OBJ;
var TOTAL_COLUMNS_2 = [];
var mFormatX = mFormat;

function containsFloat(arr) {
    for (let i = 0; i < arr.length; i++) {
        if (typeof arr[i] === 'number') {
            if (arr[i] % 1 !== 0) {
                return true;
            }
        }
    }
    return false;
}

var COL_TOTAL_1 = [
    {
        column: 'NGAYCT',
        summaryType: "count",
        displayFormat: '{0} dòng',
    },
    {
        column: 'TTVND',
        summaryType: "sum",
        valueFormat: mFormatX,
        displayFormat: '{0}',
    },
    {
        column: 'TTVND_TT',
        summaryType: "sum",
        valueFormat: mFormatX,
        displayFormat: '{0}',
    }
]

var COL_TOTAL_2 = [
    {
        column: 'TTUSD',
        summaryType: "sum",
        valueFormat: mFormatX,
        displayFormat: '{0}',
    },
]
TOTAL_COLUMNS_2 = [...COL_TOTAL_1];

var COL_1 = [
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
]
var COL_2 = [
    {
        dataField: 'TYGIA',
        format: mFormatX,
        width: 60,
    },
    {
        dataField: 'TTUSD',
        format: mFormatX,
        width: 80,
    },
]
var COL_3 = [
    {
        dataField: 'TTVND',
        format: mFormatX,
        width: 150,
    },
    {
        caption: "TTVND_TT",
        dataField: 'TTVND_TT',

        format: mFormatX,
        width: 150,

    },
    {
        dataField: 'TENKH',
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
]

document.getElementById('frmNganHang').addEventListener('submit', function (event) {
    event.preventDefault(); // Prevent the default form submission
    // Add your custom submission handling logic here
  //  alert('Form submission prevented!');
});



function initCtrlNganHang() {
    let helpLink = '';// createHelpLink(1)
    $("#ctrlNganHang").html(`
        <div class="row gy-2 mt-1 ">
            <div class="col-sm-8 mt-2 col-12 d-flex justify-content-start">
                <input type="file" id="uploadNganHang" multiple style="display:none;" accept=".xls, .xlt, .xlsx" />
                <button type="button" class="btn btn-primary  btn-sm" id="btnUploadFileSaoKe"><em class="icon ni ni-upload"></em>&nbsp;Upload Excel Sao Kê</button>
                &nbsp;&nbsp;
                <button type="button" class="btn btn-sm" style="background: #9d0b3e !important;color:#FFF;border-color:#837783 !important;font-weight: 600 !important;box-shadow: 0 2px 4px rgba(0,0,0,0.2) !important;" id="btnUploadFileSaoKePDF">
                   <em class="icon ni ni-hot"></em>&nbsp;doSake - đọc sao kê PDF
                </button>
                &nbsp;&nbsp;
                <div id="infoNganHang" class='d-none justify-content-left' style="margin-top:2px;">
                    <div id="txtNganHang"></div>&nbsp;&nbsp;
                    <a href='javascript:void(0)' id="btnCapNhat" style='margin-top: 10px;font-size: 10pt;'> <em class="icon ni ni-pen2 " ></em> cập nhật tài khoản</a>
                    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                    <div id="txtTyGia"></div>
                </div>
                
            </div>
            <div class="col-sm-4 mt-2 col-12 d-flex justify-content-end">
                <button type="button" class="btn btn-danger btn-dim btn-sm" id="btnDownloadSaoKe"><em class="icon ni ni-download"></em>&nbsp;Kết xuất</button>
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                <button type="button" class="btn btn-dark  btn-sm" id="btnHuongDanSuDung"><em class="icon ni ni-help"></em></button>
            </div>
          
        </div>
        <div class="row gy-2 mt-1 ">
            <div class='col-12'>
                <a onclick='javascript:void(0)' id='btnKhacPhucACB' style='cursor: pointer;text-decoration: underline;'>Cách khắc phục lỗi sao kê ACB bị trống, hoặc bị ngược ngày tháng</a>
            </div>
        </div>
        <div class="row mt-2">
            <div id="dgNganHang" class="datagrid">
            </div>
        </div>
    `);

    $("#btnKhacPhucACB").unbind().on("click", function () { 
        let bodyHtml = `
                <div class='row' >
                    <div class='col-12'>
                         <p>Để khắc phục lỗi đảo ngược ngày tháng trong file sao kê ACB (do lỗi HTML ẩn bên trong khi tải file về từ ngân hàng)</p>
                         <p>
                            1. Mở file sao kê gốc ACB lên và copy toàn bộ nội dung trong sheet đó qua 1 file Excel mới.<br/>
                            2. Sau đó thực hiện upload file sao kê mới lên Nibot là được
                        </p>
                        <hr/>
                        <a href='https://www.youtube.com/watch?v=0y0jFZfomqg' target='_blank' class='text-danger fw-bold fs-18px'>VIDEO: HƯỚNG DẪN KHẮC PHỤC LỖI FILE CÓ CHỨA HTM</a>
                    </div>
                </div>
        `
        let btnHtml = '';

        createModal("mHelpACB", "Hướng dẫn sửa lỗi ACB", bodyHtml, btnHtml);
        showModal("mHelpACB");
    })
    $("#btnHuongDanSuDung").on("click", function () {
        let bodyHtml = `
                <div class='row' >
                    <div class='col-12'>
                         <p>
                            1. Upload file Excel Sao kê giao dịch của các ngân hàng (ACB, VCB, SCB, VCB, và nhiều ngân hàng khác...). 
                            <br/>Hoặc Upload dữ liệu sao kê theo template <a class='text-dark fs-18px' href='/TEMPLATES/NiBot_SaoKeNganHang.xlsx' target='_blank'>Excel NIBOT SAO KÊ</a> <br />
                            2. Nibot sẽ tạo ra các dòng giao dịch tương ứng vào lưới dữ liệu bên dưới.<br />
                            3. Cập nhật Mã TK tương ứng với Mã TK trong Smart Pro<br />
                            4. Nhấn Kết xuất để tải file Excel và Import vào Sổ chứng từ gốc trong Smart Pro
                        </p>
                        <hr/>
                        <a class='fs-18px fw-bold text-danger' href='https://www.youtube.com/watch?v=7cG0-kAQlTg' target='_blank'>HDSD chức năng Sao Kê Ngân Hàng</a><br/>
                        <a class='fs-18px fw-bold text-danger' href='https://www.youtube.com/watch?v=eUXtjtfIvaY' target='_blank'>HDSD Nibot Sao Kê Template</a>


                    </div>
                </div>
        `
        let btnHtml = '';

        createModal("mHelpNganHang", "Hướng dẫn sử dụng chức năng sao kê", bodyHtml, btnHtml);
        showModal("mHelpNganHang");

    })
    $("#btnCapNhat").hover(
        function () {
            $(this).css("color", "#be07a2");
        },
        function () {
            $(this).css("color", "red");
        }
    );

    txtNganHang = $("#txtNganHang").dxTextBox({
        value: "",
        label: "TK ngân hàng",
        placeholder: "",
        readOnly: true,
    }).dxTextBox("instance");


    txtTyGia = $("#txtTyGia").dxNumberBox({
        placeholder: "vd: 25,000, enter",
        label: "Tỷ giá",
        value: 1,
        min: 1,
        format: "#,##0.##",
        onValueChanged: function (e) {
            let rate = txtTyGia.option("value");
            if (rate > 1) {
                dgNH.option("columns", [...COL_1, ...COL_2, ...COL_3]);
                dgNH.option("summary.totalItems", [...COL_TOTAL_1, ...COL_TOTAL_2]);
                for (let i in RET_OBJ.LstData) {
                    RET_OBJ.LstData[i].TYGIA = rate;
                    RET_OBJ.LstData[i].TTUSD = ORG_RET_OBJ.LstData[i].TTVND;
                    RET_OBJ.LstData[i].TTVND = ORG_RET_OBJ.LstData[i].TTVND * rate;
                    RET_OBJ.LstData[i].TTVND_TT = ORG_RET_OBJ.LstData[i].TTVND * rate;
                }
                dgNH.option("dataSource", RET_OBJ.LstData);
                dgNH.refresh();
            }
            else {
                for (let i in RET_OBJ.LstData) {
                    RET_OBJ.LstData[i].TYGIA = 1;
                    RET_OBJ.LstData[i].TTVND = ORG_RET_OBJ.LstData[i].TTVND;
                    RET_OBJ.LstData[i].TTVND_TT = ORG_RET_OBJ.LstData[i].TTVND;
                }

                dgNH.option("columns", [...COL_1, ...COL_3]);
                dgNH.option("summary.totalItems", COL_TOTAL_1);
                dgNH.option("dataSource", RET_OBJ.LstData);
                dgNH.refresh();

            }
        }


    }).dxNumberBox("instance");

    $("#btnCapNhat").on("click", function () {
        let bodyHtml = `
            <form id="frmNganHangTaiKhoan" autocomplete = "off">
                <div class='row' >
                    <div class='col-12'>
                        <div class="form-group">
                            <label class="form-label" for="fTenNganHang">Tên ngân hàng</label>
                            <div class="form-control-wrap">
                                <input type="text" autocomplete="off" class="form-control"  readOnly id="fTenNganHang" value="">
                            </div>
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="fMaTaiKhoan">Mã tài khoản</label>
                            <div class="form-control-wrap">
                                <input type="text" class="form-control" id="fMaTaiKhoan" value="">
                            </div>
                        </div>
                    </div>
                    <div class='col-12 mt-2 mb-2 text-danger' id="errQuyDoi">
                    </div>
                    <div class='col-12 text-center mt-3'>
                        <button type='button' class='btn btn-primary' onclick='CapNhatTaiKhoanNganHang()'>CẬP NHẬT</button>
                    </div>
                </div>
            </form>
        `
        let btnHtml = '';

        createModal("mFrmNganHang", "Cập nhật Mã TK ngân hàng", bodyHtml, btnHtml);
        setTimeout(function () {
            $("#fMaTaiKhoan").val(RET_OBJ.MaTK);
            $("#fTenNganHang").val(RET_OBJ.TenNganHang);

            showModal("mFrmNganHang");
        }, 200)


    });

    $("#tabNH").height($("#tabHD").height())

    $("#btnUploadFileSaoKe").unbind().on('click', function () {
        $("#uploadNganHang").click();
    });

    $("#btnUploadFileSaoKePDF").unbind().on('click', function () {
        window.open(`/Dosake/${MST}/${GuidGoi}`,"_blank");
    });


    COLUMNS = [...COL_1, ...COL_3];

    dgNH = $("#dgNganHang").dxDataGrid({
        dataSource: [],
        columns: COLUMNS,
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
        summary: {
            totalItems: TOTAL_COLUMNS_2
        },
        paging: {
            enabled: false
        },
        onExporting: function (e) {
            e.cancel = true;
            var i = exportNganHang(e);
            if (i == 1)
                e.cancel = false;
        },

    }).dxDataGrid("instance");

    $("#btnDownloadSaoKe").unbind().on("click", function () {
        dgNH.option("summary.totalItems", []);
        setTimeout(function () {
            dgNH.exportToExcel();
        }, 300)
    });

    $("#uploadNganHang").unbind().on("change", function () {
        WaitModalSaoKe(1);
        $("#infoNganHang").removeClass("d-flex").addClass("d-none");
        uploadFile();

    });
 
    setTimeout(function () {
        $('input[type="text"]').attr('autocomplete', 'off');
        let h = calc_height("#dgNganHang") - 10;
        dgNH.option("height", h);
    }, 200);
}

async function uploadFile() {
    var files = document.getElementById("uploadNganHang").files;
    if (files.length > 0) {
        var countUpload = files.length;
        var kq = await readUploadedFiles(files);
        $.ajax({
            type: "POST",
            dataType: "json",
            url: '/ExcelNganHang/Upload/',
            data: {
                DataUpload: JSON.stringify(kq),
                MaSoThue: MST
            },
            success: function (data) {
                if (data.status == 99) {
                    WaitModalSaoKe(0);
                    if (data.obj) {
                        let resultS = data.obj;
                        RET_OBJ = { "LstData": [] };
                        var errMsg = "";
                        var multiNganHang = [];
                        var dataNganHang = [];
                        let cCountOk = 0;
                        let cCountErr = 0;

                        for (let i in resultS) {
                            let result = resultS[i];
                            if (result.status == 1) {
                                let rObj = result.obj;
                                if (multiNganHang.indexOf(rObj.TenNganHang) < 0) {
                                    multiNganHang.push(rObj.TenNganhang);
                                    dataNganHang.push({ "MaTK": rObj.MaTK, "TenNganHang": rObj.TenNganHang });
                                }

                                if (rObj.hasOwnProperty("LstData") && rObj.LstData.length > 0) {
                                    RET_OBJ.LstData.push(...rObj["LstData"]);
                                }
                                cCountOk++;

                            }
                            else {
                                cCountErr++;
                                errMsg += "<b>Lỗi " + cCountErr + "></b> " + result.message + "<br/>";
                            }
                        }

                        if (RET_OBJ.LstData.length > 0) {
                            for (let i in RET_OBJ.LstData) {
                                RET_OBJ.LstData[i].TTVND_TT = RET_OBJ.LstData[i].TTVND;
                            }
                        }

                        ORG_RET_OBJ = JSON.parse(JSON.stringify(RET_OBJ));
                        if (RET_OBJ.LstData.length > 0) {
                            $("#infoNganHang").addClass("d-flex").removeClass("d-none");
                            var isFloat = containsFloat(RET_OBJ.LstData.map(item => item.TTVND));
                            var financialColumns = ['TTVND', 'TTVND_TT', 'TTUSD', 'TTUSD_TT', 'TYGIA'];
                            var formatToApply = isFloat ? mFormat2 : mFormat;
                            var columns = dgNH.option("columns");
                            for (var i = 0; i < columns.length; i++) {
                                if (financialColumns.includes(columns[i].dataField)) {
                                    columns[i].format = formatToApply;
                                }
                            }
                            dgNH.option("columns", columns);
                            
                            // Cập nhật định dạng cho total columns
                            var totalColumns = dgNH.option("summary.totalItems");
                            for (var i = 0; i < totalColumns.length; i++) {
                                if (financialColumns.includes(totalColumns[i].column)) {
                                    totalColumns[i].valueFormat = formatToApply;
                                }
                            }
                            dgNH.option("summary.totalItems", totalColumns);
                            

                            dgNH.option("dataSource", RET_OBJ.LstData);
                            
                            if (multiNganHang.length == 1) {

                                RET_OBJ.TenNganHang = dataNganHang[0].TenNganHang;
                                RET_OBJ.MaTK = dataNganHang[0].MaTK;

                                txtNganHang.option("value", dataNganHang[0].TenNganHang + " - " + dataNganHang[0].MaTK);
                                if (dataNganHang[0].TenNganHang == "NIBOT") {
                                    $("#btnCapNhat").hide();
                                }
                                else {
                                    $("#btnCapNhat").show();
                                }
                            }
                            else {
                                txtNganHang.option("value", "");
                                $("#btnCapNhat").hide();
                            }
                        }

                        if (errMsg != "") {
                            setTimeout(function () {
                                errMsg =
                                    "<p class='text-start'>" +
                                    "Có " + cCountErr + " lỗi trong tổng số " + countUpload + " được upload. Cụ thể:  <div class='alert alert-danger text-start'>" + errMsg +
                                    "</div></p>";
                                console.log(errMsg);
                                var r = { "status": -99, "message": errMsg }
                                WaitModalSaoKe(2, r)
                            }, 200);

                        }
                    }
                    else {
                        dgNH.option("dataSource", []);
                        txtNganHang.option("value", "");
                    }
                }
                else if (data.status == 1) {
                    WaitModalSaoKe(0);
                    if (data.obj) {
                        let result = data.obj;
                        RET_OBJ = result;
                        if (RET_OBJ.LstData.length > 0) {
                            for (let i in RET_OBJ.LstData) {
                                RET_OBJ.LstData[i].TTVND_TT = RET_OBJ.LstData[i].TTVND;
                            }
                        }

                        ORG_RET_OBJ = JSON.parse(JSON.stringify(result));
                        if (result.hasOwnProperty("LstData") && result.LstData.length > 0) {

                            $("#infoNganHang").addClass("d-flex").removeClass("d-none");
                            var isFloat = containsFloat(RET_OBJ.LstData.map(item => item.TTVND));
                            // Điều chỉnh valueFormat cho các cột tài chính dựa vào isFloat
                            // Danh sách các cột cần định dạng đặc biệt
                            var financialColumns = ['TTVND', 'TTVND_TT', 'TTUSD', 'TTUSD_TT', 'TYGIA'];
                            var formatToApply = isFloat ? mFormat2 : mFormat;
                            
                            // Cập nhật định dạng trực tiếp vào dgNH
                            var columns = dgNH.option("columns");
                            for (var i = 0; i < columns.length; i++) {
                                if (financialColumns.includes(columns[i].dataField)) {
                                    columns[i].format = formatToApply;
                                }
                            }
                            dgNH.option("columns", columns);

                            var totalColumns = dgNH.option("summary.totalItems");
                            for (var i = 0; i < totalColumns.length; i++) {
                                if (financialColumns.includes(totalColumns[i].column)) {
                                    totalColumns[i].valueFormat = formatToApply;
                                }
                            }
                            dgNH.option("summary.totalItems", totalColumns);

                            dgNH.option("dataSource", result.LstData);
                            txtNganHang.option("value", RET_OBJ.TenNganHang + " - " + RET_OBJ.MaTK);
                            if (RET_OBJ.TenNganHang == "NIBOT") {
                                $("#btnCapNhat").hide();
                            }
                            else {
                                $("#btnCapNhat").show();
                            }

                        }
                    }
                    else {
                        dgNH.option("dataSource", []);
                        txtNganHang.option("value", "");
                    }
                }
                else {
                    WaitModalSaoKe(2, data);
                }
            },
            error: function (jqXHR, textStatus, errorThrown) {
                WaitModalSaoKe(0);
                console.log(jqXHR);
                goTohome(jqXHR.responseText);

            }
        });
        setTimeout(function () { $("#uploadNganHang").val(""); }, 200)


    }
}

function WaitModalSaoKe(i, data) {
    if (i == 0) {

        setTimeout(function () {
            $("#mWaitSaoKe").modal("hide");
            $("#mWaitSaoKe").remove();
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
                        Nibot đang phân tích nội dung file SAO KÊ<br/>
                        Vui lòng chờ trong giây lát!<br/>
                    </div>
                </div>
            </div>
        `
        let btnHtml = '';

        createModal("mWaitSaoKe", "Xử lý File Sao Kê Ngân Hàng", bodyHtml, btnHtml);
        showModal("mWaitSaoKe")
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
            msg = `Nibot không phân tích được nội dung file. Lý do: file sao kê tải về từ ngân hàng có chứa html.<br/><br/>
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

        createModal("mWaitSaoKe", "Xử lý File Sao Kê Ngân Hàng", bodyHtml, btnHtml);
        showModal("mWaitSaoKe");


    }
}
function exportNganHang(e) {

    let sheet = "NIBOT - Sao kê ngân hàng " + MST + " - " + txtNganHang.option("value");
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
            dgNH.option("summary.totalItems", TOTAL_COLUMNS_2);
        }, 200)

        return 1;
    });
}

function CapNhatTaiKhoanNganHang() {
    let tenNH = $("#fTenNganHang").val().trim();
    let maTK = $("#fMaTaiKhoan").val().trim();

    if (maTK && tenNH) {
        $.ajax({
            type: "POST",
            dataType: "json",
            url: '/ExcelNganHang/UpdateTaiKhoanNganHang/',
            data: {
                MaNganHang: tenNH,
                MaTaiKhoan: maTK,
                MaSothue: MST,
            },
            success: function (data) {
                if (RET_OBJ.MaTK != maTK) {
                    hideModal("mFrmNganHang");
                    dAlert("Cập nhật xong");

                    for (let i in RET_OBJ.LstData) {
                        if (RET_OBJ.LstData[i].TKNO == RET_OBJ.MaTK) {
                            RET_OBJ.LstData[i].TKNO = maTK;
                        }
                        if (RET_OBJ.LstData[i].TKCO == RET_OBJ.MaTK) {
                            RET_OBJ.LstData[i].TKCO = maTK;
                        }
                    }

                    RET_OBJ.MaTK = maTK;
                    dgNH.option("dataSource", RET_OBJ.LstData);
                    dgNH.refresh();
                    txtNganHang.option("value", RET_OBJ.TenNganHang + " - " + RET_OBJ.MaTK);
                }
                else {
                    hideModal("mFrmNganHang");
                }
            },
            error: function (jqXHR, textStatus, errorThrown) {
                console.log(jqXHR);
                goTohome(jqXHR.responseText);

            }
        });
    }
    else {
        dAlert("Không được để trống thông tin");
    }

}