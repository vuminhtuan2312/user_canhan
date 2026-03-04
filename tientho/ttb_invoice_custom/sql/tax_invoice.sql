-- SQL
Sau ghi chạy ghép xong

F00: check không có sản phẩm misa
0. F01 Chạy SQL insert bảng ttb_inout_product_mapper
0. F02 Chạy bộ SQL check
1. F03 Chạy SQL phân bổ nốt sản phẩm cho các dòng có dùng nhưng không dùng hết
2. F04 Chạy SQL xử lý các dòng không dùng
3. F05: Tính lại thành tiền, đơn giá, ...
4. F06: SQL ktra thành tiền
4. F02 Chạy lại bộ sql check



-- version 2:
update product_sale_item set misa_product_id = data.misa_product_id
from (
    select psi.id, min(psi_ms.id) misa_product_id
    FROM
        product_sale_item psi
        LEFT JOIN product_sale_item psi_n ON psi_n.batch_name = 'dau_ra_code_name_cotn'
        AND LOWER(psi_n.name) = LOWER(psi.name)
        LEFT JOIN product_sale_item psi_ms ON psi_ms.batch_name = 'dau_ra_code_name_misa'
        AND psi_ms.code = psi_n.code
    WHERE
        psi.batch_name = 'dau_ra'
        and psi_ms.id is not null
    GROUP BY
        psi.id
        -- psi_ms.id
) data
where data.id = product_sale_item.id


-- ---------------------------------------
-- F01 Insert map đầu vào với sản phẩm đầu ra
-- ---------------------------------------
delete from ttb_inout_product_mapper;
INSERT INTO ttb_inout_product_mapper (
    in_line_id,
    out_product_id,
    quantity,
    nimbox_invoice_id,
    ttb_vendor_invoice_date,
    active
)
select 
    ioim.in_line_id,
    psi.misa_product_id,
    sum(ioim.quantity) quantity,
    ni.id,
    ni.ttb_vendor_invoice_date,
    True
from 
    ttb_inout_invoice_mapper ioim
    join ttb_nimbox_invoice_line nil on nil.id = ioim.in_line_id
    join ttb_nimbox_invoice ni on nil.nimbox_invoice_id = ni.id
    join tax_output_invoice_line oil on oil.id = ioim.out_line_id
    join product_sale_item psi on psi.id = oil.product_id
group by ni.id, ioim.in_line_id, psi.misa_product_id
-- ---------------------------------------
-- F04 Insert map đầu vào với sản phẩm đầu ra - lượng hoá đơn chưa sử dụng
-- ---------------------------------------
INSERT INTO ttb_inout_product_mapper (
    in_line_id,
    out_product_id,
    quantity,
    nimbox_invoice_id,
    ttb_vendor_invoice_date,
    thanhtien_exclude_tax,
    active
)
select 
    nil.id,
    nil.buy_product_id,
    nil.soluong_goc,
    ni.id,
    ni.ttb_vendor_invoice_date,
    nil.thanhtien_exclude_tax,
    False
from 
    ttb_nimbox_invoice_line nil 
    join ttb_nimbox_invoice ni on nil.nimbox_invoice_id = ni.id

where
    ni.ttb_vendor_invoice_date between '2024-01-01' and '2024-12-31'
    and ni.use_state = True
    and nil.soluong_goc > 0
    and nil.soluong_used = 0
    and (ni.manual_import = True or ni.trang_thai_hd in ('1', '2'))


-- SQL sửa lỗi dùng cả hoá đơn huỷ
select * 
from ttb_inout_product_mapper ipm
join ttb_nimbox_inovice_line nil on nil.id = ipm.in_line_id
join ttb_nimbox_invoice ni on ni.id = nil.nimbox_invoice_id

where ipm.active = False and ni.manual_import = False and ni.trang_thai_hd not in ('1', '2')


-- ---------------------------------------
-- Cập nhật trường compute thành tiền trước thuế, tiền thuế
-- ---------------------------------------
update ttb_nimbox_invoice
set
    total_thanhtien = data.total_thanhtien,
    total_diff = data.total_diff,
    line_exclude_tax = data.line_exclude_tax,
    is_line_exclude_tax = data.is_line_exclude_tax
