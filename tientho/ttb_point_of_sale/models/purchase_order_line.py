from odoo import models, fields, api

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    date_order = fields.Datetime(related='order_id.date_order', store=True)
