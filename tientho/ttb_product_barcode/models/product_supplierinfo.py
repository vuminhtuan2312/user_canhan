from odoo import api, fields, models
import logging
_logger = logging.getLogger(__name__)


class SupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    augges_code = fields.Char("Auggess Code", index=True)

    @api.model
    def sync_create(self):
        """Hàm đồng bộ dữ liệu bảng giá từ Augges về Odoo"""
        conn = self.env['ttb.tools'].get_mssql_connection()
        cursor = conn.cursor()

        last_sync_id = int(self.env['ttb.tools'].get_mssql_config("mssql.product_supplierinfo.last_sync_id_create", "0"))
        
        while True:

            # Lấy dữ liệu từ bảng sản phẩm MSSQL
            cursor.execute(f"""
SELECT top 1000
    SlNxD.ID_Hang,
    SlNxD.ID_Dt,
    SlNxD.Don_Gia1
FROM
    SlNxD
    JOIN (
        SELECT
            SlNxD.ID_Hang,
            SlNxD.ID_Dt,
            SlNxD.SNgay,
            MAX(ID) AS ID,
            MAX(Stt) AS Stt
        FROM
            SlNxD
            JOIN (
                SELECT
                    SlNxD.ID_Hang,
                    SlNxD.ID_Dt,
                    MAX(SlNxD.SNgay) AS SNgay
                FROM
                    SlNxD
                    JOIN SlNxM ON SlNxM.ID = SlNxD.ID
                    JOIN DmNx ON DmNx.ID = SlNxM.ID_Nx
                WHERE
                    DmNx.Ma_Ct = 'NM'
                GROUP BY
                    SlNxD.ID_Hang,
                    SlNxD.ID_Dt
            ) AS xxx ON xxx.ID_Hang = SlNxD.ID_Hang
            AND xxx.ID_Dt = SlNxD.ID_Dt
            AND xxx.SNgay = SlNxD.SNgay
        GROUP BY
            SlNxD.ID_Hang,
            SlNxD.ID_Dt,
            SlNxD.SNgay
    ) yyy ON yyy.ID_Hang = SlNxD.ID_Hang
    AND yyy.ID_Dt = SlNxD.ID_Dt
    AND yyy.SNgay = SlNxD.SNgay
    AND yyy.ID = SlNxD.ID
    AND yyy.Stt = SlNxD.Stt

    AND SlNxD.ID_Hang > {last_sync_id}
order by SlNxD.ID_Hang asc
            """)

            product_prices = cursor.fetchall()
            if not product_prices: break

            for row in product_prices:
                augges_id_product = row.ID_Hang
                augges_id_vendor = row.ID_Dt

                product = self.env['product.template'].search([('augges_id', '=', augges_id_product)])
                if not product: continue
                vendor = self.env['res.partner'].search([('augges_id', '=', augges_id_vendor)])
                if not vendor: continue

                augges_code = '%s-%s' % (product.augges_id, vendor.augges_id)
                # Kiểm tra nếu sản phẩm đã tồn tại trong Odoo
                existed = self.sudo().with_context(active_test=False).search([("augges_code", "=", augges_code)], limit=1)

                if not existed:
                    self.create({
                        'augges_code': augges_code,
                        'product_tmpl_id': product.id,
                        'partner_id': vendor.id,
                        'price': row.Don_Gia1,
                        'date_start': '2024-04-01',
                        'date_end': '9999-01-01',
                    })
                    _logger.info(f"Created new vendor price: {augges_code}")

                last_sync_id = max(last_sync_id, augges_id_product)
            self.env["ir.config_parameter"].sudo().set_param("mssql.product_supplierinfo.last_sync_id_create", str(last_sync_id))
            self.env.cr.commit()  # Commit từng bản ghi sau khi insert/update
        
        # Cập nhật ID lớn nhất đã đồng bộ
        self.env["ir.config_parameter"].sudo().set_param("mssql.product_supplierinfo.last_sync_id_create", str(last_sync_id))

        cursor.close()
        conn.close()
        _logger.info("vendor price create completed successfully!")
