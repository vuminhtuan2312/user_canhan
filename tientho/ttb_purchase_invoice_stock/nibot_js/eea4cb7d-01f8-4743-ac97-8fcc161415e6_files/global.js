//25-01-14 13:00
var isLock = 0;

var mFormat = "#,##0;(#,##0)";

var mFormat2 = "#,##0.00;(#,##0.00)";
var dsPhanMemKeToan = ["SMART PRO", "MISA", "FAST11", "FAST ONLINE"];



var dsTuyChonDienGiai = [
    {
        "value": "",
        "text": "-------",
    },
    {
        "value": "TENKH",
        "text": "Tên khách hàng",
    },
    {
        "value": "TENDM",
        "text": "Tên hàng hóa",
    },
    {
        "value": "HOADON",
        "text": "Series - Số HĐ - Ngày HĐ",
    },
    {
        "value": "TENKH_HOADON",
        "text": "Tên khách hàng - Series - Số HĐ - Ngày HĐ",
    },
    {
        "value": "TENKH_TENDM",
        "text": "Tên khách hàng - Tên hàng hóa",
    },

    {
        "value": "TENDM_MADTPN_HOADON",
        "text": "Tên hàng hóa - Mã ĐTPN - Series - Số HĐ",
    },

    {
        "value": "GHICHU",
        "text": "Ghi chú",
    },
    {
        "value": "GHICHU_TENKH",
        "text": "Ghi chú - Tên khách hàng",
    },

]

function kiemTraMatKhauHDDT(pwd) {
    const regex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*[\W_]).{8,}$/;
    return regex.test(pwd);
}

function openTienIch() {
    if (window.location.href.indexOf("nibot.vn") >= 0) {
        window.open("https://tracuu.nibot.vn", '_blank');
    }
    else {
        window.open("https://tracuu.nangdong.online", '_blank');
    }
}

function goTohome(text) {
    if (text.indexOf("GUID hoặc Username cha") > 0) {
        dAlert("Phiên đăng nhập hết hạn")
        setTimeout(function () {
            window.location.href = "/"
        }, 3000);
    }
}
function clearAutoCompleted() {
    try {
        DevExpress.ui.dxTextBox.defaultOptions({
            device: { deviceType: "desktop" },
            options: {
            onContentReady: function (info) {
                $(info.element).find("input").attr("autocomplete", "off");
            },
            }
        });
        $('input[type="text"]').attr('autocomplete', 'off');
    }
    catch (ex) {
        console.log(ex);
    }


}

clearAutoCompleted();

function showMsg(type, msg) {
    if (type == "OK") {
        $("#modalOK").show();
        $("#modalNG").hide();
    }
    else if (type == "NG") {
        $("#modalOK").hide();
        $("#modalNG").show();
    }
    $("#modalMsg").html(msg);   
    $("#modalAlert").modal('show');
}

function fmt(num) {
    var k = num.toString().split('.');
    if (num && k.length == 2 && k[1].length > 3) {
        console.log("XX:" + k);
        var n1 = k[0].toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
        return n1.toString() + "." + k[1];
    }
    else if (num) {
        return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    }

    return "0";
}

function addDate(date, dInterval) {
    let x = new Date(date);
    x.setDate(x.getDate() + dInterval);
    return x;
}

function subtractDate(dInterval) {
    let d = new Date();
    d.setDate(d.getDate() - dInterval);
    return d;
}

function getCuoiThang() {
    var date = new Date();
    return new Date(date.getFullYear(), date.getMonth() + 1, 0);
}


function getDauThang() {
    var date = new Date();
    return new Date(date.getFullYear(), date.getMonth(),1);
}

function getCuoiThang(date) {
    return new Date(date.getFullYear(), date.getMonth() + 1, 0);
}


function getDauThang(date) {
    return new Date(date.getFullYear(), date.getMonth(), 1);
}


function getQuyNay(date) {
    let m = date.getMonth() + 1;
    //1-3 , 4-6, 7-9,10-12;
    let k = 0;
    if (m <= 3) k = 0;
    else if (m <= 6) k = 1;
    else if (m <= 9) k = 2;
    else if (m <= 12) k = 3;
    
    let m1 = k * 3 + 1;
    let m2 = m1 + 2;
    let dauQuy = new Date(date.getFullYear(), m1-1, 1);
    let cuoiQuy = getCuoiThang(new Date(date.getFullYear(), m2 - 1, 1));
    return [dauQuy, cuoiQuy];
}

function getDauThang(date) {
    return new Date(date.getFullYear(), date.getMonth(), 1);
}



function toJP(date) {
    try {
        let m = date.getMonth() + 1;
        if (m < 10) m = "0" + m;
        let d = date.getDate();
        if (d < 10) d = "0" + d;
        return date.getFullYear() + "-" + m + "-" + d;
    }
    catch {
        return null;
    }
    
}
function toVn(date) {
    try {

        let m = date.getMonth() + 1;
        if (m < 10) m = "0" + m;
        let d = date.getDate();
        if (d < 10) d = "0" + d;
        return d + "/" + m + "/" + date.getFullYear();
    }
    catch {
        return null;
    }

}
function toVnShort(date) {
    try {

        let m = date.getMonth() + 1;
        if (m < 10) m = "0" + m;
        let d = date.getDate();
        if (d < 10) d = "0" + d;
        return d + "/" + m + "/" + (date.getFullYear()-2000);
    }
    catch {
        return null;
    }

}


function toVnShort2(date) {
    try {

        let m = date.getMonth() + 1;
        if (m < 10) m = "0" + m;
        let d = date.getDate();
        if (d < 10) d = "0" + d;
        let hours = date.getHours();
        if (hours < 10) hours = "0" + hours;
        let min = date.getMinutes();
        if (min < 10) min = "0" + min;
        //let sec = date.getSeconds();
        //if (sec < 10) sec = "0" + sec;
        return d + "/" + m + "/" + (date.getFullYear() - 2000) + " " + hours + ":" + min;
    }
    catch {
        return null;
    }

}

function daoFormatNgay(str) {
    try {

        str = str.toString().substr(0, 10);
        let k = str.split('-');
        return k[2] + "-" + k[1] + "-" + k[0];
    }
    catch {
        return null;
    }
}

function toFullVn(date) {
    console.log(date);
    let m = date.getMonth() + 1;
    if (m < 10) m = "0" + m;
    let d = date.getDate();

    if (d < 10) d = "0" + d;

    let hour = date.getHours();
    if (hour < 10) hour = "0" + hour;

    let min = date.getMinutes();
    if (min < 10) min = "0" + min;

    let sec = date.getSeconds();
    if (sec < 10) sec = "0" + sec;


    return d + "/" + m + "/" + date.getFullYear() + " " + hour + ":" + min +":"+ sec;
}

function addMonths(date, months) {
    const newDate = new Date(date.getTime());

    newDate.setMonth(newDate.getMonth() + months);
    return newDate;
}

function toVnDateString(dt) {
    dt = new Date(dt);
    let m = dt.getMonth() + 1;
    let d = dt.getDate();
    if (d < 10) d = "0" + d;
    if (m < 10) m = "0" + m;

    return `Ngày ${d} tháng ${m} năm ${dt.getFullYear()}`
}


function timDauTuan(date) {
    let k = date.getDay();
    if (k == 1) {
        return date;
    }
    return timDauTuan(addDate(date, -1));

}

function timCuoiTuan(date) {
    let k = date.getDay();
    if (k == 0) {
        return date;
    }
    return timCuoiTuan(addDate(date, 1));

}

function chunks(chunkSize, array) {
    
    var lstChunks = [];
    for (let i = 0; i < array.length; i += chunkSize) {
        const chunk = array.slice(i, i + chunkSize);
        lstChunks.push(chunk);
    }
    return lstChunks;
}


    
var locFileDataSource = [
    {
        "value": "",
        "text": "--Lọc file--",
    },
    {
        "value": "NO_XML",
        "text": "Không có XML",
    },
    {
        "value": "XML_THUE",
        "text": "Có XML Thuế",
    },
    {
        "value": "XML_MANUAL",
        "text": "Có XML User",
    },
   
    {
        "value": "PDF_MANUAL",
        "text": "Có PDF gốc",
    },
    {
        "value": "NO_PDF",
        "text": "Không có PDF gốc",
    },
    {
        "value": "XML_PDF",
        "text": "Có XML và PDF",
    },
]

var lhdDataSource = [
    {
        "value": "MUA_VAO",
        "text": "Mua Vào",
    },
    {
        "value": "BAN_RA",
        "text": "Bán Ra",
    },
    {
        "value": "MUA_VAO_DV",
        "text": "Mua Vào - HĐDV",
    },
    {
        "value": "BAN_RA_DV",
        "text": "Bán Ra - HĐDV",
    },
//    {
//        "value": "TAT_CA",
//        "text": "TÂT CẢ",
//    }
];

var trangThaiDataSource = [
    {       
        "value": "",
        "text": "--Trạng thái HĐ--",
    },
    {
        "value": "46",
        "text": "HĐ Đã bị Thay thế/Hủy",
    },

    {
        "value": "1",
        "text": "HĐ Mới",
    },
  
    {
        "value": "2",
        "text": "HĐ Thay thế",
    },
    {
        "value": "3",
        "text": "HĐ Đã điều chỉnh",
    },
    {
        "value": "4",
        "text": "HĐ Đã bị thay thế",
    },
    {
        "value": "5",
        "text": "HĐ Đã bị điều chỉnh",
    },
    {
        "value": "6",
        "text": "HĐ Đã bị hủy",
    },
   


];

var ketQuaKiemTraDataSource = [
    {
        "value": "",
        "text": "--K.quả k.tra--",
    },
    {
        "value": "0",
        "text": "TCT đã nhận",
    },
    {
        "value": "1",
        "text": "Đang k.tra",
    },
    {
        "value": "2",
        "text": "CQT t.chối HĐ",
    },
    {
        "value": "3",
        "text": "HĐ đủ đ.kiện",
    },
    {
        "value": "4",
        "text": "HĐ k đủ đ.kiện",
    },
    {
        "value": "5",
        "text": "Đã cấp MST",
    },
    {
        "value": "6",
        "text": "TCT k nhận mã",
    },
    {
        "value": "7",
        "text": "Đã k.tra định kỳ",
    },
    {
        "value": "8",
        "text": "HĐ có mã từ máy tính tiền",
    },
];

var dsDuyetDatasource = [
    {
        "value": "",
        "text": "--Duyệt n.bộ--",
    },
    {
        "value": "CHO_DUYET",
        "text": "Chờ duyệt"
    },
    {
        "value": "DA_DUYET",
        "text": "Đã duyệt",
    },
    {
        "value": "KHONG_HOP_LE",
        "text": "Không hợp lệ",
    },
];