from (
    select 
        id,
        sum_thanhtien as total_thanhtien,
        tien_c_thue - sum_thanhtien as total_diff,
        case when abs(tien_c_thue - sum_thanhtien) < abs(0.000003 * tien_c_thue) then True else False end as is_line_exclude_tax,
        case 
            when abs(-tien_c_thue + sum_thanhtien) < abs(0.000003 * tien_c_thue) then '1'
            when abs(-tien_c_thue + sum_thanhtien - sum_so_tien_chiet_khau) < abs(0.000003 * tien_c_thue) then '2'
            when abs(-tien_c_thue + sum_thanhtien - sum_ti_le_chiet_khau) < abs(0.000003 * tien_c_thue) then '3'
    
            when abs(-tien_c_thue + sum_thanhtien - sum_chiet_khau_tong_don) < abs(0.000003 * tien_c_thue) then '4'
            when abs(-tien_c_thue + sum_thanhtien - sum_chiet_khau_tong_don - sum_so_tien_chiet_khau) < abs(0.000003 * tien_c_thue) then '5'
            when abs(-tien_c_thue + sum_thanhtien - sum_chiet_khau_tong_don - sum_ti_le_chiet_khau) < abs(0.000003 * tien_c_thue) then '6'
            
            when abs(-tien_c_thue + sum_thanhtien - tien_thue) < abs(0.000003 * tien_c_thue) then '7'
            when abs(-tien_c_thue + sum_thanhtien - sum_so_tien_chiet_khau - tien_thue) < abs(0.000003 * tien_c_thue) then '8'
            when abs(-tien_c_thue + sum_thanhtien - sum_ti_le_chiet_khau - tien_thue) < abs(0.000003 * tien_c_thue) then '9'
    
            when abs(-tien_c_thue + sum_thanhtien - sum_chiet_khau_tong_don - tien_thue) < abs(0.000003 * tien_c_thue) then '10'
            when abs(-tien_c_thue + sum_thanhtien - sum_chiet_khau_tong_don - sum_so_tien_chiet_khau - tien_thue) < abs(0.000003 * tien_c_thue) then '11'
            when abs(-tien_c_thue + sum_thanhtien - sum_chiet_khau_tong_don - sum_ti_le_chiet_khau - tien_thue) < abs(0.000003 * tien_c_thue) then '12'
            else '0'
        end line_exclude_tax
    from (
        select 
            ni.id,
            coalesce(ni.tien_thue, 0) tien_thue,
            coalesce(ni.tien_c_thue, 0) tien_c_thue,
            sum(case when nil.tchat in ('2', '3', '4') then 0 else coalesce(nil.thanhtien, 0) end)                                           as sum_thanhtien,
            sum(case when nil.tchat in ('2', '3', '4') then 0 else coalesce(nil.so_tien_chiet_khau, 0) end)                                  as sum_so_tien_chiet_khau,
            sum(case when nil.tchat in ('2', '3', '4') then 0 else coalesce(nil.ti_le_chiet_khau, 0) * coalesce(nil.thanhtien, 0) * 0.01 end) as sum_ti_le_chiet_khau,
            sum(case when nil.tchat not in ('2', '3', '4') then 0 else coalesce(nil.thanhtien, 0) end)                                      as sum_chiet_khau_tong_don
        from ttb_nimbox_invoice_line nil
        join ttb_nimbox_invoice ni on ni.id = nil.nimbox_invoice_id
--         where ni.id = 33499
        group by ni.id, ni.tien_c_thue) xxx
--     where id = 33499
) data
where data.id = ttb_nimbox_invoice.id

-- Cập nhật tchat từ 2 về 1 cho các dòng cho là bị nhầm
update ttb_nimbox_invoice_line set tchat = '1' where 
id in (1151879,
1151877,
1150949,
1152947,
1152946,
1152945,
1152943)


-- ---------------------------------------
-- SQL liệt kê các dòng chiết khấu cả đơn nhưng không ghi số tiền
-- (Trường hợp xuất hoá đơn từ hộ được giảm thuế 1% của 20% - Toàn bộ các trường hợp này đều lấy tổng thành tiền - tien_c_thue ra tiền chiết khấu)
-- ---------------------------------------
select nil.thanhtien, nil.* from ttb_nimbox_invoice_line nil
join ttb_nimbox_invoice ni on ni.id = nil.nimbox_invoice_id
where 1=1
-- and tchat in ('3')
and ni.ttb_vendor_invoice_date between '2024-01-01' and '2024-12-31'
and nil.tensp ilike '%Nghị quyết%' and nil.tensp ilike '%giảm%'



-- ---------------------------------------
-- SQL cập nhật nghị quyết
-- ---------------------------------------
update ttb_nimbox_invoice_line

set thanhtien = -data.total_diff
from (

select nil.id, ni.total_diff, nimbox_invoice_id, thanhtien, tchat
from 
    ttb_nimbox_invoice_line nil 
    join ttb_nimbox_invoice ni on ni.id = nil.nimbox_invoice_id
where tensp ilike '%giảm%nghị quyết%' and ni.ttb_vendor_invoice_date between '2024-01-01' and '2024-12-31' and ni.trang_thai_hd not in ('4', '6')
) data where data.id = ttb_nimbox_invoice_line.id


-- Tính phân bổ chiết khấu
-- https://trialtax.erp.tientho.vn/odoo/crons/347

-- ---------------------------------------
-- SQL cập nhật thành tiền trước thuế
-- ---------------------------------------
update ttb_nimbox_invoice_line set thanhtien_exclude_tax = data.thanhtien_exclude_tax
from (
    select 
    --     ni.id,
        nil.id,
        case 
            when ni.line_exclude_tax = '1' then nil.thanhtien
            when ni.line_exclude_tax = '2' then nil.thanhtien - nil.so_tien_chiet_khau
            when ni.line_exclude_tax = '4' then nil.thanhtien - nil.phanbo_chietkhau
            when ni.line_exclude_tax = '7' then round(nil.thanhtien / case when nil.thuesuat='5%' then 1.05 when nil.thuesuat='8%' then 1.08 else 0 end)
            else '-1.0'
        end thanhtien_exclude_tax
    --     ,* 
        
    from 
    ttb_nimbox_invoice_line nil
    join ttb_nimbox_invoice ni on ni.id = nil.nimbox_invoice_id
    where ni.ttb_vendor_invoice_date between '2024-01-01' and '2024-12-31'
    and ni.line_exclude_tax in ('1', '2', '4', '7')
) data
where data.id = ttb_nimbox_invoice_line.id


