from odoo import api, fields, models, _
# import pyodbc
from odoo.addons.ttb_product_barcode.models.product_template import tcvn3_to_unicode

import logging
_logger = logging.getLogger(__name__)

def get_value(value):
    return tcvn3_to_unicode(value.strip() if value else '')

class ResPartner(models.Model):
    _inherit = "res.partner"

    augges_id = fields.Integer("Auggess ID", index=True)

    @api.model
    def sync_vendors_from_mssql_create(self):
        """Hàm đồng bộ dữ liệu nhà cung cấp từ MSSQL về Odoo"""
        conn = self.env['ttb.tools'].get_mssql_connection()
        cursor = conn.cursor()

        last_sync_id = int(self.env['ttb.tools'].get_mssql_config("mssql.res_partner.last_sync_id_create", "0"))
        
        while True:

            # Lấy dữ liệu từ bảng sản phẩm MSSQL
            cursor.execute(f"""
                SELECT TOP 1000 
                    *
                FROM DmDt WHERE ID > {last_sync_id}
                    AND ID_Ndt = 1 -- nhóm đối tượng NCC
                ORDER BY ID ASC
            """)

            partners = cursor.fetchall()
            if not partners: break

            for row in partners:
                ma_dt = get_value(row.Ma_Dt)
                ten_dt = get_value(row.Ten_Dt)
                mst = get_value(row.MST)
                dia_chi = get_value(row.Dia_Chi)
                dien_thoai = get_value(row.Dien_Thoai)
                
                _logger.info(f'Bắt đầu đồng bộ mới {row.ID} {ten_dt}')
                partner_data = {
                    'augges_id': row.ID,
                    'ref': ma_dt,
                    'name': ten_dt,
                    'vat': mst,
                    'street': dia_chi,
                    'phone': dien_thoai,
                    'supplier_rank': 1,
                }

                # Kiểm tra nếu sản phẩm đã tồn tại trong Odoo
                existing_partners = self.sudo().search([("ref", "=", ma_dt)])

                if not existing_partners:
                    self.env["res.partner"].create(partner_data)
                    _logger.info(f"Created new partner: {ten_dt}")
                else:
                    existing_partners.message_post(body=f"Nhà cung cấp đã tạo từ trước ở Odoo khi đồng bộ. ID Augges: {row.ID}, Mã tham chiếu: {ma_dt}")

                # Cập nhật ID lớn nhất đã đồng bộ
                last_sync_id = max(last_sync_id, row.ID)
                self.env["ir.config_parameter"].sudo().set_param("mssql.res_partner.last_sync_id_create", str(last_sync_id))
                self.env.cr.commit()  # Commit từng bản ghi sau khi insert/update
        
        cursor.close()
        conn.close()
        _logger.info("partner create completed successfully!")

    def sync_customer(self, id_dt):
        conn = self.env['ttb.tools'].get_mssql_connection()
        cursor = conn.cursor()
        # Lấy dữ liệu từ bảng sản phẩm MSSQL
        cursor.execute(f"""
            SELECT * FROM DmDt WHERE ID = {id_dt}
        """)

        partners = cursor.fetchall()
        if not partners: return False

        for row in partners:
            ma_dt = get_value(row.Ma_Dt)
            ten_dt = get_value(row.Ten_Dt)
            mst = get_value(row.MST)
            dia_chi = get_value(row.Dia_Chi)
            dien_thoai = get_value(row.Dien_Thoai)
            
            _logger.info(f'Đồng bộ 01 khách hàng {row.ID} {ten_dt}')
            partner_data = {
                'augges_id': row.ID,
                'ref': ma_dt,
                'name': ten_dt,
                'vat': mst,
                'street': dia_chi,
                'phone': dien_thoai,
                # 'customer_rank': 1,
            }
            if not row.ID_Ndt or row.ID_Ndt == 2:
                partner_data['customer_rank'] = 1

            # Kiểm tra nếu sản phẩm đã tồn tại trong Odoo
            existing_partner = self.sudo().with_context(active_test=False).search([("augges_id", "=", row.ID)], limit=1)

            if not existing_partner:
                existing_partner = self.create(partner_data)
                _logger.info(f"Created new 01 partner: {ten_dt}")
            return existing_partner
        return False

    @api.model
    def sync_customers_from_mssql_create(self):
        """Hàm đồng bộ dữ liệu khách hàng từ MSSQL về Odoo"""
        conn = self.env['ttb.tools'].get_mssql_connection()
        cursor = conn.cursor()

        config_name = "mssql.res_partner.last_sync_id_create_customer"
        last_sync_id = int(self.env['ttb.tools'].get_mssql_config(config_name, "0"))
        
        while True:

            # Lấy dữ liệu từ bảng sản phẩm MSSQL
            cursor.execute(f"""
                SELECT TOP 10000 
                    *
                FROM DmDt WHERE ID > {last_sync_id}
                    AND (ID_Ndt is null or ID_Ndt != 1) -- nhóm đối tượng khách lẻ, khách buôn
                ORDER BY ID ASC
            """)

            partners = cursor.fetchall()
            if not partners: break

            for row in partners:
                ma_dt = get_value(row.Ma_Dt)
                ten_dt = get_value(row.Ten_Dt)
                mst = get_value(row.MST)
                dia_chi = get_value(row.Dia_Chi)
                dien_thoai = get_value(row.Dien_Thoai)
                
                _logger.info(f'Bắt đầu đồng bộ mới {row.ID} {ten_dt}')
                partner_data = {
                    'augges_id': row.ID,
                    'ref': ma_dt,
                    'name': ten_dt,
                    'vat': mst,
                    'street': dia_chi,
                    'phone': dien_thoai,
                    # 'customer_rank': 1,
                }
                if not row.ID_Ndt or row.ID_Ndt == 2:
                    partner_data['customer_rank'] = 1

                # Kiểm tra nếu sản phẩm đã tồn tại trong Odoo
                existing_partner = self.sudo().with_context(active_test=False).search([("augges_id", "=", row.ID)], limit=1)

                if not existing_partner:
                    self.env["res.partner"].create(partner_data)
                    _logger.info(f"Created new partner: {ten_dt}")

                last_sync_id = max(last_sync_id, row.ID)
                # Cập nhật ID lớn nhất đã đồng bộ
                self.env["ir.config_parameter"].sudo().set_param(config_name, str(last_sync_id))
                self.env.cr.commit()  # Commit từng bản ghi sau khi insert/update
        
        # Cập nhật ID lớn nhất đã đồng bộ
        self.env["ir.config_parameter"].sudo().set_param(config_name, str(last_sync_id))

        cursor.close()
        conn.close()
        _logger.info("partner create completed successfully!")


    @api.model
    def sync_vendors_from_mssql_update(self, update_fields=None):
        """Hàm đồng bộ dữ liệu nhà cung cấp từ MSSQL về Odoo"""
        conn = self.env['ttb.tools'].get_mssql_connection()
        cursor = conn.cursor()

        last_sync_id = int(self.env['ttb.tools'].get_mssql_config("mssql.res_partner.last_sync_id_update", "0"))
        
        while True:

            # Lấy dữ liệu từ bảng sản phẩm MSSQL
            cursor.execute(f"""
                SELECT TOP 1000 
                    *
                FROM DmDt WHERE ID > {last_sync_id}
                    AND ID_Ndt = 1 -- nhóm đối tượng NCC
                ORDER BY ID ASC
            """)

            partners = cursor.fetchall()
            if not partners: break

            for row in partners:
                ma_dt = get_value(row.Ma_Dt)
                ten_dt = get_value(row.Ten_Dt)
                mst = get_value(row.MST)
                dia_chi = get_value(row.Dia_Chi)
                dien_thoai = get_value(row.Dien_Thoai)
                
                _logger.info(f'Bắt đầu đồng bộ mới {row.ID} {ten_dt}')
                partner_data = {
                    'augges_id': row.ID,
                    'ref': ma_dt,
                    'name': ten_dt,
                    'vat': mst,
                    'street': dia_chi,
                    'phone': dien_thoai,
                    'supplier_rank': 1,
                }
                if update_fields:
                    partner_data = {key: partner_data[key] for key in partner_data if key in update_fields}

                # Kiểm tra nếu sản phẩm đã tồn tại trong Odoo
                existing_partner = self.sudo().with_context(active_test=False).search([("augges_id", "=", row.ID)], limit=1)

                if existing_partner:
                    existing_partner.write(partner_data)
                    _logger.info(f"Updated partner: {ten_dt}")

                last_sync_id = max(last_sync_id, row.ID)
                self.env.cr.commit()  # Commit từng bản ghi sau khi insert/update
        
        # Cập nhật ID lớn nhất đã đồng bộ
        self.env["ir.config_parameter"].sudo().set_param("mssql.res_partner.last_sync_id_update", str(last_sync_id))

        cursor.close()
        conn.close()
        _logger.info("partner update completed successfully!")

    @api.model
    def sync_customers_from_mssql_update(self, create=True, field_list=[]):
        """Hàm đồng bộ dữ liệu khách hàng từ MSSQL về Odoo"""
        conn = self.env['ttb.tools'].get_mssql_connection()
        cursor = conn.cursor()

        config_name = "mssql.res_partner.last_sync_id_write_customer"
        last_sync_id = int(self.env['ttb.tools'].get_mssql_config(config_name, "0"))
        
        while True:

            # Lấy dữ liệu từ bảng sản phẩm MSSQL
            cursor.execute(f"""
                SELECT TOP 10000 
                    *
                FROM DmDt WHERE ID > {last_sync_id}
                    AND (ID_Ndt is null or ID_Ndt != 1) -- nhóm đối tượng khách lẻ, khách buôn, ...
                ORDER BY ID ASC
            """)

            partners = cursor.fetchall()
            if not partners: break

            for row in partners:
                ma_dt = get_value(row.Ma_Dt)
                ten_dt = get_value(row.Ten_Dt)
                mst = get_value(row.MST)
                dia_chi = get_value(row.Dia_Chi)
                dien_thoai = get_value(row.Dien_Thoai)
                
                _logger.info(f'Bắt đầu đồng bộ update {row.ID} {ten_dt}')
                partner_data = {
                    'augges_id': row.ID,
                    'ref': ma_dt,
                    'name': ten_dt,
                    'vat': mst,
                    'street': dia_chi,
                    'phone': dien_thoai,
                    # 'customer_rank': 1,
                }
                if not row.ID_Ndt or row.ID_Ndt == 2:
                    partner_data['customer_rank'] = 1

                # Kiểm tra nếu sản phẩm đã tồn tại trong Odoo
                existing_partner = self.sudo().with_context(active_test=False).search([("augges_id", "=", row.ID)], limit=1)

                if not existing_partner and create:
                    self.env["res.partner"].create(partner_data)
                    _logger.info(f"Created new partner: {ten_dt}")
                if existing_partner:
                    if field_list:
                        partner_data = {key: partner_data[key] for key in field_list if key in partner_data}
                    
                    partner_data = {key: partner_data[key] for key in partner_data if partner_data[key] != existing_partner[key]}
                    if not partner_data: 
                        _logger.info(f"Partner not change. Dont' update: {ten_dt}")
                        continue
                    existing_partner.write(partner_data)
                    _logger.info(f"Updated partner: {ten_dt}")


                last_sync_id = max(last_sync_id, row.ID)
                # Cập nhật ID lớn nhất đã đồng bộ
                self.env["ir.config_parameter"].sudo().set_param(config_name, str(last_sync_id))
                self.env.cr.commit()  # Commit từng bản ghi sau khi insert/update
        
        # Cập nhật ID lớn nhất đã đồng bộ
        self.env["ir.config_parameter"].sudo().set_param(config_name, str(last_sync_id))

        cursor.close()
        conn.close()
        _logger.info("partner update completed successfully!")

