import odoo
from odoo import api, fields, models
from odoo.http import request
from odoo.modules.registry import Registry
from odoo.exceptions import AccessDenied
from odoo.http import request


import logging
_logger = logging.getLogger(__name__)

class WizardLoginAs(models.TransientModel):
    _name = 'wizard.login_as'
    _description = 'Wizard Login As'
    user_id = fields.Many2one('res.users', required=True)

    def action_login_as(self):
        # # Luồng login của base:
        # # route web/login -> authenticate(session-http.py) -> _login(res_users)

        # # Giải pháp:
        # # Mô phỏng route web/login
        
        _logger.info(f'User {self.env.user.id}-{self.env.user.login} login as {self.user_id.id}-{self.user_id.login}')

        credential = {
            'type': 'login_as',
            'login': self.user_id.login,
            'uid': self.user_id.id,
            'secret_key': 'login_as',
        }
        request.session.authenticate(request.db, credential)
        # request.params['login_success'] = True

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