-- SQL loại các đầu vào chi phí:
update ttb_nimbox_invoice set use_state = False 
where
-- ttb_vendor_vat not in ('0100109787', '0104918404-024', '0313650711-001', '3600224423-053', '0102806631-001', '0200662314-008', '0200662314-007', '0102300429-002', '0102764928-001', '0304898593-001', '0101394777-015', '0101603420-001', '0101394777-009', '0302249586-008', '0100104387-006', '0300461192-001', '0303549039-001', '0318117017-001', '0303077611-001', '0309300048-011', '0302314179-004', '3700723994-025', '3700723994-017', '0300792451-004', '0104918404-002', '0100110207-001', '0100111200-001', '0101341616-002', '0107616899-001', '0104918404-020', '0310471746-351', '0300816663-007', '8038953461', '0109892340', '0106033728', '0101198853', '0106751359', '0101526991', '3600224423-013', '0102806631', '0108526687', '0106629976-001', '0107307890', '4201938996', '0311777060', '0106188175', '0108941203', '1001106674', '0110263474', '0107561047', '0110694819', '4600366807', '0103570403', '0108325123', '4601542170', '0106932757', '0105780639', '0106825441', '0102648181', '0106476952', '0107722801', '0101294317', '0104968317', '0313462725', '0107854170', '0108148636', '0315553953', '0109301830', '0101127355', '0311795831', '0107921268', '0109547016', '0101933972', '4600412757', '0105790267', '0311509329', '0314046502', '0109359397', '0110775458', '0900218030', '0101459505', '0500441475', '0314318361', '1101912597', '0106447408', '0102345451', '0304132047', '0102250111', '0100639311', '0102797401', '0102746742', '0402183184', '0104838981', '0101602138', '0102080861', '0102883146', '0108294972', '0102300429', '0106957536', '0102147139', '0301325347', '0101341616', '0110348752', '0109953610', '0108398065', '0102764928', '0315296079', '0300363808', '0102721191-001', '0100368686', '0107762787', '0106129645', '0108458726', '0109817826', '0315014341', '0104971510', '0103762024', '2901816735', '0304475742', '0200443506', '0107467527', '0310471746', '0106797201', '0110764311', '0104585593', '0104162894', '0104923411', '0107691617', '0316833248', '0102378552', '0305225110', '0101159195', '0101394777', '0101767891', '0200653380', '0109731939', '0102923543', '0102451315', '0101488457', '0103389564', '0107864852', '0105813179', '0109403825', '0105658808', '0102688603', '0102292496', '0101398362', '0107631488-001', '0101564468', '0102596871', '0101255406', '0313738733', '0101603420', '0100100248', '0109180431', '0101496401', '0309132354', '1101171437-001', '0108480760', '0101906993', '0104221444', '0101507251', '0104274157', '0108490310', '0106804314', '0104373623', '0312079164', '0107402262', '2901870700', '2900609278', '2400299807', '0109926399', '0109252189', '0104113329', '0318699823', '0300100037-009', '0109789495', '0700869564', '3703087169', '0314339876', '0312628590', '0312628590-011', '0312628590-002', '0318055681', '0104075673', '0110624233', '2802545869', '0310178988', '0302062877', '0302062877', '0305596612', '2300275432', '3701308172', '0101042870', '0315179350', '3702431764', '0314735728', '2400800420', '3702955542', '0314267558', '0100235453', '0311827272', '0101389216', '0105418228', '0107907866', '2900802715', '2400984143', '0109993204', '0109721673', '0315595985', '0317019183', '0108193903', '0106665452', '0315693069', '0107763438', '0110723548', '0107332079', '0109909322', '0110334301', '0317952223', '2801944349', '0107555773', '2400815603', '0108641048', '0101782441', '2800403097', '0101519715', '2802855941', '3702545183', '2400871252', '2901901236', '0110883647', '3703016104', '0202157532', '0107481306', '2801693913', '2901238107', '0313799020', '0318495890', '0316045166', '0107001119', '0107660023', '0108962676', '0312299018', '0107947160', '0109881123', '0108594870', '4600236445', '0108557886', '4601588785', '4601513797', '2900531173', '4601499912', '0108400349', '4600285393', '0308620870', '0106703700', '0317716794', '8043261113', '0108032222', '0110063669', '1000988536', '0109057815', '2902147188', '0108230016', '1001210058', '3702777811', '0306252156', '0101233265', '0108688053', '0106295850', '0107660009', '4601572760', '4601447135', '0310880724', '3700629945', '0310439453-001', '0109864738', '2400811824', '0312185878', '2601048560', '0102574758', '2900874491', '0300461192', '0309885372', '0316102015', '3702139304', '0306060655', '0311969654', '0102305032', '0309455845', '3701785633', '3701785633', '0314611200', '0200412177', '0313871478', '3702003550', '0305341389', '3702037630', '2802207531', '0305497971', '0102726224', '0306411423', '3702397859', '3701840161', '0100110101', '3700896309', '0317743519', '0100109547', '0110646808', '3703221368', '0107501249', '0309200798', '3702591165', '0302963624', '0315999138', '0313020893', '0200606951', '3603461824', '0314501423', '0102799649', '0201261770', '0106740237', '0313786279', '0202234963', '0106121861', '0110521502', '0106603512', '0311229995', '4601553327', '4601622242', '0311187079-004', '0318060307', '0303549039', '3703146174', '2301267096', '0106531297', '0318117017', '4601596666', '0106880202', '0106720576', '0109166571', '0313752706', '0102354569', '4601605046', '0102305089', '0317217467', '0106910009', '2800975979', '0106036969', '0401534489', '0110350078', '0311191639', '0109161245', '0107437561', '0302845645', '2901801383', '0109237448', '0318218978', '0110152823', '0317862121', '0110653467', '0311008273', '0101209181', '0303077611', '0303192244', '0315336067', '0317910696', '0304303239', '0303077770', '0108715148', '0312606780', '0106773401', '0315074291', '0106864835', '0108370077', '2803068979', '1000710322', '0601177989', '0308607615', '4601612685', '2802143380', '0110103216', '0601254344', '0108587513', '0101389488', '0303609457', '0105885046', '0101106556', '0201703235', '0109917651', '2902085171', '0315152542', '1001204576', '0105767229', '0101267521', '0110183035', '0110489231', '0316467305', '1000214557', '4600937680', '4601033310', '0318409041', '0102376812', '2400336632', '0316940306', '2400300467', '0309300048', '0302314179', '0316975651', '0106087441', '2400932988', '2400844001', '0104120076', '2400958217', '2400741662', '3701712681', '0101909867', '1000349716', '2901384002', '0313120376', '0201797258', '2400889267', '3701625340', '3701890740', '0317001612', '0110161289', '0200661021', '0313687870', '0201401989', '3701859814', '0110809273', '3701697225', '0314510971', '0312973759', '3700798284', '0109468702', '0316008446', '0110794605', '1001247474', '0106752828', '0313523791', '0318091739', '0105978501', '0110120959', '0202045733', '0110767062', '0202111506', '2902131727', '0110266676', '0200683586', '0106484992', '0200671615', '4601330634', '1001018499', '0304136926', '0316342722', '1000340992', '2901265566', '2800491470', '0317136289', '4601593400', '0109844876', '0110264894', '4601585819', '2400809053', '1001073161', '0100902844', '0305351669', '0101410394', '3702189552', '2800664758', '0110361714', '0110460313', '0108881480', '0101507727', '0110224080', '4601616827', '0110625558', '3702512660', '2901867708', '0201281375', '0110564640', '0201968496', '0107500661', '0109078999', '2400764726', '2802480065', '2901618268', '0101148108', '0108865538', '2900599615', '0109030316', '1001245607', '0107367025', '0315365371', '0309535628', '0110535625', '0110099217', '0106049407', '0105921505', '4601604532', '0101590690', '0110656524', '0106185255', '0110404100', '0109000336', '0105622872', '0103002143', '0309058132', '0110439128', '2801715483', '0109958633', '0102312294', '0109048183', '0107285245', '0110447390', '0106351752', '0105906296', '0109019270', '2801944109', '0101884041', '4601556624', '0105878828', '0110645360', '2901144836', '0107500005', '0107537710', '0313884646', '0315491471', '3701676049', '0202234089', '2400589746', '2801548169', '0316752623', '0107788552', '0313934022', '2800719809', '0108581550', '0108686144', '0317178803', '0316774514', '3703182052', '4601515096', '4601546182', '2400987560', '0316613299', '2801870739', '2803116252', '0106477547', '2803017766', '0317334322', '0101449867', '0109802107', '0315304731', '0302077094', '0110431619', '0101883129', '0302400727', '0106610291', '0106749166', '0108285086', '0102035146', '0317093250', '0107859757', '0108381512', '0105533083', '0106193746', '4601561134', '0313544907', '3703047399', '2400276038', '0108063904', '0108323091', '0315247674', '0303728623', '0108769714', '1001284740', '0312711665', '1101886675', '0110093582', '0108004433', '0302713783', '3702942751', '0300792451', '2400101609', '0101269078', '3702660450', '0200592635', '0301472278', '0200554132', '0106222299', '0104577017', '4601604109', '0303230683', '0312625631', '4601596514', '0101209583-001', '8806924925-001', '0101243496-002', '8742891245-001', '8352863852-001', '8848939761-001', '8662839024-001', '8124481727', '2200795004', '8303705067', '8437095624-001', '8734670098-001', '8098190486-001', '8606680044-001', '8340389765-001', '8141811397-001', '0108729782', '0109552062', '8809016960-001', '0109779200', '0106517951', '8024541965', '8048733017', '8008991773-001', '0106486566', '0110798705-001', '2400903810', '0100110207', '0100111200', '0109601418', '0500462059', '0100111289-008', '0312474929', '8391222877')
ttb_vendor_vat not in ('0100235453', '0100364498', '0100911694', '0100947771', '0100956381', '0101106556', '0101148108', '0101161194', '0101243150', '0101389216', '0101405789-001', '0101410394', '0101497998', '0101583693', '0101597625', '0101871229', '0102196915-001', '0102305032', '0102305089', '0102312294', '0102317493', '0102362584', '0102519041', '0102598205', '0102608502', '0102721191-001', '0102721191-068', '0102744456', '0102806504', '0103002143', '0103674995', '0103682763', '0103863167', '0104093672', '0104266928', '0104274157', '0104406815', '0104437468', '0104630479-006', '0104913886', '0104918404-024', '0105041451', '0105200052', '0105330534', '0105413678', '0105486549', '0105795184', '0105813179', '0105815320', '0105921505', '0105931366', '0105987489', '0106011932-022', '0106085370', '0106125538', '0106185858', '0106254678', '0106263351', '0106382824', '0106629976-001', '0106637487', '0106651795', '0106662437', '0106701340', '0106703700', '0106713191', '0106777886', '0106819180', '0106868798', '0107012135', '0107015626', '0107016612-002', '0107027004', '0107144854', '0107274469', '0107333442', '0107396026', '0107602141', '0107609901', '0107631488-001', '0107660009', '0107707930', '0107723763', '0107762787', '0107832547', '0107846701', '0107854170', '0107874378', '0108093560', '0108202516', '0108308897', '0108323091', '0108333124', '0108392659', '0108438409', '0108485744', '0108533490', '0108549525', '0108562413', '0108594870', '0108629516', '0108676643', '0108683721', '0108686144', '0108721381', '0108729782', '0108796725', '0108828896', '0108865168', '0108941203', '0108951120', '0108951120-002', '0108969181', '0108971656', '0109019270', '0109067066', '0109081857', '0109096162', '0109106452', '0109116806', '0109200409', '0109222787', '0109222917', '0109237448', '0109318224', '0109324411', '0109353187', '0109482055', '0109537931', '0109559438', '0109607138', '0109626324', '0109673331', '0109754534', '0109789375', '0109818403', '0109825055', '0109843713', '0109878314', '0109955294', '0110014799', '0110059969', '0110069075', '0110093582', '0110095300', '0110099217', '0110117191', '0110134246', '0110152823', '0110158399', '0110167509', '0110176454', '0110183035', '0110224080', '0110263474', '0110269067-001', '0110269067-013', '0110269067-015', '0110282967', '0110298734', '0110316013', '0110328957', '0110342743', '0110350078', '0110474161', '0110489231', '0110495122', '0110534029', '0110535625', '0110554762', '0110574374', '0110590249', '0110629961', '0110630903', '0110657045', '0110798705-001', '0110813939', '0110845842', '0200662314-005', '0200662314-007', '0200662314-008', '0200891120', '0201240971-003', '0201261770', '0201352548', '0201400953', '0201572906', '0201968496', '0202198715', '0300100037-009', '0300363808', '0300555450-001', '0301175691-025', '0301472278', '0302017137', '0302249586-008', '0302294892', '0302309845', '0302309845-017', '0302431595', '0302862471', '0303203915', '0303217354', '0303217354-001', '0303217354-009', '0303217354-072', '0303217354-075', '0303217354-099', '0303217354-117', '0303217354-154', '0303284985-002', '0303490096', '0303517541', '0303905167', '0304453636', '0304475742', '0304741634', '0304836029-001', '0305004016', '0305071823', '0305085086', '0305225110', '0305339943', '0305767459', '0305781598', '0305825968', '0305899409', '0306411423', '0309300048', '0309300048-011', '0309323694', '0309455845', '0309535628', '0310207614', '0310258721', '0310303237', '0310350082', '0310471746', '0310471746-351', '0310544602', '0310608782', '0310745651', '0311167763', '0311187079-004', '0311241512', '0311241512-001', '0311374600-003', '0311609355-001', '0311716597', '0311854540-014', '0311858376', '0311877763', '0312040424-002', '0312120782', '0312143412', '0312176760', '0312184546', '0312202555', '0312228962', '0312321217', '0312346250', '0312795030', '0312803588', '0312847144', '0312850348', '0312920154', '0313063537', '0313120376', '0313238628', '0313244808', '0313245590', '0313386457', '0313462725', '0313506115', '0313507750', '0313615139', '0313650711-001', '0313681999', '0313736912', '0313765864', '0313784190', '0313871478', '0313915982', '0313931670', '0313946740', '0313991912', '0314025012', '0314046502', '0314212615', '0314244504', '0314259081', '0314267558', '0314318361', '0314339876', '0314351457', '0314396793', '0314400344', '0314501423', '0314534002', '0314561091', '0314587300', '0314587300-002', '0314611200', '0314726709', '0314796600', '0314826929', '0314857613', '0314920336', '0314953356', '0314995363', '0315019533', '0315042518', '0315074291', '0315157290', '0315179350', '0315222662', '0315247674', '0315275368', '0315304731', '0315505269', '0315526533', '0315686470', '0315719126', '0315748060', '0315749882', '0315761008', '0315819716', '0315847456', '0315906278', '0315974616', '0315996183', '0316032671', '0316071430', '0316152369', '0316246803', '0316331897', '0316361073', '0316422872', '0316427415', '0316458371', '0316573568', '0316613299', '0316787947', '0316822782', '0316858884', '0316872871', '0316940306', '0317113073', '0317136289', '0317247260', '0317275444', '0317409867', '0317485730', '0317566563', '0317641683', '0317642905-001', '0317648590', '0317785678', '0317914972', '0317952223', '0317971201', '0317977059', '0318079481', '0318135016', '0318163905', '0318174495', '0318218978', '0318242963', '0318256155', '0318269002', '0318379044', '0318389356', '0318407598', '0318410921', '0318514889', '0318671641', '0401534489', '0500441475', '0500451106', '0500475192', '0601124592', '0700869564', '0901058580', '1000215222', '1000219925', '1001252851', '1001284740', '1101171437-001', '1101864495', '1801301480', '2200795004', '2400589746', '2400844001', '2400865636', '2500571100', '2500717889', '2800574215', '2800719809', '2800866680', '2800975979', '2801693913', '2801715483', '2802143380', '2802305306', '2802412185', '2802480065', '2802927811', '2803022903', '2900609278', '2901238107', '2901384002', '2901816735', '2902129622', '3301647075', '3502246436', '3600224423-013', '3600224423-053', '3600738443-003', '3603153805', '3603461824', '3603851944', '3603854536', '3603939973', '3700145694', '3700146031', '3700362089', '3700586018', '3700790334', '3700798284', '3700817240', '3700891396', '3701255643', '3701511939', '3701676049', '3701734692', '3701894174', '3701906616', '3702037630', '3702058398', '3702083027', '3702086469', '3702212226', '3702281646', '3702288296', '3702290295', '3702314027', '3702315567', '3702353996', '3702484477', '3702485093', '3702545183', '3702559348', '3702642476', '3702644988', '3702678391', '3702679596', '3702707797', '3702719697', '3702730179', '3702771016', '3702777811', '3702816637', '3702851166', '3702868699', '3702869029', '3702874188', '3702882090', '3702908454', '3702926799', '3702955542', '3702992689', '3703010751', '3703016104', '3703060801', '3703146142', '3703146738', '3703165603', '3703182052', '3703194876', '3703221368', '3801240552', '4300888506', '4600171036', '4600236445', '4600285393', '4600412757', '4601122560', '4601158623', '4601604028', '4601604109', '4601604532', '4601622242', '4900891733', '5600128057-053', '8107260132-001', '8810990198-001')
and 
ttb_vendor_invoice_date >= '2024-01-01' and ttb_vendor_invoice_date <= '2024-12-31'


