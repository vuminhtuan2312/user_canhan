from odoo import api, fields, models, _

class PushAuggesConfirmWizard(models.TransientModel):
    _name = 'push.augges.confirm.wizard'
    _description = 'Wizard to confirm pushing pending invoices to Augges'

    message = fields.Text(string="Thông báo", readonly=True, default="Hành động này sẽ đẩy tất cả các hóa đơn đang chờ (bao gồm cả hóa đơn vừa áp dụng) của đơn hàng này lên Augges. Bạn có muốn tiếp tục?")
    purchase_id = fields.Many2one('purchase.order', string="Đơn mua hàng", readonly=True)
    pending_invoice_ids = fields.Many2many('ttb.nimbox.invoice', string="Các hóa đơn sẽ được đẩy", readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super(PushAuggesConfirmWizard, self).default_get(fields_list)
        purchase_id = self.env.context.get('default_purchase_id')
        if purchase_id:
            purchase = self.env['purchase.order'].browse(purchase_id)
            # Tìm tất cả hóa đơn của PO này chưa được đẩy
            invoices_to_push = purchase.invoice_nibot_ids
            res.update({
                'purchase_id': purchase.id,
                'pending_invoice_ids': [(6, 0, invoices_to_push.ids)]
            })
        return res

    def action_confirm_push(self):
        self.ensure_one()
        if self.purchase_id and self.pending_invoice_ids:
            self.purchase_id.picking_ids.update_augges_invoice(
                auto_create=False,
                invoices_to_push=self.pending_invoice_ids.ids
            )
            # Đánh dấu tất cả các hóa đơn vừa được đẩy là đã hoàn thành
            # self.pending_invoice_ids.write({'status_mapping': True})
        return {'type': 'ir.actions.act_window_close'}
