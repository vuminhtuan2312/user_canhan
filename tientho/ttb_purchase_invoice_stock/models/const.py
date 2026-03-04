purchase_invoice_stock_summary = """
CREATE MATERIALIZED VIEW purchase_invoice_stock_summary AS
WITH purchase_picking_data AS (
    SELECT 
        po.id as po_id,
        rp.name as partner_name,
        rp.vat,
        po.name as po_name,
        sp.name as sp_name,
        COALESCE(sp.amount_total, 0) as amount_total,
        po.received_amount_total,
        po.compare_invoice
    FROM purchase_order po
    JOIN purchase_order_line pol on pol.order_id = po.id
    JOIN stock_move sm on sm.purchase_line_id = pol.id
    JOIN stock_picking sp ON sp.id = sm.picking_id
    JOIN res_partner rp on rp.id = po.partner_id
    WHERE po.compare_invoice is not null 
    and sp.state = 'done'
"""

purchase_invoice_stock_summary2 = """
    group by po.id , sp_name,  rp.name, rp.vat,po.name, sp.amount_total, po.compare_invoice
),
purchase_nimbox_rel AS (
    SELECT 
        purchase_order_id as po_id,
        ttb_nimbox_invoice_id as invoice_id
    FROM ttb_nimbox_invoice_purchase_rel
),
nimbox_invoice_data AS (
    SELECT 
        tni.id as nimbox_id,
        tni.ttb_vendor_invoice_no,
        tni.ttb_price_unit,
        tni.ttb_vendor_invoice_code as invoice_code,
        tni.ttb_vendor_invoice_date as invoice_date
    FROM ttb_nimbox_invoice tni
)

SELECT 
    floor(random()*1000000000)::int as id,
	ni.ttb_vendor_invoice_no,
	ni.ttb_price_unit,
	ni.invoice_code,
	ni.invoice_date,
	po.partner_name,
    po.vat,
    po.po_name,
    po.sp_name,
    po.amount_total,
    po.received_amount_total,
	po.compare_invoice
FROM purchase_picking_data po
JOIN purchase_nimbox_rel rel on po.po_id = rel.po_id
JOIN nimbox_invoice_data ni on ni.nimbox_id = rel.invoice_id

"""

purchase_invoice_stock_summary_without_nibot = """
CREATE MATERIALIZED VIEW purchase_invoice_stock_summary_without_nibot AS
SELECT 
    floor(random()*1000000000)::int as id,
    rp.name as partner_name,
    rp.vat,
    po.name as po_name,
    sp.name as sp_name,
    COALESCE(sp.amount_total, 0) as amount_total
FROM purchase_order po
JOIN purchase_order_line pol on pol.order_id = po.id
JOIN stock_move sm on sm.purchase_line_id = pol.id
JOIN stock_picking sp ON sp.id = sm.picking_id
JOIN res_partner rp on rp.id = po.partner_id
where rp.ttb_no_invoice = True
and sp.state = 'done'
"""