-- ---------------------------------------
-- F05 Cập nhật thành tiền trước thuế, tiền thuế, đơn giá cho bảng đã chia
-- ---------------------------------------
update ttb_inout_product_mapper ipm
set 
    thanhtien_exclude_tax = data.thanhtien_exclude_tax,
    tien_thue = data.tien_thue,
    column_y = coalesce(data.dongia, 0)
from (
    SELECT
        ipm.id, 
        -- thành tiền trước thuế
        round(
        case 
            when ipm.active = False then coalesce(nil.thanhtien_exclude_tax, nil.thanhtien) 
            else round((ipm.quantity / nil.soluong) * coalesce(nil.thanhtien_exclude_tax, nil.thanhtien)) 
        end 
        ) AS thanhtien_exclude_tax,

        -- tiền thuế = tien * thue suat
        round(
        case 
            when ipm.active = False then coalesce(nil.thanhtien_exclude_tax, nil.thanhtien)
            else (ipm.quantity / nil.soluong) * coalesce(nil.thanhtien_exclude_tax, nil.thanhtien)
        end
        * 
        (
            CASE 
                WHEN coalesce(nil.thuesuat, ni.thuesuat) in ('5%', '5') THEN 0.05
                WHEN coalesce(nil.thuesuat, ni.thuesuat) in ('8%', '8', 'KHAC:08.00%', 'KHAC', 'khac') THEN 0.08
                WHEN coalesce(nil.thuesuat, ni.thuesuat) in ('10%', '10') THEN 0.1
                when coalesce(nil.thuesuat, ni.thuesuat) like '%KHAC%' THEN 0.08
                ELSE 0
            END
        )
        ) AS tien_thue,

        -- đơn giá
        round(
        CASE 
            WHEN nil.soluong = 0 OR coalesce(nil.thanhtien_exclude_tax, nil.thanhtien) = 0 or (ipm.active=False and nil.soluong_goc=0) THEN nil.dongia
            when ipm.active = False then round(coalesce(nil.thanhtien_exclude_tax, nil.thanhtien) / nil.soluong_goc)
            ELSE round(coalesce(nil.thanhtien_exclude_tax, nil.thanhtien) / nil.soluong)
        END
        ) AS dongia
        
        , ipm.active
        , ipm.in_line_id
        , ni.id ni_id
        
    FROM 
        ttb_inout_product_mapper ipm
        JOIN ttb_nimbox_invoice_line nil ON nil.id = ipm.in_line_id
        JOIN ttb_nimbox_invoice ni ON ni.id = nil.nimbox_invoice_id
) data
where data.id = ipm.id

