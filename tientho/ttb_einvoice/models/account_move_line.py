# -*- coding: utf-8 -*-
from odoo import api, fields, models

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    ttb_discount_amount = fields.Monetary(
        string='Chiết khấu (số tiền)',
        currency_field='currency_id',
        help='Số tiền chiết khấu chưa thuế cho dòng hóa đơn.'
    )
    ttb_tax_amount = fields.Monetary(
        string='Thuế (số tiền)',
        currency_field='currency_id',
        help='Số tiền thuế của dòng hóa đơn (price_total - price_subtotal).'
    )