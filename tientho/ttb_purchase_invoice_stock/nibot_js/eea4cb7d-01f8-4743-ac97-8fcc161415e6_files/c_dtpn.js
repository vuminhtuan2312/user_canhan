
//c_dtpn 26/12/24
function prepareObjectDTPN(type) {
    var searchObj = {
        'Keyword': txtDTPN_TimKiem.option("value").trim(),
        'MaSoThue': MST,
        'Loai': type,
    };
    return searchObj;
}
var txtNamHD;

function DanhDauLaiHoaDonHangLoat() {
    let bodyHtml = `
        <div class='row  '>
         
                <div class='col-12 d-flex justify-content-start '>
                    <div id="txtNamHD"></div> <div style='margin-top:10px'>&nbsp;&nbsp;&nbsp; - Nhập năm cần đánh dấu lại</div>
                </div>
                <div class='col-12 mt-2 alert alert-danger'>
                    <button class='btn btn-danger btn-sm'  onClick='DanhLai("TINHCHAT")'><em class="icon ni ni-check-circle-cut"></em>&nbsp;Đánh dấu lại tính chất HĐ Thường/Dịch vụ</button>
                    <p class='mt-2'>Nếu cột <b>Hóa đơn DV</b> trên lưới dữ liệu được tick thì những hóa đơn liên quan đến ĐTPN đó là HĐDV. Ngược lại, sẽ là hóa đơn bình thường<br/>
                             <small>Ví dụ: những ĐTPN cung cấp Hóa đơn <b>ăn uống, tiếp khách</b>, ta nên chọn là HĐDV.</small>
                    </p>
                </div>
                <div class='col-12  alert alert-primary'>
                    <button class='btn btn-primary btn-sm' onClick='DanhLai("DUYETNOIBO")'><em class="icon ni ni-check-round-cut"></em>&nbsp;Đánh dấu lại trạng thái Duyệt Nội Bộ của HĐ</button>
                    <p class='mt-2'>Đánh dấu lại <b>trạng thái duyệt nội bộ</b> của HĐ dựa vào giá trị của cột Duyệt nội bộ trên lưới dữ liệu.
                    <br/><small>Ví dụ: những HĐ <b>ngân hàng</b> nếu như không kết xuất ra bảng kê, có thể chọn trạng thái Duyệt nội bộ mặc định là <b>'Không hợp lệ'</b>. Sau đó, khi kết xuất, ta chọn trạng thái duyệt là <b>'Chờ duyệt'</b> để loại ra khỏi bảng kê.</small>
                    </p>
                </div>
        </div>
    `
    createModal("mDanhDauLai", "Đánh dấu lại HĐ hàng loạt", bodyHtml, '')

    showModal("mDanhDauLai");

    txtNamHD = $("#txtNamHD").dxTextBox({
        label: "Năm",
        width: 120,
        value: new Date().getFullYear().toString(),
        placeholder: "",
    }).dxTextBox("instance")


}

function DanhLai(loai) {
    let msg = ""
    if (loai == "TINHCHAT") {
        msg = "Đang đánh dấu lại tính chất hóa đơn thường, hóa đơn dịch vụ"
    }
    else if (loai == "DUYETNOIBO") {
        msg = "Đang đánh dấu lại trạng thái duyệt nội bộ của hóa đơn"

    }
    hideModal("mDanhDauLai");

    loadingDTPN(true, msg);


    $.ajax({
        type: "POST",
        dataType: "json",
        url: '/QLHD/DanhLaiTinhChatHoaDon',
        data: {
            "MaSoThue": MST,
            "Nam": txtNamHD.option("value"),
            "Loai":loai,
        },
        success: function (data) {
            loadingDTPN(false);
            dAlert("Đã đánh dấu lại tính chất hóa đơn xong!");

        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR);
            loadingDTPN(false);
            goTohome(jqXHR.responseText);

        }
    });
}

function DanhDauLaiHDDV() { 
    let bodyHtml = `
        <div class='row'>
                <div class='col-12'>
                    <p>Dựa vào <b>tính chất là Hóa đơn dịch vụ</b> của các đối tượng pháp nhân có trong lưới dữ liệu. NIBOT sẽ đánh dấu lại toàn bộ hóa đơn có trong hệ thống theo nguyên tắc:<br/>
                       - Nếu cột HĐDV được tick chọn thì những hóa đơn liên quan đến ĐTPN đó là HĐDV. Ngược lại, sẽ là hóa đơn bình thường<br/>
                    </p>
                    <hr/>
                </div>
                <div class='col-12 d-flex justify-content-start'>
                    <div id="txtNamHD"></div> <div style='margin-top:10px'>&nbsp;&nbsp;&nbsp; - Để trống nếu như muốn đánh dấu lại tất cả các năm</div>
                </div>
                <div class='col-12 mt-3 text-center'>
                    <button class='btn btn-danger btn-sm' id="btnDanhLai"><em class='icon ni ni-check'></em>&nbsp;Thực hiện đánh dấu lại tính chất hóa đơn</button>
                </div>
        </div>
    `
    createModal("mDanhDauLai", "Đánh dấu lại HĐ hàng loạt", bodyHtml, '')

    showModal("mDanhDauLai");

    txtNamHD = $("#txtNamHD").dxTextBox({
        label: "Năm",
        width: 120,
        value: new Date().getFullYear().toString(),
        placeholder: "",
    }).dxTextBox("instance")



}
var TuNgayDTPN, DenNgayDTPN;

