//2024-08-27 15:00
var cboHH_LoaiHD;
var chk_TimKiem_NhieuDVT;
var IsNhom = false;
var DoTuongDong = 80;
var myModalEl = null;
var IsThayThe = false;
var oldMaHang = "";
var oldMaTk = "";

function initCtrlHangHoa() {
    let dsPhanLoaiLoaiHD = [
        {
            "key": "",
            "value": "--Loại HĐ--",
        },
        {
            "key": "V",
            "value": "V",
        },
        {
            "key": "R",
            "value": "R",
        }

    ]

    var dsPhanLoaiHH = [
       
        { 'key': 'TatCa', 'value': '--Tất cả hàng hóa--' },
        { 'key': 'ChuaCoMaHang', 'value': 'Chưa có mã hàng' },
        { 'key': 'DaCoMaHang', 'value': 'Đã có mã hàng' },
    ]


    cboHH_LoaiHD = $("#cboHH_LoaiHD").dxSelectBox({
        dataSource: dsPhanLoaiLoaiHD,
        displayExpr: 'value',
        valueExpr: 'key',
        value: '',
    }).dxSelectBox("instance");
    cboHH_PhanLoai = $("#cboHH_PhanLoai").dxSelectBox({
        dataSource: dsPhanLoaiHH,
        displayExpr: 'value',
        valueExpr: 'key',
        value: 'TatCa'
    }
    ).dxSelectBox("instance");

    txtHH_TimKiem_MH = $("#txtHH_TimKiem_MH").dxTextBox({
        placeholder: 'nhập thông tin hàng hóa cần tìm'
    }).dxTextBox("instance");

    $("#toolTip_DVT").html("Hiển thị đơn vị tính của hàng hóa trong Hóa đơn Nibot tải về được")

    var toolTip_DVT = $('#toolTip_DVT').dxTooltip({
        target: '#chk_TimKiem_NhieuDVT',
        showEvent: 'mouseenter',
        hideEvent: 'mouseleave',
        hideOnOutsideClick: false,
    });

    chk_TimKiem_NhieuDVT = $("#chk_TimKiem_NhieuDVT").dxCheckBox({
        value: false,
        text: "Hiện ĐVT",
        onValueChanged(e) {

            SearchHH();
        }
    }).dxCheckBox("instance");

    $("#helpHH").html(
        `
            <div class='d-flex justify-content-end'> 
                <a  href='https://youtu.be/ixLUXA-Bre8?si=rRWOyafglnRX55WP&t=250' target='_blank'><em class=" fw-bold text-danger icon ni ni-youtube" style='font-size:32px'></em> </a> 
                <a  style='background-image: linear-gradient(45deg, #f70bc7, #5700b1);-webkit-background-clip: text; background-clip: text;color: transparent;margin-top:7px;font-weight:bold;' href='https://youtu.be/ixLUXA-Bre8?si=rRWOyafglnRX55WP&t=250' target='_blank'></a>
            </div>
        `
    )

}

function prepareObjectHH() {
    var searchObj = {
        'IsNhom': IsNhom,
        'DoTuongDong': DoTuongDong,
        'PhanLoai': cboHH_PhanLoai.option("value"),
        'KeywordMH': txtHH_TimKiem_MH.option("value").trim(),
        'MaSoThue': MST,
        'IsNhieuDonViTinh': chk_TimKiem_NhieuDVT.option("value"),
        'LoaiHD': cboHH_LoaiHD.option("value")
    };
    return searchObj;
}
function SearchHH(isNhom) {
    idGroup = 0;
    idGroups = [];
    let searchObj = prepareObjectHH();
    if (isNhom) {
        searchObj.isNhom = true;
    }
    $.ajax({
        type: "POST",
        dataType: "json",
        url: '/QLHD/HangHoa',
        data: searchObj,
        success: function (data) {
            DATA_HH = data;
            for (let i in DATA_HH) {
                DATA_HH[i]["dsp"] = DATA_HH[i].MaHang + " || " + DATA_HH[i].TenHang;
            }
            dspDataHH();
     

        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR);
            goTohome(jqXHR.responseText);
            $("#btnSpiner").html('');


        }
    });
}



function KetXuatHH() {

    let searchObj = prepareObjectHH();
    searchObj.KieuTaoMa = -999;
    $.ajax({
        type: "POST",
        dataType: "json",
        url: '/QLHD/HangHoa',
        data: searchObj,
        success: function (data) {
            var fileName = data.obj;
            var a = document.createElement('a');
            var url = "/TMP/" + fileName;
            a.href = url;
            a.download = fileName;
            document.body.append(a);
            a.click();
            a.remove();
            return;

        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR);
            goTohome(jqXHR.responseText);

        }
    });
    return


}

