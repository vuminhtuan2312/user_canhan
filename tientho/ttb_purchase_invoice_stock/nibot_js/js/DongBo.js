//2025-06-17

var newHeight = 1000;

$(document).ready(function () {
    initHtml();
    initCtrl();
    DATA = [];
})


var dictTrangThai = {
    "CHO": `<span class="badge bg-secondary"> chờ đồng bộ</span>`,
    "DANG": `<span class="badge bg-danger">đang đồng bộ</span>`,
    "DANG_GOV_MUA_VAO": `<span class="badge bg-danger">đang đồng bộ hóa đơn mua vào</span>`,
    "DANG_GOV_BAN_RA": `<span class="badge bg-danger">đang đồng bộ hóa đơn bán ra</span>`,
    "DANG_GOV_FULL": `<span class="badge bg-danger">đang đồng bộ hóa đơn mua vào/bán ra</span>`,

    "XONG": `<span class="badge bg-primary">đồng bộ xong</span>`
};

var btnGovRa, btnGovVao, btnGov, dtTuNgay, dtDenNgay;
var chkDongBoFull;
var resultGrid;
var stNam;

var cboQuy, txtNam;
var cboKetQuaPhanTich, txtKeyword, cboKhoangNgay,
    cboLoaiNgay, txtTuNgayMail, txtDenNgayMail;

var timeoutCT = 1500000;
var timeoutStrCT = `<div style='font-size:16px;line-height:1.5rem'>Thời gian chờ phản hồi quá lâu. Hãy thử làm mới trang (bấm F5) và đồng bộ lại.<br/>
             * Nếu đã thử 3-5 lần mà vẫn không được hãy liên hệ: 1900.63.65.07 hoặc 0988.988.814 (zalo) để được hỗ trợ thêm.</br>
             </div>`


var timeoutDBTQ = 1500000;
var timeoutStrDBTQ = `<div style='font-size:16px;line-height:1.5rem'>Thời gian chờ phản hồi quá lâu. Hãy thử làm mới trang (bấm F5) và đồng bộ lại.<br/>
             * Nếu công ty phát sinh nhiều hóa đơn hãy thử chỉnh khoảng thời gian đồng bộ ngắn lại.<br/>
             * Nếu đã thử 3-5 lần mà vẫn không được hãy liên hệ: 1900.63.65.07 hoặc 0988.988.814 (zalo) để được hỗ trợ thêm.</br>
             </div>`

function showPnlDongBo(idCtrl) {
    if (idCtrl == 'pnlDongBoTCT') {
        showCtrl("pnlDongBoTCT", 1);
        showCtrl("pnlDongBoEmail", 0);
        activeA("aTCT", 1);
        activeA("aMail", 0);
        showCtrl("bMail", 0);

    }
    else {
        showCtrl("pnlDongBoTCT", 0);
        showCtrl("pnlDongBoEmail", 1);
        activeA("aTCT", 0);
        activeA("aMail", 1);
        showCtrl("bMail", 1);
    }
}

