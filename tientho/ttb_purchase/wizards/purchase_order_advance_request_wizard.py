from odoo import models, fields, api, _
from odoo.exceptions import UserError

class PurchaseOrderAdvanceRequestWizard(models.TransientModel):
    _name = 'purchase.order.advance.request.wizard'
    _description = 'Wizard tạo phiếu tạm ứng từ PO'

    purchase_order_ids = fields.Many2many('purchase.order', string='Đơn mua hàng')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get('active_ids'):
            res['purchase_order_ids'] = [(6, 0, self.env.context.get('active_ids'))]
        return res

    def action_create_advance_request(self):
        self.ensure_one()
        pos = self.purchase_order_ids
        
        # 1. Kiểm tra điều kiện
        invalid_pos = pos.filtered(lambda p: p.state not in ('purchase') or p.advance_payment_status)
        if invalid_pos:
            codes = ", ".join(invalid_pos.mapped('name'))
            raise UserError(_("Đang có PO: [%s] đã hoặc đang được xử lý tạm ứng hoặc chưa được duyệt, kiểm tra lại nhé") % codes)

        if not pos:
            raise UserError(_("Vui lòng chọn ít nhất một đơn mua hàng."))

        # 2. Chuẩn bị dữ liệu cho Advance Request
        dept = self.env['hr.department'].search([('name', '=', 'Ngành hàng')], limit=1)
        
        advance_request_vals = {
            'request_user_id': self.env.user.id,
            'department_id': dept.id if dept else False,
            'date': fields.Date.context_today(self),
            'content': 'Tạm ứng hàng nhập khẩu Trung Quốc',
            'payment_type': 'bank',
            'state': 'draft',
        }

        # 3. Tạo Advance Request
        advance_request = self.env['advance.request'].create(advance_request_vals)

        # 4. Tạo Lines
        line_vals = []
        count = 1
        for po in pos:
            line_vals.append((0, 0, {
                'stt': count,
                'branch_id': po.ttb_branch_id.id,
                'po_id': po.id,
                'description': po.description,
                'product_category_id': po.product_category_id.id,
                'amount': po.amount_untaxed,
                'amount_total': po.amount_total,
            }))
            count += 1
            
            # 5. Đồng bộ trạng thái ngược lại PO
            po.write({
                'purchase_order_status': 'advance_payment',
                'advance_payment_status': 'draft'
            })

        advance_request.write({'request_lines': line_vals})

        # 6. Trả về view của phiếu tạm ứng vừa tạo
        return {
            'name': _('Phiếu tạm ứng'),
            'type': 'ir.actions.act_window',
            'res_model': 'advance.request',
            'res_id': advance_request.id,
            'view_mode': 'form',
            'target': 'current',
        }
