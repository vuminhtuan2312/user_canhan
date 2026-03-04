from odoo import fields, models, api
from datetime import datetime, timedelta

class LogQRTransaction(models.Model):
    _name = "log.qr.transaction"
    _description = "Lấy dữ liệu thanh toán QR"
    _order = "created_QR_on DESC"

    id_transaction = fields.Char(string="ID giao dịch", index=True, store=True)
    id_hd = fields.Char(string="ID HD",store=True)
    ma_Hd = fields.Char(string="Mã HD",store=True)
    vacode = fields.Char(store=True)
    mid = fields.Char(string="Merchant ID", store=True)
    tid = fields.Char(string="Terminal ID", store=True)
    account_name = fields.Char(string="Account Name", store=True)
    created_QR_on = fields.Datetime(string="Tạo vào", store=True)
    amount = fields.Float(string="Số tiền", store=True)
    ma_kho = fields.Char(string="Mã kho", store=True)
    state = fields.Selection([
        ('success', 'Thành công'),
        ('fail', 'Không thành công'),
    ], string="Trạng thái", compute="_compute_state", store=True)

    @api.depends('vacode')
    def _compute_state(self):
        for record in self:
            record.state = 'success' if record.vacode else 'fail'

    @api.model
    def sync_qr_transaction(self):
        conn = self.env['ttb.tools'].get_mssql_transaction_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT MIN(CreatedOn) FROM dbo.[Transaction]")
        result = cursor.fetchone()
        start_date_db = result[0] if result else None
        yesterday = datetime.now() - timedelta(days=1)
        start_date = start_date_db.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
        start_str = start_date.strftime('%Y-%m-%d %H:%M:%S')
        end_str = end_date.strftime('%Y-%m-%d %H:%M:%S')
        last_synced_transaction = 'mssql.last_synced_qr_transaction'
        last_synced_id = int(self.env['ttb.tools'].get_mssql_config(last_synced_transaction, 0))
        while True:
            query = f"""
                SELECT TOP 10000
                    TransactionId, ID_Hd, Ma_Hd, mid, tid, accountName, Ma_Kho, CreatedOn, vacode, amount
                FROM dbo.[Transaction]
                WHERE TransactionId > {last_synced_id} AND CreatedOn >= '{start_str}' AND CreatedOn <= '{end_str}'
                ORDER BY TransactionId ASC
            """
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            if not results:
                break
            for row in results:
                transaction_id = row.get('TransactionId')
                existing = self.env['log.qr.transaction'].sudo().search([
                    ('id_transaction', '=', transaction_id)
                ], limit=1)
                if not existing:
                    raw_amount = row.get('amount', 0)
                    try:
                        amount = float(raw_amount)
                    except (ValueError, TypeError):
                        amount = 0.0
                    self.env['log.qr.transaction'].create({
                        'id_transaction': transaction_id,
                        'id_hd': row.get('ID_Hd', '0'),
                        'mid': row.get('mid', '0'),
                        'tid': row.get('tid', ''),
                        'ma_Hd': row.get('Ma_Hd',''),
                        'account_name': row.get('accountName', ''),
                        'ma_kho': row.get('Ma_Kho', ''),
                        'created_QR_on': row.get('CreatedOn'),
                        'vacode': row.get('vacode', 0),
                        'amount': amount,
                    })
                last_synced_id = transaction_id
            self.env['ir.config_parameter'].sudo().set_param(last_synced_transaction, last_synced_id)
            self.env.cr.commit()
        self.env['ir.config_parameter'].sudo().set_param(last_synced_transaction, last_synced_id)
        cursor.close()
        conn.close()

