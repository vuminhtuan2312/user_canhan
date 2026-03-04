# Copyright 2018-2022 Sodexis
# License OPL-1 (See LICENSE file for full copyright and licensing details).

from odoo import fields, models

class Users(models.Model):
    _inherit = 'res.users'

    notification_type = fields.Selection(selection_add=[
        ('both', 'Handle by Emails and in Odoo')
    ], ondelete={'both': 'set default'}
    )
