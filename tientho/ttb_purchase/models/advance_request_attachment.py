from odoo import models, fields, api, _

class AdvanceRequestAttachment(models.Model):
    _name = 'advance.request.attachment'
    _description = 'File đính kèm tạm ứng'

    advance_request_id = fields.Many2one('advance.request', string='Yêu cầu tạm ứng', required=True, ondelete='cascade')
    attachment_type = fields.Selection([
        ('supplier_payment_bill', 'Bill thanh toán NCC'),
        ('supplier_shipping_bill', 'Bill vận chuyển NCC'),
        ('wire_transfer', 'Điện chuyển tiền'),
        ('goods_inspection', 'Phiếu kiểm hàng'),
        ('goods_receipt', 'Phiếu nhập hàng'),
        ('other', 'Chứng từ khác'),
    ], string='Loại chứng từ', required=True)
    name = fields.Char(string='Tên file', required=True)
    file_data = fields.Binary(string='File', required=True, attachment=True)
    mimetype = fields.Char(string='Định dạng file')

    @api.model
    def create(self, vals):
        if 'name' not in vals or not vals.get('name'):
            attachment_type = vals.get('attachment_type', 'other')
            type_labels = dict(self._fields['attachment_type'].selection)
            vals['name'] = type_labels.get(attachment_type, 'File')
        return super(AdvanceRequestAttachment, self).create(vals)

