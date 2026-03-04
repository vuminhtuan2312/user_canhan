from odoo import models
from odoo.exceptions import UserError

class InventorySessionLine(models.Model):
    _inherit = 'inventory.session.lines'

    def _get_fields_stock_barcode(self):
        return [
            'inventory_session_id',
            'pid_location_id',
        ]

    def _get_fields_stock_barcode(self):
        return [
            'pid_location_id',
            'user_count_id',
            'user_check_id',
        ]
