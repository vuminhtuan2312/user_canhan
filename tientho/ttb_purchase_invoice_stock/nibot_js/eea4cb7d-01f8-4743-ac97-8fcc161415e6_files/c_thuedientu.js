//2024-08-09 13:00

var stNamThue, txtNamThue, cboQuyThue, dtTuNgayThue, dtDenNgayThue, txtKyTinhThue;
var cboToKhaiThue, txtMaGiaoDichThue;
var dgThue;
var DATA_TOKHAI;

var tdtUsername, tdtPassword;

var spinerTDT = `  
                <div style="margin-top:5px;margin-left:10px" class="spinner-border spinner-border-sm" role="status">
                    <span class="visually-hidden">Loading...</span>
            </div> <i><small>...đang kết xuất...</small></i>`


var colorBangKe = '#cf0606';
var colorToKhai = 'blue';

function showPnl(type) {
    if (type == "aToKhai") {
        $("#aToKhai").addClass("text-primary").removeClass("text-muted");
        $("#aGNT").removeClass("text-primary").addClass("text-muted");
        $("#pnlToKhai").show();
        $("#pnlGNT").hide();

        let h = calc_height("#dgThue")-10;
        dgThue.option("height", h);

    }
    else {
        $("#aToKhai").removeClass("text-primary").addClass("text-muted");
        $("#aGNT").addClass("text-primary").removeClass("text-muted");
        $("#pnlToKhai").hide();
        $("#pnlGNT").show();
        if (isFirstGNT) {
            $("#btnTimKiemGnt").click();
            isFirstGNT = false;
        }
        let h = calc_height("#dgThue") - 10;
        dgThue.option("height", h);
    }
}

    
var stNamGnt, txtGntKeyword, txtGntLoaiNgay, txtGntCboQuy, txtGntTuNgay, txtGntDenNgay, txtGntNam;
var DATA_GNT;
var isFirstGNT = true;
function initCtrlThueDienTu() {

    $("#ctrlThueDienTu").html(`
             <div class="row gy-2 ">
                <div class="  col-12 fw-bold " style='margin-bottom:5px'>
                    <a href='javascript:void(0)' id='aToKhai' class='text-primary' onclick='showPnl("aToKhai")'>Tra cứu tờ khai</a>&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;<a  href='javascript:void(0)' id='aGNT' class='text-muted' onclick='showPnl("aGNT")' href='javascript:void(0)'>Tra cứu giấy nộp tiền</a>
                </div>
            </div>
            <div class="row gy-2" id="pnlToKhai" style='display:none'>
                <div class=" col-12 d-flex">
                    <table>
                        <tr width='100%'>
                            <td width='400px'><div id="txtMaGiaoDichThue"></div></td>

                            <td>&nbsp;&nbsp;Ngày nộp&nbsp;&nbsp;</td>
                            <td><div id='cboQuyThue'></div></td>
                            <td>&nbsp;&nbsp;&nbsp;&nbsp;</td>
                            <td><div id='dtTuNgayThue'></div></td>
                            <td>&nbsp;&nbsp;&nbsp;&nbsp;</td>
                            <td><div id='dtDenNgayThue'></div></td>
                            <td>&nbsp;&nbsp;&nbsp;&nbsp;</td>
                            <td><div id="txtNamThue"></div></td>
                            <td><span class='mt-1 text-muted d-none'   id="lblNamThue">(năm làm việc)</span></td>
                            <td>&nbsp;&nbsp;Kỳ tính thuế&nbsp;&nbsp;</td>
                            <td><div id="txtKyTinhThue"></div></td>
                        </tr>
                        <tr height=5px></tr>
                    </table>
                </div>
                <div class='col-12 d-flex justify-content-between'>
                    <div>
                        <button type="button" class="btn btn-primary btn-dim btn-sm" id="btnDongBoThue"><em class="icon ni ni-hot"></em>&nbsp;Đồng bộ</button>
                        &nbsp;&nbsp;&nbsp;
                        <button type="button" class="btn btn-danger btn-dim btn-sm btnCauHinh" ><em class="icon ni ni-setting-alt"></em>&nbsp;Cấu hình</button>
                    </div>
                    <div id='divMsg'>&nbsp;</div>
                    <button type="button" class="btn btn-dark btn-dim btn-sm" id="btnTimKiemThue"><em class="icon ni ni-search"></em>&nbsp;Tìm kiếm</button>
                    <div id='divMsg'>&nbsp;</div>
                    <button type="button" class="btn btn-danger btn-dim btn-sm" id="btnKetXuatThue"><em class="icon ni ni-download-cloud"></em>&nbsp;Kết xuất</button>

                </div>
                <div class='col-12 d-flex justify-content-between'>
                    <div id='dgThue' class='datagrid my-custom-grid'></div>
                </div>
            </div>
            <div class="row gy-2 mt-1" id="pnlGNT" style='display:none'>
                <div class=" col-12 d-flex">
                    <table>
                        <tr width='100%'>
                            <td width='450px'><div id="txtGntKeyword"></div></td>
                            <td><div id='txtGntLoaiNgay'></div></td>
                            <td><div id='txtGntCboQuy'></div></td>
                            <td>&nbsp;&nbsp;&nbsp;&nbsp;</td>
                            <td><div id='txtGntTuNgay'></div></td>
                            <td>&nbsp;&nbsp;&nbsp;&nbsp;</td>
                            <td><div id='txtGntDenNgay'></div></td>
                            <td>&nbsp;&nbsp;&nbsp;&nbsp;</td>
                            <td><div id="txtGntNam"></div></td>
                            <td><span class='mt-1 text-muted d-none' id="lblNamGnt">(năm làm việc)</span></td>
                        </tr>
                        <tr height=5px></tr>
                    </table>
                </div>
                <div class='col-12 d-flex justify-content-between'>
                     <div>
                    <button type="button" class="btn btn-primary btn-dim btn-sm" id="btnDongBoGnt"><em class="icon ni ni-hot"></em>&nbsp;Đồng bộ</button>
                        &nbsp;&nbsp;&nbsp;
                        <button type="button" class="btn btn-danger btn-dim btn-sm btnCauHinh" ><em class="icon ni ni-setting-alt"></em>&nbsp;Cấu hình</button>
                    </div>
                    <button type="button" class="btn btn-dark btn-dim btn-sm" id="btnTimKiemGnt"><em class="icon ni ni-search"></em>&nbsp;Tìm kiếm</button>
                                        <button type="button" class="btn btn-danger btn-dim btn-sm" id="btnKetXuatGnt"><em class="icon ni ni-download-cloud"></em>&nbsp;Kết xuất</button>

                </div>
                <div class='col-12 d-flex justify-content-between'>
                    <div id='dgGnt' class='datagrid'></div>
                </div>
            </div>

    `);

    initCtrlToKhai();
    initCtrlGnt();

    setTimeout(function () {
        showPnl("aToKhai");
        btnTimKiemThue.click();
        $('input[type="text"]').attr('autocomplete', 'off');

    }, 200);

}
function initCtrlGnt() {
   // txtGntKeyword, txtGntLoaiNgay, txtGntCboQuy, txtGntTuNgay, txtGntDenNgay, txtGntNam;
    txtGntKeyword = $("#txtGntKeyword").dxTextBox({
        placeholder:"Số tham chiếu, mã giao dịch, số chứng từ NH, số GNT, ngân hàng, loại tiền"
    }).dxTextBox("instance");

    txtGntLoaiNgay = $("#txtGntLoaiNgay").dxSelectBox({
        width: 100,
        dataSource: ["Ngày lập", "Ngày gửi", "Ngày nộp"],
        value: "Ngày lập",
    }).dxSelectBox("instance");

    stNamGnt = new Date().getFullYear();
    if (localStorage.getItem("stNamGnt")) {
        stNamGnt = localStorage.getItem("stNamGnt");
    }
    else {
        localStorage.setItem("stNamGnt", stNamGnt);
    }


    txtGntCboQuy = $("#txtGntCboQuy").dxSelectBox({
        placeholder: "chọn khoảng thời gian",
        items: ["Tháng 1", "Tháng 2", "Tháng 3", "Tháng 4", "Tháng 5", "Tháng 6", "Tháng 7", "Tháng 8", "Tháng 9", "Tháng 10", "Tháng 11", "Tháng 12", "Quý 1", "Quý 2", "Quý 3", "Quý 4", "Năm này", "Năm trước"],
        width: 120,
        value: "",
        onValueChanged(e) {
            let val = e.value;
            if (val == "Hôm nay" || val == "1 tuần" || val == "Tuần này" || val == "Tháng này" || val == "Năm này" || val == "Năm trước") {
                txtGntNam.option("visible", false);
                $("#lblNamGnt").addClass("d-none");
            }
            else {
                txtGntNam.option("visible", true);
                $("#lblNamGnt").removeClass("d-none");
            }
            var x = KhoangNgay(e.value, false, stNamGnt);
            txtGntTuNgay.option("value", x.start);
            txtGntDenNgay.option("value", x.end);
        },
    }).dxSelectBox("instance");


    txtGntNam = $("#txtGntNam").dxNumberBox({
        value: stNamThue,
        visible: false,
        step: 0,
        width: 60,
        onValueChanged(e) {
            localStorage.setItem("stNamGnt", e.value);
            stNamGnt = e.value;
            var x = KhoangNgay(cboQuyThue.option("value"), false, e.value);
            txtGntTuNgay.option("value", x.start);
            txtGntDenNgay.option("value", x.end);
        }
    }).dxNumberBox("instance");


    txtGntTuNgay = $("#txtGntTuNgay").dxDateBox({
        displayFormat: "dd/MM/yyyy",
        useMaskBehavior: true,
        width: 120,
    }).dxDateBox("instance");
    txtGntDenNgay = $("#txtGntDenNgay").dxDateBox({
        displayFormat: "dd/MM/yyyy",
        useMaskBehavior: true,
        width: 120,
    }).dxDateBox("instance");

    txtGntNam = $("#txtGntNam").dxNumberBox({
        value: stNamGnt,
        visible: false,
        step: 0,
        width: 60,
        onValueChanged(e) {
            localStorage.setItem("stNamGnt", e.value);
            stNam = e.value;
            var x = KhoangNgay(txtGntCboQuy.option("value"), false, e.value);
            txtGntTuNgay.option("value", x.start);
            txtGntDenNgay.option("value", x.end);
        }
    }).dxNumberBox("instance");

    $("#txtGntNam .dx-texteditor-input").attr("style", "text-align:center");
    setTimeout(function () {
        txtGntCboQuy.option("value", "Năm này");
    }, 200)

    COLUMNS_GNT = [
        {
            dataField: 'MaGiaoDich',
            caption: "Mã GD",
          
        },
        {
            dataField: 'SoGiayNopTien',
            headerCellTemplate: "Số GNT",
            cellTemplate(c, e) {
                if (e.rowType == 'data' ) {
                    let html = ``
                    if (e.data.DaTaiChiTiet) {
                        html += `<a  href='javascript:void(0)' onclick='xemGnt("${e.data.SoGiayNopTien}")' style='color:${colorToKhai};font-weight:bold'>${e.data.SoGiayNopTien}</a>`
                    }
                    if (e.data.DaTaiXml) {
                        html += `&nbsp; <a style='color:darkgreen;font-weight:bold'  href='javascript:void(0)' onclick='taiGnt("${e.data.MaGiaoDich}")'> (XML) </a>`
                        html += `&nbsp; <a style='color:red;font-weight:bold'  href='javascript:void(0)' onclick='taiGntPDF("${e.data.MaGiaoDich}")'> (PDF) </a>
                        <span id="wait_${e.data.MaGiaoDich}"></span>    
                        `

                    }
                    $(`<div class='text-center'> 
                           ${html}
                     </div>`).appendTo(c);
                }
            }
        },
        {
            dataField: 'SoTien',
            headerCellTemplate:"Số<br/>Tiền",
            format: mFormat,
        },
        {
            dataField: 'LoaiTien',
            headerCellTemplate: "Loại<br/>Tiền",
        },
        {
            dataField: 'TrangThai',
            headerCellTemplate: "Trạng<br/>Thái",
            width: 100,
        },
        {
            headerCellTemplate: "Số<br/>CTU",
            dataField: "SoChungTu",
        },
        {
            dataField: 'NgayLapGnt',
            caption: 'Ngày lập',
            dataType: 'datetime', format: 'dd/MM/yy HH:mm',
            width: 120,
        },
        {
            dataField: 'NgayGuiGnt',
            caption: 'Ngày gửi',
            dataType: 'datetime', format: 'dd/MM/yy HH:mm',
            width: 120,
        },
        {
            dataField: 'NgayNopGnt',
            caption: 'Ngày nộp',
            dataType: 'datetime', format: 'dd/MM/yy HH:mm',
            width: 120,
        },
        {
            dataField: 'NganHang',
            caption: 'Ngân hàng',
        },
        {
            dataField: 'TaiKhoanNganHang',
            headerCellTemplate: 'TK<br/>Ngân hàng',
        },
        {
            dataField: 'MaChuong',
            caption:"Mã Chương - Mã NDKT",
            headerCellTemplate: 'Mã Chương<br/>Mã NDKT',
        },
        {
            dataField: 'TenCQThu',
            caption: "Cơ quan Thu",
            headerCellTemplate: 'Cơ quan Thu',
        },
    ];

    var TOTAL_COLUMNS_GNT = [];

    TOTAL_COLUMNS_GNT.push(
        {
            name: 'MaGiaoDich',
            summaryType: "count",
            showInColumn: "MaGiaoDich",
            displayFormat: "{0} GNT",
        },
        {
            column: 'SoTien',
            summaryType: "sum",
            showInColumn: "SoTien",
            displayFormat: "{0}",
            valueFormat: mFormat,

        },


    );

    dgGnt = $("#dgGnt").dxDataGrid({
        dataSource: [],
        columns: COLUMNS_GNT,
        export: {
            fileName: 'NIBOT - Giấy nộp tiền - ' + MST,
        },
        showOperationChooser: false, // tắt tính năng chọn toán tử
        height: $("#dg").height() - 25,
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
            totalItems: TOTAL_COLUMNS_GNT,
        },
        paging: {
            enabled: false
        },

    }).dxDataGrid("instance");
        //btnDongBoGnt,btnTimKiemGnt,dgGnt

    $("#btnTimKiemGnt").on("click", function () {

   

        $.ajax({
            type: "POST",
            dataType: "json",
            url: '/LoadGiayNopTien/',
            data: {
                "Keyword": (txtGntKeyword.option("value")??"").trim(),
                "LoaiNgay": txtGntLoaiNgay.option("value"),
                "TuNgay": toJP( txtGntTuNgay.option("value")),
                "DenNgay": toJP( txtGntDenNgay.option("value")),
                "MaSoThue": MST,
            },
            success: function (data) {
                if (data.status == 1) {
                    DATA_GNT = data.obj;
                    //{"TenCQThu":"Chi cục thuế Quận Gò Vấp ","MaChuong":"754 - 1052"}
                    for (let i in DATA_GNT) {
                        let r = JSON.parse( DATA_GNT[i].XmlGiayNopThue);
                        DATA_GNT[i].MaChuong = r.MaChuong;
                        DATA_GNT[i].TenCQThu = r.TenCQThu;

                    }


                    dgGnt.option("dataSource", DATA_GNT);
                    dgGnt.refresh();
                }
            },
            error: function (jqXHR, textStatus, errorThrown) {
                console.log(jqXHR);
                goTohome(jqXHR.responseText);

            }
        });

    })
    $("#btnDongBoGnt").on('click', function () {

        $.ajax({
            type: "GET",
            dataType: "json",
            url: '/ChecKTaiKhoanThue/' + MST,
            success: function (data) {
                if (data.status == -2) {
                    DongBoThueDienTu(1,'GiayNopTien');

                }
                else if (data.status == -3) {
                    DongBoThueDienTu(2, 'GiayNopTien');;

                }
                else if (data.status == 1) {
                    DongBoThueDienTu(0, 'GiayNopTien');;
                }

            },
            error: function (jqXHR, textStatus, errorThrown) {
                console.log(jqXHR);
                goTohome(jqXHR.responseText);

            }
        });

    })
}