var dsTinhChatHH = [
    {
        "value": "1",
        "text": "Hàng hóa dịch vụ",
    },
    {
        "value": "2",
        "text": "Khuyến mãi",
    },
    {
        "value": "3",
        "text": "Chiết khấu thương mại",
    },
    {
        "value": "4",
        "text": "Ghi Chú",
    },
    {
        "value": "5",
        "text": "Hàng hóa đặc trưng",
    },
];
    

function dAlert(msg, title) {
    if (!title) title="Thông báo"
    DevExpress.ui.dialog.alert(msg, title);
}



function dAlert2(msg, title) {
    let t = title;
    msg = msg.replace(/<br\/>/gi, "\n");
    if(!t) t = "Lỗi"
    bodyHtml = `
                <textarea class='form-control' style='width:100%;height:400px'>${msg}</textarea>
            `
    createModal("mDalert", t, bodyHtml, '')
    showModal("mDalert");
}
function CheckMH() {
    if (localStorage.hasOwnProperty("chkMH")) {
        return localStorage.getItem("chkMH") == 'true';
    }
    else {
        return true;
    }
}


var dsDuyetGrid = dsDuyetDatasource.filter(p=>p.value!="")


function numberToLetters(num) {
    let letters = ''
    while (num >= 0) {
        letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'[num % 26] + letters
        num = Math.floor(num / 26) - 1
    }
    return letters
}



function Logout() {

    $.ajax({
        type: "GET",
        dataType: "json",
        url: '/Logout',
        success: function () {
            window.location.href = "/";
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR);
        }
    });
}

var dictVideo = {
    "KET_XUAT" : [
                {
                    n:"Hướng dẫn đối chiếu dữ liệu các sheet kết xuất Excel trên Nibot",
                    l:"https://www.youtube.com/watch?v=MQZG_zVl3nc&list=PLrIpyPu6EqvC3Q-6Hshdv4x-Fn9Ao7CSO&index=2&t=2s&ab_channel=VanNhatNguyen"
                },
                {
                    n:"Các thao tác cần thực hiện trên smart pro sau khi bổ sung dữ liệu từ Nibot",
                    l:"https://www.youtube.com/watch?v=7PpVm9n-jGM&list=PLrIpyPu6EqvC3Q-6Hshdv4x-Fn9Ao7CSO&index=1&t=2s&ab_channel=VanNhatNguyen"
                } 
    ],
    "TRA_CUU" : [
        {
            n:"Hướng dẫn sử dụng",
            l:"https://www.youtube.com/watch?v=F7zLk4Xdgcs"
        },
    ],
    "DOI_CHIEU_CHEO": [
        {
            n:"Đối chiếu chéo hóa đơn với Nibot",
            l:"https://www.youtube.com/watch?v=XacYH4KtcMc"
        }],
    "HANG_HOA": [
        {
            n: "Tạo mã hàng hóa hàng loạt, tiết kiệm thời gian nhập liệu",
            l: "https://www.youtube.com/watch?v=cfEt00YMvDw&list=PLrIpyPu6EqvC3Q-6Hshdv4x-Fn9Ao7CSO&index=12&t=5s&ab_channel=VanNhatNguyen"
        }],
    "DON_VI_TINH": [
        {
            n: "Quy đổi đơn vị tính",
            l: "https://www.youtube.com/watch?v=xmz0_3ZCUaU&ab_channel=VanNhatNguyen"
        }],
    "DOI_TUONG_PHAP_NHAN": [
        {
            n: "Hướng dẫn sử dụng chức năng Đối tượng pháp nhân",
            l: "https://www.youtube.com/watch?v=WmgG1ZlPGgw&t=9s&ab_channel=VanNhatNguyen"
        }],
    "TINH_TRANG_DOANH_NGHIEP": [
        {
            n: "Tra cứu tình trạng hoạt động của nhà cung cấp dựa vào thông tin MST",
            l: "https://www.youtube.com/watch?v=hI7hkhbV1VQ&list=PLrIpyPu6EqvC3Q-6Hshdv4x-Fn9Ao7CSO&index=14&ab_channel=VanNhatNguyen"
        }],
    "QUAN_LY_NGUOI_DUNG": [
        {
            n: "Tra cứu tình trạng hoạt động của nhà cung cấp dựa vào thông tin MST",
            l: "https://www.youtube.com/watch?v=hI7hkhbV1VQ&list=PLrIpyPu6EqvC3Q-6Hshdv4x-Fn9Ao7CSO&index=14&ab_channel=VanNhatNguyen"
        }],

    "SAO_KE_NGAN_HANG": [
        {
            n: "Hướng dẫn sử dụng chức năng Sao Kê Ngân Hàng của Nibot",
            l: "https://www.youtube.com/watch?v=7cG0-kAQlTg"
        }],
    "SAO_KE_HTM": [
        {
            n: "Nibot Khắc phục lỗi file sao kê có Htm",
            l: "https://www.youtube.com/watch?v=7cG0-kAQlTg"
        }],
    "LUONG_DOANH_NGHIEP": [
        {
            n: "XỬ LÝ LƯƠNG DOANH NGHIỆP",
            l: "https://youtu.be/KRf1bfne4oI"
        }],
    
}

var cssHelp = {
    "modalFooter": "font-size:14pt;float:right;margin-top:0px",
    "traCuu": "font-size:18pt;margin-top:-5px;margin-left:10px",
    "htm": "font-size:24pt;margin-top:-5px;margin-left:10px"

}

function createHelpLink(id){
    let htmlVideo = ``;
    var d = dictVideo[id];
    let style = "";
    switch (id) {
        case "DOI_CHIEU_CHEO":
        case "KET_XUAT":
        case "HANG_HOA":
        case "DON_VI_TINH":
        case "DOI_TUONG_PHAP_NHAN":
        case "TINH_TRANG_DOANH_NGHIEP":
            style =cssHelp.modalFooter;
            break;
        case "QUAN_LY_NGUOI_DUNG":
        case "TRA_CUU":

            style = cssHelp.traCuu;
            break;
        case "SAO_KE_HTM":
        case "LUONG_DOANH_NGHIEP":

            style = cssHelp.htm;
            break;
        default:
            break;
    }

    for (let i in d){
        let k = d[i];
        htmlVideo += `
            <a target='_blank' class='btnHelp' href='${k.l}'" data-toggle="tooltip" data-placement="top" title="${k.n}" data-bs-original-title="${k.n}">
                <em class=" fw-bold text-danger icon ni ni-youtube"></em>
            </a>
        `
    }
    return `
        <div style="${style}" class='d-none d-md-block'>
            ${htmlVideo}
        </div>
    `
}


function createModal(id, title, bodyHtml, footerHTML) {
    let fhtml = '';
    if (footerHTML)
        fhtml = `
             <div class="modal-footer text-center ">
                ${footerHTML}
            </div>
        `
    var style = '';
    if (id == "mCauHinh") {
        var w = Math.trunc($(window).width() * 0.85);
        style = `style = "width:${w}px; position: absolute;top: 50%; left: 50%;transform: translate(-50%, -50%);" `;
    }
    if (id == "mChietKhauHoaMai") {
        var w = Math.trunc($(window).width() * 0.85);
        style = `style = "width:${w}px; position: absolute;top: 50%; left: 50%;transform: translate(-50%, -50%);" `;
    }
    if (id == "mXemPDF") {
        var w = Math.trunc($(window).width() * 0.75);
        var h = Math.trunc($(window).height() * 0.9);
        style = `style = "height:${h}px; width:${w}px; position: absolute;top: 50%; left: 50%;transform: translate(-50%, -50%);" `;
    }
    if (id == "mXemGiayNopTien") {
        var w = Math.trunc($(window).width() * 0.5);
        var h = Math.trunc($(window).height() * 0.9);
        style = `style = "height:${h}px; width:${w}px; position: absolute;top: 50%; left: 50%;transform: translate(-50%, -50%);" `;
    }
    else if (id == "mKiemTraTinhHopLe") {
        var w = Math.trunc($(window).width() * 0.8);
        style = `style = "width:${w}px; position: absolute;top: 50%; left: 50%;transform: translate(-50%, -50%);" `;
    }
    else if (id == "mDoiChieu") {
        var w = Math.trunc($(window).width() * 0.4);
        style = `style = "width:${w}px; position: absolute;top: 50%; left: 50%;transform: translate(-50%, -50%);" `;
    }

    
    else if (id == "mExcelChiTiet") {
        var w = 720;
        style = `style = "width:${w}px; position: absolute;top: 50%; left: 50%;transform: translate(-50%, -50%);" `;
    }
    
    else if (id == "mShowEmail" ) {
        var w = Math.trunc($(window).width() * 0.8);
        var h = Math.trunc($(window).height() * 0.8);
        style = `style = "width:${w}px;height:${h}px; position: absolute;top: 50%; left: 50%;transform: translate(-50%, -50%);" `;
    }
 
    else if (id == "mDongBoHangLoat" || id == "mTraCuuMSTDNQL" || id == "mThongKeHoaDon") {
        var w = Math.trunc($(window).width() * 0.85);
        var h = Math.trunc($(window).height() * 0.85);
        style = `style = "width:${w}px;height:${h}px; position: absolute;top: 50%; left: 50%;transform: translate(-50%, -50%);" `;
    }
    else if ( id == "mTaiHoaDonGoc" ) {
        var w = Math.trunc($(window).width() * 0.85);
        style = `style = "width:${w}px; position: absolute;top: 50%; left: 50%;transform: translate(-50%, -50%);" `;
    }
    else if (  id=="mManaNapTien") {
        var w = Math.trunc($(window).width() * 0.85);
        style = `style = "width:${w}px; position: absolute;top: 50%; left: 50%;transform: translate(-50%, -50%);" `;
    }
    let modalBodyHtml = `
          <div class="modal-dialog" role="document">
                <div class="modal-content" ${style} >
                    <a href="#" class="close" data-bs-dismiss="modal" aria-label="Close">
                        <em class="icon ni ni-cross"></em>
                    </a>
                    <div class="modal-header">
                        <h5 class="modal-title mdl_title" >${title}</h5>
                    </div>
                    <div class="modal-body">
                        ${bodyHtml}          
                    </div>
                    ${fhtml}
                </div>
            </div>
    `
    if (!document.getElementById(id)) {
        let html = `
            <div class="modal fade" tabindex="-1" id="${id}">
               ${modalBodyHtml}
            </div>
        `
        $("body").append(html);
    } else {
        $(`#${id}`).html(modalBodyHtml);
    }

}
function showModal(id) {
    $(`#${id}`).modal("show");
}

function hideModal(id) {
    $(`#${id}`).modal("hide");
}


