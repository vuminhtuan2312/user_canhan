from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AdvanceRequestPrintWizard(models.TransientModel):
    _name = 'advance.request.print.wizard'
    _description = 'Wizard in phiếu tạm ứng'

    print_type = fields.Selection([
        ('import_advance', 'In tạm ứng nhập khẩu'),
        ('import_refund', 'In hoàn ứng nhập khẩu'),
        ('supplier_advance', 'In tạm ứng nhà cung cấp'),
        ('supplier_payment', 'In thanh toán nhà cung cấp')
    ], string='Loại in', required=True)

    advance_request_id = fields.Many2one('advance.request', string='Phiếu tạm ứng')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get('active_id'):
            res['advance_request_id'] = self.env.context.get('active_id')
        return res

    def action_print(self):
        self.ensure_one()

        if not self.advance_request_id:
            raise UserError(_("Không tìm thấy phiếu tạm ứng."))

        if self.print_type == 'import_advance':
            return self.advance_request_id.action_print_advance_request_docx()
        elif self.print_type == 'import_refund':
            return self.advance_request_id.action_print_return_request_docx()
        elif self.print_type == 'supplier_advance':
            return self.advance_request_id.action_print_supplier_advance()
        elif self.print_type == 'supplier_payment':
            return self.advance_request_id.action_print_supplier_payment()

        raise UserError(_("Vui lòng chọn loại in."))

