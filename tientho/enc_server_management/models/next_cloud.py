from odoo import models, fields, api, _


class NextCloudHost(models.Model):
    _name = 'nextcloud.host'
    _description = "NextCloud server"

    name = fields.Char('Tên Server NextCloud', required=1)
    server = fields.Char('URL', required=1)
    dav_path = fields.Char('DAV path', required=1, default='remote.php/dav/files')
    user = fields.Char('Username', default='encupload', required=1)
    password = fields.Char('Password', required=1)