function removeVietnameseTones(str) {
    str = str.replace(/à|á|ạ|ả|ã|â|ầ|ấ|ậ|ẩ|ẫ|ă|ằ|ắ|ặ|ẳ|ẵ/g, "a");
    str = str.replace(/è|é|ẹ|ẻ|ẽ|ê|ề|ế|ệ|ể|ễ/g, "e");
    str = str.replace(/ì|í|ị|ỉ|ĩ/g, "i");
    str = str.replace(/ò|ó|ọ|ỏ|õ|ô|ồ|ố|ộ|ổ|ỗ|ơ|ờ|ớ|ợ|ở|ỡ/g, "o");
    str = str.replace(/ù|ú|ụ|ủ|ũ|ư|ừ|ứ|ự|ử|ữ/g, "u");
    str = str.replace(/ỳ|ý|ỵ|ỷ|ỹ/g, "y");
    str = str.replace(/đ/g, "d");
    str = str.replace(/À|Á|Ạ|Ả|Ã|Â|Ầ|Ấ|Ậ|Ẩ|Ẫ|Ă|Ằ|Ắ|Ặ|Ẳ|Ẵ/g, "A");
    str = str.replace(/È|É|Ẹ|Ẻ|Ẽ|Ê|Ề|Ế|Ệ|Ể|Ễ/g, "E");
    str = str.replace(/Ì|Í|Ị|Ỉ|Ĩ/g, "I");
    str = str.replace(/Ò|Ó|Ọ|Ỏ|Õ|Ô|Ồ|Ố|Ộ|Ổ|Ỗ|Ơ|Ờ|Ớ|Ợ|Ở|Ỡ/g, "O");
    str = str.replace(/Ù|Ú|Ụ|Ủ|Ũ|Ư|Ừ|Ứ|Ự|Ử|Ữ/g, "U");
    str = str.replace(/Ỳ|Ý|Ỵ|Ỷ|Ỹ/g, "Y");
    str = str.replace(/Đ/g, "D");
    // Some system encode vietnamese combining accent as individual utf-8 characters
    // Một vài bộ encode coi các dấu mũ, dấu chữ như một kí tự riêng biệt nên thêm hai dòng này
    str = str.replace(/\u0300|\u0301|\u0303|\u0309|\u0323/g, ""); // ̀ ́ ̃ ̉ ̣  huyền, sắc, ngã, hỏi, nặng
    str = str.replace(/\u02C6|\u0306|\u031B/g, ""); // ˆ ̆ ̛  Â, Ê, Ă, Ơ, Ư
    // Remove extra spaces
    // Bỏ các khoảng trắng liền nhau
    str = str.replace(/ + /g, " ");
    str = str.trim();
    // Remove punctuations
    // Bỏ dấu câu, kí tự đặc biệt
    str = str.replace(/!|@|%|\^|\*|\(|\)|\+|\=|\<|\>|\?|\/|,|\:|\;|\'|\"|\&|\#|\[|\]|~|\$|_|`|-|{|}|\||\\/g, " ");
    return str;
}


function KhoangNgay(val, isLamTron, nam) {
    var TU_NGAY = "";
    var DEN_NGAY = "";
    if (val == "Hôm nay" || val == "1 tuần" || val == "Tuần này" || val == "Tháng này" || val == "Năm này" || val == "Năm trước") {
        nam = "";
    }
    var today = getToday(nam);
    
    if (val == "Hôm nay") {
        TU_NGAY = new Date(toJP(today));
        DEN_NGAY = new Date(toJP(today));
    }
    else if (val == "1 tuần") {
        DEN_NGAY = today;
        TU_NGAY = addDate(today, -7);
    }
    else if (val == "Tuần này") {
        TU_NGAY = timDauTuan(today);
        DEN_NGAY = timCuoiTuan(today);
    }
    else if (val == "Tuần trước") {
        today = addDate(timDauTuan(today), -6);
        TU_NGAY = timDauTuan(today);
        DEN_NGAY = timCuoiTuan(today);
    }
    else if (val == "Tháng này") {
        TU_NGAY = getDauThang(today);
        DEN_NGAY = today;
    }
    else if (val == "Tháng trước") {
        TU_NGAY = getDauThang(addDate(getDauThang(today), -1));
        DEN_NGAY = addDate(getDauThang(today), -1)
    }
    else if (val == "Quý này") {
        var x = getQuyNay(today);
        TU_NGAY = x[0];
        DEN_NGAY = x[1];

    }
    else if (val == "Quý trước") {
        var x = getQuyNay(today);
        var t = addDate(x[0], -10);
        x = getQuyNay(t);
        TU_NGAY = x[0];
        DEN_NGAY = x[1];

    }
    else if (val == "Quý 1") {
        var x = getQuyNay(new Date(today.getFullYear(), 0, 1));
        TU_NGAY = x[0];
        DEN_NGAY = x[1];
    }
    else if (val == "Quý 2") {
        var x = getQuyNay(new Date(today.getFullYear(), 3, 1));
        TU_NGAY = x[0];
        DEN_NGAY = x[1];
    }
    else if (val == "Quý 3") {
        var x = getQuyNay(new Date(today.getFullYear(), 6, 1));
        TU_NGAY = x[0];
        DEN_NGAY = x[1];
    }
    else if (val == "Quý 4") {
        var x = getQuyNay(new Date(today.getFullYear(), 9, 1));
        TU_NGAY = x[0];
        DEN_NGAY = x[1];
    }
    else if (val == "Năm này") {
        TU_NGAY = new Date(today.getFullYear(), 0, 1);
        DEN_NGAY = today;
    }
    else if (val == "Năm trước") {
        TU_NGAY = new Date(today.getFullYear() - 1, 0, 1);
        DEN_NGAY = new Date(today.getFullYear() - 1, 11, 31);
    }
    else if (val.indexOf("Tháng ") >= 0) {
        let k = parseInt(val.split(' ')[1]) - 1;
        TU_NGAY = new Date(today.getFullYear() , k, 1);
        DEN_NGAY = getCuoiThang(TU_NGAY)
    }
    else if (val.indexOf("Full Năm") == 0) {
        TU_NGAY = new Date(nam, 0, 1);
        DEN_NGAY = new Date(nam, 11, 31);
    }
    else if (val == "Tất cả") {
        return {
            "start": null,
            "end": null,
        }
    }
    let denNgay = new Date(DEN_NGAY);
    let tuNgay = new Date(TU_NGAY);
    let td = getToday()
    if (toJP(tuNgay) > toJP(td)) {
        return KhoangNgay(val, isLamTron, nam - 1);
    }

    if (isLamTron) {
        if (nam == new Date().getFullYear()) {
            let isCurMonth = today.getMonth() == denNgay.getMonth();
            if (isCurMonth && toJP(today) < toJP(denNgay)) denNgay = today;
        }
    }

    return {
        "start": tuNgay,
        "end": denNgay,
    }
}

function getToday(nam) {
    var d = new Date();
    if (!nam) nam = d.getFullYear();
    return new Date(nam, d.getMonth(), d.getDate());
}

function setCfg(cfgName, cfgValue) {
    localStorage.setItem(cfgName, cfgValue);
}


function getCfg(cfgName) {
    return localStorage.getItem(cfgName);
}
function XuLyThanhPho(str) {
    str = removeVietnameseTones(str);
    str = str.replace(/\s/gi, '');
    str = str.replace(/thanhpho/gi, '');
    str = str.replace(/hochiminh/gi, 'hcm');
    str = str.replace(/vietnam/gi, '');
    str = str.replace(/khupho/gi, '');
    str = str.replace(/huyen/gi, '');
    str = str.replace(/duong/gi, '');
    str = str.replace(/sonha/gi, '');
    str = str.replace(/ngach/gi, '');
    str = str.replace(/phuong/gi, '');
    str = str.replace(/tinh/gi, '');
    str = str.replace(/quan/gi, '');
    str = str.replace(/ngo/gi, '');
    str = str.replace(/tp\./gi, '');
    str = str.replace(/tp/gi, '');
    str = str.replace(/kp/gi, '');
    str = str.replace(/xa/gi, '');
    str = str.replace(/so/gi, '');
    str = str.replace(/to/gi, '');
    str = str.replace(/ap/gi, '');
    str = str.replace(/sn/gi, '');
    str = str.replace(/t\./gi, '');
    str = str.replace(/p\./gi, '');
    str = str.replace(/\./gi, '');
    return str;

}

function XuLyTenCongTy(str) {
    str = removeVietnameseTones(str);
    str = str.replace(/\s/gi, '');
    str = str.toLowerCase();

    str = str.replace(/congty/gi, 'cty');
    str = str.replace(/trachnhiemhuuhan/gi, 'tnhh');
    str = str.replace(/motthanhvien/gi, 'mtv');

    str = str.replace(/doanhnghieptunhan/gi, 'dntn');
    str = str.replace(/vatlieuxaydung/gi, 'vlxd');
    str = str.replace(/thuongmaicophan/gi, 'tmcp');
    str = str.replace(/doanhnghiep/gi, 'dn');
    str = str.replace(/phongkhamdakhoa/gi, 'pkdk');

    str = str.replace(/tunhan/gi, 'tn');
    str = str.replace(/thuongmai/gi, 'tm');
    str = str.replace(/vantai/gi, 'vt');

    str = str.replace(/cophan/gi, 'cp');
    str = str.replace(/hopdanh/gi, 'hd');
    return str;

}




var iInfo = 0;

var contentInfo = [
    {
        "TieuDe": "2023-03-22: Chức năng xử lý Lương Doanh nghiệp",
        "Url": "https://youtu.be/KRf1bfne4oI",
    },
    {
        "TieuDe": "2023-03-01: Chức năng đọc file Excel Sao Kê Ngân hàng",
        "Url": "https://www.youtube.com/watch?v=7tS2YFKnnPI&ab_channel=VanNhatNguyen",
    },
    {
        "TieuDe": "2023-02-04: Cải tiến tốc độ tải hóa đơn của Nibot",
        "Url": "https://www.youtube.com/watch?v=7tS2YFKnnPI&ab_channel=VanNhatNguyen",
    },
    {
        "TieuDe": "2023-02-02: Tải dữ liệu trực tiếp từ Nibot vào Smart Pro",
        "Url": "https://www.youtube.com/watch?v=tbv_ZeweGOE&t=288s&ab_channel=VanNhatNguyen"
    },
    {
        "TieuDe": "2023-01-16: Đối chiếu chéo Hóa đơn giữa các hệ thống",
        "Url": "https://www.youtube.com/watch?v=czWfLEM2r6c&t=12s&ab_channel=VanNhatNguyen"
    },

    {
        "TieuDe": "2023-01-15: Phân tích dữ liệu được export ra từ Nibot",
        "Url": "https://www.youtube.com/watch?v=czWfLEM2r6c&t=12s&ab_channel=VanNhatNguyen"
    },
];

function dspLinkInfo() {
    let c = contentInfo[iInfo];
    let html = `
            <div class='mt-1 d-none d-lg-block' style='max-width:300px' >
                <a href='${c.Url}' target='_blank'><span style='color:#95b7c5c4'> <em class="icon ni ni-star"></em><span class='text-truncate'>${c.TieuDe}</span></span></a>
            </div>
        `
    $("#xxx").html(html);
    iInfo = (iInfo + 1) % contentInfo.length;
}

function initInfo() {
    setInterval(function () {
        dspLinkInfo();
    }, 15000);
}
$(document).ready(function () {
  //  dspLinkInfo();
   // initInfo();
    dspThongBao();

    keyEventListen();


})

function dspThongBao() {
    $.ajax({
        type: "GET",
        dataType: "json",
        url: '/LoadThongBao/20',
        success: function (data) {
            createThongBao(data);
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR);
        }
    });

}

