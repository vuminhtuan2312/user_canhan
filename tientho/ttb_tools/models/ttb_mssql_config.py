import pyodbc
from odoo import models, fields, api

from odoo.exceptions import UserError
from ..utils.crypto import encrypt, decrypt

class TtbMssqlConfig(models.Model):
    _name = 'ttb.mssql.config'
    _description = 'MSSQL Configuration'
    _rec_name = 'server'
    _order = 'priority asc'

    server = fields.Char(required=True)
    database = fields.Char(string='Database', required=True)
    username = fields.Char(required=True)
    password = fields.Char(
        string='Encrypted Password',
        groups='base.group_system'
    )

    password_input = fields.Char(
        string='Password',
        password=True,
        store=False
    )
    active = fields.Boolean(default=True)
    driver = fields.Char(string='Driver', default='ODBC Driver 18 for SQL Server')
    priority = fields.Integer(default=1)

    @api.model
    def create(self, vals):
        if vals.get('password_input'):
            vals['password'] = encrypt(vals.pop('password_input'))

        return super().create(vals)

    def write(self, vals):
        if vals.get('password_input'):
            vals['password'] = encrypt(vals.pop('password_input'))

        return super().write(vals)

    def get_connection(self, autocommit=False):
        self.ensure_one()

        self = self.sudo()

        password = decrypt(self.password)

        conn_str = (
            f'DRIVER={{{self.driver}}};'
            f'SERVER={self.server};'
            f'DATABASE={self.database};'
            f'UID={self.username};'
            f'PWD={password};'
            f'TrustServerCertificate=yes'
        )
        return pyodbc.connect(conn_str, autocommit=autocommit)

    def get_active_connection(self):
        config = self.sudo().search([('active', '=', True)], order="priority asc", limit=1)
        if not config:
            raise UserError("Không tìm thấy cấu hình MSSQL đang hoạt động")
        return config.get_connection()

    def action_test_connection(self):
        self.ensure_one()
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT 1;")
            cursor.fetchone()

            cursor.close()
            conn.close()
        except Exception as e:
            raise UserError(
                f"Kết nối MSSQL thất bại:\n{str(e)}"
            )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Thành công",
                "message": "Kết nối MSSQL thành công",
                "type": "success",
                "sticky": False,
            },
        }
