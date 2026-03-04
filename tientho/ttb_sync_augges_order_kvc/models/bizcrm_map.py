# -*- coding: utf-8 -*-
from odoo import fields, models


class TtbBizcrmCustomerMap(models.Model):
    _name = 'ttb.bizcrm.customer.map'
    _description = 'Map khách hàng Odoo <-> BizCRM'
    _rec_name = 'partner_id'
    _order = 'id desc'

    partner_id = fields.Many2one('res.partner', required=True, index=True, ondelete='cascade')
    bizcrm_customer_id = fields.Char(required=True, index=True)
    payload_hash = fields.Char(index=True)
    last_sync_at = fields.Datetime(index=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('uniq_partner', 'unique(partner_id)', 'Khách hàng đã có map BizCRM.'),
    ]


class TtbBizcrmOrderMap(models.Model):
    _name = 'ttb.bizcrm.order.map'
    _description = 'Map pos.order Odoo <-> BizCRM'
    _rec_name = 'order_id'
    _order = 'id desc'

    order_id = fields.Many2one('pos.order', required=True, index=True, ondelete='cascade')
    bizcrm_order_id = fields.Char(required=True, index=True)
    payload_hash = fields.Char(index=True)
    last_sync_at = fields.Datetime(index=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('uniq_order', 'unique(order_id)', 'Đơn hàng đã có map BizCRM.'),
    ]
