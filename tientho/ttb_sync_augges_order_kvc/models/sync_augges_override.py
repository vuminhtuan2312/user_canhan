# -*- coding: utf-8 -*-
import datetime
import logging
from odoo import fields, models

_logger = logging.getLogger(__name__)


class TtbSyncAugges(models.Model):
    """Override the existing Augges sync to mark ticket orders and optionally filter SLBLM by Ma_Tong='VE'.

    This class assumes model `ttb.sync.augges` is provided by your existing module (where ttb_sync_augges.py lives).
    """

    _inherit = 'ttb.sync.augges'

    def _map_cashier_user_from_code(self, code):
        """Trả về res.users theo mã NV (LogName) lấy từ Augges."""
        if not code:
            return self.env['res.users'].browse(2)  # Admin

        Users = self.env['res.users'].sudo()

        # 1) thẳng theo login = mã
        user = Users.search([('login', '=', code)], limit=1)
        if user:
            return user
        return self.env['res.users'].browse(2)

    def _ttb_sql_exists_ma_tong_ve(self, ma_tong: str) -> str:
        """SQL fragment to filter SLBLM orders that have at least one SLBLD line whose DmH.Ma_Tong == ma_tong."""
        ma_tong = (ma_tong or 'VE').replace("'", "''")
        return f"""
            AND EXISTS (
                SELECT 1
                FROM SLBLD D
                LEFT JOIN DmH H ON H.ID = D.ID_Hang
                WHERE D.ID = SLBLM.ID
                  AND H.Ma_Tong = '{ma_tong}'
                  AND ISNULL(H.Inactive, 0) = 0
                  AND D.Md NOT IN (2, 7)
            )
        """

    def sync_orders_from_mssql_create(self, *args, **kwargs):

        # If caller explicitly says do not filter, fall back to original implementation.
        force_no_filter = kwargs.pop('ttb_kvc_no_filter', False)
        if force_no_filter:
            return super().sync_orders_from_mssql_create_ngay_in(*args, **kwargs)

        # Pull config
        ma_tong = self.env['ir.config_parameter'].sudo().get_param('ttb_kvc.ma_tong', 'VE')
        exists_sql = self._ttb_sql_exists_ma_tong_ve(ma_tong) if ma_tong else ''

        # We need to patch the SQL inside the method.
        # Strategy: replicate the original method but with EXISTS injected and with extra write flag on pos.order.
        number_sync = kwargs.get('number_sync', 5)
        reset = kwargs.get('reset', False)
        date_from = kwargs.get('date_from', False)
        augges_ids = kwargs.get('augges_ids', False)
        config_name = kwargs.get('config_name', 'mssql.last_synced_order_id')
        sync_hdt = kwargs.get('sync_hdt', True)
        sync_normal = kwargs.get('sync_normal', True)
        create_order = kwargs.get('create_order', True)
        write_order = kwargs.get('write_order', True)
        date_to = kwargs.get('date_to', False)
        id_from = kwargs.get('id_from', False)
        id_to = kwargs.get('id_to', False)
        printed_only = kwargs.get('printed_only', True)
        write_check = kwargs.get('write_check', True)

        conn = self.env['ttb.tools'].get_mssql_connection()
        cursor = conn.cursor()
        last_synced_id = int(self.env['ttb.tools'].get_mssql_config(config_name, '0'))
        max_id = 0 if reset else last_synced_id
        count_sync = 0
        currency_id = self.env.company.currency_id

        warehouse_augges = self.env['stock.warehouse'].search([('code', '=', 'AUG')], limit=1)
        if not warehouse_augges:
            warehouse_augges = self.env['stock.warehouse'].create({'code': 'AUG', 'name': 'Kho AUG'})

        session_id = self.env['pos.session'].sudo().search([
            ('config_id.warehouse_id', '=', warehouse_augges.id),
            ('state', '!=', 'closed')
        ], limit=1)
        if not session_id:
            pos_config = self.env['pos.config'].sudo().search([('warehouse_id', '=', warehouse_augges.id)], limit=1)
            if not pos_config:
                pos_config = self.env['pos.config'].sudo().create({
                    'name': f'POS-{warehouse_augges.display_name}',
                    'warehouse_id': warehouse_augges.id,
                    'picking_type_id': warehouse_augges.pos_type_id.id,
                })
            session_id = self.env['pos.session'].sudo().create({'config_id': pos_config.id})

        invoice_partner_id = self.env['ir.config_parameter'].sudo().get_param('ttb_purchase_invoice_stock.invoice_partner_id')

        while True:
            if number_sync and count_sync > number_sync:
                break
            count_sync += 1

            sql_augges_ids = f"and SLBLM.ID in ({', '.join(str(x) for x in augges_ids)}) " if augges_ids else ''
            sql_id_from = f" AND ID >= {id_from}" if id_from else ""
            sql_id_to = f" AND ID <= {id_to}" if id_to else ""
            sql_date_from = f"and SLBLM.InsertDate >= '{date_from}' " if date_from else ''
            sql_date_to = f"and SLBLM.InsertDate <= '{date_to}' " if date_to else ''

            cursor.execute(f"""SELECT
                               SLBLM.ID, SLBLM.ID_Kho, SLBLM.Sp, SLBLM.Quay, SLBLM.Tien_Hang, SLBLM.Tien_CK, SLBLM.Tien_Giam, SLBLM.Tien_GtGt, SLBLM.InsertDate, dmkho.Ma_kho, SLBLM.Printed,
                               du.LogName AS CashierCode
                               FROM SLBLM
                               LEFT JOIN dmkho on SLBLM.ID_Kho = dmkho.ID
                               LEFT JOIN DmUser du ON du.ID = SLBLM.UserID 
                               WHERE SLBLM.ID > {max_id} and SLBLM.ID_Kho is not null
                               AND SlBlM.InsertDate < DATEADD(SECOND, -10, GETDATE())
                               {sql_augges_ids}
                               {sql_id_from} {sql_id_to}
                               {sql_date_from} {sql_date_to}
                               {exists_sql}
                               ORDER BY SLBLM.ID ASC""")

            columns = [c[0] for c in cursor.description]
            orders = [dict(zip(columns, row)) for row in cursor.fetchall()]
            if not orders:
                break

            for row in orders:
                if not augges_ids:
                    max_id = max(max_id, row['ID'])

                printed = row['Printed']
                if not printed:
                    _logger.info("Đơn pos order chưa Printed: %s", row['ID'])
                    self.env['ttb.sync.augges.pending'].create({
                        'augges_id': row['ID'],
                        'finish_state': 0,
                        'insert_date': row['InsertDate'],
                    })
                    self.env.cr.commit()
                    if printed_only:
                        continue

                insert_date = fields.Datetime.to_datetime(row['InsertDate']) - datetime.timedelta(hours=7)

                # session by warehouse code_augges
                new_session_id = self.env['pos.session']
                ma_kho = row['Ma_kho']
                warehouse = self.env['stock.warehouse'].search([('code_augges', '=', ma_kho)], limit=1)
                if warehouse:
                    new_pos_config = self.env['pos.config'].sudo().search([('warehouse_id', '=', warehouse.id)], limit=1)
                    if not new_pos_config:
                        new_pos_config = self.env['pos.config'].sudo().create({
                            'name': f'POS-{warehouse.display_name}',
                            'warehouse_id': warehouse.id,
                            'picking_type_id': warehouse.pos_type_id.id,
                        })
                    new_session_id = self.env['pos.session'].sudo().search([
                        ('config_id', '=', new_pos_config.id),
                        ('state', '!=', 'closed')
                    ], limit=1)
                    if not new_session_id:
                        new_session_id = self.env['pos.session'].sudo().create({'config_id': new_pos_config.id})
                cashier_code = (row.get('CashierCode') or '').strip()
                cashier_user = self._map_cashier_user_from_code(cashier_code)
                # invoice session
                invoice_session_id = self.env['pos.session']
                invoice_warehouse = warehouse or warehouse_augges
                if invoice_warehouse:
                    invoice_warehouse = invoice_warehouse.ttb_branch_id.vat_warehouse_id
                    if not invoice_warehouse:
                        _logger.info("Không thể đồng bộ đơn do không tìm thấy kho thuế: %s", row['ID'])
                        return
                    invoice_session_id = self.env['pos.session'].sudo().search([
                        ('config_id.warehouse_id', '=', invoice_warehouse.id),
                        ('state', '!=', 'closed')
                    ], limit=1)
                    if not invoice_session_id:
                        invoice_pos_config = self.env['pos.config'].sudo().search([
                            ('warehouse_id', '=', invoice_warehouse.id)
                        ], limit=1)
                        if not invoice_pos_config:
                            invoice_pos_config = self.env['pos.config'].sudo().create({
                                'name': f'POS-{invoice_warehouse.display_name}',
                                'warehouse_id': invoice_warehouse.id,
                                'picking_type_id': invoice_warehouse.pos_type_id.id,
                            })
                        invoice_session_id = self.env['pos.session'].sudo().create({'config_id': invoice_pos_config.id})

                order_data = {
                    'name': f"AUGGES/{row['ID']}/{row['Quay']}/{row['Sp']}",
                    'user_id': cashier_user.id,
                    'session_id': new_session_id.id or session_id.id,
                    'id_augges': int(row['ID']),
                    'id_kho_augges': int(row['ID_Kho']),
                    'id_quay_augges': row['Quay'],
                    'sp_augges': row['Sp'],
                    'amount_tax': float(row['Tien_GtGt']),
                    'amount_paid': float(row['Tien_Hang']) - float(row.get('Tien_Ck', 0)) - float(row.get('Tien_Giam', 0)),
                    'amount_total': float(row['Tien_Hang']) - float(row.get('Tien_Ck', 0)) - float(row.get('Tien_Giam', 0)),
                    'amount_return': 0,
                    'currency_id': currency_id.id,
                    'state': 'done',
                    'date_order': insert_date.strftime('%Y-%m-%d %H:%M:%S'),
                }

                invoice_order_data = {
                    'name': f"HDT/{row['ID']}/{row['Quay']}/{row['Sp']}",
                    'user_id': cashier_user.id,
                    'warehouse_origin_id': warehouse.id or warehouse_augges.id,
                    'partner_id': int(invoice_partner_id) if invoice_partner_id else False,
                    'session_id': invoice_session_id.id,
                    'id_augges': int(row['ID']),
                    'id_kho_augges': int(row['ID_Kho']),
                    'id_quay_augges': row['Quay'],
                    'sp_augges': row['Sp'],
                    'amount_tax': float(row['Tien_GtGt']),
                    'amount_paid': float(row['Tien_Hang']) - float(row.get('Tien_Ck', 0)) - float(row.get('Tien_Giam', 0)),
                    'amount_total': float(row['Tien_Hang']) - float(row.get('Tien_Ck', 0)) - float(row.get('Tien_Giam', 0)),
                    'amount_return': 0,
                    'currency_id': currency_id.id,
                    'state': 'draft',
                    'date_order': insert_date.strftime('%Y-%m-%d %H:%M:%S'),
                }

                # Normal order
                if sync_normal:
                    existing = self.env['pos.order'].sudo().with_context(active_test=False).search([
                        ('id_augges', '=', row['ID']),
                        ('warehouse_origin_id', '=', False)
                    ], limit=1)

                    if not existing and create_order:
                        new_order = self.env['pos.order'].sudo().create(self.get_lines(order_data, cursor, row['ID'], tien_hang=float(row['Tien_Hang'])))
                        new_order.write({'ttb_is_ve_order': True})
                        for line in new_order.lines:
                            line._onchange_amount_line_all()
                        new_order._compute_prices()
                        _logger.info('Created new KVC ticket pos order: %s', row['ID'])

                    if existing and write_order:
                        to_write = (not write_check) or (not self.check_ok(float(row['Tien_Hang']), existing.amount_total))
                        if to_write:
                            existing.with_context(allow_delete=True).write(self.get_lines(order_data, cursor, row['ID'], tien_hang=float(row['Tien_Hang'])))
                            existing.write({'ttb_is_ve_order': True})
                            for line in existing.lines:
                                line._onchange_amount_line_all()
                            existing._compute_prices()
                            _logger.info('Write KVC ticket pos order: %s', row['ID'])

                # Invoice order
                if sync_hdt and printed and float(row['Tien_Hang']) > 1:
                    existing_inv = self.env['pos.order'].sudo().with_context(active_test=False).search([
                        ('id_augges', '=', row['ID']),
                        ('warehouse_origin_id', '!=', False)
                    ], limit=1)

                    if not existing_inv and create_order:
                        new_inv = self.env['pos.order'].sudo().create(self.get_lines(invoice_order_data, cursor, row['ID'], tien_hang=float(row['Tien_Hang'])))
                        new_inv.write({'ttb_is_ve_order': True})
                        for line in new_inv.lines:
                            line._onchange_amount_line_all()
                        new_inv._compute_prices()
                        _logger.info('Created new KVC ticket invoice order: %s', row['ID'])

                    if existing_inv and write_order and existing_inv.state == 'draft':
                        existing_inv.with_context(allow_delete=True).write(self.get_lines(invoice_order_data, cursor, row['ID'], tien_hang=float(row['Tien_Hang'])))
                        existing_inv.write({'ttb_is_ve_order': True})
                        for line in existing_inv.lines:
                            line._onchange_amount_line_all()
                        existing_inv._compute_prices()
                        _logger.info('Write KVC ticket invoice order: %s', row['ID'])

            # checkpoint
            if not augges_ids:
                self.env['ttb.tools'].get_mssql_config(config_name, str(max_id))
                conn.commit()

        return True



    def sync_orders_from_mssql_mark_ve_today(self, create_missing: bool = False):
        """Mark today's POS orders as VE (Ma_Tong=VE) based on Augges data.

        This does NOT move any mssql.last_synced_* pointer. It is intended to be run after the full sync
        so that VE orders created by the full sync are marked immediately, without waiting for the VE sync cursor.
        """
        import pytz
        from datetime import timedelta

        ma_tong = self.env['ir.config_parameter'].sudo().get_param('ttb_kvc.ma_tong', 'VE')
        exists_sql = self._ttb_sql_exists_ma_tong_ve(ma_tong) if ma_tong else ''
        if not exists_sql:
            return

        tz = pytz.timezone(self.env.user.tz or "UTC")
        now_utc = fields.Datetime.now().replace(tzinfo=pytz.UTC)
        now_local = now_utc.astimezone(tz)
        start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        end_local = start_local + timedelta(days=1)

        # MSSQL expects local time string; use local datetime string (no tzinfo)
        date_from = start_local.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
        date_to = end_local.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
        return self.sync_orders_from_mssql_mark_ve_range(date_from=date_from, date_to=date_to, create_missing=create_missing)

    def sync_orders_from_mssql_mark_ve_range(self, date_from: str, date_to: str, create_missing: bool = False, limit: int = 10000):
        """Mark POS orders as VE within a date range (InsertDate), without creating duplicates."""
        ma_tong = self.env['ir.config_parameter'].sudo().get_param('ttb_kvc.ma_tong', 'VE')
        exists_sql = self._ttb_sql_exists_ma_tong_ve(ma_tong) if ma_tong else ''
        if not exists_sql:
            return 0

        conn = self.env['ttb.tools'].get_mssql_connection()
        cursor = conn.cursor()

        cursor.execute(f"""SELECT TOP {int(limit)}
                           SLBLM.ID
                           FROM SLBLM
                           WHERE SLBLM.ID_Kho is not null
                           AND SLBLM.InsertDate >= '{date_from}'
                           AND SLBLM.InsertDate < '{date_to}'
                           AND SLBLM.InsertDate < DATEADD(SECOND, -10, GETDATE())
                           {exists_sql}
                           ORDER BY SLBLM.ID ASC""")
        rows = cursor.fetchall()
        ids = [int(r[0]) for r in rows] if rows else []
        cursor.close()
        conn.close()

        if not ids:
            return 0

        # Mark existing orders (normal warehouse_origin_id=False)
        orders = self.env['pos.order'].sudo().with_context(active_test=False).search([
            ('id_augges', 'in', ids),
            ('warehouse_origin_id', '=', False),
        ])
        orders.write({'ttb_is_ve_order': True})

        # If some are missing (should be rare if full sync already ran), optionally create them
        if create_missing:
            existing_ids = set(orders.mapped('id_augges'))
            missing_ids = [i for i in ids if i not in existing_ids]
            if missing_ids:
                _logger.info("[KVC] Creating missing VE orders from augges ids: %s", missing_ids[:50])
                # Create in batches to reuse existing create logic (still no duplicates due to search in create)
                batch_size = 50
                for i in range(0, len(missing_ids), batch_size):
                    self.sync_orders_from_mssql_create(augges_ids=missing_ids[i:i+batch_size])

        return len(ids)