function DongBoDTPN() {


    let bodyHtml = `
                    <div class='row'>
                            <div class='col-12'>
                           
                                <div class='d-flex justify-content-start'>
                                     <b style='margin-top:10px'> Thời gian đồng bộ:</b> &nbsp;&nbsp;&nbsp;
                                    <div id="TuNgayDTPN"></div>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<div id="DenNgayDTPN"></div> 
                                </div>
                                 <div style='margin-top:15px' class='d-flex justify-content-start'>
                                 <b>Loại hóa đơn:</b>
                                    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                                     <label style='font-size:16px'>
                                        <input type="radio" id="chkVaoDTPN" name="rdoDTPN" checked>
                                        Đầu Vào
                                    </label>
                                    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                                    <label style='font-size:16px'>
                                        <input type="radio" id="chkRaDTPN"  name="rdoDTPN" >
                                        Đầu Ra
                                    </label>
                                </div>
                            </div>
                            <div class='col-12 text-center'>
                                <hr/>
                                <button class='btn btn-primary btn-sm' id="btnDongBoDTPN"><em class='icon ni ni-reload'></em>&nbsp;Đồng bộ ĐTPN</button>
                            </div>
                    </div>
                `

    var x = KhoangNgay("Năm này", false, "");

    createModal("mDongBoDTPN", "Đồng bộ Đối tượng Pháp nhân", bodyHtml, '')

    TuNgayDTPN = $("#TuNgayDTPN").dxDateBox({
        label: "Từ ngày",
        elementAttr: {
            "style": "font-size:16px"
        },
        width: 130,
        displayFormat: "dd/MM/yyyy",
        useMaskBehavior: true,
        value: x.start,
    }).dxDateBox("instance")

    DenNgayDTPN = $("#DenNgayDTPN").dxDateBox({
        label: "Đến ngày",
        elementAttr: {
            "style": "font-size:16px"
        },
        width: 130,
        displayFormat: "dd/MM/yyyy",
        useMaskBehavior: true,
        value: x.end
    }).dxDateBox("instance")

    showModal("mDongBoDTPN");

    $("#btnDongBoDTPN").unbind().on("click", function () {

        let tuNgaydtpn = toJP(TuNgayDTPN.option("value"));
        let denNgaydtpn = toJP(DenNgayDTPN.option("value"));

        let chkVao = $("#chkVaoDTPN").prop("checked");
        let str = "ĐẦU VÀO/ĐẦU RA"
        let Loai = "";
       if (chkVao) {
            str = "ĐẦU VÀO";
            Loai = "MUA_VAO";
        }
        else  {
            str = "ĐẦU RA";
            Loai = "BAN_RA";
        }
        var result = DevExpress.ui.dialog.confirm(`Hệ thống sẽ đồng bộ đối tượng pháp nhân trong các <b>HÓA ĐƠN ${str}</b><br/>Nếu Mã số thuế của ĐTPN chưa có trong [ĐTPN của NIBOT] thì sẽ được thêm vào.<br/><br/><b>Bạn đã chắc cú chưa?</b>`, "ĐỒNG BỘ ĐTPN " + str);
        result.done(function (dialogResult) {
            if (dialogResult) {
                hideModal("mDongBoDTPN");

                loadingDTPN(true, "Đang đồng bộ ĐTPN " + str + ".<br/> Vui lòng chờ đợi")
                $.ajax({
                    type: "POST",
                    dataType: "json",
                    url: '/QLHD/DongBoDTPN',
                    data: {
                        "TuNgay": tuNgaydtpn ,
                        "DenNgay": denNgaydtpn,
                        "MaSoThue": MST,
                        "Loai": Loai,
                    },
                    success: function (data) {
                        if (data.status == 1) {
                            dAlert("Đồng bộ ĐTPN " + str + " hoàn tất", "Thông báo")
                            SearchDTPN();
                        }
                        else {
                            dAlert(data.message, "Lỗi đồng bộ")
                            SearchDTPN();

                        }
                        loadingDTPN(false)
                    },
                    error: function (jqXHR, textStatus, errorThrown) {
                        console.log(jqXHR);
                        loading(false)
                        goTohome(jqXHR.responseText);

                    }
                });
            }

        });

    });

   
}