function openThongBao(idThongBao) {
    window.location = `/QuanLyThongBao/${idThongBao}`
}

function createThongBao(data) {
    let s = data.filter(p => p.DaXem == false).length;
    
    let cssChuong = s > 0 ? "icon-status-danger" : "icon-status-info";
    let count = '';

    if (s == 0) {
        count = '';
    }
    else {
        if (s > 10) {
            s = "+10";
        }
        count = `<div style="font-size: 10pt; margin-left: 4px;color: #e85347;font-weight: bold;">${s}</div>`
    }
    
    let html = ` 
        <a href="#" class="dropdown-toggle nk-quick-nav-icon" data-bs-toggle="dropdown">
            <div class="icon-status ${cssChuong}"><em class="icon ni ni-bell"></em></div>
            ${count}
        </a>
        <div class="dropdown-menu dropdown-menu-xl dropdown-menu-end dropdown-menu-s1">
            <div class="dropdown-head">
                <span class="sub-title nk-dropdown-title"><b>Thông Báo</b></span>
            </div>
            <div class="dropdown-body">
                <div class="nk-notification">
    `
   
    if (data.length > 0) {
        for (let i in data) {
            let r = data[i];
            let cssBg = r.DaXem ? "" : ""
            html += `
                <div class="nk-notification-item dropdown-inner ${cssBg}">
                    
                    <div class="nk-notification-content ">
                        <a href='javascript:void(0)' onclick='openThongBao("${r.IdThongBao}")'>
                            <div class="nk-notification-text">${r.NoiDung}</div>
                            <div class="nk-notification-time">${r.NgayTao}</div>
                        </a>
                        
                    </div>
                </div>
            `
        }
        html += `
                </div><!-- .nk-notification -->
          </div><!-- .nk-dropdown-body -->
            <div class="dropdown-foot center">
                <a href="/QuanLyThongBao">Xem tất cả</a>
            </div>
        </div>
    `
    }
    else {
        html += `
                <div class="nk-notification-item dropdown-inner">
                    <div class="nk-notification-content ">
                        Ahihi, chưa có thông báo nào hết. Khi nào có thì NiBot sẽ báo!!!
                    </div>
                </div>
            `
    }
 
    $("#bThongBao").html(
        html
    )
}


var dsLoaiThongBao = [
    {
        "value": "CANH_BAO",
        "text": "Cảnh báo hệ thống",
    },
    {
        "value": "LICH_SU_DONG_BO",
        "text": "Lịch sử đồng bộ",
    },
    {
        "value": "",
        "text": "Tất cả",
    },
];


//////////////////////////////// XU LY THEM HANG HOA


function keyEventListen() {
    $(document).on('keydown', function (e) {
        var tab = getCurrentTab();

        if (e.altKey) { // Ctr+N
            if (e.keyCode == 78) {
                // Handle Alt+N keypress
                e.preventDefault(); // Prevent default action for this key combination
                if (tab == 'linkHH') {
                    OpenModalThemHangHoa();
                }
                else if (tab == 'linkQD') {
                    OpenModalThemQuyDoi();
                }
                else if (tab == 'linkDTPN') {
                    OpenModalThemDTPN();
                }
            }
            else if (e.keyCode == 68) {
                e.preventDefault(); 
                if (tab == 'linkHH') {
                    let r = dgHH.getSelectedRowsData();
                    if (r.length>0) {
                        OpenModalThemQuyDoi(r[0]);
                    }
                    else {
                        OpenModalThemQuyDoi();

                    }
                }
            }
            if (e.keyCode == 83) {// alt+S
                e.preventDefault(); // Prevent default action for this key combination
                XuLyForm(1, tab);
            }
            if (e.keyCode == 71) {// alt+G
                e.preventDefault(); // Prevent default action for this key combination
                XuLyForm(2, tab);
            }
            
        }

    });
}

function getCurrentTab() {
    return $('#nibotTab .nav-link.active').attr("id");
}



function XuLyForm(Loai, tab) {
    console.log("XulyForm", Loai,tab);

    if (tab == 'linkHH') {
        let k = $("#mFrmHangHoa");
        if (k && k.attr("aria-modal") == 'true') {
            btnThemHangHoa(Loai);
        }
        let d = $("#mFrmQuyDoi");
        if (d && d.attr("aria-modal") == 'true') {
            btnThemQuyDoi(Loai);
        }
    }
    else if (tab == 'linkQD') {
        let k = $("#mFrmQuyDoi");
        if (k && k.attr("aria-modal") == 'true') {
            btnThemQuyDoi(Loai);
        }
    }
    else if (tab == 'linkDTPN') {
        let k = $("#mFrmDTPN");
        if (k && k.attr("aria-modal") == 'true') {
            btnThemDTPN(Loai);
        }
    }

}

function hopLeHangHoa(data) {
    $("#errHangHoa").html("");
    let errMsg = "";
    try {
        let matk = parseInt(data.MaTK);
        if (matk.toString() == "NaN" || matk == 0) {
            errMsg += "- Mã tài khoản không hợp lệ<br/>";
        }
    }
    catch {
        errMsg += "- Mã tài khoản phải là dạng số<br/>";
    }
    if (data.MaTK == '') {
        errMsg += "- Mã tài khoản không được để trống<br/>";
    }

    if (data.MaHang == '') {
        errMsg += "- Mã hàng không được để trống<br/>";
    }

    if (!(data.LoaiHd == "" || data.LoaiHd == "V" || data.LoaiHd == "R")) {
        errMsg += "- Loại hóa đơn phải để trống hoặc là V hoặc là R<br/>";
    }
    if (errMsg != "") {
        $("#errHangHoa").html(errMsg);
        return false;
    }
    return true;
}

function newHangHoa() {
    var data = {};
    data.MaTK = ($("#fMaTK").val() ?? "").trim();
    data.MaHang = ($("#fMaHang").val() ?? "").trim();
    data.TenHang = ($("#fTenHang").val() ?? "").trim();
    data.LoaiHd = ($("#fLoaiHD").val() ?? "").toUpperCase().trim();
    data.MaSoThue = MST;
    return data;
}

function clearHangHoa() {
    $("#fMaTK").val('');
    $("#fMaHang").val('');
    $("#fTenHang").val('');
    $("#fLoaiHD").val('');
    setTimeout(function () {
        $("#fMaTK").focus();
    }, 300);

}
function ajThemHangHoa(objHangHoa, loai) {
    $.ajax({
        type: "POST",
        dataType: "json",
        url: '/QLHD/HangHoa/ThemHangHoa',
        data: objHangHoa,
        success: function (data) {
            if (data.status == 1) {
                let k = data.obj;
                k.isNew = true;
                DATA_HH.unshift(k);
                dgHH.option("dataSource", DATA_HH);
                dgHH.refresh();
                if (loai == 1) {
                    $("#mFrmHangHoa").modal('hide');
                }
                else {
                    clearHangHoa();
                }

            }
            else {
                dAlert(data.message);
            }
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR);
        }
    });
}


function btnThemHangHoa(Loai) {
    var data = newHangHoa();
    if (hopLeHangHoa(data)) {
        ajThemHangHoa(data, Loai);
    }
}


function OpenModalThemHangHoa() {
    let bodyHtml = `
        <form id="frmHangHoa" autocompleted = "off">
            <div class='row' >
                <div class='col-12'>
                    <div class="form-group">
                        <label class="form-label" for="fMaTK">Mã tài khoản</label>
                        <div class="form-control-wrap">
                            <input type="text" class="form-control" id="fMaTK" >
                        </div>
                    </div>
                        <div class="form-group">
                        <label class="form-label" for="fMaHang">Mã hàng</label>
                        <div class="form-control-wrap">
                            <input type="text" class="form-control" id="fMaHang" >
                        </div>
                    </div>
                        <div class="form-group">
                        <label class="form-label" for="fTenHang">Tên hàng</label>
                        <div class="form-control-wrap">
                            <input type="text" class="form-control" id="fTenHang" >
                        </div>
                    </div>
                        <div class="form-group">
                        <label class="form-label" for="fLoaiHD">Loại hóa đơn (để trống, V, R)</label>
                            <div class="form-control-wrap">
                            <input type="text" class="form-control" id="fLoaiHD" >
                        </div>
                    </div>
                </div>
                <div class='col-12 mt-2 mb-2 text-danger' id="errHangHoa">
                </div>
                <div class='col-12 text-center mt-3'>
                    <button type='button' class='btn btn-primary' onClick='btnThemHangHoa(2)'>LƯU VÀ TIẾP [ALT+G]</button>
                    <button type='button' class='btn btn-primary' onClick='btnThemHangHoa(1)'>LƯU VÀ ĐÓNG [ALT+S]</button>
                </div>
            </div>
        </form>
    `
    let btnHtml = '';
    createModal("mFrmHangHoa", "Thêm hàng hóa", bodyHtml, btnHtml);
    showModal("mFrmHangHoa");
    setTimeout(function () { $("#fMaTK").focus() }, 200);
}


function isNumber(str) {
    return !isNaN(str);
}


function clearQuyDoi() {
    if (ROW_HH_QD != null && ROW_HH_QD.MaHang) {
        $("#fDvtQDGoc,#fDvtQD,#fSoLuongQD").val('');
        setTimeout(function () {
            $("#fDvtQDGoc").focus();
        }, 200);
    }
    else {
        $("#fSearchQD,#fMaHangQD,#fTenHangQD,#fDvtQDGoc,#fDvtQD,#fSoLuongQD").val('');
        $("#errQuyDoi").html('')

        setTimeout(function () {
            $("#fSearchQD").focus();
        }, 200);
    }

}