var dataMail, dgMAIL;
function initHtml() {
    let ghiChu = ``
    if (GhiChuNibot) {
        GhiChuNibot = GhiChuNibot.replace("Tên đăng nhập hoặc mật khẩu không đúng", "Mật khẩu đăng nhập vào trang hoadondientu.gdt.gov.vn đã thay đổi");
        GhiChuNibot = GhiChuNibot.replace("Tài khoản đã bị khoá vì đã nhập sai thông tin quá số lần quy định", "Tài khoản trang hoadondientu.gdt.gov.vn đã bị khoá vì đã nhập sai thông tin quá số lần quy định");

        ghiChu = `

            <div class='alert alert-danger fw-bold mt-2 text-center' >${GhiChuNibot}
            <br/>
            <a class='btn btn-primary mt-1  fs-20px' href='/CapNhatThongTin/${MST}/${GuidGoi}'  >Click vào đây để Khắc phục</a>  
            
            </div>
        `;
    }

    let htmlBTN = ``;
    let sBtnVao = 'd-none', sBtnRa = 'd-none', sBtnFull = 'd-none';

    if (quyenPVHD == 'V' || quyenPVHD == 'ALL')
        sBtnVao = '';
    if (quyenPVHD == 'R' || quyenPVHD == 'ALL')
        sBtnRa = '';
    if (quyenPVHD == 'ALL')
        sBtnFull = '';
    htmlBTN += `<div  class='${sBtnVao} mb-1 w-100' id="btnGovVao"></div> <br/>`;
    htmlBTN += `<div  class='${sBtnRa} mb-1 w-100' id="btnGovRa"></div> <br/>`;
    htmlBTN += `<div  class='${sBtnFull} mb-1 w-100' id="btnGov"></div> <br/>`;

    if (ghiChu == '') {
        let zx = '';
        if (BanRaNhieu || MuaVaoNhieu)
            zx = `<span class='text-danger fw-bold'>0. Đối với doanh nghiệp có lượng HĐ đầu vào/đầu ra lớn, bạn nên chọn khoảng thời gian từ 3 đến 7 ngày cho 1 lần đồng bộ đầu ra.</span><br/>`;
        htmlBTN += `
        <div  class=' mb-1 w-100 alert alert-primary ' style='line-height:30px;font-weight:normal;font-size:12pt' id='btnInfo'>
             <h5 style='color: #5503ca;'> KHUYẾN CÁO SỬ DỤNG HIỆU QUẢ</h5>
           <div class='text-dark'><b>Bạn nên chủ động bấm nút Đồng bộ trước khi kiểm tra số liệu bởi những lý do sau đây:</b><br/>
            ${zx}
            1. Có những Hóa đơn do người bán Ký trễ hoặc hóa đơn TCT không cấp mã (ký hiệu K) gởi trễ lên TCT từ 15-45 ngày. Trong trường hợp này, Nhấn Đồng bộ sẽ giúp bạn lấy <b>đủ số lượng hóa đơn</b>.<br/>
            2. Có những hóa đơn lúc đồng bộ về là Hóa đơn mới nhưng sau đó, người bán Hủy/ Điều chỉnh/ Thay thế. Trong trường hợp này, Nhấn Đồng bộ sẽ giúp bạn lấy <b>đúng trạng thái mới nhất của hóa đơn.</b><br/>
             <b style='color:blue'>***  Đối với những tờ hóa đơn đã được tải về rồi, dù bạn có đồng bộ bao nhiêu lần đi nữa, Nibot cũng tính có 1 tờ mà thôi. Vì vậy, đừng sợ tốn số lượng tờ hóa đơn khi nhấn đồng bộ nhiều lần nhé.</b>
          </div>
        </div>`;
    }

    let tbhthtml = '';
    if (tbht != '') {
        tbhthtml = tbht;
        //tbhthtml = `
        //        <div style="margin: 0 auto;width:75%; background: linear-gradient(90deg, #1c1c1c, #2e2e2e); color: #e0e0e0; font-size: 16pt; font-weight: 500; padding: 18px 22px; border-radius: 10px; box-shadow: 0 0 12px rgba(0, 0, 0, 0.8); display: flex; align-items: center;">
        //              <div style="font-size: 16pt; margin-right: 18px; animation: blink 1s infinite ease-in-out;">
        //                ⚠️
        //              </div>
        //              <div>
        //                <div>📅 <b>Hiện tại, phần tra cứu hóa đơn từ <span style="color: #ffd700;">MÁY TÍNH TIỀN trang hoadondientu.gdt.gov.vn không ổn định</span> </b> (có khi tra được, có khi treo – mà đa phần là treo)</div>
        //                <div style="margin-top:5px;">⚠️ Mọi người cần đối chiếu kỹ số lượng hóa đơn trước khi làm sổ sách.</div>
        //                <div style="margin-top:5px; color: #ffd700;"><b>⏳ KHI NÀO THUẾ BẢO TRÌ XONG, THÔNG BÁO SẼ MẤT ĐI!</b></div>
        //              </div>
        //        </div>
        //        <style>
        //        @keyframes blink {
        //          0%, 100% { opacity: 1; }
        //          50% { opacity: 0; }
        //        }
        //        </style>
        //    `
    }
  

    let canhBaoDongBo = `
         <div class='text-danger' style=';font-size:10pt;background-color: #fff3cd;border: 1px solid #ffeeba;border-radius: 8px;padding: 15px;margin: 10px 0;position: relative;font-size: 10pt;color: #856404;'>
                    <p class='text-center' style='font-size:14pt'> <u >CẢNH BÁO QUAN TRỌNG</u></p>
                    <span style='color:black;font-weight:500'>Hiện tại trang tra cứu hoadondientu.gdt.gov.vn đang có lỗi trả về số lượng hóa đơn không giống nhau ở mỗi lần bấm nút tìm kiếm. 
                    <span style='font-weight:300'>Ví dụ: thực tế bạn có 50 tờ, nhưng khi bấm tìm kiếm thì lại ra 48 tờ, 49 tờ, hoặc 50 tờ. ==> <a href='https://www.youtube.com/watch?v=amWULH_oQ90' target='_blank' style='color:darkblue'><b>XEM VIDEO</b></a>.</span> 
                    <span style='font-weight:500;'>Vì vậy, trước khi làm sổ sách, bạn hãy chủ động bấm đồng bộ vài lần trên Nibot để lấy đủ hóa đơn và nhớ đối chiếu số lượng hóa đơn giữa Nibot và Thuế nhé.</span>
        </div>
    `

    canhBaoDongBo = ``;
    let htmlDongBoTCT = `  
       <div id='pnlDongBoTCT'>
                ${tbhthtml}
               <div class="row gy-2 mt-2">
      
	                <div class='col-12 col-sm-4'>
                 
		                <div class='d-flex justify-content-start'>
			                <div id="cboQuy"></div>&nbsp;&nbsp;&nbsp;&nbsp;
			                <div id="txtNam"></div>
		                </div>
		                <div id="dtTuNgay"></div>
		                <div id="dtDenNgay"></div>
		                <hr/>
			                ${htmlBTN}
                            ${ghiChu}

	                </div>
	                <div class="col-12 col-sm-8" style='margin-top:18px'>
                        <h4>Nhóm Hỗ trợ Smart Pro + Nibot <a href='https://zalo.me/g/tagkxh954' target='_blank'>https://zalo.me/g/tagkxh954</a></h4>
		                Trạng thái: <span id="lblTrangThai"></span>
		                <div id="spinner" style="margin-top:5px;margin-left:10px" class="d-none spinner-border spinner-border-sm" role="status">
			                <span class="visually-hidden">Loading...</span>
		                </div>
		                <br/>
		                <div class='row'>
			                <div class='col-4'>
				                <div id="textResult" >
					                <span id='t_ChungThuc'></span>
					                <span id='t_DongBoTongQuat'></span>
					                <span id='t_DongBoTongQuat_3' class='datagrid mb-2'></span>
					                <span id='t_DongBoTongQuat_2' class='mt-2 mb-2'></span>
					                <span id='t_DongBoChiTiet'></span>
				                </div>
					
			                </div>
			                <div class='col-8'>
				                <div id="result">
                                ${canhBaoDongBo}
                                </div>
			                </div>
		                </div>
	                </div>
                </div>
        </div>
    `
    let htmlDongBoMail = `
    <div id='pnlDongBoEmail' style='display:none;'>
        <div class='row gy-2 mt-2'>
            <div class='col-12 d-flex justify-content-start mb-2'>
                    <div id="cboKetQuaPhanTich"></div>
                    <div id="txtKeyword" style='margin-left:10px'></div>
                    <div id="cboKhoangNgay" style='margin-left:10px'></div>
                    <div id="cboLoaiNgay" style='margin-left:10px'></div>
                    <div id="txtTuNgayMail" style='margin-left:10px'></div>
                    <div id="txtDenNgayMail" style='margin-left:10px'></div>
            </div>
        </div>
        <div class='d-flex justify-content-between mb-2'>
            <button type='button' id="btnDongBoMail" class="btn btn-sm btn-dim btn-outline-primary"><em class="icon ni ni-hot"></em>&nbsp;&nbsp;Đồng bộ</button>
            <button type='button' id="btnSearchMail" class="btn btn-sm btn-dim btn-outline-dark"><em class="icon ni ni-search"></em>&nbsp;&nbsp;Tìm kiếm</button>
            <button type='button' id="btnPhanTichAll" class="btn btn-sm btn-dim btn-outline-danger"><em class="icon ni ni-cpu"></em>&nbsp;&nbsp;Phân tích</button>
        </div>
        <div class='row mb-2'>
            <div class='col-12'>
                <div id='statusDongBoEmail' style='font-weight:400;font-size:10pt'></div>
            </div>
        </div>


        <div class='row'>
            <div class='col-12'>
                <div id='dg_Mail' class='datagrid'></div>
            </div>
        </div>
    </div>
    `

    if (nibotEmail == 1) {

        $("#htmlContent").html(`
            <form id='frmDongBo' autocomplete="off">
                <div class="row gy-2 ">
                    <div class="  col-12 fw-bold " style='margin-bottom:5px;font-size:12pt'>
                        <div class="nk-block">
                            <div class="card card-bordered card-preview"  id="pnlDongBoHoaDon">
                                <div class="preview-block p-1" >
                                        <a  href='javascript:void(0)' id='aTCT' class='text-primary' onclick='showPnlDongBo("pnlDongBoTCT")'>ĐỒNG BỘ HĐ TCT</a>&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;
                                        <a  href='javascript:void(0)' id='aMail' class='text-muted' onclick='showPnlDongBo("pnlDongBoEmail")' href='javascript:void(0)'>HỘP THƯ </a>
                                        <span class='badge bg-dark' id="bMail" style=' display:none;float:right;margin-top:5px;margint-right:5px;'>${email}@nangdong.online</span>
                                    ${htmlDongBoTCT}
                                    ${htmlDongBoMail}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </form>
        `);

        cboKetQuaPhanTich = $("#cboKetQuaPhanTich").dxSelectBox({
            dataSource: [
                { "key": "", "display": "--- KẾT QUẢ PHÂN TÍCH ---" },
                { "key": "CHUA_PHAN_TICH", "display": "CHƯA PHÂN TÍCH" },
                { "key": "DA_PHAN_TICH", "display": "ĐÃ PHÂN TÍCH" },
                { "key": "BO_QUA", "display": "BỎ QUA" },
            ],
            width: 200,
            valueExpr: "key",
            displayExpr: "display",
            value: ""
        }).dxSelectBox("instance")

        txtKeyword = $("#txtKeyword").dxTextBox({
            width: 350,
            placeholder: "từ khóa tìm kiếm"
        }).dxTextBox("instance")

        var kngay = "Quý " + Math.ceil((new Date().getMonth() + 1) / 3);
        cboKhoangNgay = $("#cboKhoangNgay").dxSelectBox({
            placeholder: "Chọn khoảng Thời gian",
            items: ["Hôm nay", "Tháng này", "Tháng 1", "Tháng 2", "Tháng 3", "Tháng 4", "Tháng 5", "Tháng 6", "Tháng 7", "Tháng 8", "Tháng 9", "Tháng 10", "Tháng 11", "Tháng 12", "Quý 1", "Quý 2", "Quý 3", "Quý 4", "Năm này", "Năm trước", "Tất cả"],
            value: kngay,
            onValueChanged(e) {
                let val = e.value;

                var x = KhoangNgay(e.value, false, stNam);

                txtTuNgayMail.option("value", x.start);
                txtDenNgayMail.option("value", x.end);
                SearchMail();

            },
        }).dxSelectBox("instance");

        cboLoaiNgay = $("#cboLoaiNgay").dxSelectBox({
            dataSource: [
                { "key": "NGAY_GOI", "display": "Ngày gởi" },
                { "key": "NGAY_LAP", "display": "Ngày Lập" },
                { "key": "NGAY_DONG_BO", "display": "Ngày Đồng bộ" },
            ],
            width: 120,
            valueExpr: "key",
            displayExpr: "display",
            value: "NGAY_DONG_BO"
        }).dxSelectBox("instance")

        var khoangNgay = KhoangNgay(kngay, true);

        txtTuNgayMail = $("#txtTuNgayMail").dxDateBox({
            displayFormat: "dd/MM/yyyy",
            useMaskBehavior: true,
            value: khoangNgay.start,
            width: 120,
        }).dxDateBox("instance")

        txtDenNgayMail = $("#txtDenNgayMail").dxDateBox({
            displayFormat: "dd/MM/yyyy",
            useMaskBehavior: true,
            width: 120,
            value: khoangNgay.end
        }).dxDateBox("instance")



        var totals = [{
            column: 'NgaySync',
            summaryType: "count",
            displayFormat: '{0} email',
        }
        ];
        initCtrl();
        dgMAIL = $("#dg_Mail").dxDataGrid({
            dataSource: dataMail,
            showBorders: true,
            showColumnLines: true,
            showRowLines: true,
            columnAutoWidth: true,
            rowAlternationEnabled: true,
            wordWrapEnabled: true,
            filterRow: { visible: true },
            paging: {
                enabled: true,
                pageSize: 50,
                pageIndex: 0    // Shows the second page
            },
            summary: {
                totalItems: totals
            },
            columns: [
                {
                    dataField: "NgaySync",
                    dataType: "datetime",
                    format: "dd/MM/yy HH:mm",
                    headerCellTemplate: "Ngày<br/>đồng bộ",
                    width: 60,
                },
                {
                    dataField: "NgayGoi",
                    dataType: "datetime",
                    format: "dd/MM/yy HH:mm",
                    headerCellTemplate: "Ngày<br/>gởi",
                    width: 60,
                },
                {
                    headerCellTemplate: "Người<br/>gởi",
                    dataField: "NguoiGoi",
                    width: 80,
                },
                {
                    dataField: "TieuDe",
                    headerCellTemplate: "Email",
                    cellTemplate(c, e) {
                        if (e.rowType == 'data') {
                            let v = e.value;
                            let x = e.value;
                            x = GenTieuDe(x);

                            x = `<b> <a href='javascript:void(0)' onClick='viewMail("${e.data.Id}")' class='text-dark'>${x}</a></b>`;

                            let y = "";
                            if (e.data.XmlFileName) {
                                y += `<a href='javascript:void(0)' onClick='DownloadDinhKem("XML","${e.data.Id}")' ><em class="icon ni ni-clip"></em> ${e.data.XmlFileName}</a>`
                            }
                            if (e.data.PdfFileName) {
                                if (y != "") {
                                    y += "  |  ";
                                }
                                y += `<a href='javascript:void(0)' onClick='DownloadDinhKem("PDF","${e.data.Id}")' ><em class="icon ni ni-clip"></em> ${e.data.PdfFileName}</a>`
                            }
                            if (e.data.ZipFileName) {
                                if (y != "") {
                                    y += "  |  ";
                                }
                                y += `<a href='javascript:void(0)' onClick='DownloadDinhKem("ZIP","${e.data.Id}")' ><em class="icon ni ni-clip"></em> ${e.data.ZipFileName}</a>`
                            }
                            if (y != "") {
                                x += `<br/>` + y;
                            }
                            $(x).appendTo(c);

                        }
                    }
                },

                {
                    headerCellTemplate: "Kết quả Phân tích",
                    columns: [
                        {
                            dataField: "TrangThai",
                            caption: "Trạng thái",
                            width: 180,
                            cellTemplate(c, e) {
                                if (e.rowType == 'data') {
                                    if (e.data.TrangThai.indexOf("Chưa phân tích") >= 0) {
                                        $(`
                                            <a href='javascript:void(0)' onclick='PhanTich("${e.data.Id}")' class='btn btn-sm btn-dark'>Phân tích</a>&nbsp;&nbsp;
                                            <a href='javascript:void(0)' onclick='BoQua("${e.data.Id}")' class='btn btn-sm btn-danger'>Bỏ qua</a>&nbsp;&nbsp;
                                        `).appendTo(c);
                                    }
                                    else {
                                        $(`<div><a href='javascript:void(0)' onclick='OpenDoiTrangThai("${e.data.Id}")'>${e.value}</a></div>`).appendTo(c);
                                    }
                                }
                            }
                        },
                        {
                            dataField: "NguoiBan",
                            caption: "Ng.Bán",
                            width: 80,
                        },
                        {
                            dataField: "HdNgayLap",
                            caption: "Ngày lập",
                            width: 80,
                            dataType: 'datetime',
                            format: "dd/MM/yyyy"

                        },
                        {
                            dataField: "HdKyHieuHd",
                            caption: "K.hiệu HĐ",
                            width: 80,

                        },
                        {
                            dataField: "HdSoHd",
                            caption: "Số HĐ",
                            width: 80,
                            cellTemplate(c, e) {
                                if (e.rowType == 'data') {
                                    if (e.value) {
                                        if (e.data.TrangThai.indexOf("Không có") > 0) {
                                            $(`<b>${e.value}</b>`).appendTo(c);
                                        }
                                        else {
                                            $(`<a href='/ChiTietHoaDon/${MST}/${e.data.HdId}'  target='_blank'><b>${e.value}</b></a>`).appendTo(c);

                                        }
                                    }
                                }
                            }
                        },

                    ]
                },
            ]
        }).dxDataGrid("instance");


        SearchMail();

        $("#btnDongBoMail").unbind().on("click", function (e) {
            DongBoEmail();
        })

        $("#btnSearchMail").unbind().on("click", function (e) {
            SearchMail();
        })
        $("#btnPhanTichAll").unbind().on("click", function (e) {
            PhanTichAll();
        })


        setTimeout(function () {
            var newHeight2 = $(window).height() - 250;
            let h = document.getElementById("pnlDongBoHoaDon").style.height
            if (newHeight2 < h) {
                newHeight2 = h;
            }
            dgMAIL.option("height", newHeight2)
        }, 300)
        showPnlDongBo("pnlDongBoTCT")
    }
    else {


        $("#htmlContent").html(`
                <div class="nk-block" >
                    <div class="card card-bordered card-preview p-1" id="pnlDongBoHoaDon">
                        <div class="preview-block">
                            <form id="frmDongBo" autocomplete="off">
                                ${htmlDongBoTCT}
                            </form>
                        </div>
                    </div>
                </div>
        `);

        initCtrl();

        showPnlDongBo("pnlDongBoTCT");
        setTimeout(function () {
            clearAutoCompleted();
        }, 200)
    }

    var btnInfoRect = document.getElementById("btnInfo").getBoundingClientRect();

    newHeight = btnInfoRect.top + btnInfoRect.height - 50;
    var newHeight2 = $(window).height() - 120;

    if (newHeight < newHeight2) {
        newHeight = newHeight2;
    }

    // Set the new height for helpContent
    document.getElementById("pnlDongBoHoaDon").style.height = newHeight + 'px';

    //$("#pnlDongBoHoaDon").height($(window).height() - 120);


    setTimeout(function () {
        $("#frmDongBo").submit(function (e) {
            e.preventDefault();
        });
    }, 100);
}