-- F03 version 2:
UPDATE ttb_inout_product_mapper ipm
SET quantity = ipm.quantity + data.remain_qty
FROM (
    select 
        ipm.id ipm_id,
        remain.remain_qty,

        iim_target.in_line_id,
        oil.product_id,
        psi.misa_product_id
    from
        (
            SELECT 
                iim.in_line_id,
                MAX(iim.id) AS iim_id
            FROM ttb_inout_invoice_mapper iim
            JOIN tax_output_invoice_line oil ON oil.id = iim.out_line_id
            JOIN (
                SELECT 
                    iim.in_line_id,
                    MAX(oil.buy_product_rate) AS max_rate
                FROM 
                    ttb_inout_invoice_mapper iim
                    JOIN tax_output_invoice_line oil ON oil.id = iim.out_line_id
                    join product_sale_item psi on psi.id = oil.product_id
                where psi.misa_product_id is not null
                GROUP BY iim.in_line_id
            ) x ON x.in_line_id = iim.in_line_id AND x.max_rate = oil.buy_product_rate
            GROUP BY iim.in_line_id
        ) iim_target
        join (
            SELECT 
                nil.id in_line_id,
                SUM(quantity) AS total_qty,
                nil.soluong - sum(quantity) as remain_qty
            FROM 
                ttb_inout_invoice_mapper iim
                join ttb_nimbox_invoice_line nil on nil.id = iim.in_line_id
            GROUP BY nil.id having nil.soluong - sum(quantity) > 0
        ) remain on remain.in_line_id = iim_target.in_line_id
        
        join ttb_inout_invoice_mapper iim on iim.id = iim_target.iim_id
        join tax_output_invoice_line oil on oil.id = iim.out_line_id
        join product_sale_item psi on psi.id = oil.product_id

        join ttb_inout_product_mapper ipm on ipm.in_line_id = iim_target.in_line_id and ipm.out_product_id = psi.misa_product_id

) data
WHERE ipm.id = data.ipm_id