function newQuyDoi() {
    var data = {};
    data.SearchQD = $("#fSearchQD").val().trim();
    data.MaSoThue = MST; 
    data.MaHang = $("#fMaHangQD").val().trim();
    data.TenHang = $("#fTenHangQD").val().trim(); 

    if (data.MaHang =="" && data.TenHang == "" && data.SearchQD!="") {
        let m = $("#fSearchQD").val().trim();
        var x = DATA_HH.filter(p => p.dsp == m);
        if (x.length > 0) {
            data.MaHang = x[0].MaHang.trim();
            data.TenHang = x[0].TenHang.trim();
        }
    }


    data.Dvt = $("#fDvtQDGoc").val().trim(); 
    data.DvtquyDoi = $("#fDvtQD").val().trim(); 
    data.SoLuongQuyDoi = $("#fSoLuongQD").val().trim(); 
    return data;
}


function hopleQuyDoi(data) {
    $("#errQuyDoi").html("");
    let errMsg = "";
    let i = DATA_HH.filter(p => p.dsp == data.SearchQD).length;
    if (i == 0) {
        errMsg += "- Hàng hóa không tồn tại";
    }

    if (data.MaHang == "" || data.TenHang == "") {
        errMsg += "- Chưa chọn hàng hóa";
    }
   
    if (data.Dvt == '') {
        errMsg += "- Đơn vị tính (Hóa đơn) không được để trống<br/>";
    }
    if (data.DvtquyDoi == '') {
        errMsg += "- Đơn vị tính (Quy đổi) không được để trống<br/>";
    }

    if (data.SoLuongQuyDoi == '') {
        errMsg += "- Số lượng (Quy đổi) không được để trống và phải là số<br/>";
    }

    if (!isNumber(data.SoLuongQuyDoi)) {
        errMsg += "- Số lượng (Quy đổi) phải là số<br/>";
    }
    var k = DATA_QD.filter(p => p.MaHang == data.MaHang && p.TenHang == data.TenHang && p.Dvt == data.Dvt );
    if (k.length > 0) {
        errMsg += `- ${data.SearchQD} đã tồn tại ĐVT [${data.Dvt}] được quy đổi ra [${k[0].DvtquyDoi}]. <br/>`; 
    }


    if (errMsg != "") {
        $("#errQuyDoi").html(errMsg);
        return false;
    }

    return true;
}

function ajThemQuyDoi(objQuyDoi, loai) {
    $.ajax({
        type: "POST",
        dataType: "json",
        url: '/QLHD/QuyDoi/ThemQuyDoi',
        data: objQuyDoi,
        success: function (data) {
            if (data.status == 1) {
                let k = data.obj;
                k.isNew = true;
                DATA_QD.unshift(k);
                dgQuyDoi.option("dataSource", DATA_QD);
                dgQuyDoi.refresh();
                if (loai == 1) {
                    $("#mFrmQuyDoi").modal('hide');
                }
                else {
                    clearQuyDoi();
                }

            }
            else {
                dAlert(data.message);
            }
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR);
        }
    });
}


function btnThemQuyDoi(Loai) {
    var data = newQuyDoi();
    if (hopleQuyDoi(data)) {
        ajThemQuyDoi(data, Loai);
    }
}

var dsSource = [];
var ROW_HH_QD = null;
function OpenModalThemQuyDoi(dataRow=null) {
    ROW_HH_QD = dataRow;
    if (!DATA_QD) {
        SearchQuyDoi();
    }
    dsSource = [];
    if (DATA_HH.length == 0) {
        initCtrlHangHoa();
        //  isFirstClickHH = false;
        SearchHH();

        for (let i in DATA_HH) {
            if (DATA_HH[i].MaHang) {
                dsSource.push(DATA_HH[i]["dsp"]);
            }
        }
    }
    else if (DATA_HH.length > 0) {
        for (let i in DATA_HH) {
            if (DATA_HH[i].MaHang) {
                dsSource.push(DATA_HH[i]["dsp"]);
            }
        }
    }

    let bodyHtml = `
        <form id="frmQuyDoi" autocomplete = "off">
            <div class='row' >
                <div class='col-12'>
                    <div class="form-group">
                        <label class="form-label" for="fMaHangQD">Hàng hóa</label>
                        <div class="form-control-wrap">
                            <input type="text" autocomplete="off" class="form-control"  id="fSearchQD" placeholder="nhập mã hàng, tên hàng cần quy đổi">
                            <input type="hidden"  id="fMaHangQD">
                            <input type="hidden"  id="fTenHangQD" >

                        </div>
                    </div>
                  
                    <div class="form-group">
                        <label class="form-label" for="fDvtQDGoc">ĐVT gốc</label>
                        <div class="form-control-wrap">
                            <input type="text" class="form-control" id="fDvtQDGoc" >
                        </div>
                    </div>
                    <div class="form-group">
                        <label class="form-label" for="fDvtQD">ĐVT đích (quy đổi)</label>
                            <div class="form-control-wrap">
                            <input type="text" class="form-control" id="fDvtQD" >
                        </div>
                    </div>
                    <div class="form-group">
                        <label class="form-label" for="fSoLuongQD">Số lượng (quy đổi)</label>
                            <div class="form-control-wrap">
                            <input type="text" class="form-control" id="fSoLuongQD" >
                        </div>
                    </div>
                </div>
                <div class='col-12 mt-2 mb-2 text-danger' id="errQuyDoi">
                </div>
                <div class='col-12 text-center mt-3'>
                    <button type='button' class='btn btn-primary' onclick='btnThemQuyDoi(2)'>LƯU VÀ TIẾP [ALT+G]</button>
                    <button type='button' class='btn btn-primary' onclick='btnThemQuyDoi(1)'>LƯU VÀ ĐÓNG [ALT+S]</button>
                </div>
            </div>
        </form>
    `
    let btnHtml = '';
  
    createModal("mFrmQuyDoi", "Thêm Quy Đổi ĐVT", bodyHtml, btnHtml);
    showModal("mFrmQuyDoi");
    

    autocomplete(document.getElementById("fSearchQD"), dsSource);

    setTimeout(function () {
        $("#fSearchQD").focus();
        console.log("TEST", dataRow);
        if (dataRow && dataRow["MaHang"]) {
            console.log(dataRow["dsp"])
            $("#fSearchQD").val(dataRow["dsp"]);
            $("#fMaHangQD").val('');
            $("#fTenHangQD").val('');
            let k = $("#fSearchQDautocomplete-list input");
            if (k.length > 0) {
                $("#fSearchQD").val($(k[0]).val());
            }
            $("#fSearchQDautocomplete-list").html('')
            let m = $("#fSearchQD").val().trim();
            if (m) {
                var x = DATA_HH.filter(p => p.dsp == m);
                if (x.length > 0) {
                    $("#fMaHangQD").val(x[0].MaHang.trim());
                    $("#fTenHangQD").val(x[0].TenHang.trim());
                    setTimeout(function () {
                        $("#fDvtQDGoc").focus();
                    }, 50)
                }
            }
        }

    }, 200);

    $("#fSearchQD").on("keydown", function (e) {
        if (e.keyCode == 13 || e.keyCode == 9) { // Enter key
            $("#fMaHangQD").val('');
            $("#fTenHangQD").val('');
            let k = $("#fSearchQDautocomplete-list input");
            if (k.length > 0 ) {
                $("#fSearchQD").val($(k[0]).val());
            }
            $("#fSearchQDautocomplete-list").html('')
            let m = $("#fSearchQD").val().trim();
            if (m) {
                var x = DATA_HH.filter(p => p.dsp == m);
                if (x.length > 0) {
                    $("#fMaHangQD").val(x[0].MaHang.trim());
                    $("#fTenHangQD").val(x[0].TenHang.trim());
                    setTimeout(function () {
                        $("#fDvtQDGoc").focus();
                    },50)
                }
            }
        }
    })
}


function clearDTPN() {
    $("#fMst,#fMaKh").val('');
    $("#errDTPN").html('')
    setTimeout(function () {
        $("#fMst").focus();
    }, 200);
}

function newDTPN() {
    var data = {};
    data.MaSoThue = MST;
    data.Mst = $("#fMst").val().trim();
    data.MaKh = $("#fMaKh").val().trim();
    data.HoaDonDv = false;
    data.MaTaiKhoan = '';
    data.MaTkCpdt = '';
    data.Sxkd = '';

    return data;
}


function hopleDTPN(data) {
    $("#errDTPN").html("");
    let errMsg = "";

    if (data.Mst == '') {
        errMsg += "- Mã số thuế DN/Tên khách lẻ được để trống<br/>";
    }
    else {
        let k = DATA_DTPN.filter(p => p.Mst.toUpperCase() == data.Mst.toUpperCase());
        if (k.length > 0) {
            errMsg += "- Mã số thuế DN/Tên khách lẻ không được trùng<br/>";
        }
    }
    if (data.MaKh == '') {
        errMsg += "- Mã khách hàng (Smart Pro) được để trống<br/>";
    }


    if (errMsg != "") {
        $("#errDTPN").html(errMsg);
        return false;
    }

    return true;
}

function ajThemDTPN(objDTPN, loai) {
    $.ajax({
        type: "POST",
        dataType: "json",
        url: '/QLHD/DTPN/ThemDTPN',
        data: objDTPN,
        success: function (data) {
            if (data.status == 1) {
                let k = data.obj;
                k.isNew = true;
                DATA_DTPN.unshift(k);
                dgDTPN.option("dataSource", DATA_DTPN);
                dgDTPN.refresh();
                if (loai == 1) {
                    $("#mFrmDTPN").modal('hide');
                }
                else {
                    clearDTPN();
                }

            }
            else {
                dAlert(data.message);
            }
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR);
        }
    });
}


function btnThemDTPN(Loai) {
    var data = newDTPN();
    if (hopleDTPN(data)) {
        ajThemDTPN(data, Loai);
    }
}


function OpenModalThemDTPN() {
    let bodyHtml = `
        <form id="frmDTPN" autocompleted = "off">
            <div class='row' >
                <div class='col-12'>
                    <div class="form-group">
                        <label class="form-label" for="fMst">Mã số DN hoặc Tên khách lẻ</label>
                        <div class="form-control-wrap">
                            <input type="text" class="form-control" id="fMst" >
                        </div>
                    </div>
                    <div class="form-group">
                        <label class="form-label" for="fMaKh">Mã khách hàng trên Smart Pro</label>
                        <div class="form-control-wrap">
                            <input type="text" class="form-control" id="fMaKh" >
                        </div>
                    </div>
                </div>
                <div class='col-12 mt-2 mb-2 text-danger' id="errDTPN">
                </div>
                <div class='col-12 text-center mt-3'>
                    <button type='button' class='btn btn-primary' onclick='btnThemDTPN(2)'>LƯU VÀ TIẾP [ALT+G]</button>
                    <button type='button' class='btn btn-primary' onclick='btnThemDTPN(1)'>LƯU VÀ ĐÓNG [ALT+S]</button>
                </div>
            </div>
        </form>
    `
    let btnHtml = '';
    createModal("mFrmDTPN", "Thêm Đối tượng Pháp nhân", bodyHtml, btnHtml);
    showModal("mFrmDTPN");
    setTimeout(function () { $("#fMst").focus() }, 200);
}