function fmtNum(num) {
    if (num==0) {
        return "";
    }
    return num.toLocaleString();
}


var TOKHAI_KCN = [];


var TOKHAI_TOTAL_COLUMNS_2 = [];

function initCtrlToKhai() {

    txtMaGiaoDichThue = $("#txtMaGiaoDichThue").dxTextBox({
        placeholder: "mã giao dịch hoặc tên tờ khai"
    }).dxTextBox("instance");
    cboQuyThue = $("#cboQuyThue").dxSelectBox({
        placeholder: "chọn khoảng thời gian",
        items: ["Tháng 1", "Tháng 2", "Tháng 3", "Tháng 4", "Tháng 5", "Tháng 6", "Tháng 7", "Tháng 8", "Tháng 9", "Tháng 10", "Tháng 11", "Tháng 12", "Quý 1", "Quý 2", "Quý 3", "Quý 4", "Năm này", "Năm trước"],
        width: 120,
        value: "Năm này",
        onValueChanged(e) {
            let val = e.value;
            if (val == "Hôm nay" || val == "1 tuần" || val == "Tuần này" || val == "Tháng này" || val == "Năm này" || val == "Năm trước") {
                txtNamThue.option("visible", false);
                $("#lblNamThue").addClass("d-none");
            }
            else {
                txtNamThue.option("visible", true);
                $("#lblNamThue").removeClass("d-none");
            }
            var x = KhoangNgay(e.value, false, stNamThue);
            dtTuNgayThue.option("value", x.start);
            dtDenNgayThue.option("value", x.end);
        },
    }).dxSelectBox("instance");
    txtNamThue = $("#txtNamThue").dxNumberBox({
        value: stNamThue,
        visible: false,
        step: 0,
        width: 60,
        onValueChanged(e) {
            localStorage.setItem("stNamThueSearch", e.value);
            stNamThue = e.value;
            var x = KhoangNgay(cboQuyThue.option("value"), false, e.value);
            dtTuNgayThue.option("value", x.start);
            dtDenNgayThue.option("value", x.end);
        }
    }).dxNumberBox("instance");

    let dtx = new Date();
    let m = dtx.getMonth() + 1;
    let Year = dtx.getFullYear();
    let Quy = "";
    if (m <= 3) Quy = 1;
    else if (m <= 6) Quy = 2;
    else if (m <= 9) Quy = 3;
    else if (m <= 12) Quy = 4;
    if (m < 10) m = "0" + m;

    let strPlaceHolder =  Year + " hoặc " + m + "/" + Year + " hoặc Q" + Quy + "/" + Year;

    txtKyTinhThue = $("#txtKyTinhThue").dxTextBox({
        value: "",
        placeholder: strPlaceHolder,
        width: 200,
        onValueChanged(e) {
            let v = e.value.trim();
            let b = v != "";
            dtTuNgayThue.option("disabled", b);
            dtDenNgayThue.option("disabled", b);
            txtNamThue.option("disabled", b);
            cboQuyThue.option("disabled", b);
        }
    }).dxTextBox("instance");
    $("#txtNam .dx-texteditor-input").attr("style", "text-align:center");
    dtTuNgayThue = $("#dtTuNgayThue").dxDateBox({
        displayFormat: "dd/MM/yyyy",
        useMaskBehavior: true,
        width: 120,
    }).dxDateBox("instance");
    dtDenNgayThue = $("#dtDenNgayThue").dxDateBox({
        displayFormat: "dd/MM/yyyy",
        useMaskBehavior: true,
        width: 120,
    }).dxDateBox("instance");
    stNamThue = new Date().getFullYear();
    if (localStorage.getItem("stNamSearchThue")) {
        stNamThue = localStorage.getItem("stNamSearchThue");
    }
    else {
        localStorage.setItem("stNamSearch", stNamThue);
    }
    txtNamThue = $("#txtNamThue").dxNumberBox({
        value: stNamThue,
        visible: false,
        step: 0,
        width: 60,
        onValueChanged(e) {
            localStorage.setItem("stNamSearch", e.value);
            stNam = e.value;
            var x = KhoangNgay(cboQuyThue.option("value"), false, e.value);
            dtTuNgayThue.option("value", x.start);
            dtDenNgayThue.option("value", x.end);
        }
    }).dxNumberBox("instance");

    $("#txtNamThue .dx-texteditor-input").attr("style", "text-align:center");

    $("#tabThueDienTu").height($("#tabHD").height())
    cboQuyThue.option("value", "Năm này");

    COLUMNS = [
        {
            dataField: 'STT',
            caption: "STT",
            width: 40,
            allowHeaderFiltering: false,
        },

        {
            dataField: 'MaGiaoDich',
            caption: "Mã giao dịch",
            allowHeaderFiltering: false,
            headerCellTemplate: "Mã<br/>Giao dịch",
            width: 70,
        },

        {
            dataField: 'ToKhaiPhuLuc',
            caption: "Tờ khai phụ lục",
            headerCellTemplate: "Tờ khai<br/>/ Phụ lục",
            allowHeaderFiltering: true,
            headerFilter: {
                width: 700 // Adjust the width as needed
            },

            cellTemplate(c, e) {
                if (e.rowType == 'data' && e.data.DaTaiXml) {
                    let color = colorToKhai;
                    if (e.data.Loai == 'BangKe') {
                        color = colorBangKe;
                    }

                    let apHtml = ` <a href='javascript:void(0)' style='color:${color};font-weight:bold' onClick='taiToKhaiPhuLuc("${e.data.IdXml}")'>${e.data.ToKhaiPhuLuc}&nbsp;<span style='color:darkgreen'>(XML)</span></a> `
                    if (e.data.NoiDungXml=='xml') {
                        apHtml += `&nbsp;<a href='javascript:void(0)' style='color:red;font-weight:bold' onClick='taiToKhaiPhuLucPDF("${e.data.IdXml}",0)'>(PDF)</a>
                        <span id="wait_${e.data.IdXml}"></span>    
                    `
                    }
                    $(apHtml).appendTo(c)
                        
                }
                else {
                    $(`<span>${e.data.ToKhaiPhuLuc}</span>`).appendTo(c)
                }
            }
        },
        {
            allowHeaderFiltering: false,
            caption: "Thuế VAT, Giá trị HHDV mua vào, Doanh thu bán ra",
            headerCellTemplate:"<span class='text-danger'>Thuế VAT, Giá trị HHDV mua vào, Doanh thu bán ra</span>",
            columns: [
                {
                    allowHeaderFiltering: false,
                    dataField: "ct22", headerCellTemplate: "<span class='text-danger'>[22]<br/><small>Khấu trừ<br/>kỳ trước</small></span>", 
                    caption: "[22] Khấu trừ kỳ trước",
                    format: {type: "custom",formatter: fmtNum}
                },
                {
                    allowHeaderFiltering: false,
                    dataField: "ct23", headerCellTemplate: "<span class='text-danger'>[23]<br/><small>Giá trị HHDV<br/>mua vào</small></span>",
                    caption: "[23] Giá trị HHDV mua vào",
                    format: { type: "custom", formatter: fmtNum }
                },
                {
                    allowHeaderFiltering: false,
                    dataField: "ct25", headerCellTemplate: "<span class='text-danger'>[25]<br/><small>Khấu trừ<br/>kỳ này</small></span>", 
                    caption: "[25] Khấu trừ kỳ này",
                    format: { type: "custom", formatter: fmtNum }

                },
                {
                    allowHeaderFiltering: false,
                    dataField: "ct35", headerCellTemplate: "<span class='text-danger'>[35]<br/><small>HHDV<br/>bán ra</small></span>", 
                    caption: "[35] HHDV bán ra",
                    format: { type: "custom", formatter: fmtNum }

                },
                {
                    allowHeaderFiltering: false,

                    dataField: "ct37", headerCellTemplate: "<span class='text-danger'>[37]<br/><small>Đ.Chỉnh<br/>giảm</small></span>",
                    caption: "[37] Đ.Chỉnh giảm",
                    format: { type: "custom", formatter: fmtNum }

                },
                {
                    allowHeaderFiltering: false,

                    dataField: "ct38", headerCellTemplate: "<span class='text-danger'>[38]<br/><small>Đ.Chỉnh<br/>tăng</small></span>",
                    caption: "[38] Đ.Chỉnh tăng",
                    format: { type: "custom", formatter: fmtNum }

                },
                {
                    allowHeaderFiltering: false,

                    dataField: "ct40", headerCellTemplate: "<span class='text-danger'>[40]<br/><small>Phải nộp</br>trong kỳ</small></span>", 
                    caption: "[40] Phải nộp trong kỳ",
                    format: { type: "custom", formatter: fmtNum }

                },
                {
                    allowHeaderFiltering: false,

                    dataField: "ct43", headerCellTemplate: "<span class='text-danger'>[43]<br/><small>Khấu trừ<br/>chuyển kỳ sau</small></span>", 
                    caption: "[43] Khấu trừ chuyển kỳ sau",
                    format: { type: "custom", formatter: fmtNum }
                },
                {
                    allowHeaderFiltering: false,

                    dataField: "ct34", headerCellTemplate: "<span class='text-danger'>[34]<br/><small>Doanh thu<br/>HHDV bán ra</small></span>",
                    caption: "[34] Doanh thu HHDV bán ra",
                    format: { type: "custom", formatter: fmtNum }
                }
            ],
        },
        {
            allowHeaderFiltering: false,

            caption: 'Thông báo',
            width: 50,
            cellTemplate(c, e) {
                if (e.rowType == 'data' && e.data.IdThongBao) {
                    $(`<a href='javascript:void(0)' onclick = 'moThongBao("${e.data.MaGiaoDich}","${e.data.IdThongBao}")' style='color:#6a0a6a'><div class='text-center'><em class="icon ni ni-bell fs-16px" style='color:mediumvioletred'></em></div></a>`).appendTo(c);
                }
            }
        },
        {
            allowHeaderFiltering: true,

            dataField: 'KyTinhThue',
            caption:"Kỳ tính thuế",
            headerCellTemplate: "Kỳ tính<br/>Thuế",
            width: 60,
        },
        {
            allowHeaderFiltering: true,

            headerCellTemplate: "Loại<br/>Tờ khai",
            caption: "Loại tờ khai",
            dataField: "LoaiToKhai",
            width: 60,
           
        },
        {
            allowHeaderFiltering: true,

            dataField: 'LanNop',
            caption: 'Lần nộp',
            headerCellTemplate: "Lần<br/>nộp",
            width: 50,
            
        },
        {
            allowHeaderFiltering: true,

            dataField: 'LanBoSung',
            caption: 'Lần bổ sung',
            headerCellTemplate: "Lần<br/>BS",
            width: 50,
           
        },
        {
            allowHeaderFiltering: false,

            dataField: 'NgayNopNoiNop',
            caption: 'Ngày nộp - Nơi nộp',
            headerCellTemplate: "Ngày nộp - Nơi nộp",
            cellTemplate(c, e) {
                if (e.rowType == 'data') {
                    $(`<div>${toVnShort2(new Date( e.data.NgayNop))}<br/>${e.data.NoiNop}</div>`).appendTo(c);
                }
            },
            width: 105,
       
        },
        {
            allowHeaderFiltering: true,

            dataField: 'TrangThai',
            caption: 'Trạng thái',
            width: 125,
         
        },

    ];
    TOKHAI_TOTAL_COLUMNS_2.push(
        {
            name: 'MaGiaoDich',
            summaryType: "custom",
            showInColumn: "MaGiaoDich",
            displayFormat: "{0} tờ khai",
        });


    var ct = [22, 23, 25, 35, 37, 38, 40, 43,34];
    for (let i in ct) {
        TOKHAI_TOTAL_COLUMNS_2.push(
            {
                name: 'ct'+ ct[i],
                summaryType: "custom",
                showInColumn: "ct"+ct[i],
                displayFormat: '{0}',
                valueFormat: fmtNum,
            },
        );
    }


    dgThue = $("#dgThue").dxDataGrid({
        dataSource: [],
        columns: COLUMNS,
        export: {
            fileName: 'NIBOT - Tờ khai thuế - ' + MST,
        },
        cssClass: "my-custom-grid",
        onExporting: function (e) {
            e.cancel = true;
            var i = expToKhaiThue(e);
            if (i == 1)
                e.cancel = false;
        },
        onRowPrepared: function (e) {
            if (e.rowType === "data" && e.data.Loai === "BangKe") {
                $(e.rowElement).attr("style", "color:#cf0606;font-weight:bold");
            }
        },
        showOperationChooser: false, // tắt tính năng chọn toán tử
        wordWrapEnabled: true,
        allowColumnReordering: true,
        rowAlternationEnabled: true,
        showBorders: true,
        filterRow: { visible: true },
        headerFilter: { visible: true },

        showColumnLines: true,
        showRowLines: true,
        rowAlternationEnabled: true,
        columnAutoWidth: true,
        noDataText: "Không có dữ liệu",
        summary: {
            totalItems: TOKHAI_TOTAL_COLUMNS_2,
            calculateCustomSummary: function (options) {
                if (options.name == "MaGiaoDich") {
                    switch (options.summaryProcess) {
                        case "start":
                            options.totalValue = 0;
                            break;
                        case "calculate":
                            options.totalValue += (options.value.Loai == 'ToKhai') ? 1 : 0;
                            break;
                        case "finalize":
                            return options.totalValue;

                            break;
                    }
                }
                else if (options.name == "ct22") {
                    switch (options.summaryProcess) {
                        case "start":
                            options.totalValue = 0;
                            break;
                        case "calculate":
                            options.totalValue += options.value.ct22;
                            break;
                        case "finalize":
                            return options.totalValue;

                            break;
                    }
                }
                else if (options.name == "ct23") {
                    switch (options.summaryProcess) {
                        case "start":
                            options.totalValue = 0;
                            break;
                        case "calculate":
                            options.totalValue += options.value.ct23;
                            break;
                        case "finalize":
                            return options.totalValue;

                            break;
                    }
                }
                else if (options.name == "ct34") {
                    switch (options.summaryProcess) {
                        case "start":
                            options.totalValue = 0;
                            break;
                        case "calculate":
                            options.totalValue += options.value.ct34;
                            break;
                        case "finalize":
                            return options.totalValue;

                            break;
                    }
                }
                else if (options.name == "ct25") {
                    switch (options.summaryProcess) {
                        case "start":
                            options.totalValue = 0;
                            break;
                        case "calculate":
                            options.totalValue += options.value.ct25;
                            break;
                        case "finalize":
                            return options.totalValue;

                            break;
                    }
                }
                else if (options.name == "ct35") {
                    switch (options.summaryProcess) {
                        case "start":
                            options.totalValue = 0;
                            break;
                        case "calculate":
                            options.totalValue += options.value.ct35;
                            break;
                        case "finalize":
                            return options.totalValue;

                            break;
                    }
                } else if (options.name == "ct37") {
                    switch (options.summaryProcess) {
                        case "start":
                            options.totalValue = 0;
                            break;
                        case "calculate":
                            options.totalValue += options.value.ct37;
                            break;
                        case "finalize":
                            return options.totalValue;

                            break;
                    }
                }
                else if (options.name=="ct38") {
                    switch (options.summaryProcess) {
                        case "start":
                            options.totalValue = 0;
                            break;
                        case "calculate":
                            options.totalValue += options.value.ct38;
                            break;
                        case "finalize":
                            return options.totalValue;

                            break;
                    }
                }
                else if (options.name == "ct40") {
                    switch (options.summaryProcess) {
                        case "start":
                            options.totalValue = 0;
                            break;
                        case "calculate":
                            options.totalValue += options.value.ct40;
                            break;
                        case "finalize":
                            return options.totalValue;

                            break;
                    }
                }
                else if (options.name == "ct43") {
                    switch (options.summaryProcess) {
                        case "start":
                            options.totalValue = 0;
                            break;
                        case "calculate":
                            options.totalValue += options.value.ct43;
                            break;
                        case "finalize":
                            return options.totalValue;

                            break;
                    }
                }
            }
        },
        paging: {
            enabled: false
        },

    }).dxDataGrid("instance");

    $("#btnKetXuatThue").on("click", function () {
        dgThue.exportToExcel();
    })

    $("#btnKetXuatGnt").on("click", function () {
        dgGnt.exportToExcel();
    })
    $("#btnTimKiemThue").on("click", function () {

        let ltk = "";
        let mgd = txtMaGiaoDichThue.option("value") ?? "";
        mgd = mgd.trim();
        let tnThue = toJP(dtTuNgayThue.option("value"));
        let dnThue = toJP(dtDenNgayThue.option("value"));
        let kyTinhThue = txtKyTinhThue.option("value").trim();

        $("#divMsg").html('');
        TOKHAI_KCN = [];
        $.ajax({
            type: "POST",
            dataType: "json",
            url: '/LoadToKhai/',
            data: {
                "LoaiToKhai": ltk,
                "MaGiaoDich": mgd,
                "TuNgay": tnThue,
                "DenNgay": dnThue,
                "KyTinhThue": kyTinhThue,

                "MaSoThue": MST,
            },
            success: function (data) {
                if (data.status == 1) {
                    DATA_TOKHAI = data.obj;
                    for (let i in DATA_TOKHAI) {
                        DATA_TOKHAI[i].NgayNopNoiNop = toVnShort2(new Date(DATA_TOKHAI[i].NgayNop)) + "\r\n" + DATA_TOKHAI[i].NoiNop;
                    }
                    dgThue.option("dataSource", DATA_TOKHAI);
                    if (data.message != '') {
                        TOKHAI_KCN = JSON.parse(data.message);
                        $("#divMsg").html(`<span style='padding: 5px;cursor:pointer;text-decoration:underline' class='badge bg-danger fs-16px fw-bold' onclick='showToKhaiKCN()'>CÓ ${TOKHAI_KCN.length} TỜ KHAI CQT KHÔNG CHẤP NHẬN</span>`);
                    }

                }
            },
            error: function (jqXHR, textStatus, errorThrown) {
                console.log(jqXHR);
                goTohome(jqXHR.responseText);

            }
        });

    })

    $("#btnDongBoThue").on('click', function () {
        //dAlert("Chức năng đang bảo trì. Vui lòng quay lại sau");
        //return;
        $.ajax({
            type: "GET",
            dataType: "json",
            url: '/ChecKTaiKhoanThue/' + MST,
            success: function (data) {
                if (data.status == -2) {
                    DongBoThueDienTu(1,'ToKhai');

                }
                else if (data.status == -3) {
                    DongBoThueDienTu(2,'ToKhai');

                }
                else if (data.status == 1) {
                    DongBoThueDienTu(0,'ToKhai');
                }

            },
            error: function (jqXHR, textStatus, errorThrown) {
                console.log(jqXHR);
                goTohome(jqXHR.responseText);

            }
        });

    })

    $(".btnCauHinh").unbind().on('click', function () {
        DongBoThueDienTu(1);
    })


}