var NamDongBo, TinhChatHangHoa;
var TuNgay, DenNgay;
function DongBoHH() {

    let bodyHtml = `
                    <div class='row'>
                            <div class='col-12'>
                           
                                <div class='d-flex justify-content-start'>
                                     <b style='margin-top:10px'> Thời gian đồng bộ:</b> &nbsp;&nbsp;&nbsp;
                                    <div id="TuNgay"></div>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<div id="DenNgay"></div> 
                                </div>
                                 <div style='margin-top:15px' class='d-flex justify-content-start'>
                                 <b>Loại hóa đơn:</b>
                                    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                                     <label style='font-size:16px'>
                                        <input type="checkbox" id="chkVao" checked>
                                        Đầu Vào
                                    </label>
                                    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                                    <label style='font-size:16px'>
                                        <input type="checkbox" id="chkRa"  checked>
                                        Đầu Ra
                                    </label>
                                </div>
                               
                                <div style='margin-top:15px'>
                                    <b>Tính chất hàng hóa:</b>
                                </div>
                                 <div style='margin-left:10px;margin-top:5px;line-height:35px'>
                                     <label style='font-size:14px'>
                                        <input type="radio" name="TinhChatHangHoa" value="0" id="TinhChatHangHoa0" checked>
                                        Tất cả hàng hóa có trong hóa đơn
                                    </label>
                                    <br>
                                    <label style='font-size:14px'>
                                        <input type="radio" name="TinhChatHangHoa" value="1" id="TinhChatHangHoa1">
                                        Không đồng bộ HH là Chiết khấu hoặc (SLG = 0 và Thành tiền = 0)
                                    </label>
                                </div>
                                  <div style='margin-left:0px;margin-top:5px;line-height:35px'>
                                       <label style='font-size:16px'>
                                        <input type="checkbox" id="chkGanMaHangCoSan"  >
                                       <b>&nbsp;&nbsp;Gắn luôn mã hàng nếu có sẵn trong hóa đơn XML</b>
                                    </label>
                                </div>
                            </div>
                            <div class='col-12 text-center'>
                                <hr/>
                                <button class='btn btn-primary btn-sm' id="btnDBHH"><em class='icon ni ni-reload'></em>&nbsp;Đồng bộ hàng hóa</button>
                            </div>
                    </div>
                `

    var x = KhoangNgay("Năm này", false, "");

    createModal("mDongBoHangHoa", "Đồng bộ Hàng Hóa", bodyHtml, '')
    TuNgay = $("#TuNgay").dxDateBox({
        label: "Từ ngày",
        elementAttr: {
            "style":"font-size:16px"
        },
        width: 130,
        displayFormat: "dd/MM/yyyy",
        useMaskBehavior: true,
        value: x.start,
    }).dxDateBox("instance")
    DenNgay = $("#DenNgay").dxDateBox({
        label: "Đến ngày",
        elementAttr: {
            "style": "font-size:16px"
        },
        width: 130,
        displayFormat: "dd/MM/yyyy",
        useMaskBehavior: true,
        value: x.end
    }).dxDateBox("instance")

    showModal("mDongBoHangHoa");

    $("#btnDBHH").unbind().on("click", function () {
        var result = DevExpress.ui.dialog.confirm("Nếu tên hàng hóa chưa trong [Hàng Hóa Nibot] thì sẽ được thêm vào.<br/><br/><b>Bạn đã chắc cú chưa?</b>", "ĐỒNG BỘ HÀNG HÓA");
        result.done(function (dialogResult) {
            if (dialogResult) {
                hideModal("mDongBoHangHoa");
                loading(true, "Đang đồng bộ lại danh mục hàng hóa.<br/>Sẽ lâu nếu như lượng hóa đơn nhiều<br/>Vì thế nên vui lòng chờ đợi");

              //  var Nam = NamDongBo.option("value") ?? "";
            //    var TinhChat = TinhChatHangHoa.option("value");
                var hhTuNgay = toJP(TuNgay.option("value"));
                var hhDenNgay = toJP(DenNgay.option("value"));
                var hhDauVao = $("#chkVao").prop("checked");
                var hhDauRa = $("#chkRa").prop("checked");
                var hhLoaiHD = "VR";
                if (hhDauVao && hhDauRa) {
                    hhLoaiHD = "VR";
                }
                else if (hhDauVao) {
                    hhLoaiHD = "V";
                }
                else if (hhDauRa) {
                    hhLoaiHD = "R";
                }
                var chkGanMaHangCoSan = $("#chkGanMaHangCoSan").prop("checked") ? 1 : 0;

                var hhTinhChat = $("#TinhChatHangHoa0").prop("checked") ? 0 : 1;

                $.ajax({
                    type: "POST",
                    dataType: "json",
                    url: '/QLHD/DongBoLaiHangHoa',
                    data: {
                        "MaSoThue": MST,
                        "TuNgay": hhTuNgay,
                        "DenNgay": hhDenNgay,
                        "LoaiHD": hhLoaiHD,
                        "TinhChat": hhTinhChat,
                        "GanMaHangCoSan": chkGanMaHangCoSan
                    },
                    success: function (data) {
                        if (data.status == 1) {
                            dAlert("Đồng bộ hàng hóa hoàn tất", "Thông báo")
                            SearchHH();
                        }
                        else {
                            dAlert(data.message, "Lỗi đồng bộ")
                            SearchHH();
                        }
                        loading(false)


                    },
                    error: function (jqXHR, textStatus, errorThrown) {
                        console.log(jqXHR);
                        loading(false)
                        goTohome(jqXHR.responseText);


                    }
                });
            }

        });

    })

    return;

    
}

var TinhChatHangHoaXoa;

