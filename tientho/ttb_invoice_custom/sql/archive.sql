-- Tính lại số sản phẩm được ghép - Cái này chỉ phải chạy 1 lần khi chưa đưa lệnh reset vào job
UPDATE product_sale_item psi
SET count_out_product = sub.product_count
FROM (
    -- Subquery để đếm số lượng sản phẩm đầu ra (out_product_ids) cho mỗi sản phẩm đầu vào (in_product_id)
    SELECT
        mapper.in_product_id,
        COUNT(mapper.id) AS product_count
    FROM
        ttb_inproduct_outproduct_mapper mapper
    GROUP BY
        mapper.in_product_id
) sub
WHERE
    psi.id = sub.in_product_id;

-- Cập nhật các dòng còn lại (những dòng không có out_product_ids nào) về 0
UPDATE product_sale_item 
SET count_out_product = 0
WHERE count_out_product IS NULL;


-- ---------------------------------------
-- SQL lưu version
-- ---------------------------------------
WITH new_ver AS (
    SELECT COALESCE(MAX(version), 0) + 1 AS ver
    FROM ttb_inout_product_mapper_history
),
upd AS (
    UPDATE ttb_inout_product_mapper_history
    SET active = false
    WHERE active IS DISTINCT FROM false
)
INSERT INTO ttb_inout_product_mapper_history (
    in_line_id,
    out_product_id,
    create_uid,
    write_uid,
    create_date,
    write_date,
    quantity,
    nimbox_invoice_id,
    ttb_vendor_invoice_date,
    thanhtien,
    so_tien_chiet_khau,
    tien_thue,
    column_a,
    column_b,
    column_c,
    column_d,
    column_h,
    column_i,
    column_j,
    column_k,
    column_l,
    column_m,
    column_n,
    column_p,
    column_q,
    column_r,
    column_s,
    column_t,
    column_u,
    column_v,
    column_w,
    column_af,
    column_aj,
    column_ak,
    column_am,
    column_an,
    column_ao,
    column_ap,
    column_aq,
    column_ar,
    column_aw,
    column_az,
    column_e,
    column_f,
    column_al,
    column_o,
    column_x,
    column_y,
    column_z,
    column_aa,
    column_ab,
    column_ac,
    column_ad,
    column_ae,
    column_ag,
    column_ah,
    column_ai,
    column_as,
    column_at,
    column_au,
    column_av,
    column_ax,
    column_ay,
    thanhtien_exclude_tax,
    version,
    active,
    version_time
)
SELECT
    in_line_id,
    out_product_id,
    create_uid,
    write_uid,
    create_date,
    write_date,
    quantity,
    nimbox_invoice_id,
    ttb_vendor_invoice_date,
    thanhtien,
    so_tien_chiet_khau,
    tien_thue,
    column_a,
    column_b,
    column_c,
    column_d,
    column_h,
    column_i,
    column_j,
    column_k,
    column_l,
    column_m,
    column_n,
    column_p,
    column_q,
    column_r,
    column_s,
    column_t,
    column_u,
    column_v,
    column_w,
    column_af,
    column_aj,
    column_ak,
    column_am,
    column_an,
    column_ao,
    column_ap,
    column_aq,
    column_ar,
    column_aw,
    column_az,
    column_e,
    column_f,
    column_al,
    column_o,
    column_x,
    column_y,
    column_z,
    column_aa,
    column_ab,
    column_ac,
    column_ad,
    column_ae,
    column_ag,
    column_ah,
    column_ai,
    column_as,
    column_at,
    column_au,
    column_av,
    column_ax,
    column_ay,
    thanhtien_exclude_tax,
    (SELECT ver FROM new_ver) AS version,
    true AS active,
    NOW() AS version_time
FROM ttb_inout_product_mapper;


WITH new_ver AS (
    SELECT COALESCE(MAX(version), 0) + 1 AS ver
    FROM ttb_inout_invoice_mapper_history
),
upd AS (
    UPDATE ttb_inout_invoice_mapper_history
    SET active = false
    WHERE active IS DISTINCT FROM false
)
INSERT INTO ttb_inout_invoice_mapper_history (
    in_line_id,
    out_line_id,
    create_uid,
    write_uid,
    create_date,
    write_date,
    quantity,
    version,
    active,
    version_time
)
SELECT
    in_line_id,
    out_line_id,
    create_uid,
    write_uid,
    create_date,
    write_date,
    quantity,
    (SELECT ver FROM new_ver) AS version,
    true AS active,
    NOW() AS version_time
FROM ttb_inout_invoice_mapper;




-- CÁC SQL bỏ không dùng nữa
-- ---------------------------------------
-- 01. Cập nhật Cơ sở (kho) cho hoá đơn đầu ra:
-- ---------------------------------------
UPDATE
    tax_output_invoice_line
