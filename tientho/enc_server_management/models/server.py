from odoo import models, fields, api, _, tools
from odoo.exceptions import UserError
import io
import paramiko
import base64
import logging
_logger = logging.getLogger(__name__)


class ServerData(models.Model):
    _name = 'server.data'
    _description = "Cấu hình server"

    name = fields.Char('Tên Server', required=1, copy=False)
    server = fields.Char('URL/IP', required=1, copy=False)
    port = fields.Char('Port', default='22', required=1)
    user = fields.Char('Username', default='root', required=1)
    password = fields.Char('Password', copy=False)
    key_file = fields.Binary("Pkey file")
    file_name = fields.Char("Pkey file name")
    command = fields.Char("Commands", copy=False)

    _sql_constraints = [(
        'server_unique', 'unique(server)',
        'Server must be unique'
    )]

    def ssh_connect(self, test=False):
        if not self.password and not self.key_file:
            raise UserError('Vui lòng cấu hình password hoặc pkey file!')
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        if self.password:
            ssh.connect(hostname=self.server, port=self.port, username=self.user, password=self.password)
        else:
            private_key_file = io.StringIO()
            key = base64.b64decode(self.key_file).decode()
            private_key_file.write(key)
            private_key_file.seek(0)
            private_key = paramiko.RSAKey.from_private_key(private_key_file)
            ssh.connect(hostname=self.server, port=self.port, username=self.user, pkey=private_key)
        if test:
            ssh.close()
            return False
        return ssh

    def test_connection(self):
        """For test server connection"""
        try:
            self.ssh_connect(test=True)
            return self.env['warning_box'].info(title='Success',
                                                message="Connection Test\
                                                Succeeded! Everything seems\
                                                properly set up!")
        except Exception as e:
            _logger.info("Failed to connect to %s.", self.name, exc_info=True)
            raise UserError(_("Connection Test failed: %s") % tools.ustr(e))

    def action_run_command(self):
        command = self.command
        if not command:
            raise UserError('Vui lòng nhập Command!')
        data = ''
        try:
            ssh = self.ssh_connect()
            stdin, stdout, stderr = ssh.exec_command(command)
            data = ''.join(iter(stdout.readline, ""))
            ssh.close()
        except Exception as e:
            _logger.info("Run command failed %s.", self.name, exc_info=True)
            raise UserError(_("Run command failed: %s") % tools.ustr(e))
        if data:
            return {
                'type': 'ir.actions.client',
                'tag': 'run_command_result',
                'params': data,
            }
        else:
            return self.env['warning_box'].info(title='Success', message="Run command successful!")

    def run_command(self, ssh, command):
        feed_password = False
        if self.user != "root":
            command = "sudo -S -p '' %s" % command
            feed_password = self.password is not None and len(self.password) > 0
        stdin, stdout, stderr = ssh.exec_command(command)
        if feed_password:
            stdin.write(self.password + "\n")
            stdin.flush()
        return {
            'out': stdout.readlines(),
            'err': stderr.readlines(),
            'retval': stdout.channel.recv_exit_status()
        }

    def get_wssh_opts(self):
        password = ''
        privatekey = ''
        if self.password:
            password = self.password
        else:
            privatekey = base64.b64decode(self.key_file).decode()
        return {
              'hostname': self.server,
              'port': self.port,
              'username': self.user,
              'password': password,
              'privatekey': privatekey,
              'passphrase': '',
              'totp': ''
        }