function XoaTatCaDTPN() {

    var rows = dgDTPN.getSelectedRowsData();
    let bodyHtml = `
                    <div class='row'>
                            <div class='col-12'>
                                 <div style='margin-left:10px;margin-top:5px;line-height:35px'>
                                     <label style='font-size:14px'>
                                        <input type="radio" name="TinhChatDTPNXoa" value="0" id="rdoTinhChatDTPNXoa0" checked>
                                        Xóa tất cả Đối tượng pháp nhân
                                    </label>
                                    <br>
                                    <label style='font-size:14px'>
                                        <input type="radio" name="TinhChatDTPNXoa" value="2" id="rdoTinhChatDTPNXoa1">
                                        Xóa dòng Đối tượng pháp nhân đã được chọn (${rows.length} dòng)
                                    </label>
                                </div>
                            </div>
                            <div class='col-12 text-center'>
                                <hr/>
                                <button class='btn btn-danger btn-sm' id="btnXoaDTPN"><em class='icon ni ni-delete'></em>&nbsp;Xóa ĐTPN</button>
                            </div>
                    </div>
                `

    createModal("mXoaDoiTuongPhapNhan", "Xóa Đối Tượng Pháp Nhân", bodyHtml, '')
    showModal("mXoaDoiTuongPhapNhan");


    $("#btnXoaDTPN").unbind().on("click", function () {
        let searchObj = prepareObjectDTPN();
        searchObj.IsXoa = true;

        let strConfirm = "";
        if ($("#rdoTinhChatDTPNXoa0").prop("checked")) {
            searchObj.TinhChat = 0;
            strConfirm = "Xóa tất cả Đối tượng pháp nhân.";
        }
        else if ($("#rdoTinhChatDTPNXoa1").prop("checked")) {
            if (rows.length == 0) {
                dAlert("Chưa chọn dòng cần xóa");
                return;
            }

            searchObj.ListIdHang = rows.map(p => p.Mst + "\t" + p.MaKh);

            searchObj.TinhChat = 1;
            strConfirm = `Xóa dòng Đối tượng pháp nhân đã được chọn (${rows.length} dòng).`;
        }

        var result = DevExpress.ui.dialog.confirm(strConfirm + "<br/><b>Bạn đã chắc cú chưa?</b>", "XÓA ĐỐI TƯỢNG PHÁP NHÂN");
        result.done(function (dialogResult) {
            if (dialogResult) {

                loading(true, "Đang xóa ĐTPN<br/>Vui lòng chờ đợi");
                $.ajax({
                    type: "POST",
                    dataType: "json",
                    url: '/QLHD/DTPN',
                    data: searchObj,
                    success: function (data) {
                        if (data.status == 1) {
                            dAlert("Xóa ĐTPN thành công", "Thông báo")
                            SearchDTPN();
                        }
                        loading(false)
                        hideModal("mXoaDoiTuongPhapNhan");
                    },
                    error: function (jqXHR, textStatus, errorThrown) {
                        console.log(jqXHR);
                        loading(false)
                        goTohome(jqXHR.responseText);
                        hideModal("mXoaDoiTuongPhapNhan");


                    }
                });
            }

        });

    })
  

}
function SearchDTPN(type) {

    let searchObj = prepareObjectDTPN(type);
    if (type == 'xls') {
        loadingDTPN(true, "Đang kết xuất ĐTPN.<br/> Vui lòng chờ đợi")
    }
    else {
        loadingDTPN(true, "Đang tải danh sách ĐTPN.<br/> Vui lòng chờ đợi")
    }
    $.ajax({
        type: "POST",
        dataType: "json",
        url: '/QLHD/DTPN',
        data: searchObj,
        success: function (data) {
            if (searchObj.Loai == 'xls') {
                loadingDTPN(false, "");
                if (data.status == 1) {
                    DownloadFileExcel(data.obj.toString(), "DTPN_" + MST);
                }
            }
            else {
                loadingDTPN(false, "");
                DATA_DTPN = data;
                dspDataDTPN();

            }
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR);
            goTohome(jqXHR.responseText);

        }
    });
}
var dgDTPNExport; 


function initCtrlDTPN() {
    txtDTPN_TimKiem = $("#txtDTPN_TimKiem").dxTextBox({
        placeholder: "nhập từ khóa cần tìm: MS_DN, MST",
    }).dxTextBox("instance")


    $("#helpDTPN").html(
        `
            <div class='d-flex justify-content-end'> 
                <a  href='https://youtu.be/ixLUXA-Bre8?si=rRWOyafglnRX55WP' target='_blank'><em class=" fw-bold text-danger icon ni ni-youtube" style='font-size:32px'></em> </a> 
                <a  style='background-image: linear-gradient(45deg, #f70bc7, #5700b1);-webkit-background-clip: text; background-clip: text;color: transparent;margin-top:7px;font-weight:bold;' href='https://youtu.be/ixLUXA-Bre8?si=rRWOyafglnRX55WP' target='_blank'>&nbsp;&nbsp;Video HDSD chức năng ĐTPN&nbsp;&nbsp;</a>
            </div>
        `
    )


}



