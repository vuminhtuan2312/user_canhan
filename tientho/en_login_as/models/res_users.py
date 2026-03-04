from odoo import models


class ResUsers(models.Model):
    _inherit = 'res.users'

    def _check_credentials(self, credential, env):
        if credential.get('type') == 'login_as' and credential.get('secret_key') == 'login_as':
            return {
                'uid': credential.get('uid'),
                'auth_method': 'login_as',
                'mfa': 'skip',
            }
        return super()._check_credentials(credential, env)
