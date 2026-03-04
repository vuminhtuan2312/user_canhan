from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    invoice_warehouse_id = fields.Many2one(comodel_name='stock.warehouse', string='Kho hoá đơn')
    invoice_partner_id = fields.Many2one(comodel_name='res.partner', string='Khách lẻ')
    difference_amount = fields.Float(string='Số tiền chênh lệch được phép')
    difference_amount_pos = fields.Float(string='Số tiền chênh lệch đơn pos được phép')
    augges_no_tk = fields.Char(string='Tài khoản chuyển QR')

    auto_create_augges_incomming = fields.Boolean('Tạo phiếu nhập kho Augges khi Xác nhận phiếu nhập kho Odoo', default=False)
    create_bom_outgoing = fields.Boolean('Trừ tồn nguyên vật liệu khi xuất hoá đơn', default=False)
    einvoice_expiration_time_minutes = fields.Integer(string='Thời gian hết hạn yêu cầu HĐĐT (phút)', default=60)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()

        params = self.env['ir.config_parameter'].sudo()
        warehouse_id = params.get_param('ttb_purchase_invoice_stock.invoice_warehouse_id')
        invoice_partner_id = params.get_param('ttb_purchase_invoice_stock.invoice_partner_id')
        difference_amount = params.get_param('ttb_purchase_invoice_stock.difference_amount', 0)
        difference_amount_pos = params.get_param('ttb_purchase_invoice_stock.difference_amount_pos', 0)
        augges_no_tk = params.get_param('ttb_purchase_invoice_stock.augges_no_tk')
        auto_create_augges_incomming = params.get_param('ttb_purchase_invoice_stock.auto_create_augges_incomming')
        create_bom_outgoing = params.get_param('ttb_purchase_invoice_stock.create_bom_outgoing')
        einvoice_expiration_time_minutes = params.get_param('ttb_purchase_invoice_stock.einvoice_expiration_time_minutes')

        res.update(invoice_warehouse_id=int(warehouse_id) if warehouse_id else False,
                   invoice_partner_id=int(invoice_partner_id) if invoice_partner_id else False,
                   difference_amount=float(difference_amount),
                   difference_amount_pos=float(difference_amount_pos),
                   augges_no_tk=augges_no_tk,
                   auto_create_augges_incomming=auto_create_augges_incomming,
                   create_bom_outgoing=create_bom_outgoing,
                   einvoice_expiration_time_minutes= int(einvoice_expiration_time_minutes),
                   )
        return res

    def set_values(self):
        super().set_values()

        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        warehouse_id = IrConfigParameter.get_param('ttb_purchase_invoice_stock.invoice_warehouse_id')
        invoice_partner_id = IrConfigParameter.get_param('ttb_purchase_invoice_stock.invoice_partner_id')
        difference_amount = IrConfigParameter.get_param('ttb_purchase_invoice_stock.difference_amount', 0)
        difference_amount_pos = IrConfigParameter.get_param('ttb_purchase_invoice_stock.difference_amount_pos', 0)
        augges_no_tk = IrConfigParameter.get_param('ttb_purchase_invoice_stock.augges_no_tk')
        auto_create_augges_incomming = IrConfigParameter.get_param('ttb_purchase_invoice_stock.auto_create_augges_incomming')
        create_bom_outgoing = IrConfigParameter.get_param('ttb_purchase_invoice_stock.create_bom_outgoing')
        einvoice_expiration_time_minutes = IrConfigParameter.get_param('ttb_purchase_invoice_stock.einvoice_expiration_time_minutes')

        if (warehouse_id and int(warehouse_id) != self.invoice_warehouse_id.id) or not warehouse_id:
            IrConfigParameter.set_param("ttb_purchase_invoice_stock.invoice_warehouse_id", self.invoice_warehouse_id.id)
        if (invoice_partner_id and int(invoice_partner_id) != self.invoice_partner_id.id) or not invoice_partner_id:
            IrConfigParameter.set_param("ttb_purchase_invoice_stock.invoice_partner_id", self.invoice_partner_id.id)
        if float(difference_amount) != self.difference_amount:
            IrConfigParameter.set_param("ttb_purchase_invoice_stock.difference_amount", self.difference_amount)
        if float(difference_amount_pos) != self.difference_amount_pos:
            IrConfigParameter.set_param("ttb_purchase_invoice_stock.difference_amount_pos", self.difference_amount_pos)
        if float(augges_no_tk) != self.augges_no_tk:
            IrConfigParameter.set_param("ttb_purchase_invoice_stock.augges_no_tk", self.augges_no_tk)
        if bool(auto_create_augges_incomming) != self.auto_create_augges_incomming:
            IrConfigParameter.set_param("ttb_purchase_invoice_stock.auto_create_augges_incomming", self.auto_create_augges_incomming)
        if bool(create_bom_outgoing) != self.create_bom_outgoing:
            IrConfigParameter.set_param("ttb_purchase_invoice_stock.create_bom_outgoing", self.create_bom_outgoing)
        if int(einvoice_expiration_time_minutes) != self.einvoice_expiration_time_minutes:
            IrConfigParameter.set_param("ttb_purchase_invoice_stock.einvoice_expiration_time_minutes", self.einvoice_expiration_time_minutes)