function genMaDTPN(str, dsMH) {
    var t = removeVietnameseAccent(str).replace(/[^\w\s]/gi, '');
    t = t.replace(/[\s+]/gi, '');
    t = t.substring(0, 40).toUpperCase();
    var orgT = t;
    var h = 1;
    while (dsMH.indexOf(t) >= 0) {
        t = orgT + "_" + h;
        h++;
    }
    return t;

}


function bnTaoMaDTPN() {
    let kieu = 0;
    if ($("#rdoDTPNCach1").prop("checked")) {
        kieu = 1;
    }
    if ($("#rdoDTPNCach2").prop("checked")) {
        kieu = 2;
    }
    if ($("#rdoDTPNCach3").prop("checked")) {
        kieu = 3;
    }
    if (kieu == 0) {
        dAlert("Chưa chọn kiểu tạo mã ĐPTN!");
        return;
    }

    let str = "";
    if (kieu == 1) str = "Kiểu 1: lấy MST hoặc tên cá nhân mua làm ĐTPN";
    else if (kieu == 2) str = "Kiểu 2: lấy 5 ký tự cuối của MST - kiểu của Smart Pro";
    else if (kieu == 3) str = "Kiểu 3: không dấu, không khoảng cách từ tên công ty / tên cá nhân mua";

    var result = DevExpress.ui.dialog.confirm(str + "<br/><b>Bạn đã chắc cú chưa?</b>", "Tạo Mã ĐTPN Tự Động");
    result.done(function (dialogResult) {
        if (dialogResult) {
            hideModal("mTaoMaDTPN");
            loading(true, "Đang tạo mã ĐTPN.<br/>Sẽ lâu nếu như ĐTPN nhiều<br/>Vì thế nên vui lòng chờ đợi");
            var rows = dgDTPN.getSelectedRowsData();
            if (rows.length > 0) {
                lstIdHang = rows.map(p => p.Mst+"\t"+p.MaKh);
            }
            else {
                lstIdHang = []
            }
            let TienTo = $("#txtTienTo").val().trim();
            let HauTo = $("#txtHauTo").val().trim();

            setTimeout(function () {
                let searchObj = {
                    'IsTiny': true,
                    'MaSoThue': MST,
                    'KieuTaoMa': kieu,
                    'ListIdHang': lstIdHang,
                    'TienTo': TienTo,
                    'HauTo': HauTo,
                };
                $.ajax({
                    type: "POST",
                    dataType: "json",
                    url: '/QLHD/DTPN',
                    data: searchObj,
                    success: function (data) {
                        SearchDTPN();
                        loading(false, "");
                        dAlert(data.message);
                    },
                    error: function (jqXHR, textStatus, errorThrown) {
                        console.log(jqXHR);
                        goTohome(jqXHR.responseText);
                    }
                });
            }, 200);
        }
    });
}


function OpenModalTaoMaDTPN() {

    var rows = dgDTPN.getSelectedRowsData();
    let soDong = rows.length;
    if (soDong == 0) {
        soDong = DATA_HH.length;
    }
    let htmlSoDongDaChon = `
        <div class='col-12 mb-2'>
            Số dòng đã chọn: <b>${soDong}</b>
        </div>
    `

    let bodyHtml = `
        <form id="frmTaoMaDTPN" autocompleted = "off">
            Chức năng tạo mã ĐTPN tự động. Hãy chọn 1 trong 3 kiểu tạo mã sau:
            <div class='row mt-2' >
                <div class='col-12 mb-2'>
                    <label for="rdoDTPNCach1" class='d-flex justify-content-start'>
                            <input type="radio" id="rdoDTPNCach1" name="rdoDTPNCach">
                            <div>&nbsp;&nbsp;&nbsp;Kiểu 1: lấy MST hoặc tên cá nhân mua làm ĐTPN</div>
                    </label>
                </div>
                <div class='col-12 mb-2'>
                    <label for="rdoDTPNCach2" class='d-flex justify-content-start'>
                             <input type="radio" id="rdoDTPNCach2" name="rdoDTPNCach">
                              <span>&nbsp;&nbsp;&nbsp;Kiểu 2: lấy 5 ký tự cuối của MST - kiểu của Smart Pro</span>
                    </label>
                </div>
                <div class='col-12 mb-2'>
                    <label for="rdoDTPNCach3" class='d-flex justify-content-start'>
                             <input type="radio" id="rdoDTPNCach3" name="rdoDTPNCach">
                              <span>&nbsp;&nbsp;&nbsp;Kiểu 3: không dấu, không khoảng cách từ tên công ty/tên cá nhân mua</span>
                    </label>
                </div>
                <hr/>
                <div class='col-12 mb-2'>
                    Thêm tiền tố, hậu tố cho mã (vd: [131]mã ĐTPN, mã ĐTPN[131])
                </div>
                <div class='col-12 mb-2 d-flex justity-content-start'>
                    <input type="text" id="txtTienTo"   class='form-control' placeholder='tiền tố trước mã'>
                    &nbsp;&nbsp;&nbsp;
                    <input type="text" id="txtHauTo"   class='form-control' placeholder='hậu tố sau mã'>
                </div>

                <hr/>

                <div class='col-12 mb-2'>
                    ${htmlSoDongDaChon}
                </div>
                <div class='col-12 text-center mt-3'>
                    <button type='button' class='btn btn-primary' onClick='bnTaoMaDTPN()'>Tạo Mã ĐTPN tự động</button>
                </div>
            </div>
        </form>
    `
    let btnHtml = '';
    createModal("mTaoMaDTPN", "Tạo mã ĐPTN", bodyHtml, btnHtml);
    showModal("mTaoMaDTPN");

}


