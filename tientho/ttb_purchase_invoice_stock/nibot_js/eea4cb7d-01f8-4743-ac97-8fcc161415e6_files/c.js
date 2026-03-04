//c.js 9
var dg;
var gridId = "#dg";
var initSummary = false;
var isFirstClickTC = true;
var isFirstClickHD = false;
var isFirstClickDTPN = true;
var CURRENT_TAB = "";
var isFirstClickHH = true;
var isFirstClickNH = true;
var isFirstClickThueDienTu = true;
var isFirstClickHoSo = true;
var isFirstClickHaiQuan = true;

var toolTip, toolTip2;

var datagrid;
var cboHH_PhanLoai, txtHH_TimKiem_MH;
var dgHH = null;
var DATA = [];
var DATA_HH = [];
var DATA_TC = [];
var dgHHExport;

var impX = 0;
var impC = 0;

var txtDTPN_TimKiem, dgDTPN, DATA_DTPN;
var EXCEL_DATA;
var SEARCH_OBJ;
var beginTime, endTime;
var ttC = 0, ttX = 0;
var CHUNKS_SIZE_MST = 30;


var stNam, txtNam;
var cboLocFile, cboLHD, cboDuyet, txtThongTin, cboTTHD, cboKetQuaKiemTra, dtTuNgay, dtDenNgay,
    txtKHMSHD, txtKHHD, txtSoHD;
var cboQuy;
var chkMH;

var label = "";
var isSelection = false;

var txtMST, dgTraCuuThongTin;
var isFirstClickQuyDoi = true;
var isFirstClickLuong = true;


function goToTab() {
    if (CURRENT_TAB == "tabHD") {
        cboDuyet.repaint();
        cboLocFile.repaint();
        cboDuyet.repaint();
        txtThongTin.repaint();
        cboTTHD.repaint();
        cboKetQuaKiemTra.repaint();
        dtTuNgay.repaint();
        dtDenNgay.repaint();
        datagrid.repaint();
        datagrid.refresh();
   
    }
    if (CURRENT_TAB == "tabHH") {
        if (isFirstClickHH) {
            initCtrlHangHoa();
            isFirstClickHH = false;
            SearchHH();
        }
    }
    else if (CURRENT_TAB == "tabTC") {

        if (isFirstClickTC) {
            initCtrlTraCuu();
            isFirstClickTC = false;
        }
    }
    else if (CURRENT_TAB == "tabDTPN") {
        if (isFirstClickDTPN) {
            initCtrlDTPN();
            isFirstClickDTPN = false;
            SearchDTPN();
        }
    }
    else if (CURRENT_TAB == "tabQD") {
        if (isFirstClickQuyDoi) {
            if (isFirstClickHH == true && DATA_HH.length == 0) {
                initCtrlHangHoa();
                SearchHH();
            }
            initCtrlQuyDoi();
            isFirstClickQuyDoi = false;
            SearchQuyDoi();
        }
    }
    else if (CURRENT_TAB == "tabLuong") {
        if (isFirstClickLuong) {
            isFirstClickLuong = false;
            initCtrlLuong();
        }
    }
    else if (CURRENT_TAB == "tabNH") {
        if (isFirstClickNH) {
            isFirstClickNH = false;
            initCtrlNganHang();
        }
    }
    else if (CURRENT_TAB == "tabThueDienTu") {
        if (isFirstClickThueDienTu) {
            isFirstClickThueDienTu = false;
            initCtrlThueDienTu();
        }
    }
    else if (CURRENT_TAB == "tabHoSoKeToan") {
        if (isFirstClickHoSo) {
            isFirstClickHoSo = false;
            initCtrlHoSoKeToan();
        }
    }
    else if (CURRENT_TAB == "tabToKhaiHaiQuan") {
        if (isFirstClickHaiQuan) {
            isFirstClickHaiQuan = false;
            initCtrlToKhaiHaiQuan();
        }
    }
}
$(document).ready(function () {

    $(".dx-datagrid-summary-item").css("cursor", "pointer");
    $(".dx-datagrid-summary-item").unbind().on("click", function () {
        alert("X")
    })

    DATA = [];

    $("#mHD,#mHH,#mTTDN").on("click", function () {

        $(".nk-menu-item").removeClass("active");
        $(this).parent().addClass("active");
    })
    let stt = 1;
    for (let i in lstDN) {
        lstDN[i].TenDoanhNghiep = stt.toString().padStart(3, "0") + ". " + lstDN[i].TenDoanhNghiep.toUpperCase() + " (" + lstDN[i].MaSoThue + ")";
        stt++;
    }
    $("#cboMST").dxSelectBox({
        dataSource: lstDN,
        displayExpr: "TenDoanhNghiep",
        valueExpr: "MaSoThue",
        value: MST,
        width: 600,
        dropDownOptions: {
            width: 600 // Đặt độ rộng của cửa sổ xổ xuống ở đây
        },
        searchEnabled: true, // Enable searching
        searchExpr: 'TenDoanhNghiep',
        searchMode: 'contains',
        minSearchLength: 3,
        onValueChanged(e) {
            if (e.value) {
                var k = lstDN.filter(p => p.MaSoThue == e.value)[0];
                window.location.href = "/QLHD/" + k.MaSoThue + "/" + k.GuidGoi + "#" + CURRENT_TAB;
            }
        }
    })

    loadCfg();
    initCtrl();


    if (isLock) {
        $("#btnDongBo").attr("href", "javascript:void(0)")
        $("#btnTaiBangKeTCT").attr("onclick", "javascript:void(0)")

        $("#btnDongBo").unbind().on("click", function () {
            dAlert("NIBOT tạm khóa chức năng này đến khi trang https://hoadondientu.gdt.gov.vn khắc phục xong sự cố!");
            return;
        })
        $("#btnTaiBangKeTCT").unbind().on("click", function () {
            dAlert("NIBOT tạm khóa chức năng này đến khi trang https://hoadondientu.gdt.gov.vn khắc phục xong sự cố!");
            return;
        })
    }

    $("#linkHD").on("click", function () {
        CURRENT_TAB = "tabHD";
        goToTab();
    })
    $("#linkHH").on("click", function () {
        CURRENT_TAB = "tabHH";
        goToTab();
    })

    $("#linkTC").on("click", function () {
        CURRENT_TAB = "tabTC";
        goToTab();
    })

    $("#linkDTPN").on("click", function () {
        CURRENT_TAB = "tabDTPN";
        goToTab();
    })

    $("#linkQD").on("click", function () {
        CURRENT_TAB = "tabQD";
        goToTab();
    })

    $("#linkLuong").on("click", function () {
        CURRENT_TAB = "tabLuong";
        goToTab();
    })

    $("#linkNH").on("click", function () {
        CURRENT_TAB = "tabNH";
        goToTab();
    })

    $("#linkThueDienTu").on("click", function () {
        CURRENT_TAB = "tabThueDienTu";
        goToTab();

    })

    $("#linkHoSoKeToan").on("click", function () {
        CURRENT_TAB = "tabHoSoKeToan";
        goToTab();
    })
    $("#linkToKhaiHaiQuan").on("click", function () {
        CURRENT_TAB = "tabToKhaiHaiQuan";
        goToTab();
    })


    //option A
    $("#frmHoaDon,#frmHangHoa,#frmTraCuu,#frmDTPN", "#frmQuyDoi", "#frmKetXuat", "#frmNganHang", "#frmThueDienTu").submit(function (e) {
        e.preventDefault();
    });



    if (MST == "0302797984") {
        
        TaoFormChietKhau();
    }

})

function loadCfg() {
    isSelection = getCfg("isSelection") == "true";
}

$(window).on("resize", function () {
    change_grid_height();
});

function equalSize() {
    var t = $("#cboLHD").width();
    $("#cboLocFile,#cboDuyet,#cboKetQuaKiemTra,#cboTTHD, #txtKHHD,#txtSoHD,#txtThongTin,#cboQuy").width(t)
    $("#dtTuNgay,#dtDenNgay").width(t - 60)
}

function calc_height(gridId) {
    let win_height = $(window).height();
    let grid_top = $(gridId).position().top;
    console.log(gridId + "  grid_top  " + grid_top);
    let footer_height = 50;
    let win_width = $(window).widthchange_grid_height
    let height = win_height - grid_top - footer_height - 60;
    if (win_width <= 640) {
        if (height < 400)
            height = 500;
    }
    if (height < 400)
        height = 400;
    return parseInt(height);
}
function change_grid_height(grid) {
    equalSize();
    if (grid) {
        gridId = grid;
    }
    else {
        gridId = "#dg";
    }

    let height = calc_height(gridId);
    $(gridId).dxDataGrid("instance").option("height", height);
    console.log(gridId, height);
    return height;
}


function daoFormatNgay2(str) {
    try {
        if (typeof str == 'object') {
            let d = new Date(str);
            return toJP(d);
        }
        else {

            str = str.toString().substr(0, 10);
            let k = str.split('/');
            let nam = parseInt(k[2]);
            let thang = parseInt(k[1]) - 1;
            let ngay = parseInt(k[0]);
            return toJP(new Date(nam, thang, ngay));
        }

    }
    catch {
        return null;
    }
}
var dataImportTCT = [];
var InDATA = [];
function getData(d) {
    try {
        if (d.hasOwnProperty("result")) {
            let k = d["result"].toString();
            return k ?? "";
        }
        if (d != null && d.toString() != "")
            return d.toString();

    }
    catch {
        return null;
    }
}
function createRowTemplate(data, tInfo) {
    let khms = getData(data[tInfo.KyHieuMauSo]);
    let khd = getData(data[tInfo.KyHieuHoaDon]);

    if (khd == null || khd.length < 6 ) {
        return null;
    }
    if (khd.length >= 7) {
        khms = khd[0];
        khd = khd.substr(1);
        if (khms!="1" && khms!="2") {
            return null;
        }
        if (khd[0] != "C" && khd[0]!="K") {
            return null;
        }
    }
    let sohd = getData(data[tInfo.SoHoaDon]);
    while (sohd.indexOf("0") == 0)
        sohd = sohd.substr(1);

    let ngaylap = "1970-01-01";

    if (data[tInfo.NgayLap] != null)
        ngaylap = daoFormatNgay2(data[tInfo.NgayLap]);
    let mst = getData(data[tInfo.MaSoThue]);
    if (!mst) {
        mst = null;
    }
    else {
        mst = mst.replace(/\s|\t/g, "").trim();
        if (mst.length == 9 || mst.length == 13) {
            mst = "0" + mst;
        }
    }

    return {
        "KyHieuHoaDon": khms + khd,
        "SoHD": sohd,
        "NgayLap": ngaylap,
        "MaSoThue": mst
    }
}
function ImportTCT() {
    dataImportTCT = [];
    InDATA = [];
    $("#importFileTCT").val('');
    $("#importFileTCT").unbind().on("change", function () {
        var rI = -1;
        var tInfo = {
            "KyHieuMauSo": 0,
            "KyHieuHoaDon": 0,
            "SoHoaDon": 0,
            "NgayLap": 0,
            "MaSoThue": 0,
        }
        var fileUpload = $("#importFileTCT").prop('files')[0];
        if (fileUpload) {
            if (typeof (FileReader) != "undefined") {
                const wb = new ExcelJS.Workbook();
                const reader = new FileReader()
                reader.readAsArrayBuffer(fileUpload)
                reader.onload = () => {
                    const buffer = reader.result;
                    var foundCol = false;
                    wb.xlsx.load(buffer).then(workbook => {
                        workbook.eachSheet((sheet, id) => {
                            sheet.eachRow((row, rowIndex) => {
                                let data = row.values;
                                if (!foundCol) {
                                    for (let k in data) {
                                        let v = getData(data[k])
                                        if (v) {
                                            v = v.toLowerCase();
                                            if (v == "ký hiệu mẫu số") tInfo.KyHieuMauSo = k;
                                            if (v == "ký hiệu hóa đơn" || v == "seri" ||  v == "seri hđ") {
                                                tInfo.KyHieuHoaDon = k;
                                            }
                                            if (v == "số hóa đơn" || v == "số hđ") tInfo.SoHoaDon = k;
                                            if (v == "ngày lập" || v == "ngày hđ") {
                                                tInfo.NgayLap = k;
                                                if (v=="ngày hđ") {
                                                    tInfo.MaSoThue = (parseInt(k) + 2).toString();
                                                }
                                            }
                                            if (v.indexOf("mst") == 0 && tInfo.MaSoThue == 0 && k>0) tInfo.MaSoThue = k;
                                        }
                                    }
                                    strMSG = "File template không đủ các cột: Ký hiệu mẫu số, Ký hiệu hóa đơn, Số hóa đơn, Ngày lập, MST.";
                                    if (tInfo.KyHieuHoaDon > 0 && tInfo.SoHoaDon > 0 && tInfo.NgayLap > 0 && tInfo.MaSoThue > 0) {
                                        rI = rowIndex;
                                        foundCol = true;
                                        strMSG = "";
                                    }
                                }

                                if (foundCol) {
                                    if (rI > 0 && rI <= rowIndex) {
                                        var dataHoaDon = createRowTemplate(data, tInfo);
                                        if (dataHoaDon != null) {
                                            if (dataImportTCT.filter(p => p.KyHieuHoaDon == dataHoaDon.KyHieuHoaDon && p.SoHD == dataHoaDon.SoHD && p.MaSoThue == dataHoaDon.MaSoThue).length == 0) {
                                                dataImportTCT.push(dataHoaDon);
                                            }
                                        }
                                        strMSG = "";
                                    }
                                }
                            });
                        })
                    }).then(function () {
                        for (let i in DATA) {
                            if (DATA[i].mst2)
                                DATA[i].mst2 = DATA[i].mst2.replace(/\s|\t/g, "");
                        }


                        if (dataImportTCT.length > 0) {
                            for (var i = 0; i < dataImportTCT.length; i++) {
                                let r = dataImportTCT[i];

                                let c = DATA.filter(p => r.KyHieuMauSo == p.khms && r.KyHieuHoaDon == p.khhd && (r.MaSoThue == p.mst2) && r.SoHD == p.so && r.NgayLap == p.ngay);
                                if (c.length == 0) {
                                    InDATA.push({
                                        "Nguon": "XLS",
                                        "KyHieuHoaDon": r.KyHieuHoaDon,
                                        "SoHD": r.SoHD,
                                        "NgayLap": new Date(r.NgayLap),
                                        "MaSoThue": r.MaSoThue,
                                        "TrangThaiKetQua":"",
                                    })
                                }
                            }
                            for (var i = 0; i < DATA.length; i++) {
                                let r = DATA[i];

                                let c = dataImportTCT.filter(p => p.KyHieuHoaDon == r.khhd && p.MaSoThue == r.mst2 && p.SoHD == r.so && p.NgayLap == r.ngay);
                          
                                if (c.length == 0) {
                                    let kq = '';
                                    if (r.kqhd=='2' || r.kqhd=='4') {
                                        kq = ketQuaKiemTraDataSource.filter(p => p.value == r.kqhd)[0].text;
                                    }

                                    if (r.tthhd == '4' || r.tthhd == '6') {
                                        if (kq != '') kq += '-';
                                        kq += trangThaiDataSource.filter(p => p.value == r.tthhd)[0].text;
                                    }


                                    InDATA.push({
                                        "Nguon": "NiBot",
                                        "KyHieuHoaDon": r.khhd,
                                        "SoHD": r.so,
                                        "NgayLap": new Date(r.ngay),
                                        "MaSoThue": r.mst2,
                                        "TrangThaiKetQua": kq 
                                    });
                                }
                            }
                            DoiChieu(2, InDATA);


                        }
                        else {
                            DoiChieu(3);
                        }
                    });
                }
            }

        }
    });

    $("#importFileTCT").click();

}


