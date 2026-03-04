-- F02
-- Bước 1: Ktra có phân bổ quá hoặc thiếu số lượng có hay không:
select min(ni.id), min(ni.ttb_branch_id), nil.id, max(ipm.id), sum(ipm.quantity), nil.soluong, nil.soluong - sum(ipm.quantity) as lech 
from 
    ttb_inout_invoice_mapper ipm
    join ttb_nimbox_invoice_line nil on nil.id = ipm.in_line_id
    join ttb_nimbox_invoice ni on ni.id = nil.nimbox_invoice_id
group by nil.id
    having nil.soluong - sum(ipm.quantity) != 0;

-- Kiểm tra số lượng còn lại + số lượng đã dùng có bằng soluong
select * from ttb_nimbox_invoice_line nil
join ttb_nimbox_invoice ni on ni.id = nil.nimbox_invoice_id
where 1=1
and coalesce(nil.soluong, 0) != coalesce(nil.soluong_used, 0) + coalesce(nil.soluong_remain, 0);

-- Kiểm tra số lượng đã dùng có bằng tổng số lượng các bản ghi phân bổ:
select nil.id, sum(ipm.quantity), nil.soluong_used from ttb_nimbox_invoice_line nil
join ttb_nimbox_invoice ni on ni.id = nil.nimbox_invoice_id
left join ttb_inout_invoice_mapper ipm on ipm.in_line_id = nil.id
where 1=1

group by nil.id having sum(ipm.quantity) != nil.soluong_used;
    
-- Kiểm tra hoá đơn kho chung có bị phân bổ vào nhiều kho không
-- Không phải kho chung
select ni.ttb_branch_id, ni.in_branch_id, oil.ttb_branch_id
from
    ttb_inout_invoice_mapper iim
    join ttb_nimbox_invoice_line nil on nil.id = iim.in_line_id
    join ttb_nimbox_invoice ni on ni.id = nil.nimbox_invoice_id
    join tax_output_invoice_line oil on oil.id = iim.out_line_id

where ni.in_branch_id is null and coalesce(ni.ttb_branch_id, 0) != coalesce(oil.ttb_branch_id, 0);

-- Kho chung id kho đầu ra khác id kho được ghép
select ni.ttb_branch_id, ni.in_branch_id, oil.ttb_branch_id
from
    ttb_inout_invoice_mapper iim
    join ttb_nimbox_invoice_line nil on nil.id = iim.in_line_id
    join ttb_nimbox_invoice ni on ni.id = nil.nimbox_invoice_id
    join tax_output_invoice_line oil on oil.id = iim.out_line_id

where ni.in_branch_id is not null and coalesce(ni.in_branch_id, 0) != coalesce(oil.ttb_branch_id, 0);

-- Kho chung bị ghép với nhiều kho đầu ra
select id from (
    select ni.id, oil.ttb_branch_id
    from
        ttb_inout_invoice_mapper iim
        join ttb_nimbox_invoice_line nil on nil.id = iim.in_line_id
        join ttb_nimbox_invoice ni on ni.id = nil.nimbox_invoice_id
        join tax_output_invoice_line oil on oil.id = iim.out_line_id
    
    where ni.in_branch_id is not null
    group by ni.id, oil.ttb_branch_id
) data
group by id having count(*) > 1;

-- Ktra phân bổ thiếu
select min(ni.id), min(ni.ttb_branch_id), nil.id, max(ipm.id), sum(ipm.quantity), nil.soluong, nil.soluong - sum(ipm.quantity) as lech 
from 
    ttb_inout_invoice_mapper ipm
    join ttb_nimbox_invoice_line nil on nil.id = ipm.in_line_id
    join ttb_nimbox_invoice ni on ni.id = nil.nimbox_invoice_id
group by nil.id
    having nil.soluong - sum(ipm.quantity) > 0;





-- CÁC SQL kiểm tra các line có tchat là 2,3,4 (line discount)
-- tchat = 2
-- - Bước 1 xét Tien_C_Thue nếu = 0 thì là loại 2. Nếu khác 0 thì chuyển bước 2
-- - Bước 2: Cxét thanhtien tại line nếu = 0 thì là loại 1. Nếu khác 0 thì chuyển bước 3
-- - Bước 3: xét tensp có chữ TBKM, nếu có thì là loại 3, không có loại 4
-- SQL liệt kê các trường hợp bị nhầm




tchat = 3

select nil.thanhtien, nil.* from ttb_nimbox_invoice_line nil
join ttb_nimbox_invoice ni on ni.id = nil.nimbox_invoice_id
where tchat in ('3')
and ni.ttb_vendor_invoice_date between '2024-01-01' and '2024-12-31'
and ni.trang_thai_hd in ('1')
-- and ni.trang_thai_hd in ('2', '3', '5')
and ni.tien_c_thue != 0 and nil.thanhtien != 0
and nil.tensp not ilike '%giảm giá%' and nil.tensp not ilike '%chiết khấu%' and nil.tensp not ilike '%C/k%' and nil.tensp not ilike '%tặng%'