function expToKhaiThue(e) {

    let sheet = "NIBOT - Tờ khai thuế - " + MST;
    let fileName = sheet+".xlsx";
    var workbook = new ExcelJS.Workbook();
    var worksheet = workbook.addWorksheet(sheet);
    var startRow = 1;
    DevExpress.excelExporter.exportDataGrid({
        component: e.component,
        worksheet: worksheet,
        topLeftCell: { row: startRow, column: 1 },
        customizeCell: function (options) {
            var gridCell = options.gridCell;
            var excelCell = options.cell;
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
            if (gridCell.rowType != 'header' && gridCell.column.dataField && gridCell.column.dataField.indexOf("ct") >= 0) {
                if (gridCell.value && gridCell.value != 0) {
                    excelCell.value = gridCell.value;
                    excelCell.numFmt = '#,##0'; // See https://www.npmjs.com/package/exceljs#styles
                }
                else {
                    excelCell.value = "";

                }
                
            }



            if (excelCell.col > 0) {
                Object.assign(excelCell, {
                    alignment: { wrapText: true },
                    border: {
                        top: { style: 'thin' },
                        left: { style: 'thin' },
                        bottom: { style: 'thin' },
                        right: { style: 'thin' }
                    },
                });
            }



        }
    }).then(function () {
        let columnsWidth = [
            5, 
            20, 
            60,
            15,
            15, //so
            15, //mst
            15, //mst
            15, //so
            15, //mst
            15, //mst
        ]
        for (let j in columnsWidth) {
            worksheet.columns[j].width = columnsWidth[j]
        }
        workbook.xlsx.writeBuffer().then(function (buffer) {
            saveAs(new Blob([buffer], { type: 'application/octet-stream' }), fileName);
        })
        return 1;
    });
}