SET
    ttb_branch_id = data.ttb_branch_id
FROM
    (
        SELECT
            oil.id,
            tbm.ttb_branch_id
        FROM
            tax_output_invoice_line oil
            LEFT JOIN tax_branch_mapper tbm ON tbm.name = SUBSTRING(
                oil.invoice_symbol
                FROM
                    2
            )
            AND tbm.type = 'sale'
        WHERE
            oil.ttb_branch_id IS NULL
    ) DATA
WHERE
    data.id = tax_output_invoice_line.id

-- 02. Cập nhật sản phẩm đầu ra misa từ sản phẩm đầu ra ms invoice
-- version 1:
update tax_output_invoice_line set misa_product_id = data.misa_product_id
from (
    select oil.id, map.misa_product_id
    from
        tax_output_invoice_line oil
        join (
            SELECT
                psi.id product_id,
                psi_ms.id misa_product_id
            FROM
                product_sale_item psi
                LEFT JOIN product_sale_item psi_n ON psi_n.batch_name = 'dau_ra_code_name_cotn'
                AND LOWER(psi_n.name) = LOWER(psi.name)
                LEFT JOIN product_sale_item psi_ms ON psi_ms.batch_name = 'dau_ra_code_name_misa'
                AND psi_ms.code = psi_n.code
            WHERE
                psi.batch_name = 'dau_ra'
            GROUP BY
                psi.id,
                psi_ms.id
         ) map on map.product_id = oil.product_id
     where oil.misa_product_id is null
) data
where data.id = tax_output_invoice_line.id

-- 03. Cập nhật Cơ sở (kho) cho hoá đơn đầu vào:
-- ---------------------------------------
update ttb_nimbox_invoice set ttb_branch_id = data.ttb_branch_id
from
(select 
    ni.id, mapper.ttb_branch_id
--     ni.hvtnmhang, * 
from 
    ttb_nimbox_invoice ni
    left join (select lower(UNACCENT(name)) xx, min(ttb_branch_id) ttb_branch_id
    from tax_branch_mapper
    group by lower(UNACCENT(name)) ) mapper on mapper.xx = lower(UNACCENT(ni.hvtnmhang))
) data
where data.id = ttb_nimbox_invoice.id


-- Lấy danh sách đơn vị tính nhà cung cấp
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
where data.id_dong = ttb_nimbox_invoice_line.id;

select data_ncc.*, data_dvt.donvi, data_dvt.ten_san_pham_ghep 
from

    (
        select * from (
            select 
                ni.ttb_vendor_name ten_ncc, pct.name mch1, 
                count(*) as total_count,
                row_number() over (
                    partition by ni.ttb_vendor_name -- trường phân vùng
                    order by count(*) desc -- trường sắp xếp
                ) as rn -- trường thứ tự 1,2,...
            from
                ttb_nimbox_invoice_line nil
                join ttb_nimbox_invoice ni on ni.id = nil.nimbox_invoice_id
                
                join product_category_training pct on pct.id = nil.category_id_level_1
            where ni.ttb_vendor_invoice_date between '2024-01-01' and '2024-12-31'
            
            group by ni.ttb_vendor_name, pct.id
        ) data
        where data.rn = 1
    ) data_ncc

join
    (
        select 
            ten_ncc,
            donvi,
            STRING_AGG(name, ' | ') AS ten_san_pham_ghep
        from (
            select * from (
                select 
                    ni.ttb_vendor_name ten_ncc, nil.donvi, psi.name,
                    count(*) as total_count,
                    row_number() over (
                        partition by ni.ttb_vendor_name, nil.donvi -- trường phân vùng
                        order by count(*) desc -- trường sắp xếp
                    ) as rn -- trường thứ tự 1,2,...
                from
                    ttb_nimbox_invoice_line nil
                    join ttb_nimbox_invoice ni on ni.id = nil.nimbox_invoice_id
                    
                    join product_category_training pct on pct.id = nil.category_id_level_1
                    join product_sale_item psi on psi.id = nil.buy_product_id
                where 1=1
                    and ni.ttb_vendor_invoice_date between '2024-01-01' and '2024-12-31'
                    and coalesce(nil.donvi, '') != ''
                    and ni.use_state = True
                group by ni.ttb_vendor_name, nil.donvi, psi.id
            ) data
            where data.rn < 4
            order by ten_ncc, donvi
        ) data
        group by ten_ncc, donvi   
    ) data_dvt
on data_ncc.ten_ncc = data_dvt.ten_ncc
order by data_ncc.mch1, data_ncc.ten_ncc, data_dvt.donvi