function OpenDoiTrangThai(Id) {
    let r = dataMail.filter(p => p.Id == Id);
    if (r.length == 1) {
        r = r[0];
        let bodyHtml = `
            <div class='row'>
            <div class='col-12'>
                <p style='line-height:2.5em'>
                    Việc phục hồi sẽ hủy bỏ gắn kết thông tin XML/PDF giữa Email và NIBOT.<br/>
                    Đồng thời trả Email lại trạng thái ban đầu 'Chưa phân tích'.<br/>
                    <b>Bạn đã chắc cú chưa?</b>
                </p>
                <button class='btn btn-sm btn-dark' type='button' onClick='PhucHoiEmail("${Id}")' >Phục hồi dữ liệu từ Email gốc</button> 
            </div>
        `
        let btnHtml = ``
        createModal("mDoiTrangThai", "Phục hồi lại trạng thái Chưa phân tích", bodyHtml, btnHtml)
        showModal("mDoiTrangThai");
    }
}
function PhucHoiEmail(Id) {
    $.ajax({
        type: "GET",
        dataType: "json",
        url: '/QLHD/PhucHoiEmail/' + MST + "/" + Id,
        success: function (data) {
            if (data.status == 1) {
                SearchMail();
                hideModal("mDoiTrangThai");
                dAlert(data.message);
            }
            else {
                dAlert(data.message);
            }
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR);
            goTohome(jqXHR.responseText);
        }
    });

}