function getExcelData(data, col) {
    try {
        if (data[col].hasOwnProperty("result")) {
            return data[col].result.toString();
        }
        else {
            return data[col];
        }
    }
    catch {
        return "";
    }
}

function autocomplete(inp, arr) {
    /*the autocomplete function takes two arguments,
    the text field element and an array of possible autocompleted values:*/
    var currentFocus;
    /*execute a function when someone writes in the text field:*/
    inp.addEventListener("input", function (e) {
        var a, b, i, val = this.value;
        /*close any already open lists of autocompleted values*/
        closeAllLists();
        if (!val) { return false; }
        currentFocus = -1;
        /*create a DIV element that will contain the items (values):*/
        a = document.createElement("DIV");
        a.setAttribute("id", this.id + "autocomplete-list");
        a.setAttribute("class", "autocomplete-items");
        /*append the DIV element as a child of the autocomplete container:*/
        this.parentNode.appendChild(a);
        /*for each item in the array...*/
        for (i = 0; i < arr.length; i++) {
            /*check if the item starts with the same letters as the text field value:*/
            if (arr[i].toUpperCase().indexOf(val.toUpperCase())>=0) {
                /*create a DIV element for each matching element:*/
                b = document.createElement("DIV");
                /*make the matching letters bold:*/
                b.innerHTML = "<strong>" + arr[i].substr(0, val.length) + "</strong>";
                b.innerHTML += arr[i].substr(val.length);
                /*insert a input field that will hold the current array item's value:*/
                b.innerHTML += "<input type='hidden' value=\"" + arr[i] + "\">";
                /*execute a function when someone clicks on the item value (DIV element):*/
                b.addEventListener("click", function (e) {
                    /*insert the value for the autocomplete text field:*/
                    inp.value = this.getElementsByTagName("input")[0].value;
                    /*close the list of autocompleted values,
                    (or any other open lists of autocompleted values:*/
                    closeAllLists();
                });
                a.appendChild(b);
            }
        }
    });
    /*execute a function presses a key on the keyboard:*/
    inp.addEventListener("keydown", function (e) {
        var x = document.getElementById(this.id + "autocomplete-list");
        if (x) x = x.getElementsByTagName("div");
        if (e.keyCode == 40) {
            /*If the arrow DOWN key is pressed,
            increase the currentFocus variable:*/
            currentFocus++;
            /*and and make the current item more visible:*/
            addActive(x);
        } else if (e.keyCode == 38) { //up
            /*If the arrow UP key is pressed,
            decrease the currentFocus variable:*/
            currentFocus--;
            /*and and make the current item more visible:*/
            addActive(x);
        } else if (e.keyCode == 13) {
            /*If the ENTER key is pressed, prevent the form from being submitted,*/
            e.preventDefault();
            if (currentFocus > -1) {
                /*and simulate a click on the "active" item:*/
                if (x) x[currentFocus].click();
            }
        }
    });
    function addActive(x) {
        /*a function to classify an item as "active":*/
        if (!x) return false;
        /*start by removing the "active" class on all items:*/
        removeActive(x);
        if (currentFocus >= x.length) currentFocus = 0;
        if (currentFocus < 0) currentFocus = (x.length - 1);
        /*add class "autocomplete-active":*/
        x[currentFocus].classList.add("autocomplete-active");
    }
    function removeActive(x) {
        /*a function to remove the "active" class from all autocomplete items:*/
        for (var i = 0; i < x.length; i++) {
            x[i].classList.remove("autocomplete-active");
        }
    }
    function closeAllLists(elmnt) {
        /*close all autocomplete lists in the document,
        except the one passed as an argument:*/
        var x = document.getElementsByClassName("autocomplete-items");
        for (var i = 0; i < x.length; i++) {
            if (elmnt != x[i] && elmnt != inp) {
                x[i].parentNode.removeChild(x[i]);
            }
        }
    }
    /*execute a function when someone clicks in the document:*/
    document.addEventListener("click", function (e) {
        closeAllLists(e.target);
    });
}


function _arrayBufferToBase64(buffer) {
    var binary = '';
    var bytes = new Uint8Array(buffer);
    var len = bytes.byteLength;
    for (var i = 0; i < len; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    return window.btoa(binary);
}



var DATA_LICHSU_MANA = [];

function loadLichSuMana(call_back) {
    DATA_LICHSU_MANA = [];
    $.ajax({
        type: "GET",
        dataType: "json",
        url: '/QuanLyMana/LoadLichSu',
        success: function (data) {
            if (data.status == 1) {
                DATA_LICHSU_MANA = data.obj;
                call_back();
            }
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR);
        }
    });
}

function readUploadedFiles(files) {
    return new Promise((resolve, reject) => {
        let result = [];

        const readFile = (file) => {
            return new Promise((resolve, reject) => {
                let reader = new FileReader();
                reader.onload = function () {
                    let content = btoa(reader.result);
                    resolve({
                        fileName: file.name,
                        content: content
                    });
                };
                reader.onerror = reject;
                reader.readAsBinaryString(file);
            });
        };

        const readFiles = async () => {
            for (let i = 0; i < files.length; i++) {
                let file = files[i];
                let fileResult = await readFile(file);
                result.push(fileResult);
            }
            resolve(result);
        };

        readFiles();
    });
}



function activeA(ctrlId, isActive) {
    if (isActive == 1) {
        $("#" + ctrlId).addClass("text-primary").removeClass("text-muted");
    }
    else {
        $("#" + ctrlId).removeClass("text-primary").addClass("text-muted");
    }
}

function showCtrl(ctrlId, isShow) {
    if (isShow == 1) {
        $("#" + ctrlId).show();
    }
    else {
        $("#" + ctrlId).hide();
    }
}

function MoNhomHoTro() {
        
    bodyHtml = `
        <p>
        1. <b>Nhóm Zalo:</b> <a href='https://zalo.me/g/pizzti048'  target='_blank'>https://zalo.me/g/pizzti048</a><br/>
            - Hỗ trợ sử dụng phần mềm Smart Pro và Nibot trên Zalo.</p>
        <p>2. <b>Điện thoại:</b> :<a href='tel:1900636507' >1900.63.65.07</a><br/>
            - Phòng kỹ thuật Hướng dẫn sử dụng Nibot + Smart Pro.
        </p>
            `
    createModal("mHoTro", "Hỗ trợ sử dụng NIBOT + SMART PRO", bodyHtml, '')
    showModal("mHoTro");
}