function XoaTatCaHH() {
    var rows = dgHH.getSelectedRowsData();
    let bodyHtml = `
                    <div class='row'>
                            <div class='col-12'>
                                 <div style='margin-left:10px;margin-top:5px;line-height:35px'>
                                     <label style='font-size:14px'>
                                        <input type="radio" name="TinhChatHangHoaXoa" value="0" id="rdoTinhChatHangHoaXoa0" checked>
                                        Xóa tất cả hàng hóa
                                    </label>
                                    <br>
                                    <label style='font-size:14px'>
                                        <input type="radio" name="TinhChatHangHoaXoa" value="1" id="rdoTinhChatHangHoaXoa1">
                                        Xóa hàng hóa chưa được gán mã 
                                    </label>
                                    <br>
                                    <label style='font-size:14px'>
                                        <input type="radio" name="TinhChatHangHoaXoa" value="2" id="rdoTinhChatHangHoaXoa2">
                                        Xóa dòng hàng hóa đã được chọn (${rows.length} dòng)
                                    </label>
                                </div>
                            </div>
                            <div class='col-12 text-center'>
                                <hr/>
                                <button class='btn btn-danger btn-sm' id="btnXoaHH"><em class='icon ni ni-delete'></em>&nbsp;Xóa hàng hóa</button>
                            </div>
                    </div>
                `

    createModal("mXoaHangHoa", "Xóa Hàng Hóa", bodyHtml, '')
    showModal("mXoaHangHoa");

    $("#btnXoaHH").unbind().on("click", function () {
        let searchObj = prepareObjectHH();
        searchObj.IsXoa = true;
        let strConfirm = "";
        if ($("#rdoTinhChatHangHoaXoa0").prop("checked")) {
            searchObj.TinhChat = 0;
            strConfirm = "Xóa tất cả hàng hóa.";
        }
        else if ($("#rdoTinhChatHangHoaXoa1").prop("checked")) {
            searchObj.TinhChat = 1;
            strConfirm = "Xóa hàng hóa chưa được gán mã.";
        }
        else if ($("#rdoTinhChatHangHoaXoa2").prop("checked")) {
            if (rows.length == 0) {
                dAlert("Chưa chọn dòng cần xóa");
                return;
            }

            searchObj.TinhChat = 2;
            strConfirm = `Xóa hàng hóa đã được chọn (${rows.length} dòng).`;
            searchObj.ListIdHang = rows.map(p => p.GuidHang);
        }


        var result = DevExpress.ui.dialog.confirm(strConfirm + "<br/><b>Bạn đã chắc cú chưa?</b>", "XÓA HÀNG HÓA");
        result.done(function (dialogResult) {
            if (dialogResult) {
                hideModal("mXoaHangHoa");
                loading(true, "Đang xóa Hàng Hóa<br/>Vì thế nên vui lòng chờ đợi")
                $.ajax({
                    type: "POST",
                    dataType: "json",
                    url: '/QLHD/HangHoa',
                    data: searchObj,
                    success: function (data) {
                        if (data.status == 1) {
                            dAlert("Xóa hàng hóa thành công", "Thông báo")
                            SearchHH();
                        }
                        else {
                            dAlert(data.message, "Lỗi đồng bộ")
                            SearchHH();
                        }
                        loading(false)
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
function OpenQuyDoi(MaHang, TenHang) {

    $.ajax({
        type: "POST",
        dataType: "json",
        url: '/QLHD/QuyDoi/LoadQuyDoi',
        data: {
            MaHang: MaHang,
            TenHang: TenHang,
            MaSoThue: MST,
        },
        success: function (data) {
            if (data.status == 1) {
                let bodyHtml = `
                <p>Mã hàng: <b>${MaHang}</b></p>
                <p>Tên hàng: <b>${TenHang}</b></p>
                <div id="dgSubQuyDoi" class='datagrid'></div>  

                `
                let btnHtml = ``

                createModal("mOQuyDoi", "Thông tin Quy Đổi ĐVT", bodyHtml, btnHtml)

                $("#dgSubQuyDoi").dxDataGrid({
                    dataSource: data.obj,
                    showBorders: true,
                    rowAlternationEnabled: true,
                    showBorders: true,
                    showColumnLines: true,
                    showRowLines: true,
                    columnAutoWidth: true,
                    noDataText: "Không có dữ liệu",
                    columns: [
                        {
                            dataField: "Dvt", caption: "ĐVT GỐC (HÓA ĐƠN)",
                        },
                        {
                            dataField: "DvtquyDoi", caption: "ĐVT (QUY ĐỔI)",
                        },
                        {
                            dataField: "SoLuongQuyDoi", caption: "SỐ LƯỢNG",
                        }
                    ]
                });
                showModal("mOQuyDoi");
            

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

function bnTaoMaHang() {
    let kieu = 0;
    if ($("#rdoCach1").prop("checked")) {
        kieu = 1;
    }
    if ($("#rdoCach2").prop("checked")) {
        kieu = 2;
    }
    if ($("#rdoCach3").prop("checked")) {
        kieu = 3;
    }
 
    if (kieu == 0) {
        dAlert("Chưa chọn kiểu tạo mã hàng!");
    }
    else {
        let str = "";
        if (kieu == 1) str = "Tạo mã hàng dạng HH1, HH2, HH3,...";
        if (kieu == 2) str = "Tạo mã Không dấu, không khoảng cách";
        if (kieu == 3) str = "Tạo mã bằng cách lấy ký tự đầu của các từ";

        var result = DevExpress.ui.dialog.confirm(str + "<br/><b>Bạn đã chắc cú chưa?</b>", "Tạo Mã Hàng Tự Động");
        result.done(function (dialogResult) {
            var lstIdHang = [];
            var rows =  dgHH.getSelectedRowsData();
            if (rows.length > 0) {
                lstIdHang = rows.map(p => p.GuidHang);
            }
            else {
                lstIdHang = []
            }

            if (dialogResult) {
                hideModal("mTaoMaHang");
                loading(true, "Đang tạo mã hàng.<br/>Sẽ lâu nếu như hàng hóa nhiều<br/>Vì thế nên vui lòng chờ đợi");
                setTimeout(function () {
                    let searchObj = {
                        'IsTiny': true,
                        'MaSoThue': MST,
                        'KieuTaoMa': kieu,
                        'TienTo': $("#TienToHangHoa").val()+"@##@" + $("#SoLuongChuSo").val(),
                        'ListIdHang': lstIdHang
                    };

                    $.ajax({
                        type: "POST",
                        dataType: "json",
                        url: '/QLHD/HangHoa',
                        data: searchObj,
                        success: function (data) {
                            SearchHH();
                            loading(false,"");
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
}

function OpenModalTaoMaHang() {

    var rows = dgHH.getSelectedRowsData();
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
        <form id="frmTaoMaHang" autocompleted = "off">
            <b class='text-danger'>Chức năng tạo mã hàng tự động cho các mặt hàng chưa được gán mã.</b><br/>
            Hãy chọn 1 trong 2 kiểu tạo mã sau:
            <div class='row mt-2' >
                <div class='col-12 mb-2'>
                    <label for="rdoCach1" class='d-flex justify-content-start'>
                            <input type="radio" id="rdoCach1" name="rdoCach">
                            <span><b>&nbsp;&nbsp;&nbsp;Kiểu 1: Tạo mã hàng dạng HH1, HH2, HH3,...</b></span>
                    </label>
                    <div style='margin-left:22px;margin-top:10px;margin-bottom:10px;' class='justify-content-start d-flex'>
                        <table>
                            <tr>
                                <td>&nbsp;&nbsp;Tiền tố mã hàng:&nbsp;&nbsp;&nbsp;</td>
                                <td><input class='form-control' value='HH' id='TienToHangHoa' style='width:200px'/></td>
                            </tr>
                            <tr>
                                <td>&nbsp;&nbsp;Độ dài chữ số:&nbsp;&nbsp;&nbsp;</td>
                                <td><input class='form-control' value='6' id='SoLuongChuSo' style='width:200px' />  </td>
                            </tr>
                             <tr>
                                <td></td>
                                <td> <small class='text-danger' id='txtExample'>ví dụ: </small>
                                </td>
                            </tr>
                           
                        </table>
                    </div>
                </div>
                <div class='col-12 mb-2'>
                    <label for="rdoCach2" class='d-flex justify-content-start'>
                             <input type="radio" id="rdoCach2" name="rdoCach">
                              <span><b>&nbsp;&nbsp;&nbsp;Kiểu 2: Tạo mã Không dấu, không khoảng cách.</b></span>
                    </label>
                </div>
                <div class='col-12 mb-2'>
                    <label for="rdoCach3" class='d-flex justify-content-start'>
                             <input type="radio" id="rdoCach3" name="rdoCach">
                              <span><b>&nbsp;&nbsp;&nbsp;Kiểu 3: Tạo mã bằng cách lấy ký tự đầu của các từ</b></span>
                    </label>
                </div>
                <hr/>
                <div class='col-12 mb-2'>
                    ${htmlSoDongDaChon}
                </div>
                <div class='col-12 text-center mt-3'>
                    <button type='button' class='btn btn-primary' id="btnTaoMaHang">Tạo Mã hàng tự động</button>
                </div>
            </div>
        </form>
    `
    let btnHtml = '';
    createModal("mTaoMaHang", "Tạo mã hàng", bodyHtml, btnHtml);
    showModal("mTaoMaHang");
    $("#TienToHangHoa,#SoLuongChuSo").unbind().on('keyup', function () {
        showExample();
    })

    showExample();
    $("#btnTaoMaHang").unbind().on("click", function () {
        bnTaoMaHang();
    })
}
        
function showExample() {
    let t = $("#TienToHangHoa").val();
    let s = parseInt($("#SoLuongChuSo").val());
    if (s>15) {
        s = 15;
        $("#SoLuongChuSo").val('15');
    }
    let number = 1;
    let formattedNumber = number.toString().padStart(s, '0');
    $('#txtExample').html('ví dụ: ' + t + formattedNumber)
}
var selectCotDTPN, oldValueDTPN, newValueDTPN;
function ThayTheHangLoat(col) {
    IsThayThe = false;
    oldMaHang = "";
    oldMaTk = "";
    var rows = dgHH.getSelectedRowsData();
    if (rows.length == 0) {
        dAlert("Chưa chọn dòng cần gán mã");
        return;
    }
    let bodyHtml = `
               <div class='row'>
                    <div class='col-12'>
                        <table style='line-height:35px'>
                           
                            <tr>
                                <td width='120px'><b>Tên cột:</b></td>
                                <td>
                                    <div id='selectCot'></div>
                                </td>
                            </tr>
                            <tr >
                                <td><b>Giá trị ban đầu:</b></td>
                                <td>
                                    <div id='oldValue'  ></div>
                                </td>
                            </tr>
                             <tr class='mt-2'> 
                                <td><b>Giá trị thay thế:</b>    </td>
                                <td>
                                    <div id='newValue'></div>
                                </td>
                            </tr>
                             <tr class='mt-2'>
                                <td><b>Số dòng đã chọn:</b>    </td>
                                <td >
                                    <span style='color:red;font-weight:bold'>${rows.length} </span>
                                    <span id='ketquaThayThe' style='color:darkgreen;font-weight:bold'></span>
                                </td>
                            </tr>
                        </table>
                    </div>  
                    <div class='col-12 text-center'>
                        <div id='waitThayThe'></div>
                        <hr/>
                        <button class='btn btn-primary btn-sm' id="btnThayThe"><em class='icon ni ni-target'></em>&nbsp;Thay thế</button>
                    </div>
            </div>
            `
    let btnHtml = ``
    createModal("mThayThe", "Thay thế hàng loạt", bodyHtml, btnHtml)

    if (myModalEl==null) {
        myModalEl = document.getElementById('mThayThe');
        myModalEl.addEventListener('hidden.bs.modal', function (event) {
            if (IsThayThe) {
                indexesToSelect = [];
                dgHH.refresh();
                dgHH.selectRows([]);
                console.log('Modal đã đóng');
            }
           
        });
    }
  

    selectCotDTPN = $("#selectCot").dxSelectBox({
        dataSource: [
            { "value": "MaTk", "dsp": "Mã TK" },
            { "value": "MaHang", "dsp": "Mã hàng" },
        ],
        value:col,
        displayExpr: "dsp",
        valueExpr: "value",
        onValueChanged(e) {
            if (e.value == 'MaTk') {
                oldMaHang = newValueDTPN.option("value")
                if (oldMaTk) {
                    newValueDTPN.option("value", oldMaTk);
                }
                else {
                    newValueDTPN.option("value", "");
                }
            }
            else {
                oldMaTk = newValueDTPN.option("value");
                if (oldMaHang) {
                    newValueDTPN.option("value", oldMaHang);
                }
                else {
                    newValueDTPN.option("value", "");
                }
            }

        }
    }).dxSelectBox("instance");

    oldValueDTPN = $("#oldValue").dxTextBox({
        placeholder: 'để trống nếu không cần quan tâm giá trị ban đầu',
        value: "",
        width: 300,
        showClearButton: true

    }).dxTextBox("instance");


    newValueDTPN = $("#newValue").dxTextBox({
        placeholder: '',
        value: "",
        width: 300,
        showClearButton: true

    }).dxTextBox("instance");

    showModal("mThayThe");

    setTimeout(function () {
        newValueDTPN.focus();
    },200)
    $("#btnThayThe").unbind().on("click", function () {
        IsThayThe = true;
        $("#ketquaThayThe").html("");
        loadingCtrl("#waitThayThe", false, "");
        var rows = dgHH.getSelectedRowsData();
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

            dAlert("Chưa chọn cột cần gán");
            return;
        }


        loadingCtrl("#waitThayThe", true, "Đang thay thế. Vui lòng chờ" );
        $.ajax({
            type: "POST",
            dataType: "json",
            url: '/QLHD/HangHoa/ThayThe',
            data: {
                rowIds: rows.map(p => p.GuidHang),
                oldValue: oldValue1,
                newValue: newValue1,
                maCot: maCot1,
                maSoThue: MST
            },
            success: function (data) {
                if (data.status==-1) {
                    dAlert(data.message);
                    return;
                }
                else if (data.status == 1) {
                    let c = 0;
                    for (let rI in rows) {
                        if (oldValue1=="") {
                            rows[rI][maCot1] = newValue1;
                        }
                        else if (rows[rI][maCot1] == oldValue1 || rows[rI][maCot1] == null) {
                            rows[rI][maCot1] = newValue1;
                            c++;
                        }
                    }
                    $("#ketquaThayThe").html("&nbsp;&nbsp;&nbsp;--> thay thế được <span style='color:darkgreen'> " + data.message +"</b> dòng")
                   // dgHH.refresh();
                    dgHH.option("dataSource", DATA_HH);
                    dgHH.selectRows(indexesToSelect, true);

                    loadingCtrl("#waitThayThe", false, "");


                }
                else {
                    dAlert(data.message, "Thông báo");
                    loadingCtrl("#waitThayThe", false, "");

                }
            },
            error: function (jqXHR, textStatus, errorThrown) {
                console.log(jqXHR);
                loadingCtrl("#waitThayThe", false, "");

                goTohome(jqXHR.responseText);
            }
        });
      
    })
}
var fIdNhom = "";
var fIdNhomColor = ["#8600c9d4", "#0b7231"];

var fNhomColorIdx = 0;
var fColor = "";

var spinerGomNhom = `  
                <div style="margin-top:5px;margin-left:10px" class="spinner-border spinner-border-sm" role="status">
                    <span class="visually-hidden">Loading...</span>
            </div> <i><small>...đang gom nhóm...</small></i>`
var indexesToSelect = [];
function union(arr1, arr2) {
    return [...new Set([...arr1, ...arr2])];
}
function intersect(arr1, arr2) {
    return arr1.filter(value => arr2.includes(value));
}
function except(arr1, arr2) {
    return arr1.filter(value => !arr2.includes(value));
}

function checkSub(e, groupKey) {
    let isCheck = $(e).prop("checked");
    const rows = dgHH.getVisibleRows();
    let subCheck = [];
    rows.forEach(function (row, index) {
        if (row.rowType === 'data' && row.data.IdNhom === groupKey) {
            subCheck.push(row.key);
        }
    });
    
    if (isCheck) {
        indexesToSelect = union(indexesToSelect, subCheck);
        dgHH.selectRows(subCheck, true);
    }
    else {
        indexesToSelect = except(indexesToSelect, subCheck);

        dgHH.deselectRows(subCheck);
    }
}

function dspDataHH() {
    idGroup = 0;
    idGroups = [];
    var COLUMNS_HH = [
        { dataField: "MaTk", caption: "Mã TK", allowHeaderFiltering: true, },
        { dataField: "MaHang", caption: "Mã hàng", allowHeaderFiltering: true, },
        { dataField: "TenHang", caption: "Tên hàng", allowHeaderFiltering: false, },
    ];
    if (chk_TimKiem_NhieuDVT.option("value")) {
        COLUMNS_HH.push({ dataField: "DonViTinh", caption: "ĐVT", allowEditing: false, allowHeaderFiltering: false, });
        COLUMNS_HH.push({
            dataField: "DonViTinhQuyDoi", caption: "ĐVT - Quy đổi", allowEditing: false, allowHeaderFiltering: false,
            cellTemplate(c, e) {
                if (e.rowType == 'data' && e.value) {
                    $(`<a  href='javascript:void' onclick='OpenQuyDoi("${e.data.MaHang}","${e.data.TenHang}")'><span class='badge bg-primary'>${e.value}</span></a>`).appendTo(c)
                }
            }

        });

    }
    COLUMNS_HH.push({
        dataField: "LoaiHd",
        caption: "Loại HĐ", allowHeaderFiltering: true,
    });
    COLUMNS_HH.push({
        dataField: "GhiChu", caption: "Ghi chú", width: 200, allowHeaderFiltering: true,
    });
    if (IsNhom) {
        COLUMNS_HH.push({
            dataField: "IdNhom", caption: "Nhóm", width: 200, allowHeaderFiltering: true, width: 250, groupIndex: 0,
            groupCellTemplate: function (element, info) {
                // Tùy chỉnh hiển thị nhóm
                var groupValue = info.value; // Giá trị nhóm
                var count = info.data.items.length; // Số lượng mục trong nhóm
                var customGroupText = `
                    <label class='d-flex justify-content-start'>
                        <input type="checkbox" class='chkSubClick' data-value ='${info.value}'  onClick='checkSub(this,"${info.value}")' >
                        &nbsp;&nbsp;<span >Nhóm: ${groupValue} (${count})</span>
                    </label>
                
                `
                $("<div>")
                    .addClass("custom-group-name")
                    .html(customGroupText)
                    .appendTo(element);
            }


        });

    }


    if (dgHH) {
        dgHH.option("dataSource", DATA_HH);
        dgHH.option("columns", COLUMNS_HH);
       // dgHH.refresh();
    }
    else {

        var TOTAL_COLUMNS_HH = [{
            column: 'MaHang',
            summaryType: "count",
            displayFormat: '{0} hàng hóa',
        }
        ];

        dgHH = $("#dgHH").dxDataGrid({
         
            dataSource: DATA_HH,
            repaintChangesOnly: true,
            headerFilter: { visible: true },
            groupPanel: {
                visible: IsNhom
            },
            loadingPanel: {
                visible: true,
            },

            onRowPrepared(e) {
                if (e.rowType === "group") {
                    fIdNhom = e.data.IdNhom;
                    fColor = fIdNhomColor[fNhomColorIdx % 2];
                    fNhomColorIdx++;
                    $(e.rowElement).attr("style", "background:" + fColor +";color:white");
                }
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
                            icon: "toolbox",
                            text: "GÁN MÃ HÀNG",
                            hint: "Gán mã hàng hàng loạt",

                            onClick: function () {
                                ThayTheHangLoat('MaHang');
                            }
                        }
                    },
                    {
                        location: "before",
                        widget: "dxButton",
                        options: {
                            elementAttr: {
                                style: "background: rgb(233 198 241 / 33%);border-radius: 10px;color: black;font-weight: bold;" // Add custom CSS class here
                            },
                            onContentReady: function (e) {
                                // Directly target the icon and set its color
                                $(e.element).find(".dx-icon").css("color", "black");
                            },
                            icon: "toolbox",
                            text: "GÁN MÃ TK",
                            hint: "Gán mã tài khoản hàng loạt",

                            onClick: function () {
                                ThayTheHangLoat('MaTk');
                            }
                        }
                    },
                    {
                        location: "before",
                        widget: "dxCheckBox",
                        options: {
                            elementAttr: {
                                id: "btnNhom",
                                style: "margin-left:12px;font-weight:bold;color:red" // Add custom CSS class here
                            },
                            onContentReady: function (e) {
                                // Directly target the icon and set its color
                                $(e.element).find(".dx-icon").css("color", "white");
                            },
                            text: "Gom các mặt hàng giống nhau vào 1 nhóm, độ tương đồng (%)",
                            hint: "Gom các mặt hàng giống nhau vào 1 nhóm\nGiúp cho việc gán mã tiện lợi hơn",
                            onValueChanged(e) {
                                IsNhom = !IsNhom;
                                $("#btnSpiner").html(IsNhom? spinerGomNhom: "");
                                SearchHH();
                            }
                        }
                    },
                    {
                        location: "before",
                        widget: "dxNumberBox",
                        options: {
                            width:40,
                            min: 30,
                            max: 100,
                            value: 80,
                            elementAttr: {
                                id: "txtDoTuongDong",
                                style: "" // Add custom CSS class here
                            },
                            hint: "Mặc định là 80% trở lên. Bạn có thể thay đổi để phù hợp với mục đích phân nhóm",
                            onValueChanged(e) {
                                DoTuongDong = e.value;
                                if (IsNhom) {
                                    SearchHH();
                                }
                            }
                        }
                    },
                    {
                        location: "before",
                        widget: "dxButton",
                        options: {
                            elementAttr: {
                                id:"btnSpiner",
                                style: "border:0px" // Add custom CSS class here
                            },
                            text:"",
                        }
                    },

                    {
                        location: "after",
                        widget: "dxButton",
                        options: {
                            icon: "tags",
                            text: "TẠO MÃ HÀNG TỰ ĐỘNG",
                            hint: "Tạo mã hàng tự động",
                            onClick: function () {
                                OpenModalTaoMaHang()
                            }
                        }
                    },
                    {
                        location: "after",
                        widget: "dxButton",
                        options: {
                            icon: "rowproperties",
                            text: "Thêm ĐVT",
                            hint: "Thêm ĐVT (Alt+D)",
                            onClick: function () {
                                let r = dgHH.getSelectedRowsData();
                                if (r.length>0) {
                                    OpenModalThemQuyDoi(r[0]);
                                }
                                else {
                                    OpenModalThemQuyDoi();

                                }
                            }
                        }
                    },
                    {
                    location: "after",
                    widget: "dxButton",
                    options: {
                        icon: "add",
                        text: "Thêm hàng hóa",
                       
                        hint:"Thêm hàng hóa (Alt+N)",
                        onClick: function () {
                            OpenModalThemHangHoa();
                        }
                    }
                });
            },
            scrolling: {
                columnRenderingMode: 'virtual',
                useNative: false,
                renderAsync: true,
                showScrollbar: "always",
            },
            headerFilter: { visible: true },
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
            virtualModeEnabled: true,
            paging: {
                enabled: true,
                pageSize: 100,
                pageIndex: 0    // Shows the second page
            },
            selection: {
                mode: 'multiple',
                showCheckBoxesMode: "always"

            },
            grouping: {
                autoExpandAll: true // Tự động mở tất cả các nhóm
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
                allowedPageSizes: [100, 200, 500, 1000],
                showNavigationButtons: true,
                showInfo: true,
                infoText: " Tổng cộng: {2} hàng hóa - Trang {0}/{1}"
            },
            columnFixing: {
                enabled: true
            },
            summary: {
                totalItems: TOTAL_COLUMNS_HH
            },
            columns: COLUMNS_HH,
            onContentReady: function (e) {
                $("#btnSpiner").html('')
            },
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
                    for (let k in updateData) {
                        let loai = updateData[k]["Loai"];
                        if (loai == "update" || loai == "insert") {
                            let x = updateData[k];
                            let x2 = x.LoaiHd;
                            if (x2 == null || x2 == "" || x2 == "V" || x2 == "R" || x2=="VR") {

                            }
                            else {
                                dAlert("Loại hóa đơn của mặt hàng: " + x.TenHang +" không hợp lệ.<br/>Giá trị hợp lệ là 1 trong 3 giá trị sau: (trống), V, R")
                                return;
                            }
                        }
                    }
                  
                    $.ajax({
                        type: "POST",
                        dataType: "json",
                        url: '/QLHD/HangHoa/Update',
                        data: {
                            hangHoa: updateData
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
}



function ImportHH() {
    $("#importFile").unbind().on("change", function () {
        var dataImport = [];
        var fileUpload = $("#importFile").prop('files')[0];
        var lstGuid = [];
        //Mã TK	Mã hàng	Tên hàng	ĐVT	Loại HĐ	GuidHang

        var colIndex = 
            {
                "Mã TK": -1,
                "Mã hàng": -1,
                "Tên hàng": -1,
                "Loại HĐ": -1,
                "Ghi chú": -1,
                "GuidHang": -1,
            };
        if (fileUpload) {
            var isXlsx = fileUpload.name.toLowerCase().indexOf(".xlsx") > 0;
            var errMess = "";
            if (typeof (FileReader) != "undefined") {
                const wb = new ExcelJS.Workbook();
                const reader = new FileReader()
                reader.readAsArrayBuffer(fileUpload)
                reader.onload = () => {
                    const buffer = reader.result;
                    var strMSG = "";
                    wb.xlsx.load(buffer).then(workbook => {
                        workbook.eachSheet((sheet, id) => {
                            sheet.eachRow((row, rowIndex) => {
                                let data = row.values;

                                try {
                                    if (data.length > 2 && rowIndex == 1) {
                                        for (let key in colIndex) {
                                            for (let i = 1; i <= 10; i++) {
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

                                    if ( errMess=="") {

                                        if (data.length > 2 && rowIndex > 1) {
                                            let maTK = getExcelData(data, colIndex["Mã TK"]) ?? "";
                                            let maHang = getExcelData(data, colIndex["Mã hàng"]) ?? "";
                                            let tenHang = getExcelData(data, colIndex["Tên hàng"]) ?? "";
                                            let loaiHd = getExcelData(data, colIndex["Loại HĐ"]) ?? "";
                                            let ghiChu = getExcelData(data, colIndex["Ghi chú"]) ?? "";
                                            let guidHang = getExcelData(data, colIndex["GuidHang"]) ?? "";
                                            if (maTK && maTK.toString().indexOf("[*] Nhóm hàng: ") >= 0) {
                                                console.log(maTK);
                                            }
                                            else {
                                                var dataHang = {
                                                    "MaTk": maTK.toString().trim(),
                                                    "MaHang": maHang.toString().trim(),
                                                    "TenHang": tenHang.toString().trim(),
                                                    "LoaiHd": loaiHd.toString().trim(),
                                                    "GhiChu": ghiChu.toString().trim(),
                                                    "GuidHang": guidHang.toString().trim(),
                                                    "MaSoThue": MST,
                                                    "GuidGoi": GuidGoi,
                                                };
                                                if (dataHang.MaHang.length > 50) {
                                                    strMSG += "Dòng " + (rowIndex) + ", Mã hàng: " + dataHang.MaHang.trim() + " quá độ dài quy định<br/>";
                                                }
                                                else if (dataHang.TenHang == "") {
                                                    strMSG += "Dòng " + (rowIndex) + ", Tên hàng bị trống - " + JSON.stringify(dataHang) + "<br/>";
                                                }
                                                else if (dataHang.TenHang.length > 300) {
                                                    strMSG += "Dòng " + (rowIndex) + ", Tên hàng: " + dataHang.TenHang + " quá độ dài quy định<br/>";
                                                }
                                                else if (!(dataHang.LoaiHd == null || dataHang.LoaiHd == "" || dataHang.LoaiHd == "V" || dataHang.LoaiHd == "R")) {
                                                    strMSG += "Dòng " + (rowIndex) + ", Loại hóa đơn không đúng quy định<br/>";
                                                }
                                                else {
                                                    dataImport.push(dataHang);
                                                }
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
                        $("#importFile").val("");
                        if (errMess != "") {
                            dAlert(errMess, "Lỗi");
                            return;

                        }

                        else if (strMSG != "") {
                            dAlert2(strMSG, "Lỗi")
                            return;
                        }
                        else if (!isXlsx) {
                            strMSG = "File Excel không đúng định dạng XLSX (Office 2007 trở lên)";
                            dAlert(strMSG, "Lỗi")
                            return;

                        }
                        
                        if (strMSG == "" && errMess =="") {
                            if (dataImport.length > 0) {
                                var dataTrung = timTenHangTrungNhau(dataImport);
                                if (dataTrung.length > 0) {
                                    let msg = "Có " + dataTrung.length + " hàng hóa bị trùng tên.";
                                    let k = dataTrung.join("\n");
                                    let bodyHtml = `
                                        <div class = 'alert alert-danger text-center mt-1 mb-1'>
                                           ${msg}
                                        </div>
                                        Danh sách tên hàng bị trùng: 
                                        <textarea class='form-control mt-1' cols='100' rows = '8'>${k}</textarea>
                                    `
                                    let btnHtml = `<div class='row' style='width:100%'>
                                                    <div class='col-6 text-center'>
                                                        <button class='btn btn-dark btn-sm' onClick='hideModal("mBaoTrung")'>Đóng để kiểm tra</button>
                                                    </div>
                                                    <div class='col-6  text-center'>
                                                        <button class='btn btn-danger btn-sm' id='btnImportDup'>Import và loại bỏ trùng</button>
                                                    </div>
                                                 </div>`
                                    createModal("mBaoTrung", "Cảnh báo trùng tên hàng", bodyHtml, btnHtml)
                                    showModal("mBaoTrung");
                                    $("#btnImportDup").on("click", function () {
                                        if (dataImport.length > 0) {
                                            hideModal("mBaoTrung");
                                            let uniqueArray = [];
                                            dataImport.forEach(obj => {
                                                if (!uniqueArray.some(o => o.TenHang.toLowerCase() === obj.TenHang.toLowerCase())) {
                                                    uniqueArray.push(obj);
                                                }
                                            });

                                            ImportHangHoaChiTiet(uniqueArray);
                                        }
                                    })
                                }
                                else {
                                    ImportHangHoaChiTiet(dataImport);
                                }
                            }
                            else {
                                dAlert("Không đọc được dữ liệu trong file Excel.<br/>Hãy chắc rằng file Excel có dữ liệu và đúng định dạng XLSX thực sự (Office 2007 trở lên).", "Lỗi");
                            }
                        }
                     
                    });
                }
            }

        }
    });

    $("#importFile").click();



}

function timTenHangTrungNhau(dataImport) {
    const tenHangList = dataImport.map(item => item.TenHang.toLowerCase().trim()); // Chuyển toàn bộ tên hàng thành chữ thường
    const duplicateTenHangList = []; // Khởi tạo danh sách tên hàng trùng lặp

    tenHangList.forEach((tenHang, index) => {
        // Kiểm tra xem tên hàng hiện tại có xuất hiện trong phần tử sau không
        if (tenHangList.indexOf(tenHang, index + 1) !== -1 && duplicateTenHangList.indexOf(tenHang) === -1) {
            duplicateTenHangList.push(tenHang); // Nếu tìm thấy, thêm vào danh sách tên hàng trùng lặp
        }
    });

    return duplicateTenHangList;
}


function ImportHangHoaChiTiet(array) {
    impX = array.length;
    impC = 0;

    var lstChunks = chunks(150, array);
    aj_import(lstChunks, 0, lstChunks.length);
}


function aj_import(lst, b, e) {

    if (b == e) {
        SearchHH();
        dAlert("Import hàng hóa thành công", "Thông báo")
        loading(false)
    }
    else {
        $.ajax({
            type: "POST",
            dataType: "json",
            url: '/QLHD/HangHoa/Import',
            data: {
                hangHoa: lst[b]
            },
            success: function (data) {
                if (data.status == 1) {
                    impC = impC + lst[b].length;
                    loading(true, "Đang import được " + impC + "/" + impX + " hàng hóa")
                    b++;
                    aj_import(lst, b, e)

                }
                else {
                    dAlert(data.message, "Thông báo")
                    loading(false)
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
function loading(isShow, status) {

    if (isShow) {
        $("#statusImport").html(
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
        $("#statusImport").hide();
    }
}

function loadingCtrl(ctrl, isShow, message) {

    if (isShow) {
        $(ctrl).html(
            `<div class = 'alert alert-success text-center'>
                <div class="spinner-border " role="status">
                  <span class="visually-hidden">đang import ...</span>
                </div>
            <div class='mt-2'>
                ${message}   
            </div>
        </div>`
        ).show();
    }
    else {
        $(ctrl).hide();
    }
}