function DownloadDinhKem(Type, Id) {

    var a = document.createElement('a');
    var url = `/QLHD/Mail/TaiFile/${Type}/${MST}/${Id}`;
    a.href = url;
    document.body.append(a);
    a.click();
    a.remove();

}
function viewMail(Id) {
    let r = dataMail.filter(p => p.Id == Id);
    if (r.length == 1) {
        r = r[0];
        let height = $(window).height() * 0.6;
        let bodyHtml = `
            <div style='width: 100%;height: ${height}px ;overflow-x: auto;overflow-y: auto;'>${r.NoiDung}</div>
        `
        let btnHtml = ``
        createModal("mShowEmail", "Nội dung Email", bodyHtml, btnHtml)
        showModal("mShowEmail");
    }
}
function loadingDongBoEmail(isShow, status) {

    if (isShow) {
        $("#statusDongBoEmail").html(
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
        $("#statusDongBoEmail").hide();
    }

}
function GenTieuDe(x) {
    try {
        if (x) {
            if (x.indexOf("Fwd: ") >= 0) {
                x = x.replace("Fwd: ", "");
            }
        }
        if (x.trim() == "") {
            x = "Không có tiêu đề";
        }
    }
    catch {
        x = "Không có tiêu đề";
    }
   
    return x;
}
var lyDoBoQua = 1;
function BoQua(Id) {
    let r = dataMail.filter(p => p.Id == Id);
    r = r[0];
    lyDoBoQua = 1;
    let bodyHtml = `
                Bỏ qua email <b>${GenTieuDe(r.TieuDe)}</b>
                <table style='width:100%;margin-top:10px'>
                    <tr>
                        <td  style='width:30%'><b>Lý do bỏ qua: </b></td>
                        <td><div id='cboBoQua'></div></td>
                    </tr>
                </table>
                <div class='text-center mt-2'><button class='btn btn-sm btn-outline-danger' id='btnBoQua' data-id='${Id}'>BỎ QUA</button>

        `
    createModal("mShowBoQua", "Bỏ qua", bodyHtml, '')
    showModal("mShowBoQua");
    $("#cboBoQua").dxSelectBox({
        dataSource: [{ "key": 1, "dsp": "Không phải hóa đơn" }, { "key": 2, "dsp": "HĐ bị hủy" }, { "key": 3, "dsp": "HĐ trùng" },],
        valueExpr: "key",
        displayExpr: "dsp",
        value: 1,
        onValueChanged(e) {
            lyDoBoQua = e.value;
        }
    })
    $("#btnBoQua").unbind().on("click", function () {
        var Id = $(this).data("id");
        $.ajax({
            type: "GET",
            dataType: "json",
            url: '/QLHD/BoQuaEmail/' + MST + "/" + Id + "/" + lyDoBoQua,
            success: function (data) {
                dAlert(data.message);
                SearchMail();
                hideModal("mShowBoQua");

            },
            error: function (jqXHR, textStatus, errorThrown) {
                console.log(jqXHR);
                goTohome(jqXHR.responseText);
            }
        });
    })


}





function PhanTich(Id) {
    loadingDongBoEmail(true, 'Đang phân tích email. Vui lòng chờ!')

    $.ajax({
        type: "GET",
        dataType: "json",
        url: '/QLHD/PhanTichEmail/' + MST + "/" + Id,
        success: function (data) {
            if (data.status == 1) {
                dAlert(data.message);
                SearchMail();
                loadingDongBoEmail(false);
            }
            else {
                dAlert(data.message);
                loadingDongBoEmail(false);

            }


        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR);
            goTohome(jqXHR.responseText);
            $("#btnDongBoMail").attr("disabled", false);
            loadingDongBoEmail(false);

        }
    });
}



function PhanTichAll() {
    loadingDongBoEmail(true, "Đang phân tích Email. Vui lòng chờ");
    $("#btnPhanTichAll").attr("disabled", true);
    $.ajax({
        type: "GET",
        dataType: "json",
        url: '/QLHD/PhanTichEmail/' + MST + "/ALL",
        success: function (data) {
            dAlert(data.message);
            SearchMail();
            loadingDongBoEmail(false);
            $("#btnPhanTichAll").attr("disabled", false);
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR);
            goTohome(jqXHR.responseText);
            loadingDongBoEmail(false);
            $("#btnPhanTichAll").attr("disabled", false);


        }
    });
}

function DongBoEmail() {
    var searchObj = {
        "MaSoThue": MST,
    }
    $("#btnDongBoMail").attr("disabled", true);
    loadingDongBoEmail(true, "Đang kiểm tra và đồng bộ email.<br/>Vui lòng chờ đợi");

    $.ajax({
        type: "POST",
        dataType: "json",
        url: '/QLHD/DongBoEmail',
        data: searchObj,
        success: function (data) {
            if (data.status == 1) {
                let obj = data.obj;
                dAlert("Đồng bộ xong!</br>Tải được thêm: <b>" + obj.CountOk + "</b> email!");
                SearchMail();
                loadingDongBoEmail(false);
                $("#btnDongBoMail").attr("disabled", false);
            }
            else {
                dAlert(data.message);
                $("#btnDongBoMail").attr("disabled", false);
                loadingDongBoEmail(false);

            }
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR);
            goTohome(jqXHR.responseText);
            $("#btnDongBoMail").attr("disabled", false);
            loadingDongBoEmail(false);

        }
    });
}

function SearchMail() {

    var searchObj = {
        "MaSoThue": MST,
        "Keyword": txtKeyword.option("value"),
        "KetQuaPhanTich": cboKetQuaPhanTich.option("value"),
        "LoaiNgay": cboLoaiNgay.option("value"),
        "TuNgay": toJP(txtTuNgayMail.option("value")),
        "DenNgay": toJP(txtDenNgayMail.option("value")),
    }

    $.ajax({
        type: "POST",
        dataType: "json",
        url: '/QLHD/SearchMail',
        data: searchObj,
        success: function (data) {
            if (data.status == 1) {
                dataMail = data.obj;
                dgMAIL.option("dataSource", dataMail);
                dgMAIL.refresh();
            }
        },
        error: function (jqXHR, textStatus, errorThrown) {

            console.log(jqXHR);
            goTohome(jqXHR.responseText);
        }
    });

}

function DongBoHoaDonGOV(LDB) {

    PHAM_VI_DONG_BO_GOV = LDB;

    let tuNgay = dtTuNgay.option("value");
    let denNgay = dtDenNgay.option("value");
    if (tuNgay == null && denNgay == null) {
        dAlert("Giá trị Từ ngày/Đến ngày không hợp lệ")
        return;
    }
    else if (tuNgay == null) {
        dAlert("Giá trị Từ ngày không hợp lệ")
        return;
    }
    else if (denNgay == null) {
        dAlert("Giá trị Đến ngày không hợp lệ")
        return;
    }

    tuNgay = new Date(toJP(tuNgay));
    denNgay = new Date(toJP(denNgay));

    kqDongBoGOV = [];
    btnGov.option("disabled", true);
    btnGovRa.option("disabled", true);
    btnGovVao.option("disabled", true);
    setTrangThai("GOV", "DANG");
    setTimeout(function () {
        ajChungThucTaiKhoan();

    }, 100)

}

var spiner = `  
                <div style="margin-top:5px;margin-left:10px" class="spinner-border spinner-border-sm" role="status">
                    <span class="visually-hidden">Loading...</span>
            </div> <i><small>...đang xử lý...</small></i>`