-- F03 Phân bổ Bù số lượng còn thiếu chọn dòng theo tiêu chí max diff rate
-- WITH target AS (
--     SELECT 
--         MAX(ipm.id) AS ipm_id,
--         ipm.in_line_id
--     FROM ttb_inout_invoice_mapper ipm
--     JOIN tax_output_invoice_line oil ON oil.id = ipm.out_line_id
--     JOIN ttb_nimbox_invoice_line nil ON nil.id = ipm.in_line_id
--     JOIN (
--         SELECT 
--             ipm.in_line_id,
--             MAX(oil.buy_product_rate) AS max_rate
--         FROM ttb_inout_invoice_mapper ipm
--         JOIN tax_output_invoice_line oil ON oil.id = ipm.out_line_id
--         GROUP BY ipm.in_line_id
--     ) x ON x.in_line_id = ipm.in_line_id AND x.max_rate = oil.buy_product_rate
--     GROUP BY ipm.in_line_id
-- ),
-- agg AS (
--     SELECT 
--         in_line_id,
--         SUM(quantity) AS total_qty
--     FROM ttb_inout_invoice_mapper
--     GROUP BY in_line_id
-- )

-- -- select nil.soluong - agg.total_qty, * 
-- -- FROM target
-- -- JOIN agg ON agg.in_line_id = target.in_line_id
-- -- JOIN ttb_nimbox_invoice_line nil ON nil.id = target.in_line_id
-- -- WHERE nil.soluong - agg.total_qty != 0

