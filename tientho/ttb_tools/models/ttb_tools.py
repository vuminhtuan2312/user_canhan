from odoo import models, api
from .ttb_tcvn3 import tcvn3_to_unicode, unicode_to_tcvn3
import pyodbc
from odoo.addons.ttb_tools.ai import product_similar_matcher as ai_product
from odoo.addons.ttb_tools.ai import product_category_matcher as ai_pc


class Tools(models.AbstractModel):
    _name = 'ttb.tools'
    _description = 'Tools'
    def lib_ai_product(self):
        return ai_product
        
    def lib_ai_pc(self):
        return ai_pc

    @api.model
    def unicode_to_tcvn3(self, text):
        return unicode_to_tcvn3(text)

    @api.model
    def tcvn3_to_unicode(self, text):
        return tcvn3_to_unicode(text)

    @api.model
    def get_mssql_config(self, key, default_value):
        """Lấy thông số từ ir.config_parameter, nếu không có thì dùng giá trị mặc định"""
        return self.env["ir.config_parameter"].sudo().get_param(key, default_value)

    @api.model
    def get_mssql_connection(self):
        """
            Lấy thông tin kết nối từ MS SQL Config
        """
        return self.env['ttb.mssql.config'].get_active_connection()

    @api.model
    def get_mssql_cursor(self):
        connection = self.get_mssql_connection()
        return connection.cursor()

    @api.model
    def get_mssql_transaction_connection(self):
        """Lấy thông tin kết nối từ System Parameters"""
        server = self.get_mssql_config("mssql.server", "103.157.218.16,52021")
        database = self.get_mssql_config("mssql.database", "MSB_QRCODE")
        username = self.get_mssql_config("mssql.username", "test")
        password = self.get_mssql_config("mssql.password", "TT@2025")
        driver = self.get_mssql_config("mssql.driver", "ODBC Driver 18 for SQL Server")

        conn_str = f"DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password};TrustServerCertificate=yes"
        return pyodbc.connect(conn_str, autocommit=False)

    @api.model
    def get_mssql_connection_send(self):
        """
        Quy về 1 hàm get_mssql_connection
        """
        return self.get_mssql_connection()

    @api.model
    def get_mssql_custom_connection(self, driver='', server='', database='', username='', password=''):
        server = server or self.get_mssql_config("mssql.send_server", False)
        database = database or self.get_mssql_config("mssql.send_database", "AA_augges")
        username = username or self.get_mssql_config("mssql.send_username", False)
        password = password or self.get_mssql_config("mssql.send_password", False)
        driver = driver or self.get_mssql_config("mssql.driver", "ODBC Driver 18 for SQL Server")
        if not server or not username or not password:
            raise UserError(f"Không tìm thấy thông tin server, vui lòng liên hệ với admin để được hỗ trợ")

        conn_str = f"DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password};TrustServerCertificate=yes"
        return pyodbc.connect(conn_str, autocommit=False)