function ajChungThucTaiKhoan() {
    if (resultGrid) { resultGrid.option("dataSource", []) }
    $("#t_ChungThuc,#t_DongBoTongQuat,#t_DongBoChiTiet").html('')
    beginTime = new Date();
    $("#t_ChungThuc").html(`<span class='text-muted'>1. chứng thực tài khoản</span>`);
    let tuNgay = dtTuNgay.option("value");
    let denNgay = dtDenNgay.option("value");
    if (tuNgay == null && denNgay == null) {
        dAlert("Giá trị Từ ngày/Đến ngày không hợp lệ")
        return;
    }
    else if (tuNgay == null) {
        dAlert("Giá trị Từ ngày không hợp lệ")
        return;
    }
    else if (denNgay == null) {
        dAlert("Giá trị Đến ngày không hợp lệ")
        return;
    }

    tuNgay = new Date(toJP(tuNgay));
    denNgay = new Date(toJP(denNgay));


    var searchObj = {
        'TuNgay': toJP(tuNgay),
        'DenNgay': toJP(denNgay),
        'MaSoThue': MST,
        'GuidGoi': GuidGoi,
        'LoaiDongBo': 'GOV',
        'PhamViDongBo': PHAM_VI_DONG_BO_GOV
    };
    $.ajax({
        type: "POST",
        dataType: "json",
        url: '/QLHD/ChungThucTaiKhoan',
        data: searchObj,
        timeout: timeoutCT,
        success: function (data) {
            if (data.status == -1) {
                //chua cau hinh
                if (data.message.indexOf("Chứng thực") >= 0) {
                    DevExpress.ui.dialog.alert("Chứng thực không thành công.<br/>Hãy chắc chắn rằng mật khẩu đăng nhập của Thuế đúng.<br/>Nếu bạn có thay đổi mật khẩu thì vui lòng cập nhật lại ở trang cấu hình trước khi bấm đồng bộ.", "Thông báo");
                }
                else if (data.message.indexOf("Liên hệ bộ phận")>=0) {
                    DevExpress.ui.dialog.alert(data.message);
                }
                else {
                    let msg = data.message;
                    msg += `<br/><br/><a class='fs-18px text-danger fw-bold' href="/CapNhatThongTin/${MST}/${GuidGoi}" target="_blank">CLICK VÀO ĐÂY ĐỂ CẬP NHẬT LẠI MẬT KHẨU MỚI</a>`
                    var result = DevExpress.ui.dialog.alert(msg, "Thông báo");
                    result.done(function (dialogResult) {
                        setTimeout(function () {
                            location.reload();
                        }, 1000);
                    });
                }
                hideModal("mDongBo");

            }
            else {
                $("#t_ChungThuc").html(`<span class='text-dark fw-bold'>1. Chứng thực tài khoản: thành công</span><br/>`);
                if (MuaVaoNhieu || BanRaNhieu) {
                    $("#t_DongBoTongQuat").html(`<span class='text-muted'>2. Từ ngày ${toVn(tuNgay)} đến ngày ${toVn(denNgay)} có: </span><br/>`);
                }
                else {
                    $("#t_DongBoTongQuat").html(`<span class='text-muted'>2. Từ ngày ${toVn(tuNgay)} đến ngày ${toVn(denNgay)} có: </span>${spiner}<br/>`);
                }

                if ((MuaVaoNhieu && searchObj.PhamViDongBo == "MUA_VAO")
                    ||
                    (BanRaNhieu && searchObj.PhamViDongBo == "BAN_RA")
                ) {
                    $("#t_DongBoTongQuat_3").html(`${spiner}<br/>`);
                    searchObj.Count = 0;
                    searchObj.strTuNgay = searchObj.TuNgay;
                    searchObj.strDenNgay = searchObj.DenNgay;
                    kqDongBoGOVPhanCap = [];
                    dataTongQuat = [];
                    DongBoHoaDonBanRaPhanCap(searchObj);
                }
                else {
                    $.ajax({
                        type: "POST",
                        dataType: "json",
                        url: '/QLHD/DongBoHoaDonTongQuat',
                        data: searchObj,
                        timeout: 180000,
                        success: function (data) {
                            if (data.status == -1) {
                                //chua cau hinh
                                DevExpress.ui.dialog.alert(data.message, "Thông báo");
                                hideModal("mDongBo");
                            }
                            else {
                                dspThongBao();
                                let lstKQ = data.obj;
                                let thongTinDongBo = { "Data": [] };
                                let htmlKQ = ``;
                                if (searchObj.PhamViDongBo == "FULL") {
                                    htmlKQ = `&nbsp;&nbsp;&nbsp;- ${lstKQ[0].message.replace('Đồng bộ được ', '')}<br/>&nbsp;&nbsp;&nbsp;- ${lstKQ[1].message.replace('Đồng bộ được ', '')}<br/> `
                                    if (lstKQ[0].obj && lstKQ[0].obj.listDongBo.length > 0) {
                                        thongTinDongBo.Data = thongTinDongBo.Data.concat(lstKQ[0].obj.listDongBo);
                                    }
                                    if (lstKQ[1].obj && lstKQ[1].obj.listDongBo.length > 0) {
                                        thongTinDongBo.Data = thongTinDongBo.Data.concat(lstKQ[1].obj.listDongBo);
                                    }

                                }
                                else if (searchObj.PhamViDongBo == "MUA_VAO") {
                                    htmlKQ = `&nbsp;&nbsp;&nbsp;- ${lstKQ[0].message.replace('Đồng bộ được ', '')}<br/> `
                                    if (lstKQ[0].obj && lstKQ[0].obj.listDongBo.length > 0) {
                                        thongTinDongBo.Data = thongTinDongBo.Data.concat(lstKQ[0].obj.listDongBo);
                                    }

                                }
                                else if (searchObj.PhamViDongBo == "BAN_RA") {
                                    htmlKQ = `&nbsp;&nbsp;&nbsp;- ${lstKQ[1].message.replace('Đồng bộ được ', '')}<br/> `
                                    if (lstKQ[1].obj && lstKQ[1].obj.listDongBo.length > 0) {
                                        thongTinDongBo.Data = thongTinDongBo.Data.concat(lstKQ[1].obj.listDongBo);
                                    }
                                }
                                if (htmlKQ.indexOf("hết ") >= 0) {
                                    htmlKQ = `<span class='text-danger' style='font-size:16pt'>${htmlKQ}</span>`
                                }
                                $("#t_DongBoTongQuat").html(`<span class='text-dark fw-bold'>2. Từ ngày ${toVn(tuNgay)} đến ngày ${toVn(denNgay)} có:<br/>${htmlKQ}</span>`)
                                $("#t_DongBoChiTiet").html(`<span class='text-muted'>3. Đồng bộ HĐ chi tiết:</span></br>${spiner}`)

                                thongTinDongBo.MaSoThue = MST;
                                thongTinDongBo.GuidGoi = GuidGoi;

                                kqDongBoGOV = thongTinDongBo.Data;
                                if (kqDongBoGOV.length == 0) {
                                    btnGov.option("disabled", false);
                                    btnGovRa.option("disabled", false);
                                    btnGovVao.option("disabled", false);
                                    setTrangThai('GOV', 'XONG');
                                    $("#t_DongBoChiTiet").html(`<span class='text-dark fw-bold'>3. Đồng bộ hóa đơn: xong</span>`)
                                    return;
                                }
                                var COLUMNS = [
                                    { dataField: "Loai", headerCellTemplate: "Loại HĐ" },
                                    { dataField: "NgayLap", headerCellTemplate: "Ngày lập", type: 'datetime', format: 'dd/MM/yy' },
                                    { dataField: "KyHieuMauSo", headerCellTemplate: "Ký hiệu<br/>Mẫu số" },
                                    { dataField: "KyHieuHoaDon", headerCellTemplate: "Ký hiệu<br/>Hóa đơn" },
                                    { dataField: "SoHoaDon", headerCellTemplate: "Số<br/>Hóa đơn" },
                                    { dataField: "Type", headerCellTemplate: "Loại<br/>Đồng bộ" },
                                    { dataField: "KetQuaDongBo", headerCellTemplate: "Kết quả<br/>Đồng bộ" },
                                ];
                                var TOTAL_COLUMNS = [];

                                TOTAL_COLUMNS.push({
                                    column: 'KetQuaDongBo',
                                    summaryType: "count",
                                    displayFormat: 'Tổng số hóa đơn: 0/{0}',
                                });

                                resultGrid = $("#result").dxDataGrid({
                                    dataSource: kqDongBoGOV,
                                    repaintChangesOnly: true,

                                    scrolling: {
                                        columnRenderingMode: 'virtual',
                                        useNative: false,
                                        renderAsync: true,
                                        showScrollbar: "always"
                                    },
                                    paging: { enabled: false },
                                    noDataText: "",
                                    height: newHeight - 100,
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
                                        totalItems: TOTAL_COLUMNS
                                    },
                                    columns: COLUMNS
                                }).dxDataGrid("instance");
                                hideModal("mDongBo");
                                var CHUNK_S = 50;
                                DU_LIEU_DONG_BO = chunks(CHUNK_S, kqDongBoGOV);
                                ajDongBoChiTiet(DU_LIEU_DONG_BO, 0, DU_LIEU_DONG_BO.length);
                            }
                        },
                        error: function (jqXHR, textStatus, errorThrown) {
                            if (textStatus == 'timeout') {
                                dAlert(timeoutStr) 
                            }
                            goTohome(jqXHR.responseText);
                        }
                    });
                }
            }
        },
        error: function (jqXHR, textStatus, errorThrown) {

            if (textStatus == 'timeout') {
                dAlert(timeoutStrCT)
            }

            console.log(jqXHR);
            goTohome(jqXHR.responseText);
        }
    });
}
var kqDongBoGOVPhanCap = [];

