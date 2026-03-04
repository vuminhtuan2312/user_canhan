from odoo import api, fields, models
from datetime import datetime, date, time, timedelta
import logging
_logger = logging.getLogger(__name__)


class TtbPosInvoiceAuto(models.Model):
    _name = 'ttb.pos.invoice.schedule'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Lịch xuất hoá đơn điện tử tự động'
    _order = 'sequence'
    # _rec_name = 'time_schedule'

    name = fields.Char('Tên lịch', tracking=True)
    time_schedule = fields.Float('Giờ chạy', tracking=True)
    time_from = fields.Float('Giờ tạo đơn from', tracking=True)
    time_to = fields.Float('Giờ tạo đơn to', tracking=True)
    branch_ids = fields.Many2many('ttb.branch', string='Cơ sở', help='Bỏ trống tức là chạy cho tất cả cơ sở')
    enabled = fields.Boolean('Hoạt động', default=True, tracking=True)
    cron_id = fields.Many2one('ir.cron', 'Tác vụ đã lên lịch', tracking=True)
    to_step = fields.Selection([('1', 'Tạo phiếu'), ('2', 'Tạo phiếu -> Tính tồn kho'), ('3', 'Tạo phiếu -> Tính tồn kho -> Xác nhận'), ('4', 'Tạo phiếu -> Tính tồn kho -> Xác nhận -> Xuất hoá đơn')], default='2', tracking=True)
    kvc = fields.Boolean('KVC', help='Xuất hoá đơn Khu vui chơi', default=False, tracking=True)
    get_bank_transfer = fields.Boolean('Chuyển khoản', help='Tạo phiên xuất hoá đơn chuyển khoản', default=True, tracking=True)
    get_cash_transfer = fields.Boolean('Tiền mặt', help='Tạo phiên xuất hoá đơn tiền mặt', default=False, tracking=True)
    note = fields.Text('Ghi chú')
    sequence = fields.Integer('Thứ tự hiển thị')
    khop_tien_mat = fields.Boolean('Khớp tiền mặt 8%', default=False, tracking=True)

    def unlink(self):
        self.cron_id and self.cron_id.unlink()
        return super().unlink()

    def get_nextcall(self):
        hour = int(self.time_schedule)
        minute = int(round((self.time_schedule - hour) * 60))
        today = date.today()
        nextcall = datetime.combine(today, time(hour, minute))

        now = datetime.now()
        if nextcall <= now:
            nextcall += timedelta(days=1)

        nextcall -= timedelta(hours=7)
        return nextcall

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        for rec in res:
            rec.cron_id = self.env['ir.cron'].create({
                'name': 'Xuất hoá đơn điện tử tự động. Thời gian %s -> %s' % (rec.time_from, rec.time_to),
                'model_id': self.env['ir.model']._get_id(self._name),
                'state': 'code',
                'code': f'model.browse({rec.id}).xuat_hddt_tu_dong_schedule()',
                'interval_number': 1,
                'interval_type': 'days',
                'nextcall': rec.get_nextcall(),
                'active': rec.enabled
            })
        return res

    def write(self, vals):
        super().write(vals)
        if 'time_from' in vals or 'time_to' in vals:
            for rec in self:
                rec.cron_id.name = 'Xuất hoá đơn điện tử tự động. Thời gian %s -> %s' % (rec.time_from, rec.time_to)

        if 'time_schedule' in vals or 'enabled' in vals:
            for rec in self:
                cron_vals = {}
                if 'time_schedule' in vals:
                    cron_vals['nextcall'] = rec.get_nextcall()
                if 'enabled' in vals:
                    cron_vals['active'] = rec.enabled

                rec.cron_id.write(cron_vals)


    def xuat_hddt_tu_dong_schedule(self, auto_commit=True):
        _logger.info(f'Xuất HDDT. Bắt đầu thực hiện lịch: {self.name}')
        self = self.with_context(xuat_hddt_time_from = self.time_from, xuat_hddt_time_to = self.time_to)
        branch_ids = self.branch_ids or self.env['ttb.branch'].search([])
        for branch_id in branch_ids:
            _logger.info(f'Xuất HDDT. Bắt đầu thực hiện lịch cho cơ sở: {branch_id.name}')
            try:
                if self.get_bank_transfer:
                    self.env['ttb.pos.invoice'].xuat_hddt_tu_dong(branch_id, to_step=int(self.to_step), kvc=self.kvc, time_from=self.time_from, time_to=self.time_to)
                if self.get_cash_transfer:
                    self.env['ttb.pos.invoice'].xuat_hddt_tu_dong_tien_mat(branch_id, to_step=int(self.to_step), kvc=self.kvc, time_from=self.time_from, time_to=self.time_to, khop_tien_mat=self.khop_tien_mat)
                # self.env['ttb.pos.invoice'].xuat_hddt_tu_dong(to_step=int(self.to_step), kvc=self.kvc)
                if auto_commit:
                    self.env.cr.commit()
            except Exception as e:
                message = f'Lỗi khi Xuất HDDT. Lịch: {self.name}. Cơ sở: {branch_id.name}. Lỗi: {str(e)}'
                _logger.info(message)
                if auto_commit:
                    self.env.cr.rollback()
                self.message_post(body=message)
