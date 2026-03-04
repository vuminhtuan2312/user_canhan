# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools, _
import logging
from odoo.exceptions import UserError
_logger = logging.getLogger(__name__)
import time


class ActionUpdate(models.Model):
    _name = 'action.update'
    _description = 'Action Update'

    name = fields.Char('Tên', required=1)
    name_display = fields.Char('Tên', related='name')
    note = fields.Char('Ghi chú')
    server = fields.Many2one('server.data', string="Server", required=1)
    admin_server = fields.Many2one(related='server', string="Admin Server", readonly=0)

    update_command = fields.Text('Update Command', required=True)
    stop_command = fields.Text('Stop Command', required=True)
    restart_command = fields.Text('Restart Command', required=True)
    history_ids = fields.One2many('server.action.history', 'server_id', 'Server Update History')

    active = fields.Boolean('Active', default=True)

    log_file = fields.Char('Log file')
    number_line_log_file = fields.Integer('Số dòng file log', default=15)

    def test_connection(self):
        """For test server connection"""
        return self.server.test_connection()

    def action_update(self):
        self.action_create_log(self.update_command, 'update')
        command = self.update_command + f'& tail -f {self.log_file}'
        return command

    def action_stop(self):
        self.action_create_log(self.stop_command, 'stop')
        command = self.stop_command
        return command

    def action_restart(self):
        self.action_create_log(self.restart_command, 'restart')
        command = self.restart_command
        return command

    def action_create_log(self, command, message):
        if not command:
            raise UserError('Vui lòng nhập Command!')
        self.env['server.action.history'].create({'server_id': self.id, 'state': message})

    def button_view_log_file(self):
        command = f'tail -{self.number_line_log_file}f {self.log_file}'
        return command

    def button_view_one_log_file(self):
        command = f'tail -{self.number_line_log_file} {self.log_file}'
        return command

    def get_wssh_opts(self):
        return self.server.get_wssh_opts()

    def name_get(self):
        result = []
        for rec in self:
            result.append((rec.id, ''))
        return result

    #
    # @api.model
    # def action_view_log_file(self, data_id=False, number=0):
    #     data_id = data_id or self.id
    #     time.sleep(1)
    #     number += 1
    #     if number > 50:
    #         return
    #     print(number)
    #     self = self.browse(data_id)
    #     if not self.log_file:
    #         raise UserError('Vui lòng nhập đường dẫn file log!')
    #     if not (0 < self.number_line_log_file < 1000):
    #         self.number_line_log_file = 10
    #     command = f'tail -{self.number_line_log_file} {self.log_file}'
    #     try:
    #         ssh = self.server.ssh_connect()
    #         stdin, stdout, stderr = ssh.exec_command(command)
    #         data = ''.join(iter(stdout.readline, ""))
    #         ssh.close()
    #     except Exception as e:
    #         _logger.info("Run command failed %s.", self.name, exc_info=True)
    #         raise UserError(_("Run command failed: %s") % tools.ustr(e))
    #     return data, number, data_id


class ServerActionHistory(models.Model):
    _name = 'server.action.history'
    _description = 'Server Action History'
    _rec_name = 'server_id'
    _order = 'create_date desc'

    server_id = fields.Many2one('action.update', 'Server')
    state = fields.Selection([
        ('update', 'Updated'),
        ('stop', 'Stopped'),
        ('restart', 'Restarted')
    ], string='Status')