function DongBoHoaDonBanRaPhanCap(searchObj) {
    let tuNgay = searchObj.TuNgay;
    let denNgay = searchObj.DenNgay;
    if (tuNgay > denNgay) {
        $("#t_DongBoTongQuat_3").html(``);

        $("#t_DongBoChiTiet").html(`<span class='text-muted'>3. Đồng bộ HĐ chi tiết:</span></br>${spiner}`)

        var thongTinDongBo = {};
        thongTinDongBo.MaSoThue = MST;
        thongTinDongBo.GuidGoi = GuidGoi;
        thongTinDongBo.Data = kqDongBoGOVPhanCap;
        kqDongBoGOV = thongTinDongBo.Data;
        if (kqDongBoGOV.length == 0) {
            btnGov.option("disabled", false);
            btnGovRa.option("disabled", false);
            btnGovVao.option("disabled", false);
            setTrangThai('GOV', 'XONG');
            $("#t_DongBoChiTiet").html(`<span class='text-dark fw-bold'>3. Đồng bộ hóa đơn: xong</span>`)
            return;
        }



        var COLUMNS = [
            { dataField: "Loai", headerCellTemplate: "Loại HĐ" },
            { dataField: "NgayLap", headerCellTemplate: "Ngày lập", type: 'datetime', format: 'dd/MM/yy' },
            { dataField: "KyHieuMauSo", headerCellTemplate: "Ký hiệu<br/>Mẫu số" },
            { dataField: "KyHieuHoaDon", headerCellTemplate: "Ký hiệu<br/>Hóa đơn" },
            { dataField: "SoHoaDon", headerCellTemplate: "Số<br/>Hóa đơn" },
            { dataField: "Type", headerCellTemplate: "Loại<br/>Đồng bộ" },
            { dataField: "KetQuaDongBo", headerCellTemplate: "Kết quả<br/>Đồng bộ" },
        ];
        var TOTAL_COLUMNS = [];

        TOTAL_COLUMNS.push({
            column: 'KetQuaDongBo',
            summaryType: "count",
            displayFormat: 'Tổng số hóa đơn: 0/{0}',
        });

        resultGrid = $("#result").dxDataGrid({
            dataSource: kqDongBoGOVPhanCap,
            repaintChangesOnly: true,

            scrolling: {
                columnRenderingMode: 'virtual',
                useNative: false,
                renderAsync: true,
                showScrollbar: "always",
                mode: "virtual" // or "virtual" | "infinite"

            },
            paging: { enabled: false },
            noDataText: "",
            height: newHeight - 100,
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
                totalItems: TOTAL_COLUMNS
            },
            columns: COLUMNS
        }).dxDataGrid("instance");
        hideModal("mDongBo");
        var CHUNK_S = 250; // calcChunks(kqDongBoGOV.length);
        DU_LIEU_DONG_BO = chunks(CHUNK_S, kqDongBoGOVPhanCap);

        ajDongBoChiTiet(DU_LIEU_DONG_BO, 0, DU_LIEU_DONG_BO.length);
    }
    else {
        var j = JSON.parse(JSON.stringify(searchObj));
        j.DenNgay = j.TuNgay;
        $.ajax({
            type: "POST",
            dataType: "json",
            url: '/QLHD/DongBoHoaDonTongQuat',
            data: j,
            timeout: timeoutDBTQ,
            success: function (data) {
                if (data.status == -1) {
                    //chua cau hinh
                    DevExpress.ui.dialog.alert(data.message, "Thông báo");
                    hideModal("mDongBo");
                    searchObj.TuNgay = searchObj.DenNgay;
                    searchObj.TuNgay = toJP(addDate(new Date(searchObj.TuNgay), 1));
                    DongBoHoaDonBanRaPhanCap(searchObj);
                }
                else {
                    //  dspThongBao();
                    let lstKQ = data.obj;
                    //"Đã sử dụng hết MaxQuota (445) của Mã Số Thuế"
                    if (lstKQ[1].message.indexOf("Đồng bộ được") < 0) {
                        let msg = `<span class='fs-18px text-danger fw-bold'>${lstKQ[1].message}</span>`
                        $("#t_DongBoTongQuat").html(`<span class='text-dark fw-bold'>2. Từ ngày ${toVn(new Date(searchObj.strTuNgay))} đến ngày ${toVn(new Date(searchObj.strDenNgay))} có:</span><br/>${msg}`)
                        $("#t_DongBoTongQuat_3").html('')
                        btnGov.option("disabled", false);

                        btnGovRa.option("disabled", false);
                        btnGovVao.option("disabled", false);
                        return;

                    }
                    let idx = PHAM_VI_DONG_BO_GOV == "BAN_RA" ? 1 : 0;
                    let c = lstKQ[idx].obj.listDongBo.length;;
                    searchObj.Count += c;
                    //   htmlKQ = `&nbsp;&nbsp;&nbsp;-${searchObj.TuNgay} - ${c} hóa đơn bán ra<br/> `

                    //let thongTinDongBo = { "Data": [] };
                    //thongTinDongBo.Data.concat(lstKQ[1].obj.listDongBo)
                    kqDongBoGOVPhanCap.push(...lstKQ[idx].obj.listDongBo);
                    $("#t_DongBoTongQuat").html(`<span class='text-dark fw-bold'>2. Từ ngày ${toVn(new Date(searchObj.strTuNgay))} đến ngày ${toVn(new Date(searchObj.strDenNgay))} có: <span class='text-danger' style='font-size:16pt'>${searchObj.Count}</span> HĐ</span><br/>`)

                    dataTongQuat.push({ 'NGÀY': searchObj.TuNgay, 'SỐ LƯỢNG HĐ': c });
                    $("#t_DongBoTongQuat_2").dxDataGrid({
                        dataSource: dataTongQuat,
                        repaintChangesOnly: true,
                        scrolling: {
                            columnRenderingMode: 'virtual',
                            useNative: false,
                            renderAsync: true,
                            showScrollbar: "always"
                        },
                        paging: { enabled: false },
                        noDataText: "",
                        height: 430,
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
                            totalItems: [{
                                column: 'SỐ LƯỢNG HĐ',
                                summaryType: "sum",
                                displayFormat: `Tổng: {0}`,
                            }]
                        },
                    }).dxDataGrid("instance");

                    searchObj.TuNgay = toJP(addDate(new Date(searchObj.TuNgay), 1));
                    DongBoHoaDonBanRaPhanCap(searchObj);
                }
            },
            error: function (jqXHR, textStatus, errorThrown) {
                if (textStatus == 'timeout') {
                    dAlert(timeoutStrDBTQ);
                    //dAlert("Không kết nối được Server TCT. Vui lòng thử lại vào lúc khác");
                    ////do something. Try again perhaps?
                    //searchObj.TuNgay = searchObj.DenNgay;
                    //searchObj.TuNgay = toJP(addDate(new Date(searchObj.TuNgay), 1));
                    //DongBoHoaDonBanRaPhanCap(searchObj);
                }
                goTohome(jqXHR.responseText);
            }
        });

    }



}