-- UPDATE ttb_inout_invoice_mapper ipm
-- SET quantity = ipm.quantity + nil.soluong - agg.total_qty
-- FROM target
-- JOIN agg ON agg.in_line_id = target.in_line_id
-- JOIN ttb_nimbox_invoice_line nil ON nil.id = target.in_line_id
-- WHERE ipm.id = target.ipm_id and nil.soluong - agg.total_qty != 0


-- Lấy giá sản phẩm đầu vào
-- https://trial.erp.tientho.vn/odoo/crons/319

-- Tính đơn giá theo thành tiền trước thuế và hệ số đơn vị:
update ttb_nimbox_invoice_line set dongia_ban = data.dongia_ban
from (
    select ni.id id_don, nil.id id_dong, nil.thanhtien_exclude_tax, nil.dongia, nil.soluong_goc, nil.donvi_rate,
        case when nil.soluong_goc = 0 then nil.dongia else nil.thanhtien_exclude_tax / nil.soluong_goc end
        / nil.donvi_rate as dongia_ban
    from ttb_nimbox_invoice_line nil
        join ttb_nimbox_invoice ni on ni.id = nil.nimbox_invoice_id
        where 1=1
        and ni.ttb_vendor_invoice_date between '2024-01-01' and '2024-12-31'
        and ni.line_exclude_tax in ('1', '2', '5')
        and nil.tchat='1'
        and coalesce(nil.thanhtien_exclude_tax, 0) != 0
) data
where data.id_dong = ttb_nimbox_invoice_line.id

-- Tính giá nhập của sản phẩm đầu vào - Trước khi chạy cần tính lại dongia_ban ngay phía trên
-- update product_sale_item set price = 0 where batch_name = 'dau_vao'; -- bỏ lệnh này vì chỉ cần chạy 1 lần
update product_sale_item set price = data.dongia_ban
from (
    select psi.id, psi.price, data.dongia_ban
    from product_sale_item psi
    join ( 
        select nil.buy_product_id, min(dongia_ban) dongia_ban
        from ttb_nimbox_invoice_line nil
        join ttb_nimbox_invoice ni on ni.id = nil.nimbox_invoice_id
        where 1=1
        and ni.ttb_vendor_invoice_date between '2024-01-01' and '2024-12-31'
        and ni.line_exclude_tax in ('1', '2', '5')
        and nil.tchat='1'
        and dongia_ban > 0
        group by nil.buy_product_id
        ) data
    on data.buy_product_id = psi.id
    where psi.price != data.dongia_ban
) data 
where data.id = product_sale_item.id



update ttb_nimbox_invoice_line set soluong = soluong_goc * donvi_rate
where donvi_rate > 1
-- tính lại donvi_rate do dòng bị tạo lại
update ttb_nimbox_invoice_line set donvi_rate = data.donvi_rate
from (

select nil.id as nil_id, ni.id, psi.id, psi.name, psi.price, nil.donvi, nil.soluong, nil.dongia, nil.thanhtien_exclude_tax, floor(thanhtien_exclude_tax / (soluong * psi.price)) as donvi_rate, thanhtien_exclude_tax / (soluong)
from 
    ttb_nimbox_invoice_line nil
    join ttb_nimbox_invoice ni on ni.id = nil.nimbox_invoice_id
    join product_sale_item psi on psi.id = nil.buy_product_id
    where ni.ttb_vendor_invoice_date between '2024-01-01' and '2024-12-31'
    and nil.create_date > '2025-12-10' 
    and soluong != 0 and psi.price != 0
    and thanhtien_exclude_tax is not null
    and thanhtien_exclude_tax / (soluong * psi.price) > 2

) data
where data.nil_id = ttb_nimbox_invoice_line.id