-- SQL kiểm tra phân bổ chiết khấu:
select 
    id,
    sum_thanhtien as total_thanhtien,
    sum_phanbo_chietkhau,
    sum_chiet_khau_tong_don
from (
    select 
        ni.id,
        coalesce(ni.tien_thue, 0) tien_thue,
        coalesce(ni.tien_c_thue, 0) tien_c_thue,
        sum(case when nil.tchat in ('2', '3', '4') then 0 else coalesce(nil.thanhtien, 0) end)                                           as sum_thanhtien,
        sum(case when nil.tchat in ('2', '3', '4') then 0 else coalesce(nil.phanbo_chietkhau, 0) end)                                    as sum_phanbo_chietkhau,
        sum(case when nil.tchat not in ('2', '3', '4') then 0 else coalesce(nil.thanhtien, 0) end)                                       as sum_chiet_khau_tong_don
    from ttb_nimbox_invoice_line nil
    join ttb_nimbox_invoice ni on ni.id = nil.nimbox_invoice_id
    where ni.line_exclude_tax = '4' 
--         and ni.id = 33699
    group by ni.id, ni.tien_c_thue) xxx
where sum_phanbo_chietkhau != sum_chiet_khau_tong_don



-- SQL kiểm tra thành tiền trước thuế
select 
    *
from (
    select 
        ni.id,
        ni.tien_c_thue,
        sum(case when nil.tchat in ('2', '3', '4') then 0 else coalesce(nil.thanhtien_exclude_tax, 0) end) as sum_thanhtien_exclude_tax
    from ttb_nimbox_invoice_line nil
    join ttb_nimbox_invoice ni on ni.id = nil.nimbox_invoice_id
    where ni.line_exclude_tax = '4' 
--         and ni.id = 33699
    group by ni.id, ni.tien_c_thue) xxx
where tien_c_thue != sum_thanhtien_exclude_tax



select 
abs(tien_c_thue - sum_thanhtien_exclude_tax),
    *
from (
    select 
        ni.id,
        ni.line_exclude_tax,
        ni.tien_c_thue,
        sum(case when nil.tchat in ('2', '3', '4') then 0 else coalesce(nil.thanhtien_exclude_tax, 0) end) as sum_thanhtien_exclude_tax
    from ttb_nimbox_invoice_line nil
    join ttb_nimbox_invoice ni on ni.id = nil.nimbox_invoice_id
    where 1=1
    and ni.ttb_vendor_invoice_date between '2024-01-01' and '2024-12-31'
    and ni.line_exclude_tax in ('1', '2', '5')
--         and ni.id = 33699
    group by ni.id, ni.tien_c_thue) xxx
where abs(tien_c_thue - sum_thanhtien_exclude_tax) > 3


-- Số lượng tại hoá đơn đầu ra khác số lượng đã phân bổ
select oil.id, sum(nil.dongia_ban * iim.quantity), sum(iim.quantity), oil.quantity from ttb_inout_invoice_mapper iim
join tax_output_invoice_line oil on oil.id = iim.out_line_id
join ttb_nimbox_invoice_line nil on nil.id = iim.in_line_id

group by oil.id having sum(iim.quantity) != oil.quantity





-- Kiểm tra phân bổ quá số lượng đầu ra:
select iim.quantity, oil.quantity, oil.id, *
from 
    ttb_inout_invoice_mapper iim
    join tax_output_invoice_line oil on oil.id = iim.out_line_id
    join product_sale_item psi on psi.id = oil.product_id
    where iim.quantity > oil.quantity
    limit 1000


F06:
select nil.id, nil.nimbox_invoice_id, nil.soluong, sum(ipm.quantity)
from ttb_inout_product_mapper ipm
join ttb_nimbox_invoice_line nil on nil.id = ipm.in_line_id
where ipm.active = True

group by nil.id having nil.soluong != sum(ipm.quantity)


select nil.id, nil.nimbox_invoice_id, nil.soluong, sum(ipm.quantity)
from ttb_inout_product_mapper ipm
join ttb_nimbox_invoice_line nil on nil.id = ipm.in_line_id
where ipm.active = False

group by nil.id having nil.soluong_goc != sum(ipm.quantity)



F00:
select 
    oil.product_id, psi.misa_product_id
    ,*
from 
    ttb_inout_invoice_mapper ioim
    join ttb_nimbox_invoice_line nil on nil.id = ioim.in_line_id
    join ttb_nimbox_invoice ni on nil.nimbox_invoice_id = ni.id
    join tax_output_invoice_line oil on oil.id = ioim.out_line_id
    left join product_sale_item psi on psi.id = oil.product_id
where psi.misa_product_id is null
