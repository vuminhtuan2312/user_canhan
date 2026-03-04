from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = "pos.order"

    id_augges = fields.Integer(string='ID Augges', index=True)
    id_kho_augges = fields.Integer(string='ID Kho Augges')
    id_quay_augges = fields.Char(string='Quầy')
    sp_augges = fields.Char(string='Số phiếu')
    warehouse_id = fields.Many2one(string='Kho hàng', comodel_name='stock.warehouse', related='config_id.warehouse_id', store=True)
    ttb_branch_id = fields.Many2one(string='Cơ sở', comodel_name='ttb.branch', related='config_id.ttb_branch_id', store=True)
    warehouse_origin_id = fields.Many2one(string='Kho hàng gốc', comodel_name='stock.warehouse')
    ttb_branch_origin_id = fields.Many2one(string='Cơ sở gốc', comodel_name='ttb.branch', related='warehouse_origin_id.ttb_branch_id', store=True)
    is_personalized_invoice = fields.Boolean(string='Xuất hoá đơn đích danh')
    partner_name = fields.Char(string='Tên công ty', tracking=True)
    partner_vat = fields.Char(string='Mã số thuế', tracking=True)
    partner_address = fields.Char(string='Địa chỉ công ty', tracking=True)
    partner_email = fields.Char(string='Email', tracking=True)
    partner_phone = fields.Char(string='Số điện thoại', tracking=True)
    is_invoice_origin = fields.Boolean(string='Xuất hoá đơn nguyên bản')
    augges_no_tk = fields.Char(string='Tài khoản')
    keep_pos_discount = fields.Boolean('Giữ chiết khấu', default=True)
    amount_total_avg = fields.Float(string='Trung bình', related='amount_total', aggregator='avg', store=False)
    ttb_einvoice_manual = fields.Boolean('Xuất hoá đơn tay', default=False)

    ttb_total_point_earn = fields.Float(string="Tổng điểm tích", default=0.0)
    ttb_total_point_spent = fields.Float(string="Tổng điểm tiêu", default=0.0)

    ttb_weekday = fields.Selection(
        [
            ('0', 'Thứ 2'),
            ('1', 'Thứ 3'),
            ('2', 'Thứ 4'),
            ('3', 'Thứ 5'),
            ('4', 'Thứ 6'),
            ('5', 'Thứ 7'),
            ('6', 'Chủ nhật'),
        ],
        string='Ngày trong tuần',
        compute='_compute_tt_time_info',
        store=True,
        index=True,
    )
    ttb_hour_of_day = fields.Integer(
        string='Giờ mua',
        compute='_compute_tt_time_info',
        store=True,
        index=True,
    )

    code_qhns = fields.Char(string='Mã đơn vị Quan hệ ngân sách', tracking=True)

    @api.depends('date_order')
    def _compute_tt_time_info(self):
        for order in self:
            if not order.date_order:
                order.ttb_weekday = False
                order.ttb_hour_of_day = False
                continue

            dt_local = fields.Datetime.context_timestamp(order, order.date_order)

            # 0=Thứ 2 … 6=Chủ Nhật
            order.ttb_weekday = str(dt_local.weekday())
            order.ttb_hour_of_day = dt_local.hour

    def confirm_pos_synced(self, from_date='2025-05-01'):
        domain = [('picking_ids', '=', False), ('name', 'not like', 'HDT/'), ('date_order', '>=', from_date)]
        pos_to_create_pickings_from = self.sudo().search(domain, order='date_order asc')
        for pos in pos_to_create_pickings_from:
            _logger.info('Tạo stock picking đơn id: %s', pos.id)
            try:
                # TODO: fix ngày stock.move.line
                pos._create_order_picking()
                self.env.cr.commit()
                _logger.info('Tạo stock picking xong đơn id: %s', pos.id)
            except Exception as e:
                self.env.cr.rollback()
                _logger.info('Tạo stock picking thất bại đơn id: %s', pos.id)

