from odoo import models, fields, api, _


class FtpHost(models.Model):
    _name = 'ftp.host'
    _description = "FTP server"

    name = fields.Char('Tên Server FTP', required=1)
    server = fields.Char('URL/IP', required=1)
    port = fields.Char('Port', default='21', required=1)
    user = fields.Char('Username', default='ftp', required=1)
    password = fields.Char('Password', required=1)
