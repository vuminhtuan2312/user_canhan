from odoo import api, fields, models

class ProductMaster(models.Model):
    _name = 'product.master'
    _description = 'Master data sản phẩm'

    area = fields.Selection(related='product_id.area', string='Khu vực', store=True)
    barcode = fields.Char(string='Mã sản phẩm', related='product_id.barcode', store=True)
    categ_id_level_1 = fields.Many2one('product.category',string='MCH1', related= 'product_id.categ_id_level_1', store=True)
    categ_id_level_2 = fields.Many2one('product.category',string='MCH2', related= 'product_id.categ_id_level_2', store=True)
    categ_id_level_3 = fields.Many2one('product.category',string='MCH3', related= 'product_id.categ_id_level_3', store=True)
    categ_id_level_4 = fields.Many2one('product.category',string='MCH4', related= 'product_id.categ_id_level_4', store=True)
    categ_id_level_5 = fields.Many2one('product.category',string='MCH5', related= 'product_id.categ_id_level_5', store=True)
    supplier_line_ids = fields.One2many(
        'product.master.supplier.line',
        inverse_name='master_id',
        string='Danh sách nhà cung cấp',
    )

    product_id = fields.Many2one(string='Tên hàng', comodel_name='product.template')
    uom_id = fields.Many2one(string='Đơn vị tính', comodel_name='uom.uom', related='product_id.uom_id', store=True)
    list_price = fields.Float(string='Giá bán', related='product_id.list_price', store=True)
    time_start_list_price = fields.Date(string='Thời gian bắt đầu giá bán')
    time_end_list_price = fields.Date(string='Thời gian kết thúc giá bán', default='9999-12-31')
    active = fields.Boolean(string='Active', related='product_id.active', store=True)
    lock_purchase = fields.Boolean(string='Khóa mua')
    lock_sale = fields.Boolean(string='Khóa bán')
    assortment_status = fields.Selection([
        ('in', 'In assortment'),
        ('out', 'Out assortment'),
    ], string='In/Out assortment', default='in')
    season_id = fields.Many2one(comodel_name='season.type', string='Loại mùa vụ', related='product_id.season_type_id', store=True)
    discount_condition = fields.Char(string='Điều kiện chiết khấu')
    @api.depends('product_id')
    def _compute_default_code(self):
        for rec in self:
            rec.default_code = rec.product_id.barcode or rec.product_id.default_code

    @api.onchange('product_id')
    def _onchange_supplier_lines(self):
        for rec in self:
            rec.supplier_line_ids = [(5, 0, 0)]
            if not rec.product_id:
                return

            vals = []
            for seller in rec.product_id.seller_ids:
                vals.append((0, 0, {
                    'partner_id': seller.partner_id.id,
                    'price': seller.price,
                    'time_start_import_price': False,
                    'time_end_import_price': '9999-12-31'
                }))
            rec.supplier_line_ids = vals