class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    purchase_invoiced_qty = fields.Float(string='Số lượng xuất hóa đơn', readonly=True)
    invoiced_done_qty = fields.Float(string='Số lượng đã xuất hóa đơn', compute='_compute_invoiced_done_qty', store=True)
    ttb_branch_id = fields.Many2one(string='Cơ sở', comodel_name='ttb.branch', related='order_id.ttb_branch_id', store=True)
    invoice_date = fields.Date(string='Ngày xuất hóa đơn')
    augges_no_tk = fields.Char(string='Tài khoản đối ứng doanh thu')
    categ_id_level_1 = fields.Many2one('product.category', string='MCH1', store=True,  related='product_id.product_tmpl_id.categ_id_level_1')
    categ_id_level_2 = fields.Many2one('product.category', string='MCH2', store=True,  related='product_id.product_tmpl_id.categ_id_level_2')
    categ_id_level_3 = fields.Many2one('product.category', string='MCH3', store=True,  related='product_id.product_tmpl_id.categ_id_level_3')
    categ_id_level_4 = fields.Many2one('product.category', string='MCH4', store=True,  related='product_id.product_tmpl_id.categ_id_level_4')
    categ_id_level_5 = fields.Many2one('product.category', string='MCH5', store=True,  related='product_id.product_tmpl_id.categ_id_level_5')

    # Thêm thuộc tính vào trường của base
    order_id = fields.Many2one(auto_join=True)

    ttb_weekday = fields.Selection(
        [
            ('0', 'Thứ 2'),
            ('1', 'Thứ 3'),
            ('2', 'Thứ 4'),
            ('3', 'Thứ 5'),
            ('4', 'Thứ 6'),
            ('5', 'Thứ 7'),
            ('6', 'Chủ nhật'),
        ],
        string='Ngày trong tuần',
        compute='_compute_tt_time_info',
        store=True,
        index=True,
    )
    ttb_hour_of_day = fields.Integer(
        string='Giờ mua',
        compute='_compute_tt_time_info',
        store=True,
        index=True,
    )

    @api.depends('order_id.date_order')
    def _compute_tt_time_info(self):
        for line in self:
            if not line.order_id or not line.order_id.date_order:
                line.ttb_weekday = False
                line.ttb_hour_of_day = False
                continue

            dt_local = fields.Datetime.context_timestamp(line, line.order_id.date_order)

            line.ttb_weekday = str(dt_local.weekday())
            line.ttb_hour_of_day = dt_local.hour

    @api.depends('purchase_invoiced_qty', 'invoice_date')
    def _compute_invoiced_done_qty(self):
        for rec in self:
            rec.invoiced_done_qty = rec.purchase_invoiced_qty if rec.invoice_date else 0

    @api.model
    def get_purchase_invoiced_qty(self, product_id, ttb_branch_id):
        pos_order_line = self.env['pos.order.line'].search([('product_id', '=', product_id.id), ('purchase_invoiced_qty', '>', 0), ('ttb_branch_id', '=', ttb_branch_id.id)])
        pos_order_invoiced_qty = sum(pos_order_line.mapped('purchase_invoiced_qty'))
        purchase_invoice_stock_line = self.env['ttb.purchase.invoice.stock.line'].search([('product_id', '=', product_id.id), ('ttb_branch_id', '=', ttb_branch_id.id)])
        purchase_qty = sum(purchase_invoice_stock_line.mapped('qty'))
        return max(0, purchase_qty - pos_order_invoiced_qty)

    def cron_purchase_invoiced_qty(self, date_from=False, date_to=False, order_ids=[]):
        domain = [('invoice_date', '=', False)]
        if date_from:
            domain.append(('order_id.date_order', '>=', date_from))
        if date_to:
            domain.append(('order_id.date_order', '<=', date_to))
        if order_ids:
            domain.append(('order_id.id', 'in', order_ids))
        self_sudo = self.sudo().search(domain)
        for rec in self_sudo:
            purchase_qty = self.get_purchase_invoiced_qty(rec.product_id, rec.ttb_branch_id)
            purchase_invoiced_qty = max(0, min(purchase_qty, rec.qty))
            rec.write({'purchase_invoiced_qty': purchase_invoiced_qty})

    @api.ondelete(at_uninstall=False)
    def _unlink_except_order_state(self):
        if self._context.get('allow_delete'):
            return
        return super()._unlink_except_order_state()

