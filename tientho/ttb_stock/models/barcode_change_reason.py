from odoo import fields, api, models

class BarcodeChangeReason(models.Model):
    _name = 'barcode.change.reason'
    _description = 'Lý do chuyển mã'
    _rec_name = 'reason'

    name = fields.Char(string='Mã phiếu', required=True, readonly=True, copy=False, default='Mới')
    reason = fields.Char(string='Lý do chuyển mã', required=True)
    note = fields.Text(string='Ghi chú')
    active = fields.Boolean(string='Kích hoạt', default=True, help='Chỉ lý do được kích hoạt mới dùng được')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == 'Mới':
                vals['name'] = self.env['ir.sequence'].next_by_code('barcode.change.reason') or 'Mới'
        return super().create(vals_list)