function showToKhaiKCN() {
    let k = [];
    for (let i in TOKHAI_KCN) {
        k.push(DATA_TOKHAI.filter(p => p.MaGiaoDich == TOKHAI_KCN[i].MaGiaoDich)[0]);
    }
    DATA_TOKHAI = k;
    dgThue.option("dataSource", DATA_TOKHAI);
    dgThue.refresh();
    //if (data.message != '') {
    //    TOKHAI_KCN = JSON.parse(data.message);
}



let taxWindow = null;
let isXuLy = false;



function openModalPDF(title, id) {

    $.ajax({
        type: "GET",
        dataType: "json",
        url: "/XemPDF/" + id ,
        success: function (data) {
            const contentType = "application/pdf";
            const blob = b64toBlob(data.obj, contentType);
            const blobUrl = URL.createObjectURL(blob);

            let bodyHtml = `
            <iframe src='${blobUrl}' style="border: 0; width: 100%; height: 100%;"></iframe>
        `
            let btnHtml = '';
            createModal("mXemPDF", title, bodyHtml, btnHtml);
            showModal("mXemPDF")
        },
        error: function (jqXHR, textStatus, errorThrown) {
            dAlert("ERROR ")
        }
    });

   
}

function openModalGnt(title, data) {
    let bodyHtml = `
            <button onclick="printIframe()" class='btn btn-primary'>In giấy nộp tiền</button>
            <iframe id='ifGnt' src='${data}' style="border: 0; width: 100%; height: 95%;"></iframe>
        `
    let btnHtml = '';
    createModal("mXemGiayNopTien", title, bodyHtml, btnHtml);
    showModal("mXemGiayNopTien")
}
function printIframe() {
    var iframe = document.getElementById('ifGnt');
    iframe.contentWindow.focus();
    iframe.contentWindow.print();
}

