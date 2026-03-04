# -*- coding: utf-8 -*-
from odoo import models, fields

class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    ttb_branch_ids = fields.Many2many(
        comodel_name='ttb.branch',
        string='Cơ sở áp dụng',
        help="Các cơ sở áp dụng ca làm việc này"
    )

class ResourceCalendarAttendance(models.Model):
    _inherit = 'resource.calendar.attendance'

    ttb_audit_hour = fields.Float(string='Giờ sinh phiếu hậu kiểm')
