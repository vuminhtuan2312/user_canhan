from odoo import api, models, fields

class BarcodeChangeRequestLine(models.Model):
    _name = 'barcode.change.request.line'
    _description = 'Chi tiết yêu cầu chuyển mã'

    request_id = fields.Many2one('barcode.change.request', required=True, ondelete='cascade')
    product_from_id = fields.Many2one('product.product', string='Tên sản phẩm gốc')
    barcode_from = fields.Char(string='Mã vạch gốc', compute='_compute_barcode_from', store=True)
    product_to_id = fields.Many2one('product.product', string='Tên sản phẩm cần quy đổi')
    barcode_to = fields.Char(string='Mã vạch cần quy đổi', compute='_compute_barcode_to', store=True)
    uom_from = fields.Char(string='Đơn vị gốc', compute='_compute_uom_from', store=True)
    uom_to = fields.Char(string='Đơn vị quy đổi', compute='_compute_uom_to', store=True)
    qty_from = fields.Float(string='Số lượng gốc')
    qty_to = fields.Float(string='Số lượng quy đổi')
    qty_import = fields.Float(string='Số lượng nhập', compute='_compute_qty_import', store=True)
    qty_export = fields.Float(string='Số lượng xuất')
    reason_id = fields.Many2one('barcode.change.reason', string='Lý do', required=True)

    @api.depends('product_from_id', 'product_from_id.barcode')
    def _compute_barcode_from(self):
        for line in self:
            line.barcode_from = line.product_from_id.barcode if line.product_from_id else False

    @api.depends('product_to_id', 'product_to_id.barcode')
    def _compute_barcode_to(self):
        for line in self:
            line.barcode_to = line.product_to_id.barcode if line.product_to_id else False

    @api.depends('product_from_id', 'product_from_id.uom_id', 'product_from_id.uom_id.name')
    def _compute_uom_from(self):
        for line in self:
            line.uom_from = line.product_from_id.uom_id.name if line.product_from_id and line.product_from_id.uom_id else False

    @api.depends('product_to_id', 'product_to_id.uom_id', 'product_to_id.uom_id.name')
    def _compute_uom_to(self):
        for line in self:
            line.uom_to = line.product_to_id.uom_id.name if line.product_to_id and line.product_to_id.uom_id else False

    @api.depends('qty_export', 'qty_to')
    def _compute_qty_import(self):
        for line in self:
            line.qty_import = line.qty_export * line.qty_to

    @api.onchange('product_from_id')
    def _onchange_product_from_id(self):
        """Auto-fill fields from most recent barcode change request with same product"""
        if self.product_from_id:
            previous_line = self.env['barcode.change.request.line'].search([
                ('product_from_id', '=', self.product_from_id.id)
            ], order='id desc', limit=1)

            if previous_line:
                self.product_to_id = previous_line.product_to_id
                self.qty_from = previous_line.qty_from
                self.qty_to = previous_line.qty_to
                self.reason_id = previous_line.reason_id