-- xử lý code trên ở diện rộng: 2,5,8,10: quà tặng, đồ chơi, vpp, thực phẩm
update ttb_nimbox_invoice_line set soluong = soluong_goc * data.donvi_rate
from (
select 
--     pct.name, ni.id, psi.id, psi.name, psi.price, nil.donvi, nil.soluong, nil.dongia, nil.thanhtien_exclude_tax, floor(thanhtien_exclude_tax / (soluong * psi.price)) as donvi_rate, thanhtien_exclude_tax / (soluong)
    nil.id as nil_id,
    case when nil.donvi_rate = 1 then floor(thanhtien_exclude_tax / (soluong * psi.price)) else nil.donvi_rate end as donvi_rate 
    
from
    ttb_nimbox_invoice_line nil
    join ttb_nimbox_invoice ni on ni.id = nil.nimbox_invoice_id
    join product_sale_item psi on psi.id = nil.buy_product_id
    left join product_category_training pct on pct.id = psi.category_id_level_1
where ni.ttb_vendor_invoice_date between '2024-01-01' and '2024-12-31'
    and psi.category_id_level_1 in (2,5,8,10)
    and soluong != 0 and psi.price != 0
    and thanhtien_exclude_tax is not null
    and thanhtien_exclude_tax / (soluong * psi.price) > 2
) data
where data.nil_id = ttb_nimbox_invoice_line.id


-- SQL lấy lợi nhuận
-- version 1: Chưa bị phân bổ lượng dư
select * from 
(
select psi.id, psi.code, psi.name, 
    sum(iim.quantity) tong_sl_ban, 
    round(sum((iim.quantity / oil.quantity) *oil.price_total)) tong_tien_ban, 
    
    round(sum((iim.quantity / nil.soluong) * coalesce(nil.thanhtien_exclude_tax, thanhtien))) tong_tien_nhap,
    
    round(sum((iim.quantity / oil.quantity) *oil.price_total) - sum(iim.in_price_total)) tong_loi_nhuan
from 
    ttb_inout_invoice_mapper iim
    join tax_output_invoice_line oil on oil.id = iim.out_line_id
    join ttb_nimbox_invoice_line nil on nil.id = iim.in_line_id
    join product_sale_item psi on psi.id = oil.product_id

group by psi.id
)
data
order by data.tong_loi_nhuan desc


-- version 2: đã bị phân bổ lượng dư:
SELECT
    *
FROM
    (
        SELECT
            psi.id,
            psi.code,
            psi.name,
            SUM(quantity) tong_sl_ban,
            ROUND(
                SUM(
                    (quantity / nil_quantity) * thanhtien_exclude_tax
                )
            ) tong_tien_nhap,
            ROUND(
                SUM(
                    (quantity / oil_quantity) * price_total
                )
            ) tong_tien_ban,
            round(SUM(
                (quantity / oil_quantity) * price_total
            ) - SUM(
                (quantity / nil_quantity) * thanhtien_exclude_tax
            )) tong_loi_nhuan
        FROM
            (
                SELECT
                    CASE WHEN pbt.row_split = 1 THEN oil.quantity WHEN pbt.row_split > 1
                    AND lech = 0 THEN iim.quantity ELSE 0 END quantity,
                    oil.product_id,
                    coalesce(nil.thanhtien_exclude_tax, nil.thanhtien) thanhtien_exclude_tax,
                    oil.price_total,
                    oil.quantity oil_quantity,
                    nil.soluong nil_quantity,
                    nil.id nil_id,
                    oil.id oil_id
                FROM
                    ttb_inout_invoice_mapper iim
                    JOIN tax_output_invoice_line oil ON oil.id = iim.out_line_id
                    JOIN ttb_nimbox_invoice_line nil ON nil.id = iim.in_line_id
                    LEFT JOIN (
                        SELECT
                            oil.id,
                            COUNT(*) AS row_split,
                            SUM(iim.quantity) - oil.quantity AS lech
                        FROM
                            ttb_inout_invoice_mapper iim
                            JOIN tax_output_invoice_line oil ON oil.id = iim.out_line_id
                        GROUP BY
                            oil.id
                    ) AS pbt ON pbt.id = oil.id --     limit 10000
                    ) DATA
            JOIN product_sale_item psi ON psi.id = data.product_id
        GROUP BY
            psi.id
    ) data2
ORDER BY
    tong_loi_nhuan DESC






SQL bỏ misa product bị trùng
update product_sale_item
set code = concat(code, '-removed')
where id in
(select psi.id 

from
    product_sale_item psi
    join (select code, min(id) id, count(*) from product_sale_item psi
    where psi.batch_name = 'dau_ra_code_name_misa' and code not like '%removed%'
    group by code having count(*) > 1
    ) data on data.code = psi.code and data.id != psi.id
where psi.batch_name = 'dau_ra_code_name_misa')    