function openModalNibotMailBox(type = 1) {
    let cta = "";
    if (type == "2") {
        cta = `
        <div style="background-color: #fff3cd; border: 1px solid #ffeeba; color: #856404; padding: 15px; margin-bottom: 20px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <div style="display: flex; align-items: center;">
            <span style="font-size: 24px; margin-right: 10px;">⚠️</span>
            <div>
                <strong style="font-size: 1.1em;">Bạn cần đăng ký DOLAGO hoặc DOLAGO-ONE để sử dụng được tính năng này!!!</strong>
            </div>
        </div>
    </div>
       `
    }
    // Tạo popup container nếu chưa tồn tại
    if (!document.getElementById('dolago-popup')) {
        const popupHTML = `
            <div id="dolago-popup" style="display: none; font-size:0.95rem; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(0, 0, 0, 0.7); backdrop-filter: blur(5px); z-index: 9999; display: flex; justify-content: center; align-items: center;">
                <div style="position: relative; background-color: #fff; padding: 15px; width: 80%; max-width: 800px; border-radius: 10px; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2); animation: dolagoPopupFadeIn 0.3s ease;">
                    <span class="dolago-popup-close" style="position: absolute; right: 15px; top: 10px; font-size: 24px; cursor: pointer; color: #666; width: 32px; height: 32px; background: rgba(0,0,0,0.1); border-radius: 50%; display: flex; align-items: center; justify-content: center; transition: all 0.2s;">&times;</span>
                     <h1 style="color: #007acc; text-align: center; font-size: 1.3em; margin-bottom: 10px;">🔥 DOLAGO - Tải Hóa Đơn PDF Gốc! </h1>
                        ${cta}
                        <p style="margin: 8px 0;"><span style="color: #d63384; font-weight: bold;">🔥 DOLAGO</span> là dịch vụ mở rộng có tính phí của <strong>Nibot</strong>, giúp <strong>tải hóa đơn XML & PDF gốc</strong> từ người bán một cách <strong>nhanh chóng, tiện lợi</strong>! </p>
                        <div style="margin: 6px 0; padding-left: 15px; position: relative; font-size: 0.9em;">🧾 Tải được PDF bản gốc của <strong>97% nhà cung cấp</strong> hóa đơn điện tử</div>
                        <div style="margin: 6px 0; padding-left: 15px; position: relative; font-size: 0.9em;">⚡Tốc độ cực nhanh: <strong>100 hóa đơn/phút</strong> </div>
                        <div style="margin: 6px 0; padding-left: 15px; position: relative; font-size: 0.9em;">🖨 Tải <strong>từng tờ</strong> hoặc <strong>hàng loạt</strong>, <strong>kết xuất in ấn hàng loạt</strong> dễ dàng</div>
                        <p style="margin: 8px 0;"><span style="color: #0e7434; font-weight: bold;">🎥 Video DEMO: </span> <a style="font-weight:bold" href='https://www.youtube.com/watch?v=d_pETicbqec' target='_blank'> https://www.youtube.com/watch?v=d_pETicbqec </a> </p>

                        <p style="margin: 8px 0;">📦<span style="color: #d63384; font-weight: bold;">DOLAGO</span> có 2 gói là <span style="color: #d63384; font-weight: bold;">Dolago-All (gọi tắt là Dolago)</span> và <span style="color: #d63384; font-weight: bold;">Dolago-One</span>.</p>
                        <table style="width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 0.85em;">
                          <tr>
                            <th style="border: 1px solid #ddd; padding: 4px; text-align: center; background-color: #343a40; color: #fff;">Tính năng</th>
                            <th style="border: 1px solid #ddd; padding: 4px; text-align: center; background-color: #343a40; color: #fff;"><span style="color: #28a745; font-weight: bold;">Dolago</span></th>
                            <th style="border: 1px solid #ddd; padding: 4px; text-align: center; background-color: #343a40; color: #fff;"><span style="color: #9acd32; font-weight: bold;">dolago-One</span></th>
                          </tr>
                          <tr>
                            <td style="border: 1px solid #ddd; padding: 4px; text-align: center; font-weight: bold; background-color: #f8f9fa;">Tải từng tờ</td>
                            <td style="border: 1px solid #ddd; padding: 4px; text-align: center; color: #4caf50; font-size: 1.1em;">✔️</td>
                            <td style="border: 1px solid #ddd; padding: 4px; text-align: center; color: #4caf50; font-size: 1.1em;">✔️</td>
                          </tr>
                          <tr>
                            <td style="border: 1px solid #ddd; padding: 4px; text-align: center; font-weight: bold; background-color: #f8f9fa;">Tải hàng loạt</td>
                            <td style="border: 1px solid #ddd; padding: 4px; text-align: center; color: #4caf50; font-size: 1.1em;">✔️</td>
                            <td style="border: 1px solid #ddd; padding: 4px; text-align: center; color: #f44336; font-size: 1.1em;">❌</td>
                          </tr>
                          <tr>
                            <td style="border: 1px solid #ddd; padding: 4px; text-align: center; font-weight: bold; background-color: #f8f9fa;">In hàng loạt</td>
                            <td style="border: 1px solid #ddd; padding: 4px; text-align: center; color: #4caf50; font-size: 1.1em;">✔️</td>
                            <td style="border: 1px solid #ddd; padding: 4px; text-align: center; color: #4caf50; font-size: 1.1em;">✔️</td>
                          </tr>
                          <tr>
                            <td style="border: 1px solid #ddd; padding: 4px; text-align: center; font-weight: bold; background-color: #f8f9fa;">Nhu cầu sử dụng</td>
                            <td style="border: 1px solid #ddd; padding: 4px; text-align: center;">Tải nhiều, in nhanh</td>
                            <td style="border: 1px solid #ddd; padding: 4px; text-align: center;">Chỉ tải những tờ cần</td>
                          </tr>
                          <tr>
                            <td style="border: 1px solid #ddd; padding: 4px; text-align: center; font-weight: bold; background-color: #f8f9fa;">Tính phí</td>
                            <td style="border: 1px solid #ddd; padding: 4px; text-align: center;">Trả phí theo MST/năm</td>
                            <td style="border: 1px solid #ddd; padding: 4px; text-align: center;">Trả phí theo số tờ tải bằng Mana</td>
                          </tr>
                          <tr>
                            <td style="border: 1px solid #ddd; padding: 4px; text-align: center; font-weight: bold; background-color: #f8f9fa;">MST sử dụng</td>
                            <td style="border: 1px solid #ddd; padding: 4px; text-align: center;">Giới hạn</td>
                            <td style="border: 1px solid #ddd; padding: 4px; text-align: center;">Không giới hạn</td>
                          </tr>
                        </table>

                        <p style="margin-top: 20px; font-weight: bold; color: #0d6efd;">
                          📞 Liên hệ tư vấn và đăng ký: VƯƠNG HUỲNH LONG - 0988.988.814 (ZALO)
                        </p>
                </div>
            </div>
            <style>
                @keyframes dolagoPopupFadeIn {
                    from { opacity: 0; transform: translateY(-20px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                .dolago-popup-close:hover {
                    background: rgba(0,0,0,0.2) !important;
                    transform: rotate(90deg);
                }
            </style>
        `;
        
        document.body.insertAdjacentHTML('beforeend', popupHTML);
        
        // Thêm sự kiện đóng popup
        document.querySelector('.dolago-popup-close').addEventListener('click', function() {
            document.getElementById('dolago-popup').style.display = 'none';
        });
        
        // Đóng popup khi click ra ngoài
        document.getElementById('dolago-popup').addEventListener('click', function(e) {
            if (e.target === this) {
                this.style.display = 'none';
            }
        });
    }
    
    // Hiển thị popup
    document.getElementById('dolago-popup').style.display = 'flex';
}

var HTML_NIBOT_MAILBOX = `
<div class='text-dark'>
    <b id='CanDangKy'></span></b>
    <br/>
    <div style='margin-top:5px; line-height:2.0rem'>
        1. Tải hóa đơn PDF gốc của người bán về và lưu trữ trên Nibot.<br/>
        2. Dễ dàng tìm kiếm hóa đơn đã có/chưa có PDF gốc.</br>
        3. Tải về máy và In tất cả hóa đơn gốc chỉ với 1 cú click chuột.<br/>
        4. Hóa đơn gốc tải về được lưu trữ 10 năm.<br/>
        <b style='color: #040988;font-size:14pt'> Link Youtube Video Demo: <a class='text-danger' href='https://www.youtube.com/watch?v=d_pETicbqec' target='_blank'>https://www.youtube.com/watch?v=d_pETicbqec</a></b>
    </div>
    <hr/>
    <b>NIBOT DOLAGO là một dịch vụ mở rộng của Nibot và được tính Phí riêng.<b/> Hiện tại, có 2 gói như sau: <br/>
    Liên hệ tư vấn chức năng, phí dịch vụ và đăng ký sử dụng: <b><a href='tel:0988988814' style='color:blue'>VƯƠNG HUỲNH LONG - 0988.988.814</a></b>
    <table style='width:100%;margin-top:10px'>
        <tr>
            <td style='border-right: 1px solid #ccc;'>
                <b class='fs-14px' style='color:#d50584'>Gói dành cho Kế toán Doanh nghiệp</b><br/>
                &nbsp;&nbsp;&nbsp; + Tải 100% hóa đơn từ Email của doanh nghiệp.<br/>
                &nbsp;&nbsp;&nbsp; + Tải 90-100% hóa đơn gốc từ thuật toán tải của Nibot.<br/>
                &nbsp;&nbsp;&nbsp; + Phí: <b style='color:blue'>dao động từ 500.000 VND trở lên/ 1 MST / 1 Năm.</b>
            </td>
            <td style='padding-left:20px'>
                <b class='fs-14px' style='color:#6e009f'>Gói dành cho Kế toán Dịch vụ</b><br/>
                &nbsp;&nbsp;&nbsp; <del class='text-muted'>+ Tải 100% hóa đơn từ Email của doanh nghiệp.</del><br/>
                &nbsp;&nbsp;&nbsp; + Tải 90-100% hóa đơn gốc từ thuật toán của Nibot.<br/>
                &nbsp;&nbsp;&nbsp; + Phí: <b style='color:blue'>dao động từ 500.000 VND trở lên / nhiều hoặc không giới hạn MST / 1 Năm.
            </td>
        </tr>
    </table>
</div>
`
function openThamKhao() {
    var src = [
        { "TieuDe": "49 công ty ma - CV ngày 06/10/23","Link": "https://nangdong.online/49congtyma.png"},
        { "TieuDe": "Danh sách 62 doanh nghiệp mua bán HĐ", "Link": "https://nangdong.online/ds_62_dn_mbhd.xlsx" },
        { "TieuDe": "Danh sách 1500 doanh nghiệp (có bao gồm 524 DN) rủi ro về thuế", "Link": "https://nangdong.online/ds_1500_dn.xlsx" },
        { "TieuDe": "Danh sách 91 doanh nghiệp theo CV 3123/CV-ĐCSKT-MT của công an thị xã nghi sơn ngày 16/12/2023", "Link": "https://drive.google.com/file/d/1KI6R4aj5SiixexAodF0ogt3LFzTXrQfx/view" },
        { "TieuDe": "Danh sách 1520 doanh nghiệp mua hóa đơn của công ty Ma theo CV 1328/ĐCSKT của công an quận Tân Phú ngày 3/4/2024", "Link": "https://drive.google.com/file/d/1zITbddWpSWHQ44uIWeCRIIHLeS9ngpKX/view" },
        { "TieuDe": "Danh sách 16 doanh nghiệp bán hóa đơn cho 583 doanh nghiệp - Công An Bình Thạnh", "Link": "https://drive.google.com/file/d/10mbH-pgQQZPn9ip4OSe9IXIF8BGVBjhX/view" },
        { "TieuDe": "Danh sách 583 doanh nghiệp mua hóa đơn của công ty Ma - Công An Bình Thạnh", "Link": "https://drive.google.com/file/d/1qgc6jKd9ghWXEPEkGQGcAXebbUjDV-lj/view" },
        { "TieuDe": "Danh sách 7 doanh nghiệp bán và 21 doanh nghiệp mua hóa đơn do Phùng Thị Vân Anh điều hành - Cục thuế TP.HCM ngày 5/6/2024", "Link": "https://docs.google.com/spreadsheets/d/1wm5EQ9R4kkfuofFb_rq-H0yGC5plJOgR/edit?gid=970629747#gid=970629747" },
        { "TieuDe": "113 doanh nghiệp rủi ro bổ sung - Ng Minh Tú - Công văn 3385/TCT-TTKT (1/8/2024)", "Link": "https://drive.google.com/file/d/1z_CvFqoZSXaT8zXuzG-XTK3hqeVzYu4r/view" },
        { "TieuDe": "8+21 công ty Ma của Đinh Xuân Mười - CV 3684/CQĐT-KT Công An Thủ Đức (17/07/2024)", "Link": "https://drive.google.com/file/d/14CPnHt_wZ_9yRmien378fo-nNJx_m0Jz/view" },
        { "TieuDe": "Danh sách 12 công ty MA - CA Quận 12 - Cục thuế TP Hồ Chí Minh - Số 8237/CTTPHCM-TTKT2 (20/08/2024)", "Link": "https://drive.google.com/file/d/1TNL_0Vp4rQZQ2GjS-vjh8-4J1rIw8YhV/view" },
        { "TieuDe": "Danh sách 66 doanh nghiệp mua bán trái phép hóa đơn và trốn thuế - CV 5108/CTTB1-TTKT1, Cục thuế Thái Bình, ngày 16/09/2024", "Link": "https://docs.google.com/spreadsheets/d/1G4dJeB5YQ7fI4eEAEKr_6iSDex-t_qLq/" },
        { "TieuDe": "Danh sách 185 doanh nghiệp xuất bán trái phép hóa đơn - CV 2937/CV-ĐCSKT-MT Công an thị xã Nghi Sơn, 30-09-2024", "Link": "https://drive.google.com/file/d/1fxoN9FZeLjeYhqtgx6sl_ro876Vx-xgG/" },
        { "TieuDe": "Danh sách 31 công ty có dấu hiệu vi phạm pháp luật, Công văn 633/CV-CSKT(Đ3) của Công an Nam Định, ngày 17/10/2024", "Link": "https://docs.google.com/spreadsheets/d/1bEe1Mzf4U9n6QB0CTyTA0ALGWceg1DqQ/" },
        { "TieuDe": "Danh sách 102 doanh nghiệp liên quan đến vụ án 'Đào Minh Thọ và đồng phạm mua bán trái phép hóa đơn, chứng từ thu nộp ngân sách nhà nước; Trốn thuế', công văn số 5445/YC-ANĐT-P3 Bộ Công An", "Link": "https://drive.google.com/file/d/1GvEWpwMcigaeEDq1qx3cuhfjgTROwXK0/view" },
        
    ]
    let tbody = '';
    for (let i in src) {
        let d = src[i];
        tbody += `
            <tr>
                <td style="text-align: left;">${parseInt(i)+1}</td>
                <td style="text-align: left;">${src[i].TieuDe}</td>
                <td style="text-align: left;"><a href="${src[i].Link}" target="_blank">Link</a></td>
            </tr>
        `
    }

    let msg = `
       <h2 class="text-center" style="margin-top: 20px;">Danh Sách Công Văn, Tài Liệu Tham Khảo</h2>
        <div style="max-height: 400px; overflow-y: auto; margin-top: 20px;">
            <table class="table table-bordered table-hover table-striped">
                <thead class="thead-dark">
                    <tr>
                        <th style="text-align: left;">#</th>
                        <th style="text-align: left;">Nội dung</th>
                        <th style="text-align: left;">Link</th>
                    </tr>
                </thead>
                <tbody>
                    ${tbody}
                </tbody>
            </table>
    `
    dAlert(msg,'Tài liệu tham khảo')
}
function TraCuuRuiRo(mst = 'ALL') {
    let titleP = `
            <div class='d-flex justify-content-start' style='margin-top:-10px;'>
            <b>Kiểm tra xem có mua hóa đơn của các DN trong danh sách Rủi ro hay không?</b>
            <span>
               &nbsp;&nbsp; Tham khảo: <b><a href='javascript:void(0)' onClick='openThamKhao()' class='text-danger'><u>tài liệu tham khảo</u></a></b>
            </span>
            </div>
            
    `
    let bodyHtml = `
        <div class='text-dark'>
            ${titleP}        
            <div class = 'alert alert-primary text-center mt-1 mb-1'>
                    <div class="spinner-border " role="status">
                            <span class="visually-hidden"></span>
                    </div>
                    <br/>
                    <br/>
                    <br/>
                        ĐANG PHÂN TÍCH DỮ LIỆU, VUI LÒNG CHỜ MỘT CHÚT!!!
                </div>

        </div>
    `

    createModal("mDongBoHangLoat", "NIBOT - KIỂM TRA DN RỦI RO", bodyHtml, '')
    showModal("mDongBoHangLoat");
    var height = $("#mDongBoHangLoat").height() - 320;

    $.ajax({
        type: "GET",
        dataType: "json",
        url: '/QLHD/KiemTraRuiRo/' + mst,
        success: function (data) {
            if (data.status == 1) {
                if (data.obj.length == 0) {

                    let x = mst == 'ALL' ? 'KHÔNG CÓ DN MUA PHẢI HÓA ĐƠN CỦA CÁC DN RỦI RO.':'CÔNG TY NÀY KHÔNG CÓ MUA HÓA ĐƠN CỦA CÁC DOANH NGHIỆP RỦI RO'
                    bodyHtml = `${titleP}<br/><h3 style='line-height:3.5rem'>XIN CHÚC MỪNG BẠN!!!!<br/>${x} <h3>
                    `
                    createModal("mDongBoHangLoat", "NIBOT - KIỂM TRA DN RỦI RO", bodyHtml, '')
                    showModal("mDongBoHangLoat");

                }
                else {
                    bodyHtml = `  
                        
                    <p class='text-dark'>${titleP}Có <b>${data.obj.length}</b> hóa đơn mua vào của các doanh nghiệp rủi ro. <button class='btn btn-sm btn-primary btnExportRuiRo' style='float:right' >Export Excel</button></p>
                    <div id='dgRuiRo' class='datagrid'></div>      `
                    createModal("mDongBoHangLoat", "NIBOT - KIỂM TRA DN RỦI RO", bodyHtml, '')
                  
                    TOTAL_COLUMNS_RUIRO =
                        [{
                            column: 'NguoiMua',
                            summaryType: "count",
                            displayFormat: '{0} HĐ'
                        }];

                    var ttcolumns = ["TienChuaThue", "TienThue", "TienThanhToan"]
                    for (var idx in ttcolumns) {
                        TOTAL_COLUMNS_RUIRO.push({
                            column: ttcolumns[idx],
                            summaryType: "sum",
                            valueFormat: mFormat,
                            displayFormat: '{0}',
                        });
                    }

                    var dx = $("#dgRuiRo").dxDataGrid({
                        dataSource: data.obj,
                        height: height,
                        repaintChangesOnly: true,
                        loadPanel: {
                            enabled: false // or false | "auto"
                        },
                        showBorders: true,
                        columnAutoWidth: true,
                        headerFilter: { visible: true, width:500 },
                        scrolling: {
                            useNative: true,
                        },
                        export: {
                            enabled: false,
                            fileName: "Danh sách HĐ rủi ro"
                        },
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
                        paging: {
                            enabled: false
                        },
                        summary: {
                            totalItems: TOTAL_COLUMNS_RUIRO
                        },
                     
                        columns: [
                            { dataField: "NguoiMua", caption: "Người mua" },
                            { dataField: "NgayLap", caption: "Ngày HĐ" },
                            { dataField: "KyHieu", caption: "Ký hiệu" },
                            { dataField: "SoHd", caption: "Số HĐ" },
                            { dataField: "TienChuaThue", caption: "Tiền chưa thuế", headerCellTemplate: "Tiền<br/>C.Thuế", format: mFormat, },
                            { dataField: "TienThue", caption: "Tiền thuế", headerCellTemplate: "Tiền<br/> Thuế", format: mFormat, },
                            { dataField: "TienThanhToan", caption: "Tiền thanh toán", headerCellTemplate: "Tiền<br/>T.Toán", format: mFormat, },
                            { dataField: "NguoiBan", caption: "Người bán" },
                            { dataField: "RuiRo", caption: "Rủi ro" },

                        ]
                    }).dxDataGrid("instance");
                    $(".btnExportRuiRo").unbind().on("click", function () {
                        dx.exportToExcel();
                    })
                    showModal("mDongBoHangLoat");

                }

            }

        },
        error: function (jqXHR, textStatus, errorThrown) {
            goTohome(jqXHR.responseText);
            return;
        }

    });

}