var selectCotDTPN, oldValueDTPN, newValueDTPN;
function ThayTheHangLoatDTPN() {
    var rows = dgDTPN.getSelectedRowsData();
    if (rows.length == 0) {
        dAlert("Chưa chọn dòng cần thay thế");
        return;
    }
    let bodyHtml = `
               <div class='row'>
                    <div class='col-12'>
                        <table style='line-height:35px'>
                           
                            <tr>
                                <td width='120px'><b>Tên cột:</b></td>
                                <td>
                                    <div id='selectCotDTPN'></div>
                                </td>
                            </tr>
                            <tr >
                                <td><b>Giá trị ban đầu:</b></td>
                                <td>
                                    <div id='oldValueDTPN'  ></div>
                                </td>
                            </tr>
                             <tr class='mt-2'> 
                                <td><b>Giá trị thay thế:</b>    </td>
                                <td>
                                    <div id='newValueDTPN'></div>
                                </td>
                            </tr>
                             <tr class='mt-2'>
                                <td><b>Số dòng đã chọn:</b>    </td>
                                <td >
                                    <span style='color:red;font-weight:bold'>${rows.length} </span>
                                    <span id='ketquaThayTheDTPN' style='color:darkgreen;font-weight:bold'></span>
                                </td>
                            </tr>
                        </table>
                    </div>  
                    <div class='col-12 text-center'>
                        <div id='waitThayTheDTPN'></div>
                        <hr/>
                        <button class='btn btn-primary btn-sm' id="btnThayTheDTPN"><em class='icon ni ni-target'></em>&nbsp;Thay thế</button>
                    </div>
            </div>
            `
    let btnHtml = ``
    createModal("mThayTheDTPN", "Thay thế ĐTPN hàng loạt", bodyHtml, btnHtml)

    selectCotDTPN = $("#selectCotDTPN").dxSelectBox({
        dataSource: [
            { "value": "MaKh", "dsp": "Mã khách hàng" },
            { "value": "MaTaiKhoan", "dsp": "Mã TK TM/CK" },
            { "value": "MaTkCpdt", "dsp": "Mã TK CP/DT" },
        ],
        value:"MaKh",
        displayExpr: "dsp",
        valueExpr: "value",
    }).dxSelectBox("instance");

    oldValueDTPN = $("#oldValueDTPN").dxTextBox({
        placeholder: 'để trống nếu không cần quan tâm giá trị ban đầu',
        value: "",
        width: 300
    }).dxTextBox("instance");

    newValueDTPN = $("#newValueDTPN").dxTextBox({
        placeholder: '',
        value: "",
        width: 300
    }).dxTextBox("instance");

    showModal("mThayTheDTPN");
    $("#btnThayTheDTPN").unbind().on("click", function () {
        $("#ketquaThayTheDTPN").html("");
        loadingCtrl("#waitThayTheDTPN", false, "");
        var rows = dgDTPN.getSelectedRowsData();
        var maCot1 = selectCotDTPN.option("value");
        var oldValue1 = oldValueDTPN.option("value");
        if (oldValue1 == null) {
            oldValue1 = "";
        }
        var newValue1 = newValueDTPN.option("value");
        if (newValue1 == null) {
            newValue1 = "";
        }
        if (!maCot1) {

            dAlert("Chưa chọn cột cần thay thế");
            return;
        }

        let htmlConfirm = ` 

            <p class='line-height:30px;font-size:16px'>
                Thực hiện thay thế cho cột: ${maCot1}
                <br/>- Giá trị ban đầu: ${oldValue1}
                <br/> - Giá trị thay thế: ${newValue1}
                <br/><b>Bạn đã chắc cú chưa?</b>
            </p>

        `
        var result = DevExpress.ui.dialog.confirm(htmlConfirm, "XÁC NHẬN THAY THẾ");

        result.done(function (dialogResult) {
            if (dialogResult) {
                loadingCtrl("#waitThayTheDTPN", true, "Đang thay thế. Vui lòng chờ");
                $.ajax({
                    type: "POST",
                    dataType: "json",
                    url: '/QLHD/DTPN/ThayThe',
                    data: {
                        rowIds: rows.map(p => p.Mst + "\t" + p.MaKh),
                        oldValue: oldValue1,
                        newValue: newValue1,
                        maCot: maCot1,
                        maSoThue: MST
                    },
                    success: function (data) {
                        if (data.status == -1) {
                            dAlert(data.message);
                            return;
                        }
                        else if (data.status == 1) {
                            let c = 0;
                            for (let rI in rows) {
                                console.log("XXXX")
                                if (oldValue1 == "") {
                                    rows[rI][maCot1] = newValue1;
                                }
                                else if (rows[rI][maCot1] == oldValue1 || rows[rI][maCot1] == null) {
                                    rows[rI][maCot1] = newValue1;
                                    c++;
                                }
                            }
                           
                            $("#ketquaThayTheDTPN").html("&nbsp;&nbsp;&nbsp;--> thay thế được <span style='color:darkgreen'> " + data.message + "</b> dòng")
                            dgDTPN.refresh();
                            loadingCtrl("#waitThayTheDTPN", false, "");

                        }
                        else {
                            dAlert(data.message, "Thông báo");
                            loadingCtrl("#waitThayTheDTPN", false, "");

                        }
                    },
                    error: function (jqXHR, textStatus, errorThrown) {
                        console.log(jqXHR);
                        loadingCtrl("#waitThayTheDTPN", false, "");

                        goTohome(jqXHR.responseText);

                    }
                });
            }
        });

    })

}

