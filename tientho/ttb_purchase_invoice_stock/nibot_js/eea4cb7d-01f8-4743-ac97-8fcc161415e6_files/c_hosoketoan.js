var cboLoaiHoSo, txtKyBaoCao, txtTieuDe,dgHoSo;
function initCtrlHoSoKeToan() {
    $.ajax({
        type: "GET",
        dataType: "json",
        url: '/HoSoKeToan/Init/'+MST,
        success: function (data) {
            if (data.status == 1 || data.status == 99) {
                initHoSo(data.status);
            }
            else if (data.status == -1)
                dAlert(data.message)
            else if (data.status == -99) {
                initHuongDan();
            }
       
        },
        error: function (jqXHR, textStatus, errorThrown) {
            goTohome(jqXHR.responseText);
        }
    });
}
function initHuongDan() {
    $("#ctrlHoSo").html(`
        <form id="frmHoSoKeToan" autocompleted='' >
            <div class="row gy-2 mt-2  " style='line-height:1.5rem'>
                <div class="col-sm-12 col-12 ">
                    <b>Chức năng này cho phép lưu trữ các báo cáo tài chính, sổ kế toán và các tài liệu liên quan khác được tải lên từ phần mềm kế toán Smart Pro phiên bản Tháng 4 năm 2023 cùng với Nibot Token. 
                    </b>
                    <hr/>
                    Để sử dụng chức năng này, bạn cần thực hiện hai bước:<br/>
                    <b>Bước 1.</b> bạn phải khai báo Nibot Token trên phần mềm kế toán Smart Pro.<br/>
                    <b>Bước 2.</b> Khi xuất báo cáo, bạn sẽ click vào nút Gửi hồ sơ lên Nibot.
                    <hr/>

                    <p style='color:red;font-weight:bold'>Ngoài ra, giao diện chức năng được thiết kế để phù hợp cho việc xem và tải các báo cáo trên điện thoại di động.</p>
                </div>
               
            </div>
       
        </form>
    `);

    $("#frmHoSoKeToan").height($(window).height() - 300);

}
function initHoSo(initStatus) {
    let noData = '';
    if (initStatus == 1) {
        noData = 'Chưa có dữ liệu về hồ sơ kế toán được gởi lên từ Smart Pro'
    }
    else {
        noData = 'Không có dữ liệu thỏa điều kiện tìm kiếm'

    }
    console.log("initHoSo")
    $("#ctrlHoSo").html(`
        <form id="frmHoSoKeToan" autocompleted='' >
            <div class="row gy-2 mt-2  ">
                <div class="col-sm-4 col-8 ">
                    <div id="cboLoaiHoSo"></div>
                </div>
                <div class="col-sm-4 col-4 ">
                    <div id="txtKyBaoCao"></div>
                </div>
                <div class="col-sm-4 col-12 ">
                    <div id="txtTieuDe"></div>
                </div>
            </div>
            <div class="row gy-2 mt-2">
                <div class="col-sm-12 mt-2 col-12 d-flex justify-content-center">
                    <button id='btnTimKiemHoSo' class='btn btn-sm btn-dim btn-outline-dark ' >Tìm kiếm</button>
                </div>
            </div>
            <div class="row mt-2">
                <div id="dgHoSo" class="datagrid">
                </div>
            </div>
        </form>
    `);

    cboLoaiHoSo = $("#cboLoaiHoSo").dxSelectBox({
        dataSource: [
            { "key": "", "value": "--Loại báo cáo--" },
            { "key": "BCTC", "value": "Báo cáo tài chính" },
            { "key": "SKT", "value": "Sổ kế toán" },
        ],
        valueExpr: "key",
        displayExpr: "value",
        value: "",
    }).dxSelectBox("instance");

    txtKyBaoCao = $("#txtKyBaoCao").dxTextBox({
        placeholder: "Kỳ báo cáo MM-yyyy | Qx-yyyy | yyyy ",
        value: new Date().getFullYear().toString(),
    }).dxTextBox("instance")

    txtTieuDe = $("#txtTieuDe").dxTextBox({
        placeholder: "Tiêu đề, có thể nhập tiếng việt không dấu"
    }).dxTextBox("instance")

    $("#btnTimKiemHoSo").on("click", function (e) {
        e.preventDefault();
        SearchHoSo();
    })
    setTimeout(function () {
        $('input[type="text"]').attr('autocomplete', 'off');
    }, 200);

    dgHoSo = $("#dgHoSo").dxDataGrid({
        dataSource: [],
        columns: [
            {
                dataField: "Id",
                caption: "Hồ sơ",
                cellTemplate(c, e) {
                    if (e.rowType == 'data') {
                        let r = e.data;
                        let html = `
                                <div class='row ' style=';'>
                                    <div class='col-10 col-sm-9'>
                                        <span style='font-weight:bold;'>${r.KyBaoCao} - ${r.LoaiHoSo} - ${r.TieuDe}</span><br/>
                                        <span style='font-size:8pt'>${toJP(new Date(r.NgayCapNhatCuoi))} - ${r.NguoiCapNhat} </span>
                                    </div>
                                    <div class='col-2 col-sm-3 d-flex justify-content-end fs-16px '>
                                        <a  href='javascript:void(0)' onClick='TaiHoSo("${r.Id}")' class='text-primary '><em class="icon ni ni-download"></em></a><br/>
&nbsp;&nbsp;&nbsp;
      <a  href='javascript:void(0)' onClick='XoaHoSo("${r.Id}")' class='text-danger'><em class="icon ni ni-trash"></em></a>&nbsp;
                                    </div>
                                </div>
                            `
                        $(html).appendTo(c)

                    }

                }

            }
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
        wordWrapEnabled: true,
        allowColumnReordering: true,
        showColumnHeaders: false,
        noDataText: noData,
        rowAlternationEnabled: true,
        showBorders: true,

        columnAutoWidth: true,

        paging: {
            enabled: false
        },


    }).dxDataGrid("instance");
    $("#frmHoSoKeToan").height($(window).height() - 200);
    setTimeout(function () {
        SearchHoSo();
        dgHoSo.option("height", $("#frmHoSoKeToan").height() - 150)

    }, 200)
}
function prepareHoSo() {
    return {
        "MaSoThue": MST,
        "LoaiHoSo": cboLoaiHoSo.option("value") ?? "",
        "KyBaoCao": txtKyBaoCao.option("value") ?? "",
        "TieuDe": txtTieuDe.option("value")??"",
    }
}
function SearchHoSo() {
    var searchObj = prepareHoSo();
    $.ajax({
        type: "POST",
        dataType: "json",
        url: '/HoSoKeToan/Search',
        data: searchObj,
        success: function (data) {
            if (data.status == 1) {
                dgHoSo.option("dataSource", data.obj);
                dgHoSo.refresh();
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


function TaiHoSo(IdHoSo) {
    var a = document.createElement('a');
    a.href = "/HoSoKeToan/TaiFile/" + IdHoSo + "/" + MST;
    a.target = '_blank';
    document.body.append(a);
    a.click();
    a.remove();
}

function XoaHoSo(IdHoSo) {
    var result = DevExpress.ui.dialog.confirm("<b>Bạn đã chắc cú chưa?</b>", "Xóa bỏ Hồ sơ");
    result.done(function (dialogResult) {
        if (dialogResult) {

            $.ajax({
                type: "POST",
                dataType: "json",
                url: '/HoSoKeToan/XoaHoSo',
                data: {
                    IdHoSo: IdHoSo,
                    MaSoThue: MST,
                },
                success: function (data) {
                    if (data.status == 1) {
                        dAlert("Xóa thành công", "Thông báo")
                        SearchHoSo();
                    }
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    console.log(jqXHR);
                    loading(false)
                    goTohome(jqXHR.responseText);
                }
            });
        }
    });

}