# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime, time


class XuatNhapKhoAuggesSyncWizard(models.TransientModel):
    _name = 'ttb.xuat.nhap.kho.augges.sync.wizard'
    _description = 'Wizard đồng bộ Xuất nhập kho Augges'

    date_start = fields.Datetime(string='Ngày bắt đầu', required=True, default=lambda self: datetime.combine(fields.Date.today(), time(0, 0, 0)))
    date_end = fields.Datetime(string='Ngày kết thúc', required=True, default=fields.Datetime.now)
    custom_sql = fields.Text(
        string='SQL tùy chỉnh',
        help='Để trống thì dùng SQL mặc định theo khoảng ngày. Nếu điền, sẽ chạy nguyên câu SQL này (chú ý định dạng cột trùng với báo cáo).'
    )

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for w in self:
            if w.date_start and w.date_end and w.date_end < w.date_start:
                raise UserError('Ngày kết thúc phải sau ngày bắt đầu.')

    def action_sync(self):
        self.ensure_one()
        if self.date_end < self.date_start:
            raise UserError('Ngày kết thúc phải sau ngày bắt đầu.')
        count = self.env['ttb.xuat.nhap.kho'].sudo()._cap_nhat_ton(self.date_start, self.date_end)
        message = 'Đã đồng bộ %s dòng.' % count
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Đồng bộ',
                'message': message,
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.act_window_close',
                },
            }
        }
