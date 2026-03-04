from odoo import api, fields, models, _
from odoo import tools
import logging
_logger = logging.getLogger(__name__)
from odoo.exceptions import UserError
from collections import defaultdict

import traceback

class TtbPosInvoice(models.Model):
    _name = 'ttb.pos.invoice'
    _description = 'Hoá đơn POS'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Tên', readonly=True, copy=False, default='Mới')
    date = fields.Date(string='Ngày xuất', default=fields.Date.today, tracking=True)
    user_id = fields.Many2one(string='Người xuất', comodel_name='res.users', default=lambda self: self.env.user, tracking=True)
    pos_ids = fields.Many2many(string='Đơn POS xuất hoá đơn', comodel_name='pos.order', help='Cần domain đơn như nào')
    domain_pos_ids = fields.Binary(string='Lọc đơn hàng', compute='_compute_domain_pos_ids')
    picking_id = fields.Many2one(comodel_name='stock.picking', string='Điều chuyển')
    processed_number = fields.Integer('Số đơn đã xử lý')
    success_number = fields.Integer('Số đơn xuất HĐĐT thành công')
    note = fields.Text(string='Ghi chú')
    amount_total = fields.Float(string='Tổng tiền', compute='_compute_amount_total', store=True)

    product_change_ids = fields.One2many(string='Sản phẩm thay thế', comodel_name='ttb.pos.product.invoice.change', inverse_name='pos_change_id')
    product_not_change_ids = fields.One2many(string='Sản phẩm không thay thế', comodel_name='ttb.pos.product.invoice.change', inverse_name='pos_not_change_id')
    product_delete_ids = fields.One2many(string='Sản phẩm xoá', comodel_name='ttb.pos.product.invoice.change', inverse_name='pos_delete_id')
    product_notax_ids = fields.One2many(string='Dòng đơn hàng không thuế', comodel_name='ttb.pos.product.invoice.change', inverse_name='pos_notax_id')
    # product_hastax_ids = fields.One2many(string='Dòng đơn hàng có thuế', comodel_name='ttb.pos.product.invoice.change', inverse_name='pos_hastax_id')

    @api.depends('pos_ids', 'pos_ids.amount_total')
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = sum(rec.pos_ids.mapped('amount_total'))

    @api.depends('state')
    def _compute_domain_pos_ids(self):
        vat_warehouse_ids = self.env['ttb.branch'].with_context(active_test=False).search([]).mapped('vat_warehouse_id')
        for pos in self:
            if pos.state == 'new':
                domain = [('state', '=', 'draft'), ('warehouse_id', 'in', vat_warehouse_ids.ids), '|', ('ttb_einvoice_state', '=', 'new'), ('ttb_einvoice_state', '=', False)]
            else:
                domain = [('id', '=', False)]
            pos.domain_pos_ids = domain

    state = fields.Selection(string='Trạng thái', selection=[
        ('new', 'Mới'),
        ('waiting_approve','Chờ xác nhận'),
        ('waiting', 'Chờ xuất'),
        ('einvoicing', 'Đang xuất'),
        ('done_partial', 'Đã xuất một phần'),
        ('done', 'Đã xuất toàn bộ'),
        # TODO: thêm trạng thái huỷ
        # ('cancel', 'Huỷ'),
    ], default='new', tracking=True)
    show_button_einvoice = fields.Boolean(string='Hiện nút xuất hoá đơn', compute='_compute_show_button_einvoice', store=False)

    def _compute_show_button_einvoice(self):
        for rec in self:
            rec.show_button_einvoice = rec.state in ('waiting', 'done_partial') \
                or ( \
                    rec.state == 'einvoicing' \
                    and rec.einvoice_job_state in ('done', 'cancelled', 'failed') \
                )

    einvoice_job_uuid = fields.Char(string="E-invoice Job UUID", copy=False, readonly=True)
    einvoice_job_state = fields.Selection(
        related='einvoice_job_id.state', # Sử dụng related field để hiển thị trạng thái job
        string="E-invoice Job Status",
        readonly=True
    )
    einvoice_job_id = fields.Many2one(
        'queue.job',
        string='E-invoice Job',
        compute='_compute_einvoice_job_id', # Tính toán dựa trên UUID
        store=False, # Không cần lưu, chỉ để hiển thị và truy cập
        readonly=True
    )
    @api.depends('einvoice_job_uuid')
    def _compute_einvoice_job_id(self):
        for record in self:
            if record.einvoice_job_uuid:
                job = self.env['queue.job'].search([('uuid', '=', record.einvoice_job_uuid)], limit=1)
                record.einvoice_job_id = job.id
            else:
                record.einvoice_job_id = False


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name', False) == 'Mới':
                vals['name'] = self.env['ir.sequence'].next_by_code('seg.ttb.pos.invoice')
        results = super().create(vals_list)
        for rec in results:
            if not rec.pos_ids:
                raise UserError('Chưa chọn đơn hàng')

        return results

    # Hàm này không dùng tới nữa
    # def process_line_notax(self):
    #     for pos in self.pos_ids:
    #         for line in pos.lines:
    #             if not line.tax_ids:
    #                 self.env['ttb.pos.product.invoice.change'].create({
    #                     'pos_notax_id': self.id,
    #                     'pos_id': pos.id,
    #                     'pos_line_id': line.id,
    #                     'product_origin_id': line.product_id.id,
    #                     'qty_origin': line.qty,
    #                     'origin_product_price': line.price_unit,
    #                 })
                # else:
                #     self.env['ttb.pos.product.invoice.change'].create({
                #         'pos_hastax_id': self.id,
                #         'pos_id': pos.id,
                #         'pos_line_id': line.id,
                #         'product_origin_id': line.product_id.id,
                #         'qty_origin': line.qty,
                #         'origin_product_price': line.price_unit,
                #         'tax_ids': line.tax_ids.ids
                #     })


    # Hàm này chỉ dùng cho xuất hoá đơn tiền mặt, còn chuyển khoản đã dùng hàm button_ready_auto
    def button_ready(self):
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        augges_no_tk = IrConfigParameter.get_param('ttb_purchase_invoice_stock.augges_no_tk') or '11220'

        for rec in self:
            pos_state = list(set(rec.pos_ids.mapped('state')))
            if any(state not in ['draft', 'paid'] for state in pos_state):
                raise UserError('Chỉ được chọn các đơn hàng có trạng thái mới, đã thanh toán. Vui lòng kiểm tra lại')
            
            # Xoá các dòng 0đ
            remove_pos_ids = []
            for pos in rec.pos_ids:
                if pos.amount_total <= 1:
                    remove_pos_ids.append((3, pos.id))
                    continue
                has_remove = False
                for line in pos.lines:
                    if line.price_unit <= 1 or line.price_subtotal <= 1:
                        line.unlink()
                        has_remove = True
                if has_remove:
                    pos._compute_prices()

                if pos.amount_total <= 1:
                    remove_pos_ids.append((3, pos.id))
            
            if remove_pos_ids:
                rec.write({'pos_ids': remove_pos_ids})

            # Hàm Thiện 1
            result_lines = rec.action_compute_stock_reserve()
            # Hàm Thiện 2
            rec.process_product_substitution(result_lines)

            # rec.process_line_notax()

            #Xoá tồn luôn đối với đơn tiền mặt
            pos_order = rec.pos_ids.filtered(lambda pos: not pos.is_personalized_invoice and pos.augges_no_tk != augges_no_tk)
            for pos in pos_order:
                for line in pos.lines:
                    free_qty = line.product_id.with_context(location=pos.warehouse_id.lot_stock_id.id).free_qty
                    if free_qty <= 0:
                        self.env['ttb.pos.product.invoice.change'].create({
                            'pos_id': pos.id,
                            'product_origin_id': line.product_id.id,
                            'qty_origin': line.qty,
                            'qty_needed': line.qty,
                            'pos_delete_id': self.id,
                        })
                        line.with_context(allow_delete=True).unlink()
                    elif free_qty < line.qty and free_qty > 0:
                        self.env['ttb.pos.product.invoice.change'].create({
                            'pos_id': pos.id,
                            'product_origin_id': line.product_id.id,
                            'qty_origin': line.qty,
                            'qty_needed': line.qty - free_qty,
                            'pos_delete_id': self.id,
                        })
                        line.write({'qty': free_qty})
                        line._onchange_amount_line_all()
                pos._compute_prices()
            rec.write({'state': 'waiting_approve'})
            

    def button_done(self):
        augges_no_tk = self.env['ir.config_parameter'].sudo().get_param('ttb_purchase_invoice_stock.augges_no_tk') or '11220'
        
        errors = []
        if any(not line.product_change_id for line in self.product_change_ids) or any(not line.product_change_id for line in self.product_not_change_ids):
            errors.append('Bạn chưa điền sản phẩm thay thế, vui lòng kiểm tra lại.')

        # Kiểm tra thuế:
        if self.product_notax_ids and any(not line.tax_ids for line in self.product_notax_ids):
            errors.append('Có dòng đơn hàng chưa điền thuế, vui lòng kiểm tra lại tab: DS dòng đơn hàng không thuế.')

        if self.product_change_ids and any(not line.change_tax_ids for line in self.product_change_ids):
            errors.append('Có dòng đơn hàng chưa điền thuế, vui lòng kiểm tra lại tab: DS sản phẩm thay thế.')

        if self.product_not_change_ids and any(not line.change_tax_ids for line in self.product_not_change_ids):
            errors.append('Có dòng đơn hàng chưa điền thuế, vui lòng kiểm tra lại tab: DS không tìm thấy sản phẩm thay thế.')
        if errors:
            raise UserError(' '.join(errors))

        # Gán thuế
        # for line in self.product_notax_ids:
        #     pos_line_id = line.pos_line_id
        #     pos_line_id.tax_ids = line.tax_ids
        #     pos_line_id._onchange_amount_line_all()
        #     pos_line_id.order_id._compute_prices()
        # for line in self.product_hastax_ids.filtered(lambda x: x.tax_ids and x.pos_line_id.tax_ids != x.tax_ids):
        #     pos_line_id = line.pos_line_id
        #     pos_line_id.tax_ids = line.tax_ids
        #     pos_line_id._onchange_amount_line_all()
        #     pos_line_id.order_id._compute_prices()
        
        for pos in self.pos_ids:
            if not pos.keep_pos_discount:
                has_discount = False
                for line in pos.lines:
                    if line.discount:
                        has_discount = True
                        price_unit = pos.currency_id.round(line.price_unit - (line.discount * line.price_unit / 100))
                        line.write({'price_unit': price_unit, 'discount': 0})
                        line._onchange_amount_line_all()
                if has_discount:
                    pos._compute_prices()

        all_line = self.product_change_ids + self.product_not_change_ids if self.product_change_ids and self.product_not_change_ids else self.product_change_ids or self.product_not_change_ids
        # order_ids = all_line.mapped('pos_id')
        data = defaultdict(float)
        for line in all_line:
            key = (line.product_change_id, line.location_id)
            data[key] += line.qty_needed
        err = []
        for key, val in data.items():
            available_qty = self.env['stock.quant']._get_available_quantity(key[0], key[1])
            if available_qty < val:
                err.append(key)
        # Tạm thời không check tồn sản phẩm thay thế
        # if err:
        #     raise UserError('Sản phẩm thay thế không đủ tồn, vui lòng kiểm tra lại')
        #Case 1: Xử lý toàn bộ đơn đích danh + nguyên bản:
        personalize_origin_invoice = self.pos_ids.filtered(lambda pos: pos.is_personalized_invoice and pos.is_invoice_origin)
        for origin in personalize_origin_invoice:
            #hủy giữ hàng và tạo picking:
            for picking in origin.reserve_picking_ids:
                picking.action_cancel()
            # origin._create_order_picking()

        # Case 2: Xử lý toàn bộ đơn có thay thế sản phẩm:

        for line in all_line:
            # tax_ids = line.pos_line_id.tax_ids.ids if line.pos_line_id.qty <= line.qty_needed else line.product_change_id.taxes_id.ids
            tax_ids = line.product_change_id.taxes_id.ids
            vals = {
                'name': line.product_change_id.name,
                'product_id': line.product_change_id.id,
                'price_unit': line.pos_line_id.price_unit,
                'price_subtotal': 1,
                'price_subtotal_incl': 1,
                'discount': line.pos_line_id.discount,
                'order_id': line.pos_line_id.order_id.id,
                'qty': line.qty_needed,
                'tax_ids': [(6, 0, tax_ids)],
            }
            new_line = self.env['pos.order.line'].create(vals)
            new_line._onchange_amount_line_all()

            if line.pos_line_id.qty <= line.qty_needed:
                #Nếu số lượng line mà nhỏ hơn số lượng cần tức là phải xóa line, và chỉ thay thế sản phẩm
                line.pos_line_id.with_context(allow_delete=True).unlink()
            else:
                # Nếu số lượng line mà nhỏ hơn số lượng cần thì sinh line thay thế sản phẩm và sửa tồn cần
                line.pos_line_id.write({'qty': line.pos_line_id.qty - line.qty_needed})
                line.pos_line_id._onchange_amount_line_all()

        # Đơn hàng có thay đổi (ví dụ thay đổi thuế) -> Tính toán lại đơn hàng
        if all_line:
            all_line.pos_line_id.order_id._compute_prices()

        #xử lý trường hợp đơn chuyển khoản, đích danh không nguyên bản
        personalize_invoice = self.pos_ids.filtered(lambda pos: (pos.is_personalized_invoice and not pos.is_invoice_origin) or pos.augges_no_tk == augges_no_tk)
        for order in personalize_invoice:
            order._compute_prices()
            for picking in order.reserve_picking_ids:
                picking.action_cancel()
            # order._create_order_picking()
        #Xử lý những đơn tiền mặt (Những đơn còn lại) có tồn bao nhiêu thì xuất bấy nhiêu

        pos_order = self.pos_ids.filtered(lambda pos: pos.id not in personalize_invoice.ids and pos.id not in personalize_origin_invoice.ids)
        self.product_delete_ids = False
        
        # TODO: Đoạn này cần check dữ liệu xem có xảy ra không, và bỏ xử lý này
        for pos in pos_order:
            for line in pos.lines:
                free_qty = line.product_id.with_context(location=pos.warehouse_id.lot_stock_id.id).free_qty
                if free_qty <= 0:
                    self.env['ttb.pos.product.invoice.change'].create({
                            'pos_id': pos.id,
                            'product_origin_id': line.product_id.id,
                            'qty_origin': line.qty,
                            'pos_delete_id': self.id,
                        })
                    line.with_context(allow_delete=True).unlink()
                elif free_qty < line.qty and free_qty > 0:
                    self.env['ttb.pos.product.invoice.change'].create({
                        'pos_id': pos.id,
                        'product_origin_id': line.product_id.id,
                        'qty_origin': line.qty,
                        'qty_needed': line.qty - free_qty,
                        'pos_delete_id': self.id,
                    })
                    line.write({'qty': free_qty})
                    line._onchange_amount_line_all()
            pos._compute_prices()
            # pos._create_order_picking()

        self.apply_tax_and_stock()

        self.write({'state': 'waiting'})

    def button_cancel(self):
        for pos in self.pos_ids:
            for picking in pos.reserve_picking_ids:
                picking.action_cancel()
        self.write({'state': 'new'})

    def create_public_einvoice(self):
        error = False
        pos_count = len(self.pos_ids)
        _logger.info('Bắt đầu xử lý %s pos' % pos_count)
        i = 0
        self.write({'processed_number': 0, 'success_number': 0})
        self.env.cr.commit()

        payment_methods = {}

        # Không tạo file pdf gắn với hoá đơn
        self = self.with_context(generate_pdf=False)
        success_number = 0
        for pos in self.pos_ids:
            current_error = False
            i += 1
            _logger.info('xử lý pos %s/%s' % (i, pos_count))

            # B1. Thực hiện thanh toán nếu chưa thanh toán
            pos.create_payment_auto(payment_methods)

            # Tạm bỏ điều kiện trạng thái của đơn
            try:
                if pos.state == 'paid' and not pos.account_move:
                    pos.action_pos_order_invoice()

                if not pos.account_move: continue

                invoice_info = {
                    'CusName': pos.partner_name,
                    'CusAddress': pos.partner_address,
                    'CusTaxCode': pos.partner_vat,
                    'EmailDeliver': pos.partner_email,
                } if pos.is_personalized_invoice else {}
                
                # ghi nhận lại hoá đơn tránh trường hợp hệ thống bị rollback thì hoá đơn vẫn gửi sang vnpt nhưng odoo thì lại bị rollback
                # Đặc biệt là tình huống restart server
                # Phía vnpt khá hay khi mà không cho xuất trùng. Nên là không cần xử lý trường hợp 1 đơn hàng gọi api nhiều lần
                self.env.cr.commit()
                old_invoice_state = pos.account_move.ttb_einvoice_state

                # Tách đôi quá trình gọi api. Commit từng phần:
                # pos.account_move.ttb_call_api_einvoice(invoice_info)
                if pos.account_move.ttb_einvoice_state == 'new':
                    pos.account_move.ttb_create_einvoice(invoice_info)
                self.env.cr.commit()
                if pos.account_move.state == 'posted' and pos.account_move.ttb_einvoice_state == 'created':
                    pos.account_move.ttb_publish_einvoice()
                self.env.cr.commit()

                if pos.account_move.ttb_einvoice_state != 'published' or pos.account_move.call_error:
                    pos.write({'ttb_einvoice_message': (pos.ttb_einvoice_message or '') + ' - ' + (pos.account_move.call_error or 'Chưa xuất được hoá đơn điện tử')})
                    current_error = True
                    error = True
                
                if not current_error and pos.account_move.ttb_einvoice_state == 'published':
                    success_number += 1
                    self.success_number = success_number
                self.processed_number = i

                create_bom_outgoing = self.env['ir.config_parameter'].sudo().get_param('ttb_purchase_invoice_stock.create_bom_outgoing')
                # TODO: Bổ sung trường đánh dấu đã tạo picking trừ tồn NVL hay chưa.
                # Vì Có tình huống tạo xong hoá đơn rồi mà chưa kịp tạo picking trừ tồn NVL. Ví dụ như restart đúng đoạn giữa.
                if create_bom_outgoing and pos.account_move.ttb_einvoice_state == 'published' and old_invoice_state != 'published':
                    self.process_bom_product(pos)
                self.env.cr.commit()
            except Exception as e:
                self.env.cr.rollback()
                error_detail = traceback.format_exc()  # Lấy toàn bộ traceback dưới dạng chuỗi
                pos.write({'ttb_einvoice_message': (pos.ttb_einvoice_message or '') + '\n---\n' + error_detail})
                _logger.info("Einvoice error: %s", error_detail)
                self.processed_number = i
                self.env.cr.commit()
                error = True
        self.processed_number = len(self.pos_ids)

        if all(pos.amount_total == 0 or pos.account_move.ttb_einvoice_state == 'published' for pos in self.pos_ids):
            self.state = 'done'
        else:
            self.state = 'done_partial'

    def button_create_public_einvoice(self):
        self.ensure_one()
        if fields.Date.today() != self.date:
            raise UserError('Ngày xuất không phải ngày hiện tại. Nếu muốn xuất hoá đơn cho phiếu này, hãy sửa Ngày xuất thành %s (sau đó có thể sửa lại như cũ)' % fields.Date.today())
        if self.show_button_einvoice:
            self.state = 'einvoicing'
            job_delayed = self.with_delay(description='Xuất HĐĐT: %s, id=%s'%(self.name,self.id)).create_public_einvoice()
            # Lấy UUID của job và lưu lại
            if job_delayed and hasattr(job_delayed, 'uuid'):
                self.einvoice_job_uuid = job_delayed.uuid
            else:
                # Xử lý trường hợp không lấy được job (ví dụ: queue_job chưa được cài đặt đúng)
                # Hoặc nếu with_delay được gọi trong một ngữ cảnh không tạo job ngay
                # (ví dụ: trong một transaction đã rollback)
                _logger.warning("Không thể lấy được UUID của job cho bản ghi %s", self.id)
                self.einvoice_job_uuid = False # Hoặc một giá trị báo lỗi

    def action_compute_stock_reserve(self):
        """
        Tạo ra stock-picking ảo để giữ tồn cho toàn bộ các sản phẩm trong các đơn.
        Thứ tự giữ tồn theo ...
        Sau khi giữ tồn tính toán số lượng thiếu cho các pos order line
        
        Đầu ra: Danh sách line (sản phẩm) kèm số lượng tồn bị thiếu
        [{'pos_line_id': 1, 'location_id': 2, 'qty_to_replace': 3}]

        """

        IrConfig = self.env['ir.config_parameter'].sudo()
        configured_11220 = IrConfig.get_param('ttb_purchase_invoice_stock.augges_no_tk') or '11220'

        Picking = self.env['stock.picking'].with_context(ignore_merge_moves=True)
        PickingType = self.env['stock.picking.type']
        Quant = self.env['stock.quant']

        Picking.search([('reserve_pos_order_id', 'in', self.pos_ids.ids)]).unlink()

        def sorting_key(pos):
            return (
                not (pos.is_personalized_invoice and pos.is_invoice_origin),
                not pos.is_personalized_invoice,
                pos.augges_no_tk != configured_11220
            )
        #Giữ tồn trước cho các đơn không phải tiền mặt
        pos_ids = self.pos_ids.filtered_domain(['|', ('is_personalized_invoice', '=', True), ('augges_no_tk', '=', configured_11220)])
        sorted_pos = pos_ids
        if pos_ids:
            sorted_pos = sorted(pos_ids, key=sorting_key)
        for pos in sorted_pos:
            warehouse = pos.warehouse_id
            location = warehouse.lot_stock_id
            picking_type = PickingType.search([
                ('code', '=', 'internal'),
                ('warehouse_id', '=', warehouse.id)
            ], limit=1)

            move_vals = []

            for line in pos.lines:
                if line.qty:
                    move_vals.append((0, 0, {
                        'name': line.product_id.display_name,
                        'product_id': line.product_id.id,
                        'product_uom_qty': line.qty,
                        'product_uom': line.product_id.uom_id.id,
                        'location_id': location.id,
                        'location_dest_id': location.id,
                        'pos_order_line_id': line.id,
                    }))

            if move_vals:
                picking = Picking.create({
                    'picking_type_id': picking_type.id,
                    'location_id': location.id,
                    'location_dest_id': location.id,
                    'origin': f'POS Reserve for Invoice {pos.name}',
                    'reserve_pos_order_id': pos.id,
                    'move_ids_without_package': move_vals,
                })

                picking.action_confirm()
                picking.action_assign()

        #Đơn đích danh sẽ không có sản phẩm thay thế.
        if pos_ids:
            sorted_pos = self.env['purchase.order']
            personalized = pos_ids.filtered_domain([('is_personalized_invoice', '=', True), ('is_invoice_origin', '=', True)])
            if personalized:
                pos_ids -= personalized
            if pos_ids:
                sorted_pos = sorted(pos_ids, key=sorting_key)

        # Lấy danh sách sản phẩm không thay thế
        no_change_product_ids = {item.product_id.id for item in self.env['ttb.pos.product.no.change'].search([])}
        result_lines = []
        for pos in sorted_pos:
            if pos.is_personalized_invoice and pos.is_invoice_origin:
                continue

            location = pos.warehouse_id.lot_stock_id
            for line in pos.lines:
                if line.product_id.id in no_change_product_ids: continue

                reserved_qty = sum(self.env['stock.move'].search([
                    ('pos_order_line_id', '=', line.id),
                    ('state', 'not in', ['cancel'])
                ]).mapped('quantity'))

                if reserved_qty < line.qty:
                    result_lines.append({
                        'pos_line_id': line.id,
                        'location_id': pos.warehouse_id.lot_stock_id.id,
                        'qty_to_replace': line.qty - reserved_qty
                    })

        def line_sort_key(l):
            pos = self.env['pos.order.line'].browse(l['pos_line_id']).order_id
            return (
                pos.is_personalized_invoice == False,
                pos.augges_no_tk != configured_11220
            )

        result_lines = sorted(result_lines, key=line_sort_key)

        return result_lines


    """
    CODE HÀM:
    Đầu vào: Danh sách Đơn, Sản phẩm, Kho, số lượng thiếu (cần thay thế bằng sản phẩm khác có số lượng tồn đủ so với số lượng thiếu)
    [{'pos_line_id': 1, 'location_id': 2, 'qty_to_replace': 3}]

    Lấy từ hệ thống:
    1. Location, sản phẩm, số lượng tồn sau giữ hàng
    Lấy từ stock.quant trường số lượng sau giữ hàng
    
    Sản phẩm thay thế ở trường product_template.ttb_substitute_product_ids
    ttb_substitute_product_ids là trường one2many tới model ttb.substitute.product
    ttb.substitute.product có các trường:
    priority = fields.Integer(string='Ưu tiên')
    product_id = fields.Many2one(string='Sản phẩm', comodel_name='product.product')
    different = fields.Float(string='Khác biệt')
    product_template_id = fields.Many2one(string='Sản phẩm gốc',comodel_name='product.template')


    Đầu ra:
    Lưu vào bảng:
    class TtbPosProductInvoiceChange(models.Model):
        _name = 'ttb.pos.product.invoice.change'
        _inherit = ['mail.thread', 'mail.activity.mixin']
        _description = 'Xác nhận sản phẩm thay thế'

        pos_id = fields.Many2one(string='Mã đơn', comodel_name='pos.order', related='pos_line_id.order_id')
        pos_line_id = fields.Many2one(string='Chi tiết đơn hàng', comodel_name='pos.order.line')
        product_origin_id = fields.Many2one(string='Sản phẩm', comodel_name='product.product', related='pos_line_id.product_id')
        qty_origin_id = fields.Float(string='Số lượng', related='pos_line_id.qty')
        qty = fields.Float(string='Tồn hiện có')
        product_change_id = fields.Many2one(string='Sản phẩm thay thế', comodel_name='product.product')
        pos_change_id = fields.Many2one(string='Pos sp thay thế', comodel_name='ttb.pos.invoice')
        pos_not_change_id = fields.Many2one(string='Pos sp ko thay thế', comodel_name='ttb.pos.invoice')
        pos_delete_id = fields.Many2one(string='Pos xoá sản phẩm', comodel_name='ttb.pos.invoice')
    Trường hợp tìm thấy sản phẩm thay thế: pos_line_id, pos_change_id là self.id, product_change_id
    Trường hợp không tìm thấy sản phẩm thay thế: pos_line_id, pos_not_change_id là self.id, product_change_id

    """
    def process_product_substitution(self, input_lines):
        """
        Đầu vào: danh sách dict {'pos_line_id', 'location_id', 'qty_to_replace'}
        Đầu ra: tạo record trong ttb.pos.product.invoice.change

        Logic xử lý:
        - Dựa vào bảng sản phẩm thay thế để lấy ra sản phẩm thay thế.
        - Trường hợp không tìm được sản phẩm thay thế thì lưu dữ liệu ra tab riêng
        """
        Quant = self.env['stock.quant']
        PosLine = self.env['pos.order.line']
        ChangeModel = self.env['ttb.pos.product.invoice.change']

        # Xoá dữ liệu liên kết cũ của invoice này
        ChangeModel.search([('pos_change_id', '=', self.id)]).unlink()
        ChangeModel.search([('pos_not_change_id', '=', self.id)]).unlink()

        # Gom tất cả sản phẩm thay thế cần thiết
        all_sub_products = set()
        line_map = {}  # pos_line_id -> product_id
        product_to_subs = {}  # product_id -> list[ttb.substitute.product]

        for line in input_lines:
            pos_line = PosLine.browse(line['pos_line_id'])
            product = pos_line.product_id
            line_map[line['pos_line_id']] = product.id
            # Bổ sung: Chỉ lấy sản phẩm có thuế và sale_ok
            subs = product.product_tmpl_id.ttb_substitute_product_ids.filtered(lambda p: p.product_id.taxes_id and p.product_id.sale_ok).sorted(key=lambda x: x.priority)
            product_to_subs[product.id] = subs
            all_sub_products.update([sub.product_id.id for sub in subs])

        # Lấy tồn kho theo (location_id, product_id)
        location_product_keys = set(
            (line['location_id'], sub.product_id.id)
            for product_id in product_to_subs
            for sub in product_to_subs[product_id]
            for line in input_lines if line_map[line['pos_line_id']] == product_id
        )

        stock_map = defaultdict(float)
        for location_id, product_id in location_product_keys:
            domain = [('product_id', '=', product_id), ('location_id', '=', location_id)]
            qty = sum(Quant.search(domain).mapped('available_quantity'))
            stock_map[(location_id, product_id)] = qty
        quant_use = defaultdict(float)

        # Lấy ra các sản phẩm thay thế cố định
        fix_change_product_ids = {item.product_id.id: item.change_product_id.id for item in self.env['ttb.pos.product.fix.change'].search([])}
        # Bắt đầu xử lý từng dòng
        for line in input_lines:
            pos_line_id = line['pos_line_id']
            location_id = line['location_id']
            qty_to_replace = line['qty_to_replace']

            pos_line = PosLine.browse(pos_line_id)
            product = pos_line.product_id

            # Thay thế cố định
            if pos_line.product_id.id in fix_change_product_ids:
                selected_product = fix_change_product_ids[pos_line.product_id.id]
                quant_use[(location_id, selected_product)] += qty_to_replace
                ChangeModel.create({
                    'pos_id': pos_line.order_id.id,
                    'pos_line_id': pos_line_id,
                    'qty_origin': pos_line.qty,
                    'product_origin_id': product.id,
                    'pos_not_change_id': self.id,
                    'qty_needed': qty_to_replace,
                    'product_change_id': selected_product,
                })

                continue

            subs = product_to_subs.get(product.id, [])
            found_substitute = False
            for sub in subs:
                sub_product_id = sub.product_id.id
                key = (location_id, sub_product_id)
                available = stock_map.get(key, 0)

                if available >= qty_to_replace:
                    # Ghi nhận thay thế
                    ChangeModel.create({
                        'pos_id': pos_line.order_id.id,
                        'pos_line_id': pos_line_id,
                        'product_origin_id': product.id,
                        'qty_origin': pos_line.qty,
                        'product_change_id': sub_product_id,
                        'qty_needed': qty_to_replace,
                        'pos_change_id': self.id,  # Hoặc gán giá trị cụ thể
                    })
                    stock_map[key] -= qty_to_replace
                    quant_use[key] += qty_to_replace
                    found_substitute = True
                    break

            if found_substitute: continue

            # - - - - - - - - - - - - - -
            # Không có sản phẩm thay thế
            # Tiếp tục tìm sản phẩm thay thế dựa theo mch5, độ lệch giá và còn tồn
            # - - - - - - - - - - - - - -

            product_price = pos_line.price_unit
            # quant_use = defaultdict(float)

            # B1: Lấy các quants thỏa mãn tồn và location
            quant_lines = Quant.search([
                ('location_id', '=', location_id),
                ('product_id', '!=', product.id),
                ('quantity', '>=', qty_to_replace),
                ('product_id.list_price', '>=', product_price * 0.85),
                ('product_id.list_price', '<=', product_price * 1.15),
                
                # Thêm điều kiện sản phẩm thay thế phải có thuế và sale_ok (không phải NVL)
                ('product_id.taxes_id', '!=', False),
                ('product_id.sale_ok', '=', True),
            ])

            # B2: Lọc theo điều kiện giá và chuẩn bị sắp xếp
            candidates = []
            for quant in quant_lines:
                p = quant.product_id
                p_price = p.list_price or 0.0
                    
                p_level5 = p.product_tmpl_id.categ_id_level_5.id
                price_diff = abs(p_price - product_price) / product_price if product_price != 0 else 0


                key = (location_id, p.id)
                quant_use_qty = quant_use.get(key, 0)
                if quant.available_quantity - quant_use_qty < qty_to_replace: continue

                candidates.append({
                    'product': p,
                    # 'qty': quant.available_quantity,
                    'same_mch5': p_level5 and p_level5 == product.categ_id_level_5.id,
                    'same_mch4': p.product_tmpl_id.categ_id_level_4.id and p.product_tmpl_id.categ_id_level_4.id == product.categ_id_level_4.id,
                    'same_mch3': p.product_tmpl_id.categ_id_level_3.id and p.product_tmpl_id.categ_id_level_3.id == product.categ_id_level_3.id,
                    'same_mch2': p.product_tmpl_id.categ_id_level_2.id and p.product_tmpl_id.categ_id_level_2.id == product.categ_id_level_2.id,
                    'same_mch1': p.product_tmpl_id.categ_id_level_1.id and p.product_tmpl_id.categ_id_level_1.id == product.categ_id_level_1.id,
                    'price_diff': price_diff,
                })

            # Ưu tiên: cùng MCH5 → giá lệch ít
            sorted_candidates = sorted(candidates, key=lambda x: (not x['same_mch5'], not x['same_mch4'], not x['same_mch3'], not x['same_mch2'], not x['same_mch1'], x['price_diff']))

            selected_product = sorted_candidates[0]['product'].id if sorted_candidates else False

            if selected_product:
                quant_use[(location_id, selected_product)] += qty_to_replace

            ChangeModel.create({
                'pos_id': pos_line.order_id.id,
                'pos_line_id': pos_line_id,
                'qty_origin': pos_line.qty,
                'product_origin_id': product.id,
                'pos_not_change_id': self.id,
                'qty_needed': qty_to_replace,
                'product_change_id': selected_product,
            })


# test_input = [{
#     'pos_line_id': 115326,
#     'location_id': 8,
#     'qty_to_replace': 1.0
# }]
#
# env['ttb.pos.invoice'].browse(20).process_product_substitution(test_input)


    def action_self_product_alternative(self):
        for line in self.product_not_change_ids:
            if not line.product_change_id:
                line.write({'product_change_id': line.product_origin_id.id})
    def action_cheet_waiting_approve(self):
        self.state = 'waiting_approve'

    def action_auto_tax(self):
        product_notax_ids = self.product_notax_ids.filtered(lambda x: not x.tax_ids)
        for line in product_notax_ids:
            product_id = line.product_origin_id.id
            last_line = self.env['ttb.pos.product.invoice.change'].search([('pos_notax_id', '!=', False), ('product_origin_id', '=', product_id), ('tax_ids', '!=', False)], order='id desc', limit=1)
            if last_line:
                line.tax_ids = last_line.tax_ids
        
