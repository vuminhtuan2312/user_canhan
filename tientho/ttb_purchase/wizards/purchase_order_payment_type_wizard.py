from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PurchaseOrderPaymentTypeWizard(models.TransientModel):
    _name = 'purchase.order.payment.type.wizard'
    _description = 'Wizard chọn hình thức thanh toán'

    payment_type = fields.Selection([
        ('supplier_advance', 'Tạm ứng cho nhà cung cấp'),
        ('supplier_payment', 'Thanh toán/tất toán cho nhà cung cấp')
    ], string='Hình thức thanh toán', required=True)
    purchase_order_ids = fields.Many2many('purchase.order', string='Đơn mua hàng')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get('active_ids'):
            res['purchase_order_ids'] = [(6, 0, self.env.context.get('active_ids'))]
        elif self.env.context.get('active_id'):
            res['purchase_order_ids'] = [(6, 0, [self.env.context.get('active_id')])]
        return res

    def action_confirm_payment_type(self):
        self.ensure_one()
        pos = self.purchase_order_ids

        invalid_pos = pos.filtered(lambda p: p.state not in ('purchase') or p.advance_payment_status)
        if invalid_pos:
            codes = ", ".join(invalid_pos.mapped('name'))
            raise UserError(_("Đang có PO: [%s] đã hoặc đang được xử lý tạm ứng hoặc chưa được duyệt, kiểm tra lại nhé") % codes)

        if not pos:
            raise UserError(_("Vui lòng chọn ít nhất một đơn mua hàng."))

        document_type = self.payment_type

        dept = self.env['hr.department'].search([('name', '=', 'Ngành hàng')], limit=1)

        if document_type == 'supplier_advance':
            content = 'Tạm ứng cho nhà cung cấp'
        else:
            content = 'Thanh toán/tất toán cho nhà cung cấp'
        po_id = pos[0]

        advance_request_vals = {
            'document_type': document_type,
            'request_user_id': self.env.user.id,
            'department_id': dept.id if dept else False,
            'date': fields.Date.context_today(self),
            'content': content,
            'payment_type': 'bank',
            'state': 'draft',
            'supplier_delivery_note': po_id.ttb_vendor_doc or False,
            'warehouse_receipt': po_id.ttb_receipt_doc or False,
            'red_invoice': po_id.invoice_nibot_ids.ids
        }

        advance_request = self.env['advance.request'].create(advance_request_vals)

        line_vals = []
        count = 1
        for po in pos:
            line_vals.append((0, 0, {
                'stt': count,
                'branch_id': po.ttb_branch_id.id if po.ttb_branch_id else False,
                'po_id': po.id,
                'partner_id': po.partner_id.id if po.partner_id else False,
                'description': po.description or po.name,
                'product_category_id': po.product_category_id.id if po.product_category_id else False,
                'amount': po.amount_untaxed,
            }))
            count += 1

            po.write({
                'purchase_order_status': 'advance_payment',
                'advance_payment_status': 'draft'
            })

        advance_request.write({'request_lines': line_vals})

        return {
            'name': _('Phiếu đề nghị tạm ứng'),
            'type': 'ir.actions.act_window',
            'res_model': 'advance.request',
            'res_id': advance_request.id,
            'view_mode': 'form',
            'target': 'current',
        }