function taiToKhaiPhuLucPDF(id,itryC) {

    if (itryC == 2) {
        isXuLy = false;
        $("#wait_" + id).html('');
        dAlert('Thử lại 1 lần nữa');
        return;
    }
    if (isXuLy) {
        return;
    }
    isXuLy = true;
    $("#wait_" + id).html(spinerTDT);

    $.ajax({
        type: "GET",
        dataType: "json",
        url: "/TaiThueDienTu/ToKhaiPhuLuc/" + id + "/" + MST + "/PDF",
        success: function (data) {
            $("#wait_" + id).html('');
            isXuLy = false;
            if (data.status == -1) {
                taiToKhaiPhuLucPDF(id, itryC + 1);
            }
            else {
                
                var title = DATA_TOKHAI.filter(p => p.MaGiaoDich == id)[0].ToKhaiPhuLuc;
                openModalPDF (title, data["obj"]);

            }
        },
        error: function (jqXHR, textStatus, errorThrown) {
            isXuLy = false;
            //hideModal("mWaitExport2");
            $("#wait_" + id).html('');
            console.log("FAIL ");

            goTohome(jqXHR.responseText);
        }
    });

}



function taiGntPDF(id, itryC) {

    if (itryC == 2) {
        isXuLy = false;
        $("#wait_" + id).html('');
        dAlert('Thử lại 1 lần nữa');
        return;
    }
    if (isXuLy) {
        return;
    }
    isXuLy = true;
    $("#wait_" + id).html(spinerTDT);

    $.ajax({
        type: "GET",
        dataType: "json",
        url: "/TaiThueDienTu/GiayNopTien/" + id + "/" + MST + "/PDF",
        success: function (data) {
            $("#wait_" + id).html('');
            isXuLy = false;
            if (data.status == -1) {
                taiGntPDF(id, itryC + 1);
            }
            else {

                var title = DATA_GNT.filter(p => p.MaGiaoDich == id)[0].SoGiayNopTien;
                openModalPDF(title, data["obj"]);

            }
        },
        error: function (jqXHR, textStatus, errorThrown) {
            isXuLy = false;
            //hideModal("mWaitExport2");
            $("#wait_" + id).html('');
            console.log("FAIL ");

            goTohome(jqXHR.responseText);
        }
    });

}