function removeVietnameseAccent(str) {
    // Dấu tiếng Việt
    var diacriticsMap = {
        'à': 'a', 'á': 'a', 'ả': 'a', 'ã': 'a', 'ạ': 'a',
        'ă': 'a', 'ằ': 'a', 'ắ': 'a', 'ẳ': 'a', 'ẵ': 'a', 'ặ': 'a',
        'â': 'a', 'ầ': 'a', 'ấ': 'a', 'ẩ': 'a', 'ẫ': 'a', 'ậ': 'a',
        'đ': 'd',
        'è': 'e', 'é': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ẹ': 'e',
        'ê': 'e', 'ề': 'e', 'ế': 'e', 'ể': 'e', 'ễ': 'e', 'ệ': 'e',
        'ì': 'i', 'í': 'i', 'ỉ': 'i', 'ĩ': 'i', 'ị': 'i',
        'ò': 'o', 'ó': 'o', 'ỏ': 'o', 'õ': 'o', 'ọ': 'o',
        'ô': 'o', 'ồ': 'o', 'ố': 'o', 'ổ': 'o', 'ỗ': 'o', 'ộ': 'o',
        'ơ': 'o', 'ờ': 'o', 'ớ': 'o', 'ở': 'o', 'ỡ': 'o', 'ợ': 'o',
        'ù': 'u', 'ú': 'u', 'ủ': 'u', 'ũ': 'u', 'ụ': 'u',
        'ư': 'u', 'ừ': 'u', 'ứ': 'u', 'ử': 'u', 'ữ': 'u', 'ự': 'u',
        'ỳ': 'y', 'ý': 'y', 'ỷ': 'y', 'ỹ': 'y', 'ỵ': 'y',
        'À': 'A', 'Á': 'A', 'Ả': 'A', 'Ã': 'A', 'Ạ': 'A',
        'Ă': 'A', 'Ằ': 'A', 'Ắ': 'A', 'Ẳ': 'A', 'Ẵ': 'A', 'Ặ': 'A',
        'Â': 'A', 'Ầ': 'A', 'Ấ': 'A', 'Ẩ': 'A', 'Ẫ': 'A', 'Ậ': 'A',
        'Đ': 'D',
        'È': 'E', 'É': 'E', 'Ẻ': 'E', 'Ẽ': 'E', 'Ẹ': 'E',
        'Ê': 'E', 'Ề': 'E', 'Ế': 'E', 'Ể': 'E', 'Ễ': 'E', 'Ệ': 'E',
        'Ì': 'I', 'Í': 'I', 'Ỉ': 'I', 'Ĩ': 'I', 'Ị': 'I',
        'Ò': 'O', 'Ó': 'O', 'Ỏ': 'O', 'Õ': 'O', 'Ọ': 'O',
        'Ô': 'O', 'Ồ': 'O', 'Ố': 'O', 'Ổ': 'O', 'Ỗ': 'O', 'Ộ': 'O',
        'Ơ': 'O', 'Ờ': 'O', 'Ớ': 'O', 'Ở': 'O', 'Ỡ': 'O', 'Ợ': 'O',
        'Ù': 'U', 'Ú': 'U', 'Ủ': 'U', 'Ũ': 'U', 'Ụ': 'U',
        'Ư': 'U', 'Ừ': 'U', 'Ứ': 'U', 'Ử': 'U', 'Ữ': 'U', 'Ự': 'U',
        'Ỳ': 'Y', 'Ý': 'Y', 'Ỷ': 'Y', 'Ỹ': 'Y', 'Ỵ': 'Y',
    };
    return str.replace(/[^A-Za-z0-9\s]/g, function (char) {
        return diacriticsMap[char] || char;
    });
}





const b64toBlob = (b64Data, contentType = '', sliceSize = 512) => {
    console.log(b64Data)
    const byteCharacters = atob(b64Data);
    const byteArrays = [];

    for (let offset = 0; offset < byteCharacters.length; offset += sliceSize) {
        const slice = byteCharacters.slice(offset, offset + sliceSize);

        const byteNumbers = new Array(slice.length);
        for (let i = 0; i < slice.length; i++) {
            byteNumbers[i] = slice.charCodeAt(i);
        }

        const byteArray = new Uint8Array(byteNumbers);
        byteArrays.push(byteArray);
    }

    const blob = new Blob(byteArrays, { type: contentType });
    return blob;
}