function calcChunks(i) {
    if (maxUser == '1') {
        return 50;
    }

    let s = 1;
    if (i <= 50) {
        s = 2;
    }
    else if (i <= 100) {
        s = 3;
    }
    else {
        s = 4;
    }
    let chunks = Math.ceil(i / s);
    if (chunks <= 15) chunks = 15;
    if (chunks >= 35) chunks = 35;


    return chunks

}
var CHUNK_S = 4;
var DU_LIEU_DONG_BO = [];
var beginTime;

//function ajDongBoBoSung() {
//    $.ajax({
//        type: "POST",
//        dataType: "json",
//        url: '/QLHD/DongBoBoSung',
//        data: {
//            "MaSoThue": MST,
//            "GuidGoi": GuidGoi,
//            "Data": kqDongBoGOV,
//        },
//        success: function (data) {
//            if (data.status == -1) {

//            }
//            else {
//             //   dAlert("DONG BO BO SUNG XONG");
//            }
//        },
//        error: function (jqXHR, textStatus, errorThrown) {
//            console.log(jqXHR);
//            goTohome(jqXHR.responseText);
//        }
//    });
//}
function ajDongBoChiTiet(thongTinDongBo, b, e) {
    if (b == e) {
        endTime = new Date();
        btnGov.option("disabled", false);

        btnGovRa.option("disabled", false);
        btnGovVao.option("disabled", false);
        setTrangThai('GOV', 'XONG')
        let giay = (endTime - beginTime) / 1000;
        $("#t_DongBoChiTiet").html(`<span class='text-dark fw-bold'>3. Đồng bộ hóa đơn: xong
        <br/><span class='text-danger'>
        &nbsp;&nbsp;&nbsp;- Tổng số HĐ: ${kqDongBoGOV.length} hóa đơn<br/>
        &nbsp;&nbsp;&nbsp;- Thời gian xử lý ${giay} giây</span>
        </span>`);
        return;
    }
    var dataDongBo = DU_LIEU_DONG_BO[b];

    var isFull = true;
    if (BanRaNhieu == 1 && PHAM_VI_DONG_BO_GOV == "BAN_RA") {
        isFull = false;
    }

    var lstID = [];
    for (let i in dataDongBo) {
        let d = dataDongBo[i];
        if ((d.Type == "X" && !isFull) || d.Type == null || d.Type == "") {
            lstID.push(d.Id);
        }
    }
    if (lstID.length > 0) {
        var x = kqDongBoGOV.filter(p => lstID.indexOf(p.Id) >= 0);
        for (let i = 0; i < x.length; i++) {
            x[i].KetQuaDongBo = "OK";
        }
        dspKetQuaDongBo();
        dataDongBo = dataDongBo.filter(p => lstID.indexOf(p.Id) < 0);
    }
    if (dataDongBo.length > 0) {
        $.ajax({
            type: "POST",
            dataType: "json",
            url: '/QLHD/DongBoChiTiet',
            data: {
                "MaSoThue": MST,
                "GuidGoi": GuidGoi,
                "Data": dataDongBo,
                "IsFull": isFull
            },
            success: function (data) {
                if (data.status == -1) {
                    dAlert(data.message);
                    return;

                }
                else {
                    var lstID = data.obj;
                    var x = kqDongBoGOV.filter(p => lstID.indexOf(p.Id) >= 0);
                    for (let i = 0; i < x.length; i++) {
                        x[i].KetQuaDongBo = "OK";
                    }
                    dspKetQuaDongBo();
                    ajDongBoChiTiet(thongTinDongBo, b + 1, e);
                }
            },
            error: function (jqXHR, textStatus, errorThrown) {
                console.log(jqXHR);
                goTohome(jqXHR.responseText);
            }
        });
    }
    else {
        ajDongBoChiTiet(thongTinDongBo, b + 1, e);
    }



}

function dspKetQuaDongBo() {
    var countOK = kqDongBoGOV.filter(p => p.KetQuaDongBo == "OK").length;
    resultGrid.option("dataSource", kqDongBoGOV);
    TOTAL_COLUMNS = [{
        column: 'KetQuaDongBo',
        summaryType: "count",
        displayFormat: `Tổng số hóa đơn: ${countOK}/{0}`,
    }];
    resultGrid.option("summary", { totalItems: TOTAL_COLUMNS });
    resultGrid.refresh();

    $("#t_DongBoChiTiet").html(`<span class='text-muted'>3. Đồng bộ HĐ chi tiết: đang thực hiện, vui lòng chờ đợi</span>
                    <br/>
                    <span class='text-danger'>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;xử lý được ${countOK}/${kqDongBoGOV.length} hóa đơn</span><br/>${spiner}
                `)

}