function dspDataDTPN() {
    if (dgDTPN) {
        dgDTPN.option("dataSource", DATA_DTPN);
        dgDTPN.refresh();
    }
    else {

        var TOTAL_COLUMNS_HH = [{
            column: 'Mst',
            summaryType: "count",
            displayFormat: '{0} MST',
        }
        ];

        var dnb = dsDuyetDatasource.filter(p => p.value != "");
        var COLUMNS_HH = [
            {
                dataField: "LoaiHd", caption: "Loại HĐ", headerCellTemplate: "Loại<br/>HĐ",
                allowEditing: false,
            },
            { dataField: "TenDtpn", caption: "Tên ĐTPN", allowEditing: false },
            { dataField: "Mst", caption: "Mã số Thuế Doanh Nghiệp", headerCellTemplate: "Mã số Thuế<br/>Doanh Nghiệp" },
            { dataField: "MaKh", caption: "Mã Khách Hàng - Smart Pro" },
            {
                dataField: "DuyetNoiBo", headerCellTemplate: "<span class='text-danger'>Duyệt nội bộ</span>",
                lookup: {
                    dataSource: dnb,
                    displayExpr: "text",
                    valueExpr:"value"
                },
            },
            { dataField: "HoaDonDv", headerCellTemplate: "<span class='text-danger'>Hóa Đơn DV</span>"},
            { dataField: "MaTaiKhoan", caption: "Mã TK TM/CK", headerCellTemplate:"<span class='text-danger'>Mã TK<br/>TM/CK</span>" },
            { dataField: "MaTkCpdt", caption: "Mã TK CP/DT", headerCellTemplate: "<span class='text-danger'>Mã TK<br/>CP/DT</span>" },
            {
                dataField: "Sxkd", caption: "Loại HHDV SXKD",
                width: 80,
                headerCellTemplate: `<span class='text-danger tooltip-custom-width'  data-toggle="tooltip" data-placement="left"  title="Phân loại ĐTPN thuộc loại HHDV SXKD ở bảng Kê mua vào" >Loại HHDV<br/>SXKD</span>`,
            },

        ];


        dgDTPN = $("#dgDTPN").dxDataGrid({
            dataSource: DATA_DTPN,
            showOperationChooser: false, 
           
            repaintChangesOnly: true,
            onToolbarPreparing: function (e) {
                e.toolbarOptions.items.unshift(
                    {
                        location: "before",
                        widget: "dxButton",
                        options: {
                            icon: "toolbox",
                            text: "THAY THẾ HÀNG LOẠT",
                            hint: "THAY THẾ HÀNG LOẠT",
                            onClick: function () {
                                ThayTheHangLoatDTPN();
                            }
                        }
                    },
                    {
                        location: "after",
                        widget: "dxButton",
                        options: {
                            icon: "tags",
                            text: "TẠO MÃ ĐTPN TỰ ĐỘNG",
                            hint: "Tạo mã ĐTPN tự động",
                            onClick: function () {
                                OpenModalTaoMaDTPN()
                            }
                        }
                    },
                   {
                    location: "after",
                    widget: "dxButton",
                    options: {
                        icon: "add",
                        text:"Thêm ĐTPN",
                        hint: "Thêm ĐTPN (Alt+N)",
                        onClick: function () {
                            OpenModalThemDTPN();
                        }
                    }
                });
            },
            scrolling: {
                columnRenderingMode: 'virtual',
                useNative: false,
                renderAsync: true,
                showScrollbar: "always"
            },
            selection: {
                mode: 'multiple',
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
                infoText: " Tổng cộng: {2} MST - Trang {0}/{1}"
            },

            columnFixing: {
                enabled: true
            },
            summary: {
                totalItems: TOTAL_COLUMNS_HH
            },
            columns: COLUMNS_HH,

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
                            console.log(dataOrgs);
                            dataOrgs["MaKhOrg"] = dataOrgs["MaKh"];
                            dataOrgs["MstOrg"] = dataOrgs["Mst"];
                            for (let key in dataChanges) {
                                dataOrgs[key] = dataChanges[key];
                            }
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
                    var lstSXKD = ["", "1", "2", "3"];
                    for (let i in updateData) {
                        if (!updateData[i].Sxkd) {
                            updateData[i].Sxkd = "";
                        }
                        if (lstSXKD.indexOf(updateData[i].Sxkd) < 0) {
                            dAlert("Mã số thuế: "  + updateData[i].Mst + " sai giá trị SXKD.<br/> " +
                                `Giá trị đúng là: <br/> - <b>Để trống hoặc 1</b>: HHDV dùng riêng cho SKXD <br/> - <b>2</b>: HHDV dùng chung cho SKXD <br/> - <b>3</b>: HHDV dùng cho dự án`)
                            return;
                        }
                    }

                    $.ajax({
                        type: "POST",
                        dataType: "json",
                        url: '/QLHD/DTPN/Update',
                        data: {
                            dtpn: updateData
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
        }).dxDataGrid("instance");


    }

    setTimeout(function () {
        clearAutoCompleted();
    }, 200);
}

function KetXuatDTPN() {

    SearchDTPN('xls');
}


function ImportDTPN() {
    $("#importFileDTPN").unbind().on("change", function () {
        loadingDTPN(true, "Đang phân tích dữ liệu");
        var dataImport = [];
        var fileUpload = $("#importFileDTPN").prop('files')[0];
        if (fileUpload) {
            var isXlsx = fileUpload.name.toLowerCase().indexOf(".xlsx") > 0;
            var errMess = "";

            var colIndex =
            {
                "Loại HĐ": -1,
                "Tên đối tượng PN": -1,
                "MST doanh nghiệp": -1,
                "Mã Khách Hàng/ NCC Smart Pro": -1,
                "Duyệt nội bộ": -1,
                "Hóa Đơn DV": -1,
                "Mã Tài khoản TK/CM": -1,
                "Mã Tài khoản DT/CP": -1,
                "Loại HHDV SXKD": -1,
            };
            var sxkdLst = ["", "1", "2", "3"];

            if (typeof (FileReader) != "undefined") {
                const wb = new ExcelJS.Workbook();
                const reader = new FileReader()
                reader.readAsArrayBuffer(fileUpload)
                var strMSG = "";
                reader.onload = () => {
                    var key = [];
                    const buffer = reader.result;
                    wb.xlsx.load(buffer).then(workbook => {
                        workbook.eachSheet((sheet, id) => {
                            sheet.eachRow((row, rowIndex) => {
                                let data = row.values;
                                try {
                                
                                    if (data.length > 2 && rowIndex == 1) {
                                        for (let key in colIndex) {
                                            for (let i = 1; i <= 11; i++) {
                                                var t = getExcelData(data, i).toLowerCase().trim();
                                                if (t == key.toLowerCase()) {
                                                    colIndex[key] = i;
                                                    break;
                                                }
                                            }
                                        }
                                        for (let key in colIndex) {
                                            if (colIndex[key] == -1) {
                                                errMess = "Không tìm thấy cột " + key + ". Vui lòng sử dụng template Import mới nhất của Nibot"
                                            }
                                        }
                                    }
                                    if (errMess == "") {
                                        if (data.length > 2 && rowIndex > 1) {
                                            let mst = getExcelData(data, colIndex["MST doanh nghiệp"]);
                                            let loaiHd = getExcelData(data, colIndex["Loại HĐ"]);
                                            let makh = getExcelData(data, colIndex["Mã Khách Hàng/ NCC Smart Pro"]);
                                            let dnb = getExcelData(data, colIndex["Duyệt nội bộ"]);
                                            let hddv = getExcelData(data, colIndex["Hóa Đơn DV"]) == 1 ;
                                            let matk = getExcelData(data, colIndex["Mã Tài khoản TK/CM"]);
                                            let matkdtcp = getExcelData(data, colIndex["Mã Tài khoản DT/CP"]);
                                            let sxkd = getExcelData(data, colIndex["Loại HHDV SXKD"]) ?? "";
                                            if (mst && makh) {
                                                var dataHang = {
                                                    "Mst": mst.toString().trim(),
                                                    "MaKh": makh.toString().trim(),
                                                    "MaSoThue": MST,
                                                    "LoaiHd": loaiHd.trim(),
                                                    "GuidGoi": GuidGoi,
                                                    "DuyetNoiBo":dnb,
                                                    "HoaDonDv": hddv,
                                                    "MaTaiKhoan": matk,
                                                    "MaTkCpdt": matkdtcp,
                                                    "Sxkd": sxkd.toString(),
                                                };
                                                if (dataHang.Sxkd!="" && sxkdLst.indexOf(dataHang.Sxkd) <= 0) {
                                                    strMSG += "Dòng " + (rowIndex) + `, SXKD: '${dataHang.Sxkd}' không hợp lệ. SXKD phải là ['',1,2,3]<br/>`;
                                                }
                                                else if (key.indexOf(dataHang.Mst) == -1) {
                                                    key.push(dataHang.Mst);
                                                    dataImport.push(dataHang);
                                                }
                                                else {
                                                    strMSG += "Dòng " + (rowIndex) + ", Dữ liệu không hợp lệ. Mã Số Thuế/Tên khách lẻ bị trùng - " + JSON.stringify(dataHang) + "<br/>"
                                                }
                                            }
                                            else {
                                                strMSG += "Dòng " + (rowIndex) + ", Dữ liệu không hợp lệ. Mã Số Thuế và Mã Số Doanh Nghiệp không được để trống - " + JSON.stringify(dataHang) + "<br/>"
                                            }
                                        }
                                    }
                                }
                                catch (err) {
                                    console.log(data);
                                    console.log(err);
                                    loadingDTPN(false, "")
                                    dAlert("File dữ liệu import bị lỗi định dạng", "Lỗi định dạng")
                                    return;
                                }
                            });
                        })
                    }).then(function () {
                        $("#importFileDTPN").val("");
                        if (errMess != "") {
                            dAlert(errMess, "Lỗi");
                            return;

                        }
                        else if (strMSG != "") {
                            dAlert2(strMSG, "Lỗi");
                            return;

                        }
                        else if (!isXlsx) {
                            strMSG = "File Excel không đúng định dạng XLSX (Office 2007 trở lên)";
                            dAlert(strMSG, "Lỗi")
                            return;

                        }

                        if (errMess == "" && strMSG == "") {
                            if (dataImport.length > 0) {

                                ImportDTPNChiTiet(dataImport);
                            }
                            else {
                                dAlert("Không đọc được dữ liệu trong file Excel.<br/>Hãy chắc rằng file Excel có dữ liệu và đúng định dạng XLSX thực sự (Office 2007 trở lên).", "Lỗi");
                            }
                        }
                        else {
                            //dAlert(strMSG,"Lỗi")
                        }

                    });
                }
            }

        }
    });

    $("#importFileDTPN").click();

}


function ImportDTPNChiTiet(array) {

    impX = array.length;
    impC = 0;
    var lstChunks = chunks(150, array);
    aj_import_dtpn(lstChunks, 0, lstChunks.length);
}


function aj_import_dtpn(lst, b, e) {
    if (b == e) {
        SearchDTPN();
        dAlert("Import đối tượng pháp nhân thành công", "Thông báo")
        loadingDTPN(false)
    }
    else {
        $.ajax({
            type: "POST",
            dataType: "json",
            url: '/QLHD/DTPN/Import',
            data: {
                dtpn: lst[b]
            },
            success: function (data) {
                if (data.status == 1) {
                    impC = impC + lst[b].length;
                    loadingDTPN(true, "Đang import được " + impC + "/" + impX + " đối tượng pháp nhân")
                    b++;
                    aj_import_dtpn(lst, b, e)

                }
                else {
                    dAlert(data.message, "Thông báo")
                    loadingDTPN(false)
                    return;
                }

            },
            error: function (jqXHR, textStatus, errorThrown) {
                console.log(jqXHR);
                goTohome(jqXHR.responseText);

                b++;
            }
        });
    }
}
function loadingDTPN(isShow, status) {

    if (isShow) {
        $("#statusImportDTPN").html(
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
        $("#statusImportDTPN").hide();
    }
}