function taiToKhaiPhuLuc(id) {
    var a = document.createElement('a');
    a.href = "/TaiThueDienTu/ToKhaiPhuLuc/" + id + "/" + MST;
    a.target = '_blank';
    document.body.append(a);
    a.click();
    a.remove();
 
}

function taiThongBao(id) {

    var a = document.createElement('a');
    a.href = "/TaiThueDienTu/ThongBao/" + id + "/" + MST;
    a.target = '_blank';
    document.body.append(a);
    a.click();
    a.remove();
}

function taiGnt(id) {

    var a = document.createElement('a');
    a.href = "/TaiThueDienTu/GiayNopTien/" + id + "/" + MST;
    a.target = '_blank';
    document.body.append(a);
    a.click();
    a.remove();
}

function xemGnt(idGnt) {
    var src = '/XemGiayNopTien/' + idGnt + '/' + MST;
    openModalGnt(idGnt, src);

}
function moThongBao(maGiaoDich,  IdThongBao) {
    $.ajax({
        type: "GET",
        dataType: "json",
        url: `/LoadToKhaiThongBao/${IdThongBao}/${MST}`,
        success: function (data) {
            if (data.status == 1) {
                let dataThongBao = data.obj;
                if (dataThongBao.length == 0) {
                    dAlert("Không có thông báo");
                }
                else {
                    openModalThongBao(maGiaoDich,  data.obj);
                }
            }
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR);
        }
    });

}

function openModalThongBao(maGiaoDich, data) {
    let r = DATA_TOKHAI.filter(p => p.MaGiaoDich == maGiaoDich && p.Loai=='ToKhai')[0];
    let k = r.ToKhaiPhuLuc;
    if (maGiaoDich) {
        k += ' (' + maGiaoDich + ')';
    }


    let bodyHtml = `
            <div class='row' >
                <div class='col-12'>
                    <p>Tờ khai: <b>${k}</b></p>

                </div>
                <div class='col-12 mt-2'>
                    <div id="dgThongBao" class='datagrid'></div>
                </div>
            </div>
        `
    let btnHtml = '';

    createModal("mThongBao", "Tờ Khai/Phụ lục - Thông Báo", bodyHtml, btnHtml);
    showModal("mThongBao")

    $("#dgThongBao").dxDataGrid({
        dataSource: data,
        columns: [
            {
                dataField: "ThongBao", caption: "Thông báo", cellTemplate(c, e) {
                    if (e.rowType == 'data' ) {
                        $(`<span style='font-weight:bold'>${e.data.ThongBao}</span>`).appendTo(c);
                    }
                }
            }
            ,
            { dataField: "NgayGui", caption: "Ngày gửi", dataType: "datetime", format: "dd/MM/yy HH:mm" },
            {
                dataField: "IdXmlThongBao", caption: "Tải TB",
                cellTemplate(c, e) {
                    if (e.rowType == 'data' && e.data.DaTaiXmlThongBao) {
                        $(`<div class='text-center'> <a  href='javascript:void(0)' onclick='taiThongBao("${e.data.IdXmlThongBao}")'><em class="icon ni ni-download fs-16px" style='color:mediumvioletred'></em></a></div>`).appendTo(c);
                    }
                }
            },


        ],
        height: 300,
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
            totalItems: [{
                    name: 'ThongBao',
                    summaryType: "sum",
                    displayFormat: "{0} thông báo",
            }],
        },
        paging: {
            enabled: false
        },

    }).dxDataGrid("instance");
}