function initCtrl() {

    dtTuNgay = $("#dtTuNgay").dxDateBox({
        displayFormat: "dd/MM/yyyy",
        label: "Từ ngày",
        labelMode: "floating",
        height: 30,
        useMaskBehavior: true,
    }).dxDateBox("instance");

    dtDenNgay = $("#dtDenNgay").dxDateBox({
        displayFormat: "dd/MM/yyyy",
        useMaskBehavior: true,
        label: "Đến ngày",
        height: 30,
        labelMode: "floating",
    }).dxDateBox("instance");

    stNam = new Date().getFullYear();

    txtNam = $("#txtNam").dxNumberBox({
        value: stNam,
        labelMode: "floating",
        label: "Chọn năm",
        placeholder: "chọn năm",
        visible: false,
        step: 0,
        onValueChanged(e) {

            var x = KhoangNgay(cboQuy.option("value"), true, e.value);
            stNam = e.value;
            dtTuNgay.option("value", x.start);
            dtDenNgay.option("value", x.end);
        }
    }).dxNumberBox("instance");

    cboQuy = $("#cboQuy").dxSelectBox({
        label: "Chọn khoảng Thời gian",
        labelMode: "floating",
        placeholder: "chọn khoảng Thời gian",
        elementAttr: {
            style: "height:29px;"
        },
        items: ["Hôm nay", "1 tuần", "Tháng này", "Tháng 1", "Tháng 2", "Tháng 3", "Tháng 4", "Tháng 5", "Tháng 6", "Tháng 7", "Tháng 8", "Tháng 9", "Tháng 10", "Tháng 11", "Tháng 12", "Quý 1", "Quý 2", "Quý 3", "Quý 4",
            //"Năm này", "Năm trước"
        ],
        onValueChanged: function (e) {
            let val = e.value;
            let namVisible = !(val == "Hôm nay" || val == "1 tuần" || val == "Tháng này");
            txtNam.option("visible", namVisible);
            var x = KhoangNgay(e.value, true, stNam);
            dtTuNgay.option("value", x.start);
            dtDenNgay.option("value", x.end);
        },
    }).dxSelectBox("instance");

    cboQuy.option("value", "1 tuần");

    btnGovVao = $("#btnGovVao").dxButton({
        icon: 'ni ni-hot',
        text: "Đồng bộ HĐĐT ĐẦU VÀO",
        stylingMode: 'outlined',
        type: 'normal',
        elementAttr: {
            "class": "bg-primary text-white",
        },

        width: 200,
        onInitialized(e) {
            var s = "margin-right:25px";
            e.element.attr("style", s);
        },

        onClick: function () {
            setTrangThai("GOV", "CHO");
            DongBoHoaDonGOV('MUA_VAO');
        }
    }).dxButton("instance");
    $("#btnGovVao .dx-icon").attr("style", "color:white");


    btnGovRa = $("#btnGovRa").dxButton({
        icon: 'ni ni-hot',
        text: "Đồng bộ HĐĐT ĐẦU RA",
        stylingMode: 'outlined',
        type: 'normal',
        width: 200,
        elementAttr: {
            "class": "bg-danger ",
            "style": "color:yellow;width:200px",
        },

        onInitialized(e) {
            var s = " margin-right:25px";
            e.element.attr("style", s);
        },

        onClick: function () {
            setTrangThai("GOV", "CHO");
            DongBoHoaDonGOV('BAN_RA');
        }
    }).dxButton("instance");
    $("#btnGovRa .dx-icon").attr("style", "color:yellow");

    btnGov = $("#btnGov").dxButton({
        icon: 'ni ni-hot',
        text: "Đồng bộ HĐĐT VÀO/RA",
        stylingMode: 'outlined',
        type: 'normal',
        width: 200,
        elementAttr: {
            "style": "background-color: #8c0f9d;color:white;width:200px",
        },

        onInitialized(e) {
            var s = e.element.attr("style") + "; margin-right:25px";
            e.element.attr("style", s);
        },

        onClick: function () {
            setTrangThai("GOV", "CHO");
            DongBoHoaDonGOV('FULL');
        }
    }).dxButton("instance");
    $("#btnGov .dx-icon").attr("style", "color:white");

    if (MuaVaoNhieu || BanRaNhieu) {
        btnGov.option("visible", false)
    }

    setTrangThai("GOV", "CHO");
    setTrangThai("Mail", "CHO");
    if (GhiChuNibot) {
        btnGov.option("disabled", true);
        btnGovRa.option("disabled", true);
        btnGovVao.option("disabled", true);
    }
}
var ngaySync;
var PHAM_VI_DONG_BO_GOV;
var kqDongBoGOV = [];
function ajaxDongBoGOV(tuNgay, denNgay) {

    type = 'GOV';
    let cong = 3;
    var denNgay2 = addDate(tuNgay, cong);

    if (denNgay2 > denNgay)
        denNgay2 = denNgay;

    if (tuNgay > denNgay2) {
        btnGov.option("disabled", false);
        btnGovRa.option("disabled", false);
        btnGovVao.option("disabled", false);
        setTrangThai(type, "XONG");
        return;
    }

    var searchObj = {
        'TuNgay': toJP(tuNgay),
        'DenNgay': toJP(denNgay2),
        'MaSoThue': MST,
        'GuidGoi': GuidGoi,
        'LoaiDongBo': 'GOV',
        'PhamViDongBo': PHAM_VI_DONG_BO_GOV
    };

    $.ajax({
        type: "POST",
        dataType: "json",
        url: '/QLHD/DongBo',
        data: searchObj,
        success: function (data) {
            if (data.status == -2) {
                //chua cau hinh
                DevExpress.ui.dialog.alert(data.message, "Thông báo");
                setTrangThai(type, "CHO");
                btnGov.option("disabled", false);
                btnGovRa.option("disabled", false);
                btnGovVao.option("disabled", false);

            }
            else if (data.status == -1) {
                //loi dong bo
                let obj = JSON.stringify(data.obj);
                var result = DevExpress.ui.dialog.alert(data.message + "\r\n" + obj, "Lỗi đồng bộ");
                let objmua = data.obj[0].message;
                let objban = data.obj[1].message;

                kqDongBoGOV.push({
                    'TU_NGAY': toVn(tuNgay),
                    'DEN_NGAY': toVn(denNgay2),
                    'MUA_VAO': objmua,
                    'BAN_RA': objban,
                    'TONG': ''
                });
            }
            else if (data.status == 1) {
                let objmua = data.obj[0].message;
                let MUA_COUNT = 0;
                let objban = data.obj[1].message;
                let BAN_COUNT = 0;
                let str = '<br/>Hãy thử đồng bộ lại trong khoảng thời gian này. Nếu vẫn không được xin liên hệ PKT';
                str = '';
                if (objmua.indexOf('Đồng bộ được ') >= 0 && objmua.indexOf('hoá đơn mua vào') >= 0) {
                    objmua = objmua.replace('Đồng bộ được ', '').replace('hoá đơn mua vào', '');
                    objmua = objmua.trim()
                    MUA_COUNT = parseInt(objmua);
                }
                else {
                    dAlert(`Lỗi đồng bộ từ ${searchObj.TuNgay} - ${searchObj.DenNgay}<br/>${objmua}${str}`, "Lỗi Đồng Bộ")
                    btnGov.option("disabled", false);
                    btnGovRa.option("disabled", false);
                    btnGovVao.option("disabled", false);
                    setTrangThai(type, "XONG");
                    return;
                }

                if (objban.indexOf('Đồng bộ được ') >= 0 && objban.indexOf('hoá đơn bán ra') >= 0) {
                    objban = objban.replace('Đồng bộ được ', '').replace('hoá đơn bán ra', '');
                    objban = objban.trim()
                    BAN_COUNT = parseInt(objban);
                }
                else {
                    dAlert(`Lỗi đồng bộ từ ${searchObj.TuNgay} - ${searchObj.DenNgay}<br/>${objban}${str}`, "Lỗi Đồng Bộ")
                    btnGov.option("disabled", false);
                    btnGovRa.option("disabled", false);
                    btnGovVao.option("disabled", false);
                    setTrangThai(type, "XONG");
                    return;
                }

                kqDongBoGOV.push({
                    'TU_NGAY': toVn(tuNgay),
                    'DEN_NGAY': toVn(denNgay2),
                    'MUA_VAO': MUA_COUNT,
                    'BAN_RA': BAN_COUNT,
                    'TONG': MUA_COUNT + BAN_COUNT
                });

                resultGrid.refresh();

                if (denNgay2 < denNgay) {
                    denNgay2 = addDate(denNgay2, 1);
                    ajaxDongBoGOV(denNgay2, denNgay);
                }
                else {
                    btnGov.option("disabled", false);
                    btnGovRa.option("disabled", false);
                    btnGovVao.option("disabled", false);
                    setTrangThai(type, "XONG");
                    return;
                }
            }
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR);
            if (denNgay2 < denNgay) {
                denNgay2 = addDate(denNgay2, 1);
                ajaxDongBoGOV(denNgay2, denNgay);
            }
            else {
                btnGov.option("disabled", false);
                btnMail.option("disabled", false);
                btnGovRa.option("disabled", false);
                btnGovVao.option("disabled", false);
                return;
            }
            goTohome(jqXHR.responseText);
        }
    });
}


function setTrangThai(type, val) {
    if (type == "GOV") {
        if (val == 'DANG') {
            console.log(type, val, PHAM_VI_DONG_BO_GOV)
            if (PHAM_VI_DONG_BO_GOV == "MUA_VAO")
                $("#lblTrangThai").html(dictTrangThai["DANG_GOV_MUA_VAO"]);
            else if (PHAM_VI_DONG_BO_GOV == "BAN_RA")
                $("#lblTrangThai").html(dictTrangThai["DANG_GOV_BAN_RA"]);
            else
                $("#lblTrangThai").html(dictTrangThai["DANG_GOV_FULL"]);

        }
        else {
            $("#lblTrangThai").html(dictTrangThai[val]);
        }
        // if (val == 'DANG')
        //     $("#spinner").removeClass("d-none");
        // else
        //     $("#spinner").addClass("d-none");


    }
    else {
        $("#lblTrangThaiMail").html(dictTrangThai[val]);
    }

}


function waitDlg(type, isShow) {
    if (type == "GOV") {
        if (isShow) {
            $("#wait").removeClass("d-none");
            btnGov.option("disabled", true);
            btnGovRa.option("disabled", true);
            btnGovVao.option("disabled", true);
            $("#result").html('');
        }
        else {
            $("#wait").addClass("d-none");
            btnGov.option("disabled", false);
            btnGovRa.option("disabled", false);
            btnGovVao.option("disabled", false);
        }
    }
    else {
        if (isShow) {
            $("#waitMail").removeClass("d-none");
            btnGov.option("disabled", true);
            btnGovRa.option("disabled", true);
            btnGovVao.option("disabled", true);
            $("#resultMail").html('');
        }
        else {
            $("#waitMail").addClass("d-none");
            btnGov.option("disabled", false);
            btnGovRa.option("disabled", false);
            btnGovVao.option("disabled", false);
        }
    }
}