function DoiChieu(i, InDATA) {
    let bodyHtml = '';
    let btnHtml = `
         <div class="d-flex justify-content-end"> 
                <a href="https://www.youtube.com/watch?v=l6I1GUHSRZ8&list=PLsY6GrKuhR_rMVOVdFYE_rt9FODyg08Ah" target="_blank"><em class=" fw-bold text-danger icon ni ni-youtube" style="font-size:32px"></em> </a> 
                <a style="background-image: linear-gradient(45deg, #f70bc7, #5700b1);-webkit-background-clip: text; background-clip: text;color: transparent;margin-top:7px;font-weight:bold;" href="https://www.youtube.com/watch?v=l6I1GUHSRZ8&list=PLsY6GrKuhR_rMVOVdFYE_rt9FODyg08Ah" target="_blank">&nbsp;&nbsp;Video HDSD chức năng Đối chiếu chéo&nbsp;&nbsp;</a>
            </div>
    `

    let btnImport = `
            <div class='text-center mb-2'>
                <button class='btn btn-outline-dark' onClick="ImportTCT()"><b>Upload file Excel Template</b></button>
            </div>
        `
    let ghiChu = `<p style='line-height:32px'> Chức năng này giúp người dùng có thể đối chiếu sự khác biệt về số lượng hóa đơn trên lưới dữ liệu hiện có của Nibot với:<br/>
                    <a onMouseOver="this.style.color='#8d088b'"
                        onMouseOut="this.style.color='#ec13ec'" 
                        style='color:#ec13ec' href='/TEMPLATES/Excel_Template_DoiChieu.xlsx' target='_blank'><b   class='fs-16px'>1. FILE EXCEL TEMPLATE</b> (click vào để tải template)</a>. HOẶC 
                        <br/> 
                    <b   class='fs-16px'>2. FILE EXCEL BẢNG KÊ MUA VÀO, BÁN RA CỦA SMART PRO        </b>
                </p>`


    if (i == 2) {
        bodyHtml = `
                <div id="dgDoiChieu"></div>
            `
        createModal("mDoiChieu", "Kết quả đối chiếu", bodyHtml, btnHtml)
        showModal("mDoiChieu");

        let totals = []

        totals.push({
            column: 'Nguon',
            summaryType: "count",
            displayFormat: '{0} HĐ',
        });


        $("#dgDoiChieu").dxDataGrid({
            dataSource: InDATA,
            columns: [
                { dataField: "Nguon", caption: "Nguồn" },
                { dataField: "KyHieuMauSo", caption: "KHMS" },
                { dataField: "KyHieuHoaDon", caption: "KHHD" },
                { dataField: "SoHD", caption: "Số HĐ" },
                { dataField: "MaSoThue", caption: "MST" },
                { dataField: "NgayLap", caption: "Ngày", dataType: 'datetime', format: 'dd/MM/yyyy' },
                { dataField: "TrangThaiKetQua", caption: "Tình trạng HĐ - Nibot",  },

            ],

            repaintChangesOnly: true,
            loadPanel: {
                enabled: true // or false | "auto"
            },
            scrolling: {
                columnRenderingMode: 'virtual',
                useNative: true,
                renderAsync: true,
                showScrollbar: "always"
            },
            export: {
                enabled: true,
                fileName: "Nibot_KetQuaDoiChieu",
            },
            height: 500,
            wordWrapEnabled: true,
            allowColumnReordering: true,
            rowAlternationEnabled: true,
            showBorders: true,
            filterRow: { visible: true },
            showColumnLines: true,
            showRowLines: true,
            rowAlternationEnabled: true,
            columnAutoWidth: true,
            summary: {
                totalItems: totals
            },
            paging: {
                enabled: false
            },

        })


    }
    else if (i == 3) {
        bodyHtml = `
                ${btnImport}
                ${ghiChu}
                <div class='alert alert-danger'>Không đọc được dữ liệu từ file Excel</div>

            `
        createModal("mDoiChieu", "Đối chiếu chéo HĐ với Nibot", bodyHtml, btnHtml)
        showModal("mDoiChieu");
    }
    else {
        bodyHtml = `
                ${btnImport}
                ${ghiChu}
            `
        createModal("mDoiChieu", "Đối chiếu chéo HĐ từ Nibot", bodyHtml, btnHtml)
        showModal("mDoiChieu");


    }


}

var beginTime;


function TaiBangKeTuTCT(i, data) {
    let tenModal = 'mTaiBangKeTuTCT';
    let tenChucNang = 'Tải bảng kê từ Tổng cục thuế';
    let bodyHtml = '', btnHtml = '';// createHelpLink("DOI_CHIEU_CHEO");
    var tNgay = toVn(dtTuNgay.option("value"))
    var dNgay = toVn(dtDenNgay.option("value"))
    var loai = cboLHD.option("value").indexOf("BAN_RA") == 0 ? "Bán Ra" : "Mua Vào";
    let btnTaiBangKe = `
                <div class = 'alert alert-primary text-center mt-1 mb-1'>
                        <div class="spinner-border " role="status">
                                <span class="visually-hidden"></span>
                        </div><br/>
                            Nibot đang tải bảng kê Hóa đơn ${loai} (${tNgay} - ${dNgay}) từ Tổng cục Thuế<br/>
                            Vui lòng chờ trong giây lát!<br/>
                    </div>
        `

    let ghiChu = `<br/>Chức năng này giúp người dùng tải trực tiếp bảng kê hóa đơn ${loai} từ Tổng cục Thuế.<span class='fw-bold text-danger'> Chú ý: Nibot không thực hiện các thao tác biến đổi dữ liệu trên dữ liệu tải về này.</span>`
    if (i == 2) {
        console.log(data);
        btnTaiBangKe = `<p class="text-center"><button class="btn btn-sm btn-dim btn-primary" onClick="DownloadFileExcel('${data.Guid}','${data.FileName}')"><em class="icon ni ni-download-cloud"></em>&nbsp;&nbsp;TẢI FILE EXCEL KẾT QUẢ</button></p>`
        bodyHtml = `
                ${btnTaiBangKe}
                ${ghiChu}
            `
        createModal(tenModal, tenChucNang, bodyHtml, btnHtml)
        showModal(tenModal);
    }
    else if (i == 3) {
        //loi khong tai duoc file
        btnTaiBangKe = ` <div class='alert alert-danger'>${data}</div>`;
        bodyHtml = `
                ${btnTaiBangKe}
                ${ghiChu}
            `
        createModal(tenModal, tenChucNang, bodyHtml, btnHtml)
        showModal(tenModal);
    }
    else {
        bodyHtml = `
                ${btnTaiBangKe}
                ${ghiChu}
            `
        createModal(tenModal, tenChucNang, bodyHtml, btnHtml)
        showModal(tenModal);
        let searchObj = prepareObject('dsp');
        $.ajax({
            type: "POST",
            dataType: "json",
            url: '/QLHD/TaiBangKe',
            data: searchObj,
            success: function (data) {
                console.log(data);
                if (data.status == 1) {
                    TaiBangKeTuTCT(2, data.obj);
                }
                else {
                    TaiBangKeTuTCT(3, data.message);

                }
            },
            error: function (jqXHR, textStatus, errorThrown) {
                hideModal(tenModal)
                console.log(textStatus);
                console.log(errorThrown);
                console.log(jqXHR);
            }
        });

    }


}
function ExportData(type) {

    if (type == "tonghop") {
        let bodyHtml = `
                    <b>Chọn loại file đầu ra:</b><br/>
                    <div class='row mt-2'>
                         <div class='col-12'>
                                <button type='button' onClick="ExportData('xml')" class='btn btn-sm btn-outline-primary' style='width:100%'>Kết xuất các hóa đơn ra XML và nén trong 1 file ZIP </button><br/>
                                <button type='button' onClick="ExportData('html')" class='btn btn-sm btn-outline-primary mt-2' style='width:100%'>Kết xuất các hóa đơn ra HTML và nén trong 1 file ZIP</button><br/>
                                <button type='button' onClick="ExportData('pdf')" class='btn btn-sm btn-outline-primary mt-2' style='width:100%'>Kết xuất các hóa đơn ra PDF và nén trong 1 file ZIP </button><br/>
                                <button type='button' onClick="ExportData('pdf2')" class='btn btn-sm btn-outline-danger mt-2' style='width:100%'>Kết xuất các hóa đơn thành 1 file PDF </button>
                        </div>
                    </div>
                    `
        let btnHtml = ``
        createModal("mWaitExport", "NIBOT - KẾT XUẤT FILE XML/HTML/PDF", bodyHtml, btnHtml)
        showModal("mWaitExport");
    }
    else if (type == 'xlsDetailTichHop' ) {
        OpenModalExcelSmart(11,"");
    }

    else if (type == 'xlsDetail' || type == 'BangKe') {
        OpenModalExcelSmart(1, type == 'BangKe');
    }

    else {
        //if (type == 'xml' && chkMH.option("value"))
        //    type = "xmlMH";
        if (type == 'xmlMH' || type == 'xml' || type == 'html' || type == 'pdf' || type == 'pdf2') {
            let bodyHtml = `
                    <div class = 'alert alert-primary text-center mt-1 mb-1'>
                        <div class="spinner-border " role="status">
                                <span class="visually-hidden"></span>
                        </div><br/>
                            Nibot đang kết xuất file cho bạn.<br/>
                            Vui lòng chờ trong giây lát!<br/>
                    </div>
                `
            let btnHtml = ``
            createModal("mWaitExport", "NIBOT - KẾT XUẤT FILE XML/HTML/PDF", bodyHtml, btnHtml)
            showModal("mWaitExport");
            Search(type);
        }
    }
}




