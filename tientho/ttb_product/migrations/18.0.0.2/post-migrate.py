from odoo import api, SUPERUSER_ID, _


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['product.category'].search([('ttb_sequence_id', '=', False), ('category_code', '!=', False)])._create_ttb_sequence()