var cboDongBoQuy;
var dtDongBoTuNgay;
var dtDongBoDenNgay;
var txtDongBoNam;
var txtMatKhauMoi;


function DongBoThueDienTu(i =0,form='ToKhai') {

    if (i == 0) {

        let bodyHtml = `
            <div class='row' >
                <div class='col-12'>
                    <table>
                        <tr>
                            <td width='70px'><b>Chọn quý</b> </td>
                            <td width='70px'> </td>
                            <td width='30%'><b>Ngày nộp</b></td>
                            <td width='30%'></td>
                        </tr>
                        <tr>
                            <td width='70px'><div id='cboDongBoQuy'></div> </td>
                            <td width='70px'><div id='txtDongBoNam'></div> </td>
                            <td width='30%'><div id='dtDongBoTuNgay'></div> </td>
                            <td width='30%'><div id='dtDongBoDenNgay'></div> </td>
                            <td>&nbsp;&nbsp;</td>
                        </tr>
                    </table>
                </div>
                <div class='col-12 text-center mt-3'>
                    <button class='btn btn-primary btn-sm' id='btnDongBoToKhai'><em class="icon ni ni-hot"></em>&nbsp;ĐỒNG BỘ</button>
                </div>
                <div class='col-12 d-none' id='waitDongBoThue' >
                    <hr/>
                    <div class = 'alert alert-primary text-center mt-1 mb-1'>
                        <div class="spinner-border " role="status">
                                <span class="visually-hidden"></span>
                        </div><br/>
                        Nibot đang đồng bộ dữ liệu từ trang <a class='text-primary' href='https://thuedientu.gdt.gov.vn' target='_blank'>https://thuedientu.gdt.gov.vn</a>
                    </div>
                </div>
                <div class='col-12 d-none mt-1' id='ketQua' >
                    <div class = 'alert alert-primary text-center mt-1 mb-1' id="lblKetQua"></div>

                </div>
                <div class='col-12 d-none mt-2 d-flex justify-content-start' id="divDoiMatKhau">
                    <div class='fw-bold' style='margin-top:5px'>Thay đổi mật khẩu:&nbsp;&nbsp;&nbsp;</div>
                    <div id='txtMatKhauMoi'></div>&nbsp;&nbsp;&nbsp;
                    <button  id='doiMatKhau' class='btn btn-danger btn-sm btn-dim'>cập nhật</button>
                    
                </div>
                <div class='col-12 d-none mt-1 ' id='divKetQua' >
                    <div id="dgKetQua" class='datagrid mt-2'> </div>
                    <div class='mt-2' style='text-align: right;color: red;font-weight: bold;'> Thời gian xử lý: <span id='timeXuLy'></span></div>
                </div>
                
            </div>
        `
        let btnHtml = '';
        dtDongBoTuNgay = null;
        dtDongBoDenNgay = null;
        let title = '';
        if (form == 'ToKhai') {
            title = "Đồng bộ Tờ khai - Thuế điện tử"
        }
        else if (form=='GiayNopTien') {
            title = "Đồng bộ Giấy nộp tiền - Thuế điện tử"
        }

        createModal("mDongBoToKhai", title, bodyHtml, btnHtml);
        showModal("mDongBoToKhai");

        txtMatKhauMoi = $("#txtMatKhauMoi").dxTextBox({
            mode: "password",
            placeholder: "nhập mật khẩu"
        }).dxTextBox("instance");


        cboDongBoQuy = $("#cboDongBoQuy").dxSelectBox({
            height: 30,
            dataSource:["-Quý-","1","2","3","4"],
            value: "-Quý-",
            onValueChanged(e) {
                let q = e.value;
                if (q == "-Quý-") {
                    let kn = KhoangNgay("Full Năm", true, txtDongBoNam.option("value"));
                    dtDongBoTuNgay.option("value", kn.start);
                    dtDongBoDenNgay.option("value", kn.end);
                }
                else {
                    let kn = KhoangNgay("Quý "+q, true, txtDongBoNam.option("value"));
                    dtDongBoTuNgay.option("value", kn.start);
                    dtDongBoDenNgay.option("value", kn.end);
                }
            }
        }).dxSelectBox("instance")

        txtDongBoNam = $("#txtDongBoNam").dxNumberBox({
            height: 30,
            value: new Date().getFullYear(),
            step: 1,
            onValueChanged(e) {

                let q = cboDongBoQuy.option("value");
                if (q == "-Quý-") {
                    let kn = KhoangNgay("Full Năm", true, e.value);
                    dtDongBoTuNgay.option("value", kn.start);
                    dtDongBoDenNgay.option("value", kn.end);
                }
                else {
                    let kn = KhoangNgay("Quý " + q, true, e.value);
                    dtDongBoTuNgay.option("value", kn.start);
                    dtDongBoDenNgay.option("value", kn.end);
                }

                
            }
        }).dxNumberBox("instance")

        let kn = KhoangNgay("Full Năm", true, new Date().getFullYear())
        dtDongBoTuNgay = $("#dtDongBoTuNgay").dxDateBox({
            height: 30,
            value: kn.start,
            useMaskBehavior: true,
            displayFormat: 'dd/MM/yyyy',
        }).dxDateBox("instance");

        dtDongBoDenNgay = $("#dtDongBoDenNgay").dxDateBox({
            height: 30,
            value: kn.end,
            useMaskBehavior: true,

            displayFormat: 'dd/MM/yyyy',
        }).dxDateBox("instance");

        setTimeout(function () {
           cboDongBoQuy.option("value", parseInt(Math.ceil( (new Date().getMonth() + 1) / 3)).toString() );
        }, 200)

        $("#doiMatKhau").unbind().on("click", function () {
            $("#doiMatKhau").prop("disabled", true);
            let t = txtMatKhauMoi.option("value") ?? "";
            t = t.trim();
            if (t == "") {
                dAlert("Chưa nhập mật khẩu.");
                return;
            }
            $.ajax({
                type: "POST",
                dataType: "json",
                url: '/TdtDoiMatKhau',
                data: {
                    "TdtPassword": t, 
                    "MaSoThue":MST
                },
                success: function (data) {
                    if (data.status == 1) {
                        dAlert("Đổi mật khẩu thành công! Bấm [Đồng bộ] để thử lại.");
                        $("#divDoiMatKhau").addClass("d-none");
                    }
                    else {
                        //chua co tai khoan
                        $("#divDoiMatKhau").removeClass("d-none");
                        dAlert(data.message);
                        return
                    }
                    $("#doiMatKhau").prop("disabled", false);

                },
                error: function (jqXHR, textStatus, errorThrown) {
                    console.log(jqXHR);
                    dAlert("LỖI");
                    $("#doiMatKhau").prop("disabled", false);
                    goTohome(jqXHR.responseText);
                }
            });

        })
        $("#btnDongBoToKhai").unbind().on("click", function () {
            $("#ketQua").addClass("d-none");
            $("#waitDongBoThue").removeClass("d-none");
            $("#btnDongBoToKhai").prop("disabled", true);
            $("#divKetQua").addClass("d-none");
            $("#divDoiMatKhau").addClass("d-none");
            let TuNgay = toJP(dtDongBoTuNgay.option("value"));
            let DenNgay = toJP(dtDongBoDenNgay.option("value"));
            let beginTime = new Date();

            $.ajax({
                type: "GET",
                dataType: "json",
                url: `/DongBoThueDienTu/${form}/${TuNgay}/${DenNgay}/${MST}`,
                success: function (data) {

                    if (data.status == -1) {
                        //chua co tai khoan
                        $("#ketQua").removeClass("d-none");
                        $("#waitDongBoThue").addClass("d-none");

                        $("#lblKetQua").html(data.message);
                        $("#btnDongBoToKhai").prop("disabled", false);
                        if (data.message.indexOf("mật khẩu của bạn không chính xác")>0) {
                            $("#divDoiMatKhau").removeClass("d-none");
                        }
                        return
                    }
                    if (data.status == -2) {
                        //chua co tai khoan
                        $("#ketQua").removeClass("d-none");
                        $("#waitDongBoThue").addClass("d-none");

                        $("#lblKetQua").html(`Chưa thiết lập tài khoản trang https://thuedientu.gdt.gov.vn với Nibot.
                                        <br/><br/><a class='text-primary fw-bold fs-16px' href='javascript:void(0)' onclick='DongBoThue(1)'>Click vào đây để thiết lập</a>`);
                        $("#btnDongBoToKhai").prop("disabled", false);

                        return
                    }
                    else if (data.status == 1) {
                        $("#ketQua").addClass("d-none");
                        $("#divKetQua").removeClass("d-none");
                        $("#waitDongBoThue").addClass("d-none");
                        $("#btnDongBoToKhai").prop("disabled", false);

                        if (data.obj.length>0) {
                            var l = data.obj.filter(p => p.KetQua.indexOf("mật khẩu") > 0).length;
                            if (l > 0) {
                                $("#divDoiMatKhau").removeClass("d-none");
                            }
                        }

                        var COLS = [];
                        var TOTAL_COLS = [];

                        if (form == 'ToKhai') {
                            COLS = [
                                { dataField: "Thang", caption: "Tháng" },
                                { dataField: "SoToKhai", headerCellTemplate: "Tờ<br/>khai", },
                                { dataField: "SoPhuLuc", headerCellTemplate: "Phụ<br/>lục", },
                                { dataField: "KetQua", headerCellTemplate: "Kết quả<br/>Đồng bộ", },
                            ];
                            TOTAL_COLS = [
                                {
                                    column: 'Thang',
                                    summaryType: "count",
                                    displayFormat: "{0}",

                                },
                                {
                                    column: 'SoToKhai',
                                    summaryType: "sum",
                                    displayFormat: "{0}",
                                },
                                {
                                    column: 'SoPhuLuc',
                                    summaryType: "sum",
                                    displayFormat: "{0}",

                                },
                            ]
                             
                        }
                        else {
                            COLS = [
                                { dataField: "Thang", caption: "Tháng" },
                                { dataField: "SoLuongGnt", headerCellTemplate: "Số lượng<br/>GNT", },
                                { dataField: "KetQua", headerCellTemplate: "Kết quả<br/>Đồng bộ", },
                            ];
                            TOTAL_COLS = [
                                {
                                    column: 'Thang',
                                    summaryType: "count",
                                    displayFormat: "{0}",

                                },
                                {
                                    column: 'SoLuongGnt',
                                    summaryType: "sum",
                                    displayFormat: "{0}",
                                },
                            ]

                        }

                        $("#dgKetQua").dxDataGrid({
                            dataSource: data.obj,
                            columns: COLS,
                            showOperationChooser: false, // tắt tính năng chọn toán tử
                            height: 400,
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
                                totalItems: TOTAL_COLS,
                            },
                            paging: {
                                enabled: false
                            },
                        }).dxDataGrid("instance");
                        let tgian = ((new Date() - beginTime) / 1000);
                        $("#timeXuLy").html(tgian + " giây");
                    }
                  


                },
                error: function (jqXHR, textStatus, errorThrown) {
                    console.log(jqXHR);
                    dAlert("LỖI");
                    $("#waitDongBoThue").addClass("d-none");
                    $("#ketQua").addClass("d-none");
                    $("#lblKetQua").html("");
                    $("#btnDongBoToKhai").prop("disabled", false);
                    goTohome(jqXHR.responseText);


                }
            });

        })

    }
    else if (i == 1) {
        let bodyHtml = `
        <form id='ffff' autocomplete='off'>
            <div class='row' >
                <div class='col-12'>
                    Nhập tài khoản của trang <a href='https://thuedientu.gdt.gov.vn' target='_blank'>https://thuedientu.gdt.gov.vn</a>
                </div>
                <div class='col-12 mt-2'>
                    <div id='txtTdtTenDangNhap' ></div>
                </div>
                <div class='col-12 mt-2'>
                    <div id='txtTdtMatKhau' ></div>
                </div>
                <div class='col-12 text-center mt-3'>
                    <button class='btn btn-primary btn-sm' id='btnTdtSave' ><em class="icon ni ni-save"></em>&nbsp;&nbsp;CẬP NHẬT</button>
                </div>
            </div>
            </form>
        `

        let btnHtml = '';

        createModal("mDongBoToKhai", "Thiết lập tài khoản - Thuế điện tử", bodyHtml, btnHtml);
        showModal("mDongBoToKhai");
 
        tdtUsername = $("#txtTdtTenDangNhap").dxTextBox({
            label: "Tên đăng nhập - Thuế điện tử",
            height: 28,
        }).dxTextBox("instance");

        tdtPassword = $("#txtTdtMatKhau").dxTextBox({
            label: "Mật khẩu - Thuế điện tử",
            height: 28
        }).dxTextBox("instance");;

        $("#btnTdtSave").unbind().on("click", function () {
            let username = tdtUsername.option("value");

            $("#btnTdtSave").prop("disabled", true);
            $.ajax({
                type: "POST",
                dataType: "json",
                url: `/DangKyTaiKhoanTdt/`,
                data: {
                    MaSoThue: MST,
                    TdtUsername: tdtUsername.option("value"),
                    tdtPassword: tdtPassword.option("value"),
                },
                success: function (data) {
                    if (data.status == -1) {
                        dAlert("<b>Đăng ký thất bại. Lý do: </b></br>- " + data.message);
                        $("#btnTdtSave").prop("disabled", false);
                        return
                    }
                    else if (data.status == 1) {
                        dAlert(data.message);
                        hideModal("mDongBoToKhai");
                        return;
                    }
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    console.log(jqXHR);
                    $("#btnTdtSave").prop("disabled", false);
                    dAlert("LỖI ĐỒNG BỘ. THỬ LẠI 1 LẦN NỮA XEM SAO");
                     goTohome(jqXHR.responseText);

                }
            });
        });

    }
}