function OpenModalExcelSmart(type, data) {
    let bodyHtml = '', btnHtml = '';
    if (type == 1) {
        bodyHtml = `
                <div class = 'alert alert-primary text-center mt-1 mb-1'>
                    <div class="spinner-border " role="status">
                            <span class="visually-hidden"></span>
                    </div><br/>
                        Nibot đang kiểm tra tính hợp lệ của hóa đơn để kết xuất dữ liệu.<br/>
                        Vui lòng chờ trong giây lát!<br/>
                </div>
            `
        beginTime = new Date();
        btnHtml = ``
        createModal("mExcelChiTiet", "Kết xuất Excel", bodyHtml, btnHtml)
        showModal("mExcelChiTiet");
        Search('xlsDetail', data);
    }
    else if (type == 11) {
        //ngayTichHop_KT là chuỗi yyyy-MM-dd Là ngày kết thúc tích hợp
        //lấy truoc1Thang = ngayTichHop_KT - 1 tháng
        //lấy sau1Thang = ngayTichHop_KT + 1 tháng
        let truoc1Thang = new Date(ngayKT_TichHop);
        truoc1Thang.setMonth(truoc1Thang.getMonth() - 1);
        let sau1Thang = new Date(ngayKT_TichHop);
        sau1Thang.setMonth(sau1Thang.getMonth() + 1);
        let ngayHienTai = new Date();


        if ((truoc1Thang <= ngayHienTai && sau1Thang >= ngayHienTai) ) {
            bodyHtml = `
                <div style="border-left: 5px solid #ff3b30; background: linear-gradient(to right, #fff1f0, #ffffff); padding: 16px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); border-radius: 0 4px 4px 0; text-align: left;">
                    <h5 style="color: #d81b60; margin: 0 0 10px 0; font-weight: 700;">⚠️ Thông báo hết hạn</h5>
                    <p style="font-size: 14px; margin: 0; line-height: 1.5;">
                        Chức năng tích hợp HĐ đầu ra - DolagoXD hết hạn sử dụng vào ngày <span style="color: #e53935; font-weight: bold;">${ngayKT_TichHop}</span>.<br/>
                        <span style="font-weight: 600;">Hãy gia hạn để tiếp tục sử dụng chức năng này.</span>
                    </p>
                </div>
            `
        }

        bodyHtml += `
                <div class = 'alert alert-primary text-center mt-1 mb-1'>
                    <div class="spinner-border " role="status">
                            <span class="visually-hidden"></span>
                    </div><br/>
                        Nibot đang kết xuất dữ liệu Bán ra từ Nhà cung cấp hóa đơn điện tử.<br/>
                        Vui lòng chờ trong giây lát!<br/>
                </div>
            `
        beginTime = new Date();
        btnHtml = ``
        createModal("mExcelChiTiet", "Kết xuất Excel", bodyHtml, btnHtml)
        showModal("mExcelChiTiet");
        Search('xlsDetailTichHop', false);
    }
    else if (type == 22) {
        var ret = data.obj;
        if (ret.status == 1) {
            let link = "/QLHD/DownloadDauRa/" + MST + "/" + ret.obj;
            bodyHtml = `
               <p class='text-center'><a class="btn btn-sm  btn-primary" href='${link}'><em class='icon ni ni-download-cloud'></em>&nbsp;&nbsp;TẢI FILE EXCEL KẾT QUẢ</a></p>
            `
            beginTime = new Date();
            btnHtml = ``
            createModal("mExcelChiTiet", "Kết xuất Excel", bodyHtml, btnHtml)
            showModal("mExcelChiTiet");
        }
        else {
            bodyHtml = `
                 <div class = 'alert alert-danger text-center mt-1 mb-1'>
                                ${ret.message}
                        </div>
            `
            beginTime = new Date();
            btnHtml = ``
            createModal("mExcelChiTiet", "Kết xuất Excel", bodyHtml, btnHtml)
            showModal("mExcelChiTiet");
        }
    
    }
    else if (type == 2) {
        if (data) {
            var pmkt = data.PhanMemKeToan;
            var isSmart = (pmkt == "SMART PRO");

            if (data.status == -1) {
                if (
                    data.message.indexOf(" thực hiện đồng bộ lại các hóa đơn sau") >= 0
                    ||
                    data.message.indexOf("Hóa đơn không có chi tiết hàng hóa dịch vụ") >= 0
                ) {
                    data.message = data.message + "<br/><br/><div class='alert alert-primary'><b>Hãy tắt thông báo. Bấm Tìm kiếm và thực hiện đồng bộ lại hóa đơn.</b</div>"
                }
                bodyHtml = `
                        <div class = 'alert alert-danger text-center mt-1 mb-1'>
                                ${data.message}
                        </div>
                    `
            }
            else {
                if (data.hasOwnProperty("Exception")) {
                    if (
                        data.Exception.indexOf(" thực hiện đồng bộ lại các hóa đơn sau") >= 0
                        ||
                        data.Exception.indexOf("Hóa đơn không có chi tiết hàng hóa dịch vụ") >= 0
                    ) {
                        data.Exception = data.Exception + "<br/><br/><div class='alert alert-primary'><b>Hãy tắt thông báo. Bấm Tìm kiếm và thực hiện đồng bộ lại hóa đơn.</b</div>"
                    }
                    bodyHtml = `
                            <div class = 'alert alert-danger text-center mt-1 mb-1'>
                                    ${data.Exception}
                            </div>
                        `
                }
                else {
                    bodyHtml = `<div class='fs-14px' style='line-height:25px'>`;
                    if (data.hasOwnProperty("TongQuat_HoaDon")) {
                        //bodyHtml += `<b class='text-mute'><em class="icon ni ni-check-thick"></em> Tổng số hóa đơn là: ${data.TongQuat_HoaDon}</b><br/>
                        //    <small><i>&nbsp;&nbsp* hóa đơn nằm ở Sheet HoaDon_TongQuat</i></small><br/>
                        //`
                        bodyHtml += `<b class='text-mute'><em class="icon ni ni-check-thick"></em> Tổng số hóa đơn là: ${data.TongQuat_HoaDon}</b>`
                    }
                    if (data.hasOwnProperty("OkCount") && data.OkCount>0) {

                        let ghiChuStr = ``;
                        if (isSmart && data.OkGhiChuCount > 0)
                            ghiChuStr = `, có <b class='text-danger'>${data.OkGhiChuCount}</b> dòng chi tiết hóa đơn được Nibot tự tính toán để thêm vào, xem thêm ở cột NIBOT_GHICHU`;

                        bodyHtml += `<br/><b class='text-primary'><em class="icon ni ni-done"></em> Tổng số hóa đơn hợp lệ là:<span style='font-size:20px'>${data.OkCount}</span></b><br/><small><i>&nbsp;&nbsp;* những hóa đơn hợp lệ nằm ở Sheet OK${ghiChuStr}</i></small>`

                    }
                    if (data.hasOwnProperty("NgCount") && data.NgCount>0) {

                        //bodyHtml+=``
                        if (isSmart) {
                            bodyHtml += `<br/><b class='text-danger'><em class="icon ni ni-cross-round"></em> Tổng số hóa đơn Cần Xem Xét là: <span style='font-size:20px'>${data.NgCount}</span></b>`
                            if (data.NgGhiChuCount>0) {
                                bodyHtml += `<div style = "margin-top:5px;background: #f4f4f4;padding: 5px 10px 5px 10px;border: 1px solid #3e5a7473;border-radius: 5px;" > <b style="font-size:12px;color:blue">Hóa đơn có <span style="font-size:16px;color:red">sai lệch về tiền hàng, tiền thuế...</span> Nhằm đảm bảo tính chính xác khi đưa dữ liệu vào PMKT, Bạn nên kiểm tra lại thông tin ở cột NIBOT_GHICHU trong sheet CAN_XEM_XET.</b></div >`
                            }
                        }
                        else {
                            bodyHtml += `<br/><b class='text-danger'><em class="icon ni ni-cross-round"></em> Tổng số hóa đơn Cần Xem Xét là: <span style='font-size:20px'>${data.NgCount}</span></b>`
                            if (data.NgGhiChuCount > 0) {
                                bodyHtml += `<div style = "margin-top:5px;background: #f4f4f4;padding: 5px 10px 5px 10px;border: 1px solid #3e5a7473;border-radius: 5px;" > <b style="font-size:12px;color:blue">Hóa đơn có <span style="font-size:16px;color:red">sai lệch về tiền hàng, tiền thuế...</span> Nhằm đảm bảo tính chính xác khi đưa dữ liệu vào PMKT, Bạn nên kiểm tra lại thông tin trong sheet NotGood.</b></div >`
                            }
                        }

                        //<div class='alert alert-danger'>
                        //bodyHtml += `</div>`

                    }


                    if ((data.hasOwnProperty("BangKe_MuaVao_SoDong_OK") && data.BangKe_MuaVao_SoDong_OK > 0) ||
                        (data.hasOwnProperty("BangKe_MuaVao_SoDong_KCT") && data.BangKe_MuaVao_SoDong_KCT > 0)) {
                        bodyHtml += `<br/><b style='color:#a70f92'><em class="icon ni ni-calc"></em> Bảng Kê Mua Vào </b></br>
                            <small>
                        `;
                        let sheetName = '';
                        if (data.BangKe_MuaVao_SoDong_OK > 0) {
                            bodyHtml += `   &nbsp;&nbsp;- Tổng Doanh Số Chưa Thuế: <b>${fmt(data.BangKe_MuaVao_DoanhThuChuaThue)}</b><br/>
                                            &nbsp;&nbsp;- Tổng Thuế Được Khấu Trừ: <b>${fmt(data.BangKe_MuaVao_Thue)}</b><br/>`;
                            sheetName = 'BangKe_MuaVao';
                        }

                        var hasKCT = false;
                        if (data.BangKe_MuaVao_SoDong_KCT > 0) {
                            hasKCT = true;
                            bodyHtml += `   &nbsp;&nbsp;- Tổng Doanh Số KCT: <b>${fmt(data.BangKe_MuaVao_DoanhThuKCT)}</b><br/>`;
                            bodyHtml += `   &nbsp;&nbsp;- Tổng Doanh Số HĐBH: <b>${fmt(data.BangKe_MuaVao_DoanhThuHoaDon2)}</b><br/>`;

                            if (sheetName != '') sheetName += ", ";
                            sheetName += 'BangKe_MuaVao_KCT';
                        }
                        if (data.BangKe_MuaVao_SoDong_KKKNT > 0) {
                            hasKCT = true;
                            bodyHtml += `   &nbsp;&nbsp;- Tổng Doanh Số KKKNT: <b>${fmt(data.BangKe_MuaVao_DoanhThuKKKNT)}</b><br/>`;
                            if (sheetName != '') sheetName += ", ";
                            sheetName += 'BangKe_MuaVao_KKKNT';
                        }
                        if (hasKCT) {
                            bodyHtml += `   &nbsp;&nbsp;- Tổng Doanh Số Chưa thuế trước Khấu trừ: <b>${fmt(parseFloat(data.BangKe_MuaVao_DoanhThuKKKNT)
                                + parseFloat(data.BangKe_MuaVao_DoanhThuKCT)
                                + parseFloat(data.BangKe_MuaVao_DoanhThuHoaDon2)
                                + parseFloat(data.BangKe_MuaVao_DoanhThuChuaThue))}</b><br/>`;
                        }

                        bodyHtml += `<i>&nbsp;&nbsp* thông tin chi tiết nằm ở ${sheetName}</i>
                            </small>
                            <br/>
                        `
                    }

                    if (data.hasOwnProperty("BangKe_BanRa_DoanhThuTruocThue") && data.hasOwnProperty("BangKe_BanRa_DoanhThuChiuThue") && data.hasOwnProperty("BangKe_BanRa_Thue")) {
                        bodyHtml += `<br/><b style='color:#006609'><em class="icon ni ni-calc"></em> Bảng Kê Bán Ra </b></br><small>
                            - Tổng Doanh Thu Trước Thuế: <b>${fmt(data.BangKe_BanRa_DoanhThuTruocThue)}</b><br/>
                            - Tổng Doanh Thu Chịu Thuế: <b>${fmt(data.BangKe_BanRa_DoanhThuChiuThue)}</b><br/>
                            - Tổng Thuế: <b>${fmt(data.BangKe_BanRa_Thue)}</b></small>
                        `
                    }

                    if (data.BangKe_BiLech == "1") {
                        bodyHtml += `<div style="margin-top:5px;background: #ededed;padding: 5px 10px 5px 10px;border: 1px solid #3e5a7473;border-radius: 5px;"><b style="font-size:12px;color: blue;">Bảng Kê và dữ liệu Tổng quát của hóa đơn có <span style="font-size:16px;color:red">sai lệch Tiền hàng, Tiền thuế. </span>Để Kê khai được chính xác, Bạn hãy kiểm tra số liệu ở cột Dữ liệu Bảng Kê ở Sheet HoaDon_TongQuat </b></div>`
                    }


                    if (data.BangKe_BiLech == "1" || data.NgCount>0) {
                        bodyHtml += `<div class='mt-2 text-dark'><b>GỌI <a href='tel:1900636507'>1900.63.65.07</a> hoặc tham gia <a href='https://t.me/+G3FYttDs6u81ZmI1' target='_blank'>nhóm Telegram của công ty</a> để được hỗ trợ thêm.</b></div>`
                    }


                    let tgian = ((new Date() - beginTime) / 1000);

                    //bodyHtml += `<br/><b style='color:#01545f'><em class="icon ni ni-clock"></em>Thời gian xử lý: </b> ${tgian} giây<br/>`
                    bodyHtml += `<br/><p class='text-center'><button class="btn btn-sm  btn-primary" onClick="DownloadFileExcel('${data.Guid}','${data.FileName}')"><em class='icon ni ni-download-cloud'></em>&nbsp;&nbsp;TẢI FILE EXCEL KẾT QUẢ</button></p><br/>
                    `
                    btnHtml = ``//createHelpLink("KET_XUAT");
                }


            }
            createModal("mExcelChiTiet", "Kết xuất Excel chi tiết", bodyHtml, btnHtml)
            showModal("mExcelChiTiet");
        }
    }
}
function DownloadFileExcel(Guid, FileName) {
    let a = document.createElement('a');
    a.href = "/QLHD/DownloadExcel/" + MST + "/" + Guid + "/" + FileName;
    a.click();
}

function prepareObject(type) {
    let lstID = [];

    if (datagrid && type != 'dsp') {
        let selected = datagrid.getSelectedRowsData();
        if (selected.length > 0) {
            for (let i in selected)
                lstID.push(selected[i].id);
        }
    }
    else if (datagrid) {
        datagrid.clearSelection();
    }

    var searchObj = {
        'TuNgay': toJP(dtTuNgay.option("value")),
        'DenNgay': toJP(dtDenNgay.option("value")),
        'MaSoThue': MST,
        'LoaiHD': cboLHD.option("value"),
        'TrangThaiHD': cboTTHD.option("value"),
        //'KyHieuMauSoHD': txtKHMSHD.option("value"),
        'KyHieuHD': txtKHHD.option("value"),
        'SoHD': txtSoHD.option("value"),
        'ThongTin': txtThongTin.option("value"),
        'TrangThaiDuyet': cboDuyet.option("value"),
        'KetQuaKiemTra': cboKetQuaKiemTra.option("value"),
        'Type': type,
        'LocFile': cboLocFile.option("value"),
        'CheckMaHang': "1",
        'LstId': lstID,
        'IsPdf': false

    };
    if (searchObj.Type == 'pdf2') {
        searchObj.Type = 'pdf';
        searchObj.IsPdf = true;
    }

    SEARCH_OBJ = searchObj;
    return searchObj;
}

function enabledCtrl(ctrl, status) {
    if (status) {

        $(ctrl).removeClass("disabled");
    }
    else {
        $(ctrl).addClass("disabled");
    }
}

var btnSearch = "#btnSearch";

function BoSungChiTiet(dt) {
    let DATA_FULL = [];
    for (let i = 0; i < dt.length; i++) {
        let r = dt[i];
        if (r.j) {
            let details = JSON.parse(r.j);
            if (!details["hdhhdvu"]) {
                let m = JSON.parse(JSON.stringify(r));
                DevExpress.ui.dialog.alert(`Hóa đơn ${toVnDateString(details.tdlap)} chưa đồng bộ đầy đủ<br/>Vui lòng đồng bộ lại trong ngày này`, "Thông báo")
                return [];
            }
            else {
                details = details.hdhhdvu;
                for (let i2 in details) {
                    let d = details[i2];
                    let m = JSON.parse(JSON.stringify(r));
                    m.DonGia = d.dgia ?? 0;
                    m.DVT = d.dvtinh ?? "";
                    m.id = d.id ?? "";
                    m.idhdon = d.idhdon ?? "";
                    m.LoaiThueSuat = d.ltsuat ?? "";
                    m.SoLuong = d.sluong ?? 0;
                    m.stbchu = d.stbchu ?? "";
                    m.TienChietKhau = d.stckhau ?? 0;
                    m.stt = d.stt ?? "";
                    m.sxep = d.sxep ?? "";
                    m.tchat = d.tchat ?? "";
                    m.TenHHDV = d.ten ?? "";
                    m.thtcthue = d.thtcthue ?? "";
                    m.ThanhTienChuaThue = d.thtien ?? 0;
                    m.tlckhau = d.tlckhau ?? "";
                    m.tsuat = d.tsuat ?? "";
                    m.tthue = d.tthue ?? "";
                    DATA_FULL.push(m);
                }
            }
        }
        else {
            dAlert(`Hóa đơn ${toVnDateString(r.ngay)} chưa đồng bộ đầy đủ<br/>Vui lòng đồng bộ lại trong ngày này`, "Thông báo")
            return [];
        }
    }

    return DATA_FULL;
}
var DATA_LOI = [];


function showHoaDonThieuJson(dt, type = "pdf") {
    console.log(dt)
    DATA_LOI = dt;
    let msg = "";
    let html = '';
    let c = 0;
    if (type == "pdf") {
        for (let k in DATA_LOI) {
            let hd = DATA_LOI[k];
            let t = "Ngày: " + toVn(new Date(hd.NgayLap)) + ": " + hd.Loai + "_" + hd.KyHieuHd + "_" + hd.SoHd;
            if (hd.MaSoThue2) t += "_" + hd.MaSoThue2;
            msg += t + "\n";
            c++;
        }
    }
    else if (type == "dsp") {
        for (let k in DATA_LOI) {
            let hd = DATA_LOI[k];
            DATA_LOI[k].Id = hd.id;
            let t = "Ngày: " + toVn(new Date(hd.ngay)) + ": " + hd.loai + "_" + hd.khhd + "_" + hd.so;
            if (hd.mst2) t += "_" + hd.mst2;
            msg += t + "\n";
            c++;
        }
    }
    html += `<textarea class='form-control text-start text-left' rows=5>${msg}</textarea>`
    let bodyHtml = `
                                            <div class = 'alert alert-danger  mt-1 mb-1'>
                                                Có <b>${c} hóa đơn</b> bị thiếu nội dung khi đồng bộ.<br/>
                                                Để đảm bảo cho việc tính toán và kết xuất, vui lòng kiểm tra các hóa đơn hoặc bấm nút đồng bộ lại ở bên dưới.
                                            </div>
                                                ${html}
                                            <div id='spinnerDongBo' class='text-center mt-2 d-none'>
                                                <div class="spinner-border " role="status">
                                                        <span class="visually-hidden"></span><br/>
                                                </div><br/>đang đồng bộ...
                                            </div>
                                            <div class='text-center'> 
                                                <button class='mt-2 btn btn-outline-primary btn-dim' id="btnDongBoLai">YES. Đồng bộ lại các hóa đơn bị thiếu.</button>
                                                <button class='mt-2 btn btn-outline-dark btn-dim'  id="btnDongCuaSo">NO. Tôi cần kiểm tra.</button>
                                            </div>
                                        `
    let btnHtml = '';
    createModal("mWaitExport", "NIBOT - CẢNH BÁO  THIẾU NỘI DUNG", bodyHtml, btnHtml)
    showModal("mWaitExport");

    $("#btnDongBoLai").unbind().on("click", function () {
        DongBoLai()
    });

    $("#btnDongCuaSo").unbind().on("click", function () {
        hideModal("mWaitExport");
    });

}

var dspInfo = "HideNgay";

var isDangXuLy = false;

function decompressBase64(base64String) {
    // Giải mã Base64 thành mảng byte (Uint8Array)
    let compressedData = Uint8Array.from(atob(base64String), c => c.charCodeAt(0));

    // Giải nén bằng Pako
    let decompressedData = pako.inflate(compressedData);

    // Chuyển đổi mảng byte về chuỗi
    let decoder = new TextDecoder('utf-8');
    let decompressedString = decoder.decode(decompressedData);

    return decompressedString;
}


function Search(type, isFullBangKe) {

    if (!isDangXuLy) {
        isDangXuLy = true;
        DATA_LOI = [];
        let searchObj = prepareObject(type);
        if (isFullBangKe) {
            searchObj.Type = 'xlsDetail';
            searchObj.IsFullBangKe = true;
        }

        if (!searchObj) return;
        let lhdval = cboLHD.option("value");
        if (lhdval.indexOf("MUA_VAO") >= 0)
            label = "bán";
        else if (lhdval.indexOf("BAN_RA") >= 0)
            label = "mua";
        else {
            label = "mua/bán";
        }
        if (type == 'dsp')
            enabledCtrl( btnSearch, false);

        $.ajax({
            type: "POST",
            dataType: "json",
            url: '/QLHD/TraCuu',
            data: searchObj,
            timeout: 600000,
            success: function (data) {

                enabledCtrl(btnSearch, true);
                if (type == 'xlsDetail') {
                    OpenModalExcelSmart('2', data.obj);
                }
                else if (type == 'xlsDetailTichHop') {
                    OpenModalExcelSmart('22', data);
                }
                else {
                    if (data.status == 1) {
                        if (type == 'dsp') {

                            dspInfo = data.message;
                            if (dspInfo.indexOf("ZString") >= 0) {
                                DATA = JSON.parse(decompressBase64(data.obj));
                            }
                            else {
                                DATA = data.obj;
                            }

                            dspData(type);
                            let t = DATA.filter(p => p.nj == true);
                            if (t.length > 0)
                                showHoaDonThieuJson(t, "dsp");
                            $("#thongKeHoaDon").html("alo")
                        }
                        else if (type == 'xml' || type == 'xmlMH') {
                            DownloadXml(data.obj, type);
                        }
                        else if (type == 'html' || type == 'pdf' || type == 'pdf2') {
                            let r = data.obj;
                            if (r.obj.length > 0) {
                                showHoaDonThieuJson(r.obj);
                            }
                            else {
                                DownloadXml(r.message, type);
                            }
                        }
                    }
                    else if (data.status < 1) {
                        DevExpress.ui.dialog.alert(data.message, "Thông báo");
                    }
                }
                isDangXuLy = false;
            },
            error: function (jqXHR, textStatus, errorThrown) {

                enabledCtrl(btnSearch, true);
                hideModal("mExcelChiTiet")
                hideModal("mWaitExport");
                goTohome(jqXHR.responseText);
                isDangXuLy = false;

            }
        });

    }
}
function DongBoLai() {
    if (DATA_LOI.length > 0) {
        let lstIdLoi = [];
        for (let i in DATA_LOI) {
            lstIdLoi.push(DATA_LOI[i].Id);
        }

        $("#spinnerDongBo").removeClass("d-none");
        $.ajax({
            type: "POST",
            dataType: "json",
            url: '/QLHD/DongBoLaiHoaDon/',
            data: {
                lstId: lstIdLoi,
                MaSoThue: MST,
                GuidGoi: GuidGoi,
            },
            success: function (data) {
                if (data.status == 1) {
                    dAlert("Đồng bộ xong. Hãy đóng cửa sổ và thực hiện chức năng cần dùng.", "Thông báo");
                }
                else {
                    dAlert(data.message, "Lỗi");
                }
                $("#spinnerDongBo").addClass("d-none");
            },
            error: function (jqXHR, textStatus, errorThrown) {
                dAlert("Lỗi khác!", "Thông báo");
                $("#spinnerDongBo").addClass("d-none");
                goTohome(jqXHR.responseText);

            }
        });
    }
}
function DownloadXml(fileName, type) {
    let T = "";
    if (type.indexOf("xml") >= 0) T = "XML.ZIP";
    else if (type.indexOf("html") >= 0) T = "HTML.ZIP";
    else if (type == "pdf") T = "PDF.ZIP";
    else if (type == "pdf2") T = "AIO.PDF"
    let href = "/QLHD/DownloadZipXML/" + MST + "/" + fileName;
    let bodyHtml = `
                <div class="fs-14px text-center" style="line-height:20px">
                    <p style="color:#a70f92"><b>NIBOT ĐÃ KẾT XUẤT ${T} XONG</b></p>
                    <a class="btn btn-sm btn-outline-danger"  href='${href}'><em class="icon ni ni-download-cloud"></em>&nbsp;&nbsp;TẢI FILE KẾT QUẢ</a>
                </div>
                `
    let btnHtml = ``
    createModal("mWaitExport", "NIBOT - KẾT XUẤT FILE XML/HTML/PDF", bodyHtml, btnHtml)
    showModal("mWaitExport");
}

function initCtrl() {
    $("#searchControl").html(`
                <div id="toolTip2">Chọn tất cả dòng trên lưới dữ liệu ở mọi trang</div>
                <div class="row gy-2 " >

                        <div class='col-sm-12 d-flex flex-sm-row flex-column justify-content-start '>
                            <div id="cboLHD" class='  me-1 mb-1' ></div>
                            <div id="cboLocFile" class=' me-1 mb-1' ></div>
                            <div id="cboDuyet" class=' me-1 mb-1' ></div>
                            <div id="cboTTHD" class='  me-1 mb-1'  ></div>
                            <div id="cboKetQuaKiemTra" class=' me-3 mb-1' ></div>
                            <div id="chkMH" class='ctrlWidth me-1 mb-1' ></div>
                            ${createHelpLink("TRA_CUU")}
                        </div>
                    
                        <div class='col-sm-12  d-flex flex-sm-row flex-column justify-content-start ' style='margin-top:0px'>
                            <div id="txtKHHD" class=' me-1 mb-1'></div>
                            <div id="txtSoHD" class=' me-1 mb-1'></div>
                            <div id="txtThongTin" class=' me-1 mb-1'></div>
                            <div id="cboQuy" class='  me-1 mb-1'></div>
                            <div id="dtTuNgay" class=' me-1 mb-1'></div>
                            <div id="dtDenNgay" class='  me-1 mb-1'></div>
                            <div id="txtNam" class='me-1  mb-1'></div> <span class='mt-1 text-muted'  id="lblNam">(năm làm việc)</span>
                        </div>
                    </div>
        
                </div>
        `);
    if (HetHanDolago) {
        var s = HetHanDolago.split('/');
        var s1 = s[0];
        var s2 = s[1] + "/" + s[2] + "/" + s[3];
        if (s1 > 0) s1 = 'sẽ ';
        else if (s1 <= 0) s1 = 'đã';
        $("#dlgHetHan").html(`
        <p style='font-size: 12px;color: #003483;'>	DOLAGO - Tải PDF gốc ${s1} hết hạn vào ngày <b>${s2}</b>. Zalo: <b>0988.988.814</b></p>
    `)
    }

    cboLocFile = $("#cboLocFile").dxSelectBox({
        dataSource: locFileDataSource,
        displayExpr: 'text',
        valueExpr: 'value',
        id: "selectLHD",
        value: locFileDataSource[0].value,
    }).dxSelectBox("instance");

    if (quyenPVHD == 'R') {
        lhdDataSource = lhdDataSource.filter(p => p.value.indexOf("BAN_RA") >= 0);
    }
    else if (quyenPVHD == 'V') {
        lhdDataSource = lhdDataSource.filter(p => p.value.indexOf("MUA_VAO") >= 0)
    }


    cboLHD = $("#cboLHD").dxSelectBox({
        dataSource: lhdDataSource,
        displayExpr: 'text',
        valueExpr: 'value',
        id: "selectLHD",
        value: lhdDataSource[0].value,

        onValueChanged(e) {
            if (e.value.indexOf("MUA_VAO") >= 0) {
                label = "bán"

            }
            else if (e.value.indexOf("BAN_RA") >= 0) {
                label = "mua";
            }
            else {
                label = "mua/bán"
            }
        },
    }).dxSelectBox("instance");

    txtThongTin = $("#txtThongTin").dxTextBox({
        placeholder: 'MST, tên DN, ghi chú',
        value: '',
        onValueChanged() {
            Search('dsp');
        }
    }).dxTextBox("instance");

    cboDuyet = $("#cboDuyet").dxSelectBox({
        dataSource: dsDuyetDatasource,
        displayExpr: 'text',
        valueExpr: 'value',
        value: '',
    }).dxSelectBox("instance");

    cboTTHD = $("#cboTTHD").dxSelectBox({
        dataSource: trangThaiDataSource,
        multiple: true,

        displayExpr: 'text',
        valueExpr: 'value',
        value: "",
    }).dxSelectBox("instance");


    stNam = new Date().getFullYear();

    txtNam = $("#txtNam").dxNumberBox({
        value: stNam,
        visible: false,
        step: 0,
        width: 60,
        onValueChanged(e) {
        /*    localStorage.setItem("stNamSearch", e.value);*/
            stNam = e.value;
            var x = KhoangNgay(cboQuy.option("value"), false, e.value);
            dtTuNgay.option("value", x.start);
            dtDenNgay.option("value", x.end);
        }
    }).dxNumberBox("instance");

    $("#txtNam .dx-texteditor-input").attr("style", "text-align:center");

    cboQuy = $("#cboQuy").dxSelectBox({
        placeholder: "chọn khoảng thời gian",
        //items: ["Hôm nay", "1 tuần", "Tuần này", "Tuần trước", "Tháng này", "Tháng trước", "Quý này", "Quý trước", "Quý 1", "Quý 2", "Quý 3", "Quý 4", "Năm này", "Năm trước"],
        items: ["Hôm nay", "Tháng này", "Tháng 1", "Tháng 2", "Tháng 3", "Tháng 4", "Tháng 5", "Tháng 6", "Tháng 7", "Tháng 8", "Tháng 9", "Tháng 10", "Tháng 11", "Tháng 12", "Quý 1", "Quý 2", "Quý 3", "Quý 4", "Năm này", "Năm trước"],
        width: 100,
        value: "",
        onValueChanged(e) {
            let val = e.value;
            if (val == "Hôm nay" || val == "1 tuần" || val == "Tuần này" || val == "Tháng này" || val == "Năm này" || val == "Năm trước") {
                txtNam.option("visible", false);
                $("#lblNam").addClass("d-none");
            }
            else {
                txtNam.option("visible", true);
                $("#lblNam").removeClass("d-none");
            }


            var x = KhoangNgay(e.value, false, stNam);
            dtTuNgay.option("value", x.start);
            dtDenNgay.option("value", x.end);
            Search('dsp');

        },
    }).dxSelectBox("instance");

    cboKetQuaKiemTra = $("#cboKetQuaKiemTra").dxSelectBox({
        dataSource: ketQuaKiemTraDataSource,
        displayExpr: 'text',
        valueExpr: 'value',
        value: ''
    }).dxSelectBox("instance");

    dtTuNgay = $("#dtTuNgay").dxDateBox({
        displayFormat: "dd/MM/yyyy",
        useMaskBehavior: true,
        width: 120,
    }).dxDateBox("instance");

    dtDenNgay = $("#dtDenNgay").dxDateBox({
        displayFormat: "dd/MM/yyyy",
        useMaskBehavior: true,
        width: 120,
    }).dxDateBox("instance");


    txtKHHD = $("#txtKHHD").dxTextBox({
        placeholder: 'Ký hiệu HĐ',
    }).dxTextBox("instance");

    txtSoHD = $("#txtSoHD").dxTextBox({
        placeholder: 'Số HĐ',
    }).dxTextBox("instance");

    cboQuy.option("value", "Tháng này")
    txtNam.option("visible", false);
    equalSize();

    //$("#toolTip").html("Xuất XML, Excel có cột Mã hàng là mã hàng trên NiBot")
    $("#toolTip2").html("Chọn tất cả dòng trên lưới dữ liệu ở mọi trang")


    toolTip2 = $('#toolTip2').dxTooltip({
        target: '#chkTatCa',
        showEvent: 'mouseenter',
        hideEvent: 'mouseleave',
        hideOnOutsideClick: false,
    });
    setTimeout(function () {
        let k = window.location.href;
        if (k.indexOf("#tab") >= 0) {
            var pattern = /#tab/i;
            var result = k.search(pattern);
            if (result > 0) {
                setTimeout(function () {
                    CURRENT_TAB = k.substr(result + 1);
                    var link = CURRENT_TAB.replace("tab", "link");
                    $("#nibotTab .nav-link").removeClass("active");
                    $("#nibotTab #" + link).addClass("active");
                    $("#tabContainter .tab-pane").removeClass("active");
                    $("#tabContainter #" + CURRENT_TAB).addClass("active");
                    goToTab();
                }, 0)
            }
        }

    }, 250)

}


var dataSource = [];
function fncTaiFile(type, mst, id, fileName) {
    var a = document.createElement('a');
    var url = `/QLHD/TaiFile/${type}/${mst}/${id}`;
    a.href = url;
    //a.download = fileName;
    document.body.append(a);
    a.click();
    a.remove();
    return;

}
function dspData(type) {
    var ttcolumns = ['tct', 'tt', 'tck', 'tp', 'ttt'];
    var TOTAL_COLUMNS = [];
    var COLUMNS = [];
    dataSource = [];
    mf = mFormat;


    COLUMNS = [
        {
            dataField: 'Id',
            caption: "Id",
            visible: false,
        },
    ];
    if (dspInfo.indexOf("ShowNgay") >= 0) {
        COLUMNS.push(
            {
                dataField: 'ntv',
                caption: "Ngày tải về",
                width: 65,
                dataType: "date",
                format: 'dd/MM/yy',
                headerCellTemplate: `<span data-toggle="tooltip" data-placement="top" title="Ngày NIBOT tải hóa đơn về. Do tính năng bắt đầu chạy từ ngày 19/4/23 nên những HĐ được tải từ ngày này trở về sau mới được ghi nhận giá trị Ngày tải về." class='text-pink '>Ngày<br/>tải về</span>`,
                allowEditing: false,
                allowHeaderFiltering: false,
            },
            {
                dataField: 'ncn',
                caption: "Ngày cập nhật",
                width: 70,
                dataType: "date",
                format: 'dd/MM/yy',
                headerCellTemplate: `<span class='text-danger' data-toggle="tooltip" data-placement="top" title="Ngày NIBOT phát hiện HĐ thay đổi trạng thái. Nếu không có sự thay đổi, cột này sẽ trống!" >Ngày<br/>cập nhật</span>`,
                allowEditing: false,
                allowHeaderFiltering: false,

            },

        )
    }
    if (label == "mua/bán") {
        COLUMNS.push(
            {
                dataField: 'loai',
                caption: "Loại HĐ",
                width: 100,
                headerCellTemplate: "Loại HĐ",
                allowEditing: false,
                lookup: {
                    dataSource: [
                        { "val": "MUA_VAO", "dsp": "V" },
                        { "val": "BAN_RA", "dsp": "R" },
                    ],
                    displayExpr: "dsp",
                    valueExpr: "val"
                },
                allowHeaderFiltering: false,

            },
            {
                dataField: 'mst2',
                caption: "MST",
                width: 80,
                headerCellTemplate: "MST",
                allowEditing: false,
                allowHeaderFiltering: false,

            },
            {
                dataField: 'dtpn2',
                caption: "Đối tượng Pháp nhân ",
                headerCellTemplate: "ĐTPN",
                allowEditing: false,
                allowHeaderFiltering: false,

            }
        );
    }
    else {
        COLUMNS.push(
            {
                dataField: 'mst2',
                caption: "MST người " + label,
                width: 80,
                headerCellTemplate: "MST<br/>người " + label,
                allowEditing: false,
                allowHeaderFiltering: false,

            },
            {
                dataField: 'dtpn2',
                caption: "Người " + label,
                headerCellTemplate: "Người " + label,
                allowEditing: false,
                allowHeaderFiltering: false,

            }
        );
    }

    COLUMNS.push(

      
        {
            dataField: 'ngay',
            caption: "Ngày",
            headerCellTemplate: "Ngày",
            dataType: "date",
            allowEditing: false,
            width: 70,
            format: 'dd/MM/yy',
            allowHeaderFiltering: false,
            sortIndex: 0,
            sortOrder: "asc" 

        },
        {
            dataField: 'khhd',
            caption: "Ký hiệu",
            allowEditing: false,
            width: 70,
            headerCellTemplate: "Ký hiệu<br/>HĐ",
            allowHeaderFiltering: false,

        },

        {
            dataField: 'so',
            caption: "Số",
            allowEditing: false,
            dataType: "number",
            headerCellTemplate: "Số<br/>HĐ",
            allowHeaderFiltering: false,
            sortIndex: 1,
            sortOrder: "asc" 
        },

    
        {
            dataField: 'tct',
            caption: "Tiền Chưa thuế",
            allowEditing: false,
            wordWrapEnabled: false,
            autoWidth: true,
            headerCellTemplate: "Tiền<br/>C.Thuế",
            format: mf,
            allowHeaderFiltering: false

        },
        {
            dataField: 'tt',
            caption: "Tiền Thuế",
            headerCellTemplate: "Tiền<br/>Thuế",
            wordWrapEnabled: false,
            autoWidth: true,
            format: mf,
            allowEditing: false,
            allowHeaderFiltering: false

        },
        {
            dataField: 'tck',
            caption: "Tiền Chiết khấu TM",
            headerCellTemplate: "Tiền<br/>CK.TM",
            wordWrapEnabled: false,
            format: mf,
            autoWidth: true,
            allowEditing: false,
            allowHeaderFiltering: false

        },
        {
            dataField: 'tp',
            caption: "Tiền Phí",
            headerCellTemplate: "Tiền<br/>phí",
            format: mf,
            autoWidth: true,
            wordWrapEnabled: false,
            allowEditing: false,
            allowHeaderFiltering: false

        },
        {
            dataField: 'ttt',
            caption: "Tiền Thanh toán",
            headerCellTemplate: "Tiền<br/>T.Toán",
            format: mf,
            autoWidth: true,
          //      fixed: true,
            fixedPosition: 'right',
            allowEditing: false,
            allowHeaderFiltering: false

        },

        {
            dataField: 'tthhd',
            //wordWrapEnabled: true,
            caption: "Trạng thái HĐ",
            allowEditing: false,
            width: 60,
            headerCellTemplate: "T.thái<br/>HĐ",
            lookup: {

                dataSource: trangThaiDataSource,
                valueExpr: 'value',
                displayExpr: 'text'
            },
            allowHeaderFiltering: false,

        },
        {
            dataField: 'kqhd',
            caption: "Kết quả kiểm tra",
            allowEditing: false,
            width: 90,
            headerCellTemplate: "Kết quả<br/>k.tra",
            lookup: {
                dataSource: ketQuaKiemTraDataSource,
                valueExpr: 'value',
                displayExpr: 'text'
            },
            allowHeaderFiltering: false

        },

        {
            id: "cboDuyetNB",
            dataField: 'thaid',
            caption: "Duyệt nội bộ",
            width: 90,
            headerCellTemplate: "Duyệt<br/>Nội Bộ",
            fixed: true,
            allowEditing: true,
            fixedPosition: 'right',
            lookup: {
                dataSource: dsDuyetGrid,
                valueExpr: 'value',
                displayExpr: 'text',

            },
            allowHeaderFiltering: false

        },

        {
            dataField: 'dv',
            caption: "HĐ<br/>DV",
            width: 45,
            headerCellTemplate: "HĐ<br/>DV",
            fixed: true,
            allowEditing: true,
            type: 'bool',
            fixedPosition: 'right',
            allowHeaderFiltering: false

        },
    );

    if (dspInfo.indexOf("ShowMH") >= 0) {
        COLUMNS.push({
            dataField: "mh",
            caption: "Mặt hàng",
            allowEditing: false,
            type: 'text',
            fixed: true,
            fixedPosition: 'right',
            allowHeaderFiltering: true
        },);
    }
    COLUMNS.push(
        {
            dataField: "gc",
            caption: "Ghi chú",
            headerCellTemplate:'Ghi chú<br/><i><small style="color:darkgreen">cho hóa đơn ở đây!</small></i>',
            width: 200,
            allowEditing: true,
            type: 'text',
            fixed: true,
            fixedPosition: 'right',
            allowHeaderFiltering: true
        },
    );
    var x = $(window).width();

    if (x < 1360) {
        COLUMNS.filter(p => p.dataField == "dtpn2")[0].width = 250;
        COLUMNS.filter(p => p.dataField == "so")[0].width = 50;
        //COLUMNS.filter(p => p.dataField == "tct")[0].width = 60;
        //COLUMNS.filter(p => p.dataField == "tt")[0].width = 50;
        //COLUMNS.filter(p => p.dataField == "tp")[0].width = 40;
        //COLUMNS.filter(p => p.dataField == "tck")[0].width = 50;
        COLUMNS.filter(p => p.dataField == "gc")[0].width = 150;

        if (dspInfo.indexOf("ShowMH") >= 0) {
            var x = COLUMNS.filter(p => p.dataField == "mh");
            if (x.length == 1) x[0].width = 250;
        }
    }
    else if (x < 1600) {
        COLUMNS.filter(p => p.dataField == "dtpn2")[0].width = 400;

        if (dspInfo.indexOf("ShowMH") >= 0) {
            var x = COLUMNS.filter(p => p.dataField == "mh");
            if (x.length == 1) x[0].width = 200;
        }
    }

    var target = "";

    if (type == "dsp") {
        target = "#dg";
        TOTAL_COLUMNS.push({
            column: 'mst2',
            summaryType: "count",
            displayFormat: '{0} HĐ',
        });

        for (var idx in ttcolumns) {
            TOTAL_COLUMNS.push({
                column: ttcolumns[idx],
                summaryType: "sum",
                valueFormat: mf,
                displayFormat: '{0}',
            });
        }

        dataSource = DATA;

        COLUMNS.push(
            {
                fixed: true,
                fixedPosition: 'right',
                caption: "Chi tiết",
                width: 85,
                allowExporting: false,
                cellTemplate: function (c, o) {

                    if (o.rowType == "data") {
                        let html = '';
                        let d = o.data;
                        let tColor = "";

                        if (d.xmlId) {
                            tColor = d.xmlId.indexOf("nd") == 0 ? "text-primary ndBtn" : "text-danger ndBtnUser";
                            html += `<a href="/Download/XML/${d.xmlId}"  class=' ${tColor}'>XML</a>`
                        }

                        tColor = d.pdfId ? "text-danger ndBtnUser" : "text-primary ndBtn";
                        let pdf = d.pdfId ? d.pdfId : d.id;
                        let fileName = d.loai + "_" + d.khhd + "_" + d.so;
                        if (d.mst2) fileName += "_" + d.mst2;
                        fileName += ".pdf";
                        if (d.pdfId)
                            html += ` <a href="/Download/PDF/${pdf}"  class='${tColor}'>PDF</a>`
                        else
                            html += ` <a onClick = 'fncTaiFile("pdf","${MST}","${pdf}","${fileName}")' href="javascript:void(0)"  class='${tColor}'>PDF</a>`

                        html += ` <a href="/ChiTietHoaDon/${MST}/${d.id}" target='_blank'><em class='ndBtn icon ni ni-row-view'></em></a>`
                        $(html).appendTo(c);

                    }
                }
            },


        )
    }
    datagrid = $(target).dxDataGrid({
        dataSource: dataSource,
        repaintChangesOnly: true,
        loadPanel: {
            enabled: false // or false | "auto"
        },
        showBorders: true,
        columnAutoWidth: true,
        selection: {
            mode: isSelection ? 'multiple' : 'none',
            selectAllMode: 'page',//allPages,
        },
        headerFilter: { visible: true },
        scrolling: {
            useNative: true,
        },
        export: {
            enabled: false,
        },
        sorting: {
            mode: "multiple"
        },
        onRowPrepared(e) {
            if (type == "dsp") {
                if (e.rowType === "data") {
                    if (e.data.tthhd != "1" || e.data.kqhd == "0" || e.data.kqhd == "2" || e.data.kqhd == "4") {
                        $(e.rowElement).attr("style", "background:#f7e54f61;font-weight:bold;color:red");
                    }
                }
            }
        },
        onToolbarPreparing: function (e) {
            e.toolbarOptions.items.unshift({
                location: "before",
                widget: "dxCheckBox",
                options: {
                    icon: "check",
                    text: "chọn dòng",
                    elementAttr: {
                        style: "margin-right:20px"
                    },
                    value: isSelection,
                    onValueChanged: function (e) {
                        setCfg("isSelection", e.value);
                        let val = e.value ? "multiple" : "none";
                        datagrid.option("selection.mode", val);
                        $("#chkTatCa").dxCheckBox("instance").option("visible", e.value);

                    }
                },
            }, {
                location: "before",
                widget: "dxCheckBox",
                options: {
                    icon: "check",
                    text: "chọn tất cả",
                    elementAttr: {
                        style: "margin-right:20px",
                        id: "chkTatCa"
                    },
                    visible: isSelection,
                    onValueChanged: function (e) {
                        if (e.value) {
                            datagrid.option("selection.selectAllMode", "allPages");
                            datagrid.selectAll();
                        }
                        else {
                            datagrid.option("selection.selectAllMode", "page");
                            datagrid.selectRows([])
                        }
                    }
                },
            });
        },

        onSaving(e, i) {
            if (type == 'dsp') {
                let changes = e.changes;
                e.promise = true;
                if (changes.length > 0) {
                    let allData = [];
                    for (let k in changes) {
                        let dataChanges = (changes[k].data);
                        let dataOrgs = JSON.parse(JSON.stringify(changes[k].key));
                        for (let key in dataChanges) {
                            allData.push({
                                'Id': dataOrgs.id,
                                'TrangThaiDuyet': dataChanges.thaid ?? dataOrgs.thaid,
                                'TrangThaiDuyetGoc': dataOrgs.thaid,
                                'HoaDonDichVu': dataChanges.dv ?? dataOrgs.dv,
                                'HoaDonDichVuGoc': dataOrgs.dv,
                                'GhiChu': dataChanges.gc ?? dataOrgs.gc,
                                'GhiChuGoc': dataOrgs.gc,
                                'MaSoThue': MST
                            })
                        }
                    }
                    $.ajax({
                        type: "POST",
                        dataType: "json",
                        url: '/QLHD/ChangeTrangThaiDuyet',
                        data: {
                            lstHD: allData
                        },
                        success: function (data) {
                            if (data.status == -1) {
                                DevExpress.ui.dialog.alert(data.message, "LỖI CẬP NHẬT");
                            }
                            else {

                                console.log(data.message);
                            }
                        },
                        error: function (jqXHR, textStatus, errorThrown) {
                            goTohome(jqXHR.responseText);
                        }
                    });
                }
                else {
                    e.cancel = true;
                    $("#dg .dx-icon-edit-button-cancel").click();
                    e.promise = null;
                }
            }

        },
        height: 100,
        wordWrapEnabled: true,
        allowColumnReordering: true,
        rowAlternationEnabled: true,
        showBorders: true,
        filterRow: {
            visible: true,
        },
      
        showColumnLines: true,
        showRowLines: true,
        rowAlternationEnabled: true,
        noDataText: "Không có dữ liệu",
        pager: {
            showPageSizeSelector: true,
            allowedPageSizes: [10, 20, 50, 100],
            showNavigationButtons: true,
            showInfo: true,
            infoText: " Tổng cộng: {2} hoá đơn - Trang {0}/{1}"
        },
        columnFixing: {
            enabled: true
        },
        summary: {
            totalItems: TOTAL_COLUMNS
        },
        editing: {
            allowUpdating: true,
            mode: 'batch',
        },
        columns: COLUMNS,

    }).dxDataGrid("instance");
   
    //$("#gridContainer").on("click", ".dx-datagrid-summary-item", function () {
    //    if ($(this).text().includes("Tổng:")) {
    //        let valueToCopy = total.toString().replace(/[^\d]/g, ''); // Lấy số nguyên để copy
    //        navigator.clipboard.writeText(valueToCopy).then(() => {
    //            showCopyHint($(this));
    //        }).catch(err => {
    //            console.error("Failed to copy: ", err);
    //        });
    //    }
    //});

    change_grid_height();
    setTimeout(function () {
        $(".dx-datagrid-summary-item").css("cursor", "pointer");
        $(".dx-datagrid-summary-item").unbind().on("click", function () {

            let valueToCopy =  $(this).text().replaceAll(",", "");
            navigator.clipboard.writeText(valueToCopy).then(() => {
                showCopyHint($(this));
            }).catch(err => {
                console.error("Failed to copy: ", err);
            });

        })
    }, 150);
   
   
}
function showCopyHint(element) {
    let hint = $("<span>")
        .text("Đã copy")
        .css({
            position: "absolute",
            background: "linear-gradient(to right, #2c3e50, #1a252f)", 
            color:"white",
            padding: "4px 8px",
            fontSize: "12px",
            borderRadius: "12px",
            boxShadow: "0 2px 4px rgba(0, 0, 0, 0.2)", 
            zIndex: 1000
        });

    let offset = element.offset();
    let hintWidth = hint.outerWidth();
    let elementWidth = element.outerWidth();

    hint.css({
        top: offset.top + "px",
        left: offset.left + elementWidth + 5 + "px"
    });
    $("body").append(hint);

    setTimeout(() => {
        hint.fadeOut(400, function () {
            hint.remove(); // Xóa hint sau khi fade out
        });
    }, 100);
}
function exportFncKhongHopLe(e) {
    let loai = cboLHD.option("value").indexOf("MUA") >= 0 ? "Mua vào" : "Bán ra";
    let tuNgay = toJP(dtTuNgay.option("value"));
    let denNgay = toJP(dtDenNgay.option("value"));

    let sheet = "NIBOT - Hóa đơn " + loai + " cần xem xét - " + MST + " - " + tuNgay + " - " + denNgay;
    let fileName = sheet + ".xlsx";
    var workbook = new ExcelJS.Workbook();
    var worksheet = workbook.addWorksheet("HoaDonCanXemXet");
    var startRow = 4;

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

            //tất cả các cell đều phải wraptext;
            if (gridCell.rowType = 'data') {
                if (gridCell.column.dataField == "KetQua") {
                    if (excelCell.value && excelCell.value.indexOf("<b>") >= 0) {
                        excelCell.value = excelCell.value.replaceAll("<b>", "").replaceAll("</b>", "");
                    }
                }
                if (gridCell.column.dataField == "IdHd") {
                    let val = excelCell.value;
                    if (val) {
                        excelCell.value = {
                            text: 'Click để Xem',
                            hyperlink: val,
                            tooltip: val,
                        };
                    }
                }
            }

            if (excelCell.col > 0) {

                if (gridCell.column.dataField == "IdHd") {
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
                else {
                    Object.assign(excelCell, {
                        alignment: { wrapText: true },
                        border: {
                            top: { style: 'thin' },
                            left: { style: 'thin' },
                            bottom: { style: 'thin' },
                            right: { style: 'thin' }
                        }
                    });
                }

            }



        }
    }).then(function () {
        var title = sheet;
        worksheet.getCell('A1').value = title;
        let titleCell = worksheet.getCell('A1')
        Object.assign(titleCell, {
            font: {
                bold: true, size: 18,
            },
            alignment: {
                vertical: "middle",
                horizontal: "center",
                wrapText: true
            },
            //fill: { type: 'pattern', pattern: 'solid', fgColor: { argb: 'ffebcc' } }
        });
        worksheet.mergeCells('A1', 'G1');

        worksheet.getCell('A2').value = 'Chú ý: khi nhấn Click để xem bạn phải đang đăng nhập vào tài khoản Nibot tương ứng';

        let titleCell2 = worksheet.getCell('A2');
        Object.assign(titleCell2, {
            font: {
                italic: true, size: 12,
            },
            alignment: {
                vertical: "middle",
                horizontal: "center",
                wrapText: true
            },
        });
        //fil

        worksheet.mergeCells('A2', 'F2');

        let columnsWidth = [
            13, //ngay
            50,
            13, //mauso
            13, //kyhieu
            13, //kyhieu
            80, //so
            13, //mst
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
function KiemTraTinhHopLeHD() {
    var LstId = [];

    if (isSelection) {
        var rows = datagrid.getSelectedRowsData();
        for (let i in rows) {
            LstId.push(rows[i].id);
        }
    }

    if (LstId.length == 0) {
        var rows = dataSource;
        for (let i in rows) {
            LstId.push(rows[i].id);
        }
    }
    let bodyHtml = '';
    let btnHtml = ``;
    let tieude = "Kiểm tra thông tin của HĐ (ngày lập, ngày cấp, ngày ký, CKS)";
    if (LstId.length == 0) {
        bodyHtml = `
                <div class = 'alert alert-danger text-center' >
                    <div class='mt-2'>
                        Không có dữ liệu để kiểm tra
                    </div>
                </div>
            `;
        btnHtml = ``;
        createModal("mKiemTraTinhHopLe", tieude, bodyHtml, btnHtml);
        showModal("mKiemTraTinhHopLe");
        return;
    }

    bodyHtml = `
            <div class = 'alert alert-primary text-center' >
                <div class="spinner-border " role="status">
                    <span class="visually-hidden">đang kiểm tra...</span>
                </div>
                <div class='mt-2'>
                    Loại hóa đơn: <b>${cboLHD.option("value").indexOf("MUA") >= 0 ? "MUA VÀO" : "BÁN RA"}</b> / Số lượng hóa đơn kiểm tra: <b>${LstId.length}</b> 
                </div>
            </div>
        `;
    btnHtml = ``;
    createModal("mKiemTraTinhHopLe", tieude, bodyHtml, btnHtml);
    showModal("mKiemTraTinhHopLe");
    $.ajax({
        type: "POST",
        dataType: "json",
        url: '/QLHD/KiemTraTinhHopLeHD',
        data: {
            'MaSoThue': MST,
            "LstId": LstId,
        },
        success: function (data) {
            if (data.status == 1) {
                if (data.obj.length == 0) {
                    let c = fmt(LstId.length);
                    bodyHtml = `
                            <p style='font-size:16pt'>
                                    <em class="icon ni ni-check-circle-cut"></em> Kiểm tra ngày cấp, ngày ký, chữ ký số - Hợp lệ: <b>${c}/${c}</b>  hóa đơn.
                            </p>
                        `
                    createModal("mKiemTraTinhHopLe", tieude, bodyHtml, btnHtml);
                    showModal("mKiemTraTinhHopLe");
                }
                else {
                    let retData = data.obj;
                    for (let i in retData) {
                        retData[i].IdHd = '/ChiTietHoaDon/' + MST + '/' + retData[i].IdHd
                    }
                    let khongHopLe = retData.length;
                    let hopLeCount = LstId.length - khongHopLe;
                    let cTong = fmt(LstId.length);
                    let cOk = fmt(hopLeCount);
                    let cNg = fmt(khongHopLe);

                    bodyHtml = `<p style='font-size:12pt' class='text-danger'>
                                        <em class="icon ni ni-cross-round"></em> Cần xem xét: <b>${cNg}/${cTong}</b>  hóa đơn.
                                    </p>
                                
                                    <div id='dgCanXemXet' class='datagrid'></div>
                        `
                    createModal("mKiemTraTinhHopLe", tieude, bodyHtml, btnHtml);
                    showModal("mKiemTraTinhHopLe");
                    $(".modal-dialog").addClass("modal-lg")
                    //console.log(retData);
                    setTimeout(function () {
                        $("#dgCanXemXet").dxDataGrid({
                            dataSource: retData,
                            repaintChangesOnly: true,
                            loadPanel: {
                                enabled: true // or false | "auto"
                            },
                            scrolling: {
                                useNative: false,
                            },

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
                            export: {
                                enabled: true
                            },
                            summary: {
                                totalItems: [
                                    {
                                        column: 'MaSoThue',
                                        summaryType: "count",
                                        displayFormat: '{0} HĐ',
                                    }

                                ]
                            },
                            onExporting: function (e) {
                                e.cancel = true;
                                var i = exportFncKhongHopLe(e);
                                if (i == 1)
                                    e.cancel = false;
                            },
                            columns: [
                                { dataField: "MaSoThue", caption: "MST" },
                                { dataField: "TenDoanhNghiep", caption: "Tên doanh nghiệp", width: 300 },
                                { dataField: "SoHd", caption: "Số HĐ" },
                                { dataField: "KyHieuHd", caption: "KHHĐ" },
                                //{ dataField: "KyHieuMauSo", caption: "MST" },
                                { dataField: "NgayLap", caption: "Ngày" },
                                {
                                    dataField: "KetQua", caption: "Kết quả kiểm tra",
                                    cellTemplate: function (c, e) {
                                        if (e.rowType == 'data') {
                                            console.log(e.value);
                                            let x = "<div>" + e.value + "</div>";
                                            $(x).appendTo(c);
                                        }
                                    }
                                },
                                {
                                    dataField: "IdHd", caption: "Xem",
                                    cellTemplate: function (c, e) {
                                        if (e.rowType == 'data') {
                                            let x = "<a href='" + e.value + "' target='_blank' >Xem</a>";
                                            $(x).appendTo(c);
                                        }
                                    }
                                },
                            ]
                        });
                    }, 200);
                }
            }
            else {
                bodyHtml = `
                        <div class = 'alert alert-danger text-center' >
                            <div class='mt-2'>
                                ${data.obj}
                            </div>
                        </div>
                    `;
                createModal("mKiemTraTinhHopLe",tieude, bodyHtml, btnHtml);
                showModal("mKiemTraTinhHopLe");
            }

        },
        error: function (jqXHR, textStatus, errorThrown) {
            goTohome(jqXHR.responseText);
        }
    });


}
var CAU_HINH;

function updateCauHinh() {
    $.ajax({
        type: "POST",
        dataType: "json",
        url: '/QLHD/CapNhatCauHinhKetXuat/',
        data: {
            MaSoThue: MST,
            CauHinh: CAU_HINH
        },
        success: function (data) {
            if (data.status != 1) { dAlert(data.message); return; }
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR);
        }
    });

}
function CauHinh() {
    $.ajax({
        type: "GET",
        dataType: "json",
        url: '/QLHD/LoaCauHinhKetXuat/' + MST,
        success: function (data) {
            if (data.status != 1) { dAlert(data.message); return; }
            CAU_HINH = data.obj;
            for (let i in CAU_HINH.lstCotDienGiai) {
                if (CAU_HINH.lstCotDienGiai[i].CotDienGiai == null) {
                    CAU_HINH.lstCotDienGiai[i].CotDienGiai = "";
                }
                if (CAU_HINH.lstCotDienGiai[i].BoSungTruoc == null) {
                    CAU_HINH.lstCotDienGiai[i].BoSungTruoc = "";
                }
            }
            let bodyHtml = `   
                    <div class="row align-center"> 
                        <div class='col-7'>
                            <div class='row'>
                                <div class='col-12'>
                                    <div id="cboPhanMem"  ></div>
                                    <span class="form-note text-dark mt-2">&nbsp;&nbsp;* dữ liệu HĐ sẽ được kết xuất ra định dạng của phần mềm được chọn.</span>
                                </div>
                                <div class='col-12  mt-2'>
                                     <div id="cboHienThiMatHang" ></div>
                                     <span class="form-note text-dark mt-2">&nbsp;&nbsp;  * hiển thị/ẩn cột mặt hàng khi xuất Bảng kê.</span>
                                </div>
                                <div class='col-12 mt-2'>
                                    <div id="chkQuanLyLoHanDung" style='font-weight:bold;color:#6710ab'></div>
                                    <span class="form-note text-danger fw-bold mt-1">&nbsp;&nbsp;  [CHỈ DÀNH RIÊNG CHO KHÁCH ĐANG SỬ DỤNG DỊCH VỤ MỞ RỘNG DOLAGO]<br/>&nbsp;&nbsp;&nbsp;Tính năng đang phát triển. Nếu có đóng góp, liên hệ trực tiếp 0988.988.814 (LONG).</span>
                                </div>
                                <hr/>
                                <div class='col-6 mt-2'>
                                    <div id="chkLaHoKinhDoanh" style='font-weight:bold;color:#0d605b'></div><br/>
                                    <div id="chkHienThiNgayCNTV" style='font-weight:bold;color:#0e1574;margin-top:10px'></div><br/>
                                    <div id="chkHienThiMatHangDauTien" style='font-weight:bold;color:#055c7c;margin-top:10px'></div>

                                </div>
                                 <div class='col-6 mt-2'>
                                    <div id="chkBoSungTenNguoiMuaMayTinhTien" style='font-weight:bold;color:#b805ff'></div><br/>
                                    <span class="form-note text-danger fw-bold mt-1">&nbsp;&nbsp; (chú ý: cây xăng, nhà hàng không nên chọn)</span>

                                   
                                </div>
                                 
                            </div>
                        </div>
                        <div class='col-5' style='margin-top:-35px'>
                            <div class='row'>
                                <div class='col-12'>
                                    <b>Tùy chọn nội dung cho cột diễn giải khi xuất dữ liệu ra Excel</b>
                                    <div id='dgCotDienGiai' class='mt-2 datagrid'>
                                </div>
                            </div>
                        </div>
                    </div>                
                `;
            let btnHtml = '';
            createModal("mCauHinh", "CẤU HÌNH KẾT XUẤT", bodyHtml, btnHtml);
            showModal("mCauHinh");

            $("#cboPhanMem").dxSelectBox({
                dataSource: dsPhanMemKeToan,
                value: CAU_HINH.PhanMemKeToan,
                label: "Phần mềm kế toán",
                onValueChanged(e) {
                    CAU_HINH.PhanMemKeToan = e.value;
                    updateCauHinh();
                }
            }).dxSelectBox("instance")

            $("#cboHienThiMatHang").dxSelectBox({
                dataSource: [
                    { "key": "0", "dsp": "Không hiện hàng hóa trên bảng kê" },
                    { "key": "1", "dsp": "Hiện hàng hóa đầu tiên" },
                    { "key": "2", "dsp": "Hiện tất cả hàng hóa trên 1 dòng" },
                    //   { "key": "N", "dsp": "Hiện tất cả hàng hóa trên nhiều dòng" },
                ],
                displayExpr: "dsp",
                valueExpr: "key",
                value: CAU_HINH.MatHangBangKe,
                label: "Hiện/Ẩn mặt hàng trên Bảng kê",
                onValueChanged(e) {
                    CAU_HINH.MatHangBangKe = e.value;
                    updateCauHinh();
                }
            }).dxSelectBox("instance");

            $("#chkLaHoKinhDoanh").dxCheckBox({
                value: CAU_HINH.LaHoKinhDoanh,
                text: "Là HĐ đầu vào của Hộ KD",
                onValueChanged(e) {
                    CAU_HINH.LaHoKinhDoanh = e.value;
                    updateCauHinh();
                }
            }).dxCheckBox("instance");

            $("#chkBoSungTenNguoiMuaMayTinhTien").dxCheckBox({
                value: CAU_HINH.BoSungTenNguoiMuaMayTinhTien,
                text: "Bổ sung tên người mua ở HĐ Đầu Ra-MTT",
                onValueChanged(e) {
                    CAU_HINH.BoSungTenNguoiMuaMayTinhTien = e.value;
                    updateCauHinh();
                }
            }).dxCheckBox("instance");

            $("#chkHienThiNgayCNTV").dxCheckBox({
                value: CAU_HINH.HienThiNgayCNTV,
                text: "Hiển thị/ẩn ngày cập nhật, ngày tải về",
                onValueChanged(e) {
                    CAU_HINH.HienThiNgayCNTV = e.value;
                    updateCauHinh();
                    setTimeout(function () {
                        Search('dsp')

                    }, 200)
                }
            }).dxCheckBox("instance");

            $("#chkHienThiMatHangDauTien").dxCheckBox({
                value: CAU_HINH.HienThiMatHangDauTien,
                text: "Hiển thị/ẩn mặt hàng đầu tiên của hóa đơn",
                onValueChanged(e) {
                    CAU_HINH.HienThiMatHangDauTien = e.value;
                    updateCauHinh();
                    setTimeout(function () {
                        Search('dsp')

                    }, 200)
                }
            }).dxCheckBox("instance");
            $("#chkQuanLyLoHanDung").dxCheckBox({
                value: CAU_HINH.QuanLyLoHanDung,
                text: "Quản lý số lô, hạn dùng (dược phẩm)",
                onValueChanged(e) {
                    CAU_HINH.QuanLyLoHanDung = e.value;
                    updateCauHinh();
                   
                }
            }).dxCheckBox("instance");



            $("#dgCotDienGiai").dxDataGrid({
                dataSource: CAU_HINH.lstCotDienGiai,
                columns: [
                    { dataField: "LoaiChungTu", caption: "Loại CT", width: 75 },
                    { dataField: "BoSungTruoc", headerCellTemplate: "Cụm từ Bổ sung<br/>phía trước", width: 110, },
                    {
                        dataField: "CotDienGiai", headerCellTemplate: "Cột<br/>Diễn giải",
                        lookup: {
                            dataSource: dsTuyChonDienGiai,
                            valueExpr: 'value',
                            displayExpr: 'text',
                        },
                        allowEditing: true,
                    },
                ],
                editing: {
                    allowUpdating: true,
                    mode: 'cell',
                },
                onRowUpdated(e) {
                    updateCauHinh();
                },

                rowAlternationEnabled: true,
                showBorders: true,
                showColumnLines: true,
                showRowLines: true,
                rowAlternationEnabled: true,
                columnAutoWidth: true,
            });

        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR);
        }
    });


}

function DuyetHangLoat() {

    if (datagrid) {
        var rows = datagrid.getSelectedRowsData();
        if (rows.length > 0) {
            let rl = rows.length;
            let bodyHtml = `Số dòng hóa đơn đã chọn: <b class='text-danger'>${rl}</b> dòng`;
            bodyHtml += `   
                                <div class='mt-3 d-flex justify-content-start' >
                                        <b style='width:30%;margin-top:5px'>DUYỆT NỘI BỘ:</b>
                                        <button class='btn btn-sm btn-dim btn-outline-dark' onClick = "Duyet('CHO_DUYET')">Chờ duyệt</button>&nbsp;&nbsp;
                                        <button class='btn btn-sm btn-dim btn-outline-primary' onClick = "Duyet('DA_DUYET')">Duyệt</button>&nbsp;&nbsp;
                                        <button class='btn btn-sm btn-dim btn-outline-danger' onClick = "Duyet('KHONG_HOP_LE')">Không hợp lệ</button>
                                </div>
                                <div class='mt-3 d-flex justify-content-start'  >
                                        <b style='width:30%;margin-top:5px'>LOẠI HÓA ĐƠN:</b>
                                        <button class='btn btn-sm btn-dim btn-outline-danger' onClick = "Duyet('HOA_DON_DICH_VU')">Hóa đơn dịch vụ</button>&nbsp;&nbsp;
                                        <button class='btn btn-sm btn-dim btn-outline-primary' onClick = "Duyet('HOA_DON_THUONG')">Hóa đơn thường</button>
                                </div>

                                <hr/>
                                <div class='mt-3 d-flex justify-content-start' >
                                    <b style='width:20%;margin-top:5px'>GHI CHÚ:</b>
                                    <table style='width:100%;'>
                                        <tr>
                                        <td><input type="text" placeholder="Ghi chú" class='form-control' id='txtGhiChu'/></td>
                                        </tr>
                                        <tr>
                                        <td>
                                        <div class='d-flex justify-content-between'>
                                            <button class='btn btn-sm btn-dim btn-dark mt-2' onClick = "GhiChu(${rl},'XOA')">XÓA</button>
                                            <button class='btn btn-sm btn-dim btn-danger mt-2' onClick = "GhiChu(${rl},'GHI_DE')">GHI ĐÈ</button>
                                            <button class='btn btn-sm btn-dim btn-primary mt-2' onClick = "GhiChu(${rl},'GHI_NOI_TIEP')">GHI NỐI TIẾP</button>
                                        </div>
                                        </td>
                                        </tr>
                                    </table>
                                </div>
                                <div class='mt-3 d-flex justify-content-between' >

                                </div>
                `;

            let btnHtml = '';
            createModal("mDuyetHangLoat", "DUYỆT HÀNG LOẠT", bodyHtml, btnHtml);
            showModal("mDuyetHangLoat");
        }
        else {
            dAlert("Chưa chọn dòng để duyệt", "Thông báo");
        }
    }

}

function GhiChu(rl, type) {
    var LstId = [];
    var rows = datagrid.getSelectedRowsData();
    for (let i in rows) {
        LstId.push(rows[i].id);
    }

    var gc = $("#txtGhiChu").val().trim();
    if (type == 'XOA') {
        if (gc == "") {
            var result = DevExpress.ui.dialog.confirm(
                `   Xóa <b>toàn bộ</b> nội dung ghi chú của <b> ${rl} dòng</b> được chọn?
                    <br/><br/>
                    <i class='text-danger'>*** Xóa có chọn lọc: Để NIBOT chỉ xóa nội dung ghi chú mong muốn,<br/>bạn nhập cụm từ cần xóa vào ô ghi chú và nhấn XÓA</i>
                `, "Xác nhận xóa Ghi chú");
            result.done(function (dialogResult) {
                GhiChuHangLoat(type, gc, LstId)
            });
        }
        else {
            var result = DevExpress.ui.dialog.confirm(
                `   Xóa cụm từ ghi chú <b>'${gc}'</b> có trong <b>${rl} dòng</b> được chọn?
                    <br/><br/>
                    <i class='text-danger'>*** Xóa tất cả: Để NIBOT xóa toàn bộ Ghi chú,<br/>bạn để trống ô ghi chú và nhấn XÓA</i>
                `, "Xác nhận xóa Ghi chú");
            result.done(function (dialogResult) {
                GhiChuHangLoat(type, gc, LstId)

            });
        }
    }
    else if (type == 'GHI_DE') {
        if (gc == "") {
            dAlert("Chưa nhập nội dung ghi chú", "Thông báo")
        }
        else {
            var result = DevExpress.ui.dialog.confirm(
                `   Nibot sẽ ghi đè nội dung <b>'${gc}'</b> lên <b>${rl} dòng</b> được chọn?
                    <br/><br/>
                `, "Xác nhận Ghi đè Ghi chú");
            result.done(function (dialogResult) {
                GhiChuHangLoat(type, gc, LstId)
            });
        }
    }
    else if (type == 'GHI_NOI_TIEP') {
        if (gc == "") {
            dAlert("Chưa nhập nội dung ghi chú", "Thông báo")
        }
        else {
            var result = DevExpress.ui.dialog.confirm(
                `   Nibot sẽ ghi nối tiếp vào nội dung <b>'${gc}'</b> lên <b>${rl} dòng</b> được chọn?
                    <br/><br/>
                `, "Xác nhận Ghi đè Ghi chú");
            result.done(function (dialogResult) {
                GhiChuHangLoat(type, gc, LstId)
            });
        }
    }

}

function GhiChuHangLoat(type, gc, LstId) {
    $.ajax({
        type: "POST",
        dataType: "json",
        url: '/QLHD/GhiChuHangLoat',
        data: {
            'MaSoThue': MST,
            "LstId": LstId,
            "GhiChuNibot": gc,
            "Type": type,
        },
        success: function (data) {
            if (data.status == 1) {
                var dt = data.obj
                if (dt.length > 0) {
                    for (let x in dt) {
                        var k = dataSource.filter(p => p.id == dt[x].id)[0];
                        k.gc = dt[x].gc;
                    }
                    datagrid.option("dataSource", dataSource);
                    datagrid.refresh();
                }

                hideModal("mDuyetHangLoat");

            }
            else {
                dAlert(data.message);
            }

        },
        error: function (jqXHR, textStatus, errorThrown) {
            goTohome(jqXHR.responseText);
        }
    });

}



function Duyet(loai) {
    var result = DevExpress.ui.dialog.confirm("<i>Bạn đã chắc cú chưa?</i>", "Xác nhận");
    result.done(function (dialogResult) {
        var LstId = [];
        var rows = datagrid.getSelectedRowsData();
        for (let i in rows) {
            LstId.push(rows[i].id);
        }

        $.ajax({
            type: "POST",
            dataType: "json",
            url: '/QLHD/DuyetHangLoat',
            data: {
                'MaSoThue': MST,
                "LstId": LstId,
                "TrangThaiDuyet": loai,
                'Type': cboLHD.option("value")
            },


            success: function (data) {
                if (data.status == 1) {
                    if (loai == 'CHO_DUYET' || loai == 'DA_DUYET' || loai == 'KHONG_HOP_LE') {
                        for (let i = 0; i < dataSource.length; i++) {
                            if (LstId.indexOf(dataSource[i].id) >= 0) {
                                dataSource[i].thaid = loai;
                            }
                        }
                    }
                    else if (loai == 'HOA_DON_DICH_VU' || loai == 'HOA_DON_THUONG') {
                        let isDV = (loai == 'HOA_DON_DICH_VU');
                        for (let i = 0; i < dataSource.length; i++) {
                            if (LstId.indexOf(dataSource[i].id) >= 0) {
                                dataSource[i].dv = isDV;
                            }
                        }
                    }
                    datagrid.option("dataSource", dataSource);
                    datagrid.refresh();
                    hideModal("mDuyetHangLoat");

                }
                else {
                    dAlert(data.message);
                }

            },
            error: function (jqXHR, textStatus, errorThrown) {
                goTohome(jqXHR.responseText);
            }
        });
    });

}

var dgDanhSachHDTracuu;
var DATA_HD_GOC = [];
var DATA_HD_GOC_2 = [];


function PhanLoai(i) {
    if (i == 1) {
        dgDanhSachHDTracuu.option("dataSource", DATA_HD_GOC);
        dgDanhSachHDTracuu.refresh();
        $("#kqXuLy,#btnTaiHoaDonHangLoat").show();

    }
    else {
        dgDanhSachHDTracuu.option("dataSource", DATA_HD_GOC_2);
        dgDanhSachHDTracuu.refresh();
        $("#kqXuLy,#btnTaiHoaDonHangLoat").hide();
    }
}
var isKetThuc = false;
var countXuLy = 0;

function TaiHoaDonGocHangLoat() {

    isKetThuc = false;
    countXuLy = 0;
    let loaiHD = cboLHD.option("value");

    var allId = []; 

    if (MST == "0105075193" || MST == "0108139575") {
        var dt = DATA.filter(p => p.mst2 != "0107500414");
        for (let i in dt) {
            if (!dt[i].pdfId && dt[i].kqhd != 2 && dt[i].kqhd != 4) {
                allId.push(dt[i].id);
            }
        }

    }
    else {
        for (let i in DATA) {
            if (!DATA[i].pdfId && DATA[i].kqhd != 2 && DATA[i].kqhd != 4) {
                allId.push(DATA[i].id);
            }
        }
    }

    
    if (allId.length == 0) {
        dAlert("Không có hóa đơn");

        return;
    }

    let bodyHtml = '', btnHtml = '';

    bodyHtml = `
        <ul class="nav nav-tabs" style='margin-top:-25px'>
            <li class="nav-item">
                <a class="nav-link active" data-bs-toggle="tab" href="javascript:void(0)" onClick='PhanLoai(1)' style='color:green'> CÓ KHẢ NĂNG TẢI HĐ GỐC&nbsp;&nbsp;<span id='c1'></span></a>
            </li>
            <li class="nav-item">
                <a class="nav-link" data-bs-toggle="tab" href="javascript:void(0)" onClick='PhanLoai(2)' style='color:#7a1414d4'>CHƯA CÓ KHẢ NĂNG TẢI HĐ GỐC&nbsp;&nbsp;<span id='c2'></span></a>
            </li>
        </ul>
        <div class="tab-content">
            <div class="tab-pane active" id="tabHD1">
                <div class='row mb-2 mt-2' id='taiHdGocHeader'>
                    <div class='col-8'>
                        <div id='kqXuLy' style='font-weight:bold;color:mediumvioletred'></div>
                    </div>
                    <div class='col-4 text-end'> 
                        <button class='btn btn-sm btn-primary' id='btnTaiHoaDonHangLoat' type='button'>TẢI HÓA ĐƠN GỐC HÀNG LOẠT</button>
                    </div>
                </div>
                <div class = 'alert alert-primary text-center mt-1 mb-1' id='loaderHDG'>
                    <div class="spinner-border " role="status">
                            <span class="visually-hidden"></span>
                    </div><br/>
                        ĐANG TRÍCH XUẤT THÔNG TIN MÃ TRA CỨU/TRANG TRA CỨU CỦA HÓA ĐƠN.<br/>
                        Vui lòng chờ trong giây lát!<br/>
                </div>      
                <div id='lblMessage' style='display:none'></div>
                <div id='dgDanhSachHDTracuu' class='datagrid'></div>
            </div>
        </div>
         
    `
    createModal("mTaiHoaDonGoc", "TẢI HÓA ĐƠN GỐC HÀNG LOẠT", bodyHtml, btnHtml)
   // showModal("mTaiHoaDonGoc")

    $("#btnTaiHoaDonHangLoat").unbind().on("click", function () {
        $("#btnTaiHoaDonHangLoat").attr("disabled", true);
        $("#kqXuLy").show().html("Tiến trình: 0/" + DATA_HD_GOC.length)
        isKetThuc = false;
        TaiHoaDonGocDeQuy(0);
        TaiHoaDonGocDeQuy(1);
        TaiHoaDonGocDeQuy(2);
        TaiHoaDonGocDeQuy(3);
        TaiHoaDonGocDeQuy(4);
        TaiHoaDonGocDeQuy(5);
        TaiHoaDonGocDeQuy(6);
        TaiHoaDonGocDeQuy(7);
        TaiHoaDonGocDeQuy(8);
        TaiHoaDonGocDeQuy(9);
        TaiHoaDonGocDeQuy(10);
        TaiHoaDonGocDeQuy(11);
        TaiHoaDonGocDeQuy(12);
        TaiHoaDonGocDeQuy(13);

    })
    $.ajax({
        type: "POST",
        dataType: "json",
        url: '/QLHD/TaiHoaDonGoc/TrichXuat',
        data: {
            allId: allId,
            MaSoThue: MST,
            Loai: cboLHD.option("value")
        },
        success: function (data) {

            let height = $("#mTaiHoaDonGoc").height();
            if (height > 900) {
                height = height - 300;
            }
            else {
                height = height - 280;
            }

            if (data.status == 1) {

                DATA_HD_GOC = data.obj["data"];
                var lic = data.obj["lic"];
                $("#mTaiHoaDonGoc .mdl_title").html("TẢI HÓA ĐƠN GỐC HÀNG LOẠT - NGÀY HẾT HẠN: " + lic);
                showModal("mTaiHoaDonGoc");
                try {
                    for (let i in DATA_HD_GOC) {
                        if (DATA_HD_GOC[i]["PhanLoai"] == 2) {
                            if (DATA_HD_GOC[i].TrangTraCuu != "" && DATA_HD_GOC[i].TrangTraCuu.indexOf("UNKNOWN") < 0) {
                                DATA_HD_GOC[i]["KetQuaTai"] = "Nibot trích xuất được thông tin tra cứu nhưng không tải tự động được. Trường hợp này, bạn vui lòng tự tải";
                            }
                            else {
                                DATA_HD_GOC[i]["KetQuaTai"] = "Nibot chưa hỗ trợ tải được bản PDF gốc của HĐ này";
                            }
                        }
                        else {
                            DATA_HD_GOC[i]["KetQuaTai"] = "Chờ tải";
                        }
                        DATA_HD_GOC[i]["NguoiBan"] = `${DATA_HD_GOC[i].MaSoThue2} - ${DATA_HD_GOC[i].Dtpn2}`
                        DATA_HD_GOC[i]["HoaDon"] = `${DATA_HD_GOC[i].SoHd}/${DATA_HD_GOC[i].KyHieuMauSo}${DATA_HD_GOC[i].KyHieuHd}`
                        DATA_HD_GOC[i]["ThongTinTraCuu"] = `${DATA_HD_GOC[i].TrangTraCuu} ${DATA_HD_GOC[i].MaTraCuu}`

                    }
                } catch (e) {
                    TaiHoaDonGocHangLoat()
                }


                DATA_HD_GOC_2 = DATA_HD_GOC.filter(p => p.PhanLoai == 2);
                DATA_HD_GOC = DATA_HD_GOC.filter(p => p.PhanLoai == 1);
                $("#c1").html("(" + DATA_HD_GOC.length + ")");
                $("#c2").html("(" + DATA_HD_GOC_2.length + ")");

                $("#loaderHDG").hide();
                dgDanhSachHDTracuu = $("#dgDanhSachHDTracuu").dxDataGrid({
                    dataSource: DATA_HD_GOC,

                    repaintChangesOnly: true,
                    loadPanel: {
                        enabled: false // or false | "auto"
                    },
                    height: height,
                    showBorders: true,
                    columnAutoWidth: true,
                    showColumnLines: true,
                    showRowLines: true,
                    rowAlternationEnabled: true,
                    noDataText: "Không có dữ liệu",
                    wordWrapEnabled: true,

                    paging: {
                        enabled: false
                    },
                    summary: {
                        totalItems: [{
                            column: 'NguoiBan',
                            summaryType: "count",
                            displayFormat: '{0} HĐ',

                        }]
                    },
                    editing: {
                        allowUpdating: false,
                    },
                    filterRow: { visible: true },

                    columns: [
                        //{
                        //    dataField: "PhanLoai", headerCellTemplate: "Loại",
                        //},
                        {
                            dataField: "NguoiBan", headerCellTemplate: "Người bán",
                        },
                        {
                            dataField: "HoaDon", headerCellTemplate: "Hóa đơn",
                        },
                        { dataField: "NgayLap", headerCellTemplate: "Ngày<br/>lập", width: 90, dataType: "date", format: "dd/MM/yy" },
                        {
                            dataField: "ThongTinTraCuu", headerCellTemplate: "Thông tin<br/>tra cứu",
                            cellTemplate(c, e) {
                                if (e.rowType == 'data') {
                                    $(`<p style='line-height:1.25rem'><a href='${e.data.TrangTraCuu}' target='_blank' class='text-primary fw-bold'>${e.data.TrangTraCuu}</a><br/><span class='fw-bold'>${e.data.MaTraCuu}</span></p>`).appendTo(c);
                                }
                            },
                        },

                        {
                            dataField: "KetQuaTai", headerCellTemplate: "Kết quả<br>tải", width: 200,
                            fixed: true,
                            fixedPosition: 'right',
                        },


                    ]
                }).dxDataGrid("instance")
            }
            else if (data.status == -2) {
                $("#loaderHDG").hide();
                $("#taiHdGocHeader").hide();
                openModalNibotMailBox("2");
            }
            else {
                TaiHoaDonGocHangLoat();
            }

        },
        error: function (jqXHR, textStatus, errorThrown) {
        }
    });


}

function TaiHoaDonGocDeQuy(idx) {

    if (isKetThuc == true) {
        return;
    }
    if (DATA_HD_GOC.length == 0) {
        if (isKetThuc == false) {
            isKetThuc = true;
            dAlert("Không có dữ liệu để tải");
            $("#btnTaiHoaDonHangLoat").attr("disabled", false);
            return;
        }
    }
    var d = null;
    if (idx === undefined) {
        d = DATA_HD_GOC.filter(p => p.KetQuaTai == "Chờ tải");
    }
    else {
        if (idx < DATA_HD_GOC.length) {
            d = [DATA_HD_GOC[idx]];
        }
    }

    if (d == null) {
        return;
    }
    if (d.length == 0) {
        if (isKetThuc == false) {
            var d2 = DATA_HD_GOC.filter(p => p.KetQuaTai == "Đang xử lý....");
            if (d2.length == 0) {
                isKetThuc = true;
                dAlert("Đã tải xong");
                $("#btnTaiHoaDonHangLoat").attr("disabled", false);
                return;
            }
            else {
                setTimeout(function () {
                    TaiHoaDonGocDeQuy();
                }, 500);
            }
        }
    }

    if (isKetThuc == false && d.length > 0) {
        d[0].KetQuaTai = "Đang xử lý....";
        dgDanhSachHDTracuu.option("dataSource", DATA_HD_GOC);
        var hoadon = d[0];
        var lst = [];
        lst.push({
            "MaSoThue": hoadon.MaSoThue,
            "Id": hoadon.Id,
            "MaTraCuu": hoadon.MaTraCuu,
            "TrangTraCuu": hoadon.TrangTraCuu,
            "Loai": cboLHD.option("value"),
            "IsMultiple": true
        });
        TaiHoaDonGoc3(lst);

    }
}
function TaiHoaDonGoc3(lst) {
    $.ajax({
        type: "POST",
        dataType: "json",
        contentType: "application/json",
        url: '/QLHD/TaiHoaDonGoc2',
        data: JSON.stringify(lst),
        timeout: 180000,
        success: function (data) {
            var r = data[0];
            try {
                var hdGoc = DATA_HD_GOC.filter(p => p.Id == r.obj)[0];
                if (r.message.indexOf("Đã tồn tại") >= 0) {
                    r.message = "Tải thành công";
                }
                hdGoc.KetQuaTai = r.message;
                dgDanhSachHDTracuu.option("dataSource", DATA_HD_GOC);
            } catch (e) {
                var hdGoc = DATA_HD_GOC.filter(p => p.Id == lst[0].Id)[0];
                hdGoc.KetQuaTai = "Có lỗi xảy ra, hãy thử lại 1 lần nữa nhé";
                dgDanhSachHDTracuu.option("dataSource", DATA_HD_GOC);

            }
            countXuLy++;
            $("#kqXuLy").html("Tiến trình: " + countXuLy + "/" + DATA_HD_GOC.length);
            TaiHoaDonGocDeQuy();
        },
        error: function (jqXHR, textStatus, errorThrown) {
            if (textStatus == "timeout") {
                var hdGoc = DATA_HD_GOC.filter(p => lst[0].Id == p.Id)[0];
                hdGoc.KetQuaTai = "Có lỗi xảy ra, hãy thử lại 1 lần nữa nhé";
                countXuLy++;
                $("#kqXuLy").html("Tiến trình: " + countXuLy + "/" + DATA_HD_GOC.length);
                dgDanhSachHDTracuu.option("dataSource", DATA_HD_GOC);
                TaiHoaDonGocDeQuy();
            }
            return;
        }
    });
}
function KiemTraRuiRo() {

    TraCuuRuiRo(MST)
}


function TaoFormChietKhau() {
    let bodyhtml = `
                        <div class='row'>
                            <div class='col-12'><div class='datagrid' id='dgBangChietKhau'></div></div>
                        </div>`
    createModal("mChietKhauHoaMai", "BẢNG CHIẾT KHẤU NHÀ CUNG CẤP", bodyhtml, "");
    dgHeight = $(window).height() * 0.8;
    var a = false;
    dgCKHM = $("#dgBangChietKhau").dxDataGrid({
        dataSource: DATA_CK_HOAMAI,
        repaintChangesOnly: true,
        showOperationChooser: false,

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
        showBorders: true,
        paging: {
            enabled: false,
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
        height: dgHeight,
        noDataText: "Không có dữ liệu",
        loadingPanel: {
            visible: true,
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
        export: {
            fileName: 'Hoa Mai - Bảng chiết khấu',
        },
        onContentReady: function (e) {
            a = true;
        },
        onToolbarPreparing: function (e) {
            e.toolbarOptions.items.unshift(

                {
                    location: "before",
                    widget: "dxButton",
                    options: {
                        elementAttr: {
                            style: "background: #fff9d8b0;border-radius: 10px;color: black;font-weight: bold;" // Add custom CSS class here
                        },
                        onContentReady: function (e) {
                            // Directly target the icon and set its color
                            $(e.element).find(".dx-icon").css("color", "black");
                        },
                        text: "Import Excel",
                        hint: "Import Excel",

                        onClick: function () {
                            ImportFileHoaMai();
                        }
                    }
                },
                {
                    location: "before",
                    widget: "dxButton",
                    options: {
                        elementAttr: {
                            style: "background: #f5d004b0;border-radius: 10px;color: black;font-weight: bold;" // Add custom CSS class here
                        },
                        onContentReady: function (e) {
                            // Directly target the icon and set its color
                            $(e.element).find(".dx-icon").css("color", "black");
                        },
                        text: "Export Excel",
                        hint: "Export Excel",

                        onClick: function () {
                            dgCKHM.exportToExcel();
                        }
                    }
                },
                {
                    location: "before",
                    widget: "dxButton",
                    options: {
                        elementAttr: {
                            style: "margin-left:20px;background: #5c0019f0;border-radius: 10px;color: white;font-weight: bold;" // Add custom CSS class here
                        },
                        onContentReady: function (e) {
                            // Directly target the icon and set its color
                            $(e.element).find(".dx-icon").css("color", "black");
                        },
                        text: "Xóa dữ liệu",
                        hint: "Xóa dữ liệu",

                        onClick: function () {
                            var result = DevExpress.ui.dialog.confirm("Xóa dữ liệu đang hiển thị trên Bảng Chiết khấu.<br/><b>Bạn đã chắc cú chưa?</b>", "XÁC NHẬN XÓA");
                            result.done(function (dialogResult) {
                                if (dialogResult) {
                                    $.ajax({
                                        type: "POST",
                                        dataType: "json",
                                        url: '/HoaMai/ChietKhauHoaMaiXoa',
                                        data: {
                                            rows: dgCKHM.getVisibleRows().map(p => p.data)
                                        },
                                        success: function (data) {
                                            if (data.status == 1) {
                                                DATA_CK_HOAMAI = data.obj;
                                                dgCKHM.option("dataSource", DATA_CK_HOAMAI);
                                                dgCKHM.refresh();
                                                dAlert("Xóa xong!");
                                            }


                                        },
                                        error: function (jqXHR, textStatus, errorThrown) {
                                            console.log(textStatus);
                                            console.log(errorThrown);
                                            console.log(jqXHR);
                                        }
                                    });
                                }
                            })
                        }
                    }
                },
            )
        },

        onSaving(e, i) {
            let changes = e.changes;
            e.promise = true;
            if (changes.length > 0) {

                let updateData = [];
                let removeData = [];
                for (let k in changes) {
                    let type = changes[k].type;
                    let dataChanges = changes[k].data;
                    if (type == "update") {
                        let dataOrgs = JSON.parse(JSON.stringify(changes[k].key));
                        for (let key in dataChanges)
                            dataOrgs[key] = dataChanges[key];
                        updateData.push(dataOrgs);
                    }
                    else if (type == "remove") {
                        let dataOrgs = JSON.parse(JSON.stringify(changes[k].key));
                        for (let key in dataChanges)
                            dataOrgs[key] = dataChanges[key];
                        removeData.push(dataOrgs);
                    }
                }


                $.ajax({
                    type: "POST",
                    dataType: "json",
                    url: '/HoaMai/UpdateChietKhau',
                    data: {
                        rows: updateData,
                        rowDeletes: removeData,
                    },
                    success: function (data) {
                        if (data.status == 1) {
                            dAlert("Hoan hô. Đã cập nhật xong", "Thông báo")
                        }
                        else {
                            dAlert(data.message, "Thông báo");
                            SearchHH();
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

        summary: {
            totalItems: [
                {
                    column: 'MaNcc',
                    summaryType: "count",
                    displayFormat: '{0} dòng',
                }
            ]
        },
        columns: [
            { dataField: "MaNcc", headerCellTemplate: "Mã số thuế NCC", caption: "Mã số thuế NCC"},
            { dataField: "MaHang", headerCellTemplate: "Mã hàng", caption: "Mã hàng" },
            { dataField: "Dvt", headerCellTemplate: "ĐVT", caption: "ĐVT" },
            { dataField: "GiamGiaTheoTien", headerCellTemplate: "Giảm giá theo Tiền", caption: "Giảm giá theo Tiền" },
            { dataField: "GiamGiaTheoPhanTram", headerCellTemplate: "Giảm giá theo %", caption: "Giảm giá theo %" },
            { dataField: "NgayApDung", headerCellTemplate: "Ngày áp dụng", caption: "Ngày áp dụng" },
        ],


    }).dxDataGrid("instance");
}

function MoBangChietKhau() {

    showModal("mChietKhauHoaMai")
    setTimeout(function () {
        $.ajax({
            type: "GET",
            dataType: "json",
            url: '/HoaMai/MoBangChietKhau',
            success: function (data) {
                console.log(data);
                if (data.status == 1) {
                    ShowFormHoaMai(data.obj);
                }
                else {
                    dAlert(data.message);
                }
            },
            error: function (jqXHR, textStatus, errorThrown) {
                hideModal(tenModal)
                console.log(textStatus);
                console.log(errorThrown);
                console.log(jqXHR);
            }
        });

    },300)

  
}
var DATA_CK_HOAMAI = [];
var dgCKHM = null;
function ShowFormHoaMai(data) {
    DATA_CK_HOAMAI = data;
    dgCKHM.option("dataSource", DATA_CK_HOAMAI);
}

var impCK = [];

function ImportFileHoaMai() {
    $("#importFileHoaMai").val('');
    impCK = [];
    $("#importFileHoaMai").unbind().on("change", function () {
        var rI = -1;
        var fileUpload = $("#importFileHoaMai").prop('files')[0];
        var mess = "";
        if (fileUpload) {
            if (typeof (FileReader) != "undefined") {
                const wb = new ExcelJS.Workbook();
                const reader = new FileReader()
                reader.readAsArrayBuffer(fileUpload)
                reader.onload = () => {
                    const buffer = reader.result;
                    var foundCol = false;
                    wb.xlsx.load(buffer).then(workbook => {
                        workbook.eachSheet((sheet, id) => {
                            sheet.eachRow((row, rowIndex) => {
                                let data = row.values;
                                if (rowIndex == 1) {
                                    //(7) [empty, 'Mã số thuế NCC', 'Mã hàng', 'ĐVT', 'Giảm giá theo Tiền', 'Giảm giá theo %', 'Ngày áp dụng']
                                    if (data[1] != 'Mã số thuế NCC' || data[2] != 'Mã hàng' || data[3] != 'ĐVT' || data[4] != 'Giảm giá theo Tiền' || data[5] != 'Giảm giá theo %' || data[6] != 'Ngày áp dụng') {
                                        mess = ("Không đúng template");
                                    }
                                }
                                else {
                                    var r = {
                                        'MaNcc' : data[1],
                                        'MaHang': data[2],
                                        'Dvt': data[3],
                                        'GiamGiaTheoTien': data[4],
                                        'GiamGiaTheoPhanTram': data[5],
                                        'NgayApDung': data[6],
                                    }
                                    impCK.push(r);
                                }
                              
                            });
                        })
                    }).then(function () {
                        if (mess!="") {
                            dAlert(mess);
                            return;
                        }

                        $.ajax({
                            type: "POST",
                            dataType:"json",
                            url: '/HoaMai/Import',
                            data: {
                                rows:  impCK

                            },
                            success: function (data) {
                                if (data.status == -1) {
                                    let err = data.obj;
                                    let str = "";
                                    for (let i in err) {
                                        str += err[i] + "</br>";
                                    }
                                    dAlert(str);
                                }
                                else {

                                    dAlert("Import Xong!");
                                    dgCKHM.option("dataSource", data.obj);
                                }
                            },
                            error: function (jqXHR, textStatus, errorThrown) {
                                console.log(textStatus);
                                console.log(errorThrown);
                                console.log(jqXHR);
                            }
                        });

                    });
                }
            }
        }
    });

    $("#importFileHoaMai").click();

}