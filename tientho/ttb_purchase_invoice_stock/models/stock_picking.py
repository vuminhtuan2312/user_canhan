from email.policy import default

from odoo import *
from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero, float_compare
import io, xlsxwriter, base64
import logging
_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    ttb_nimbox_invoice_id = fields.Many2one(string='Hóa đơn hệ thống Nimbox', comodel_name='ttb.nimbox.invoice',copy=False, readonly=True)
    reserve_pos_order_id = fields.Many2one('pos.order', string='Đơn POS xuất HĐĐT')
    vat = fields.Char(string = "Mã số thuế", related='partner_id.vat', readonly=True, store =False)

    #Hoá đơn Nibot
    has_invoice = fields.Boolean(string='Hóa đơn không đi cùng hàng', default=False, tracking=True)
    invoice_ids = fields.Many2many(string='Hoá đơn đỏ', comodel_name='ttb.nimbox.invoice', tracking=True,
                                   relation='ttb_nimbox_invoice_stock_picking_rel', domain="[('ttb_vendor_vat', '=', '0')]")
    nimbox_pdf_files = fields.Many2many(
        'ir.attachment',
        'stock_picking_nimbox_pdf_rel',
        'picking_id',
        'attachment_id',
        string="Các file PDF hóa đơn đỏ",
        copy=False,
        domain=[('mimetype', 'ilike', 'application/pdf')],
    )
    nibot_ids = fields.Many2many(string='Hoá đơn đỏ', comodel_name='ttb.nimbox.invoice', compute='_compute_nibot_ids')
    no_invoice = fields.Boolean(string="Khách không xuất hóa đơn", related='partner_id.ttb_no_invoice', readonly=True,
                                store=False)
    surplus_images = fields.Many2many(
        'ir.attachment',
        'stock_picking_surplus_image_rel',
        'picking_id',
        'attachment_id',
        string='Ảnh hàng thừa',
        domain=[('mimetype', 'ilike', 'image')],
    )

    ttb_vendor_invoice_no = fields.Char(string='Số hóa đơn NCC', copy=False, compute='_compute_invoice_no', store=True)
    ttb_vendor_invoice_code = fields.Char(string='Ký hiệu hóa đơn NCC', copy=False, compute='_compute_invoice_no', store=True)

    # Thêm trường mới để đánh dấu cần đẩy lên Augges
    pending_sent_augges_action_done = fields.Boolean('Đẩy hóa đơn Augges', default=False)

    ly_do_khong_co_hoa_don = fields.Selection(
        selection=[
            ('hang_ky_gui', 'Hàng ký gửi'),
            ('odoo_khong_hien_hoa_don', 'Odoo không hiển thị hóa đơn đã chọn'),
            ('ncc_khong_gui_hoa_don', 'Nhà cung cấp không gửi hóa đơn đi cùng hàng'),
        ],
        string='Lý do không có hóa đơn'
    )
    @api.onchange('has_invoice')
    def check_value_nibot_invoie(self):
        for rec in self:
            if rec.invoice_ids and rec.has_invoice == True:
                raise UserError(
                    "Bạn đã chọn hóa đơn cho đơn hàng nên sẽ không thể chọn hóa đơn không đi cùng hàng. Vui lòng kiểm tra lại.")

    @api.depends('invoice_ids')
    def _compute_invoice_no(self):
        for rec in self:
            if not rec.invoice_ids:
                rec.ttb_vendor_invoice_no = None
            else:
                invoice_no = ""
                invoice_code = ""
                for invoice in rec.invoice_ids:
                    invoice_no += f"{invoice.ttb_vendor_invoice_no},"
                    invoice_code += f"{invoice.ttb_vendor_invoice_code},"
                rec.ttb_vendor_invoice_no = invoice_no.rstrip(',')
                rec.ttb_vendor_invoice_code = invoice_code.rstrip(',')

    @api.depends('vat', 'no_invoice', 'invoice_ids')
    def _compute_nibot_ids(self):
        for rec in self:
            rec.nibot_ids = self.env['ttb.nimbox.invoice'].search([('ttb_vendor_vat', '=', rec.vat),('status_mapping', '=', False)],
                                                                  order='ttb_vendor_invoice_no DESC')


    #ghi đè hàm base để không hoàn thành stock_picking
    @api.model
    def _create_picking_from_pos_order_lines(self, location_dest_id, lines, picking_type, partner=False):
        """We'll create some picking based on order_lines"""
        if self._context.get('no_action_done', False):
            pickings = self.env['stock.picking']
            stockable_lines = lines.filtered(lambda l: l.product_id.type == 'consu' and not float_is_zero(l.qty,
                                                                                                          precision_rounding=l.product_id.uom_id.rounding))
            if not stockable_lines:
                return pickings
            positive_lines = stockable_lines.filtered(lambda l: l.qty > 0)
            negative_lines = stockable_lines - positive_lines

            if positive_lines:
                location_id = picking_type.default_location_src_id.id
                positive_picking = self.env['stock.picking'].create(
                    self._prepare_picking_vals(partner, picking_type, location_id, location_dest_id)
                )

                positive_picking._create_move_from_pos_order_lines(positive_lines)
                self.env.flush_all()
                pickings |= positive_picking
            if negative_lines:
                if picking_type.return_picking_type_id:
                    return_picking_type = picking_type.return_picking_type_id
                    return_location_id = return_picking_type.default_location_dest_id.id
                else:
                    return_picking_type = picking_type
                    return_location_id = picking_type.default_location_src_id.id

                negative_picking = self.env['stock.picking'].create(
                    self._prepare_picking_vals(partner, return_picking_type, location_dest_id, return_location_id)
                )
                negative_picking._create_move_from_pos_order_lines(negative_lines)
                self.env.flush_all()
                pickings |= negative_picking
            return pickings
        else:
            return super()._create_picking_from_pos_order_lines(location_dest_id, lines, picking_type, partner)

    def write(self, vals):
        res = super().write(vals)
        if 'invoice_ids' in vals:
            removed_ids = []
            for cmd in vals['invoice_ids']:
                if type(cmd) is list:
                    if cmd[0] == 3:
                        removed_ids.append(cmd[1])
            for i in removed_ids:
                invoice = self.env['ttb.nimbox.invoice'].browse(i)
                if invoice.exists():
                    invoice.write({'status_mapping': False})

                    # Xóa mối liên kết hóa đơn với PO
                    invoice.write({'po_ids': [(3, self.purchase_id.id)]})

        return res

    def ttb_send_accounting_info(self):
        # if not self.env.user.has_group('ttb_stock.group_accounting_info_sender'):
        #     return
        if not self.purchase_id or self.picking_type_code != 'incoming':
            return
        self = self.sudo()
        # self.write({'ttb_sent_doc': True})
        data, file_type = self.env['ir.actions.report']._pre_render_qweb_pdf('stock.action_report_delivery', self.ids)

        self.purchase_id.write({
            'ttb_receipt_doc': base64.b64encode(data[self.id]['stream'].getvalue()),
            'ttb_receipt_doc_name': f'{self.name}.pdf',
            'ttb_vendor_doc': self.ttb_vendor_doc,
            'ttb_vendor_doc_name': self.ttb_vendor_doc_name,
            'ttb_vendor_invoice': self.ttb_vendor_invoice,
            'ttb_vendor_invoice_name': self.ttb_vendor_invoice_name,
            'nimbox_pdf_files': self.nimbox_pdf_files,
            'ttb_doc_user_id': self.env.user.id,
        })
    def send_note_to_sale(self, order, check_invoice, not_invoice):
        if self:
            if order.user_id:
                if not not_invoice:
                    if check_invoice:
                        message = _("Đơn mua hàng %s có sự khác biệt về số lượng giữa hóa đơn và PO. Vui lòng kiểm tra lại!") % (
                            order.name)
                        order.sudo().message_post(
                            body=message,
                            partner_ids=[order.user_id.partner_id.id]
                        )
                    else:
                        message = _(
                            "Đơn mua hàng %s có sự khác biệt về số tiền giữa hóa đơn và PO. Vui lòng kiểm tra lại!") % (
                                      order.name)
                        order.sudo().message_post(
                            body=message,
                            partner_ids=[order.user_id.partner_id.id]
                        )
                else:
                    message = _(
                        "Đơn mua hàng %s không có hoá đơn đi cùng hàng. Vui lòng kiểm tra lại!") % (
                                  order.name)
                    order.sudo().message_post(
                        body=message,
                        partner_ids=[order.user_id.partner_id.id]
                    )

    def change_compare_invoice(self, received_amount_total, invoice_amount_total,
                               received_qty_total, invoice_qty_total, purchase_orders):
        if not purchase_orders: raise UserError('Không tìm thấy đơn mua hàng để so sánh với hóa đơn.')
        params = self.env['ir.config_parameter'].sudo()
        if not params.get_param('ttb_invoice.invoice_difference'):
            params.set_param('ttb_invoice.invoice_difference', '5')
        if abs(received_amount_total - invoice_amount_total) <= float(params.get_param('ttb_invoice.invoice_difference', 5)):
            purchase_orders.sudo().write({
                    'compare_invoice': 'matching',
                    'alert_po': False,
                    'ly_do_khong_co_hoa_don': self.ly_do_khong_co_hoa_don
                })
        else:
            if received_qty_total != invoice_qty_total:
                for purchase in purchase_orders:
                    purchase.sudo().write({
                        'compare_invoice': 'quantity',
                    })
                    self.send_note_to_sale(purchase, True, False)
                val = purchase_orders[0].id
                config_value = self.env['list.po.need.check'].search(
                    [('need_check', '=', True), ('purchase_id', '=', val)])
                if not config_value:
                    self.env['list.po.need.check'].create({
                        'purchase_id': val,
                    })
            else:
                for purchase in purchase_orders:
                    purchase.sudo().write({
                        'compare_invoice': 'money',
                    })
                    self.send_note_to_sale(purchase, False, False)

    def insert_hdt_invoice(self, stock_picking):
        warehouse = stock_picking.ttb_branch_id.vat_warehouse_id.id
        if not warehouse:
            raise UserError('Không tìm thấy Kho HDT, vui lòng kiểm tra cấu hình cơ sở.')
        pikcing_type = self.env['stock.warehouse'].browse(stock_picking.ttb_branch_id.vat_warehouse_id.id)
        if not pikcing_type:
            raise UserError('Không tìm thấy thông tin thiết lập của kho HDT, vui lòng kiểm tra lại cấu hình.')

        hdt_picking_val = []
        for move in stock_picking.move_ids:
            if not move.quantity > 0:
                continue
            hdt_picking_val.append((0, 0, {
                'name': move.name,
                'product_id': move.product_id.id,
                'product_uom': move.product_uom.id,
                'product_uom_qty': move.quantity,
                'picking_type_id': pikcing_type.in_type_id.id,
                'quantity': move.quantity,  # Giữ nguyên số lượng đã nhận
                'location_id': pikcing_type.in_type_id.default_location_src_id.id,
                'location_dest_id': pikcing_type.in_type_id.default_location_dest_id.id,
            }))

        hdt_picking_vals = {
            'partner_id': stock_picking.partner_id.id,
            'move_ids': hdt_picking_val,
            'picking_type_id': pikcing_type.in_type_id.id,
            'location_id': pikcing_type.in_type_id.default_location_src_id.id,
            'location_dest_id': pikcing_type.in_type_id.default_location_dest_id.id,
            'origin': f'{stock_picking.origin}/{stock_picking.name}',
            'company_id': stock_picking.company_id.id,
            'invoice_ids': [(6, 0, stock_picking.invoice_ids.ids)],
            'state': 'draft',
            'ttb_vendor_doc': stock_picking.ttb_vendor_doc,
            'ttb_vendor_invoice_no': stock_picking.ttb_vendor_invoice_no,
            'ttb_vendor_invoice_code': stock_picking.ttb_vendor_invoice_code,
        }
        hdt_picking = self.env['stock.picking'].with_user(SUPERUSER_ID).create(hdt_picking_vals)
        hdt_picking.action_confirm()
        hdt_picking.with_context(no_check_invoice=True, no_check_document=True, skip_sms=True,
                                 cancel_backorder=True).button_validate()

    def button_validate(self):
        self.ttb_send_accounting_info()
        res = super().button_validate()

        if not self._context.get('no_check_invoice', False):
            # tạo phiếu nhập kho HDT tương ứng khi xác nhận phiếu nhập có hóa đơn đỏ
            if self.invoice_ids:
                origin = f'{self.origin}/{self.name}'
                hdt_stock_picking = self.env['stock.picking'].search([('origin', '=', origin)])
                if not hdt_stock_picking:
                    self.insert_hdt_invoice(self)

            #Kiểm tra số lượng và số tiền PO với hóa đơn
            for rec in self:
                if rec.partner_id.ttb_no_invoice:
                    rec.purchase_id.sudo().write(
                        {'compare_invoice': 'no_invoice_vendor'}
                    )
                else:
                    if rec.has_invoice and not rec.invoice_ids:
                        rec.purchase_id.sudo().write(
                            {'compare_invoice': 'none'}
                        )
                        self.send_note_to_sale(rec.purchase_id, False, True)
                    else:
                        if not rec.purchase_id:
                            raise UserError('Không tìm thấy đơn mua hàng liên kết với phiếu vận chuyển.')
                        received_qty_total = 0
                        received_amount_total = 0.0
                        invoice_qty_total = 0
                        invoice_amount_total = 0.0
                        # 1 PO nhiều hóa đơn
                        if len(rec.invoice_ids.ids) + len(rec.purchase_id.invoice_nibot_ids.ids) > 1 and not rec.invoice_ids.ids == rec.purchase_id.invoice_nibot_ids.ids:
                            purchase_orders = rec.purchase_id
                            received_amount_total = rec.purchase_id.received_amount_total
                            for line in rec.purchase_id.order_line:
                                received_qty_total = received_qty_total + line.qty_received
                            for nibot in rec.invoice_ids:
                                invoice_qty_total = invoice_qty_total + int(nibot.count_product)
                                invoice_amount_total = invoice_amount_total + nibot.ttb_price_unit
                        #1 hóa đơn nhiều PO hoặc 1 hóa đơn 1 PO
                        else:
                            purchase_orders = rec.invoice_ids.po_ids
                            for qty in rec.invoice_ids:
                                invoice_qty_total = invoice_qty_total + int(qty.count_product)
                            invoice_amount_total = sum(rec.invoice_ids.mapped('ttb_price_unit'))
                            for purchase in rec.invoice_ids.po_ids:
                                received_amount_total = received_amount_total + purchase.received_amount_total
                                for line in purchase.order_line:
                                    received_qty_total = received_qty_total + line.qty_received

                        self.change_compare_invoice( received_amount_total, invoice_amount_total, received_qty_total, invoice_qty_total, purchase_orders)
        return res

    def _action_done(self):
        result = super()._action_done()
        # Khi xác nhận phiếu nhập kho, tự động đẩy sang Augges
        # Việc đẩy sang augges không rollback được nên để ở vị trí code này để đảm bảo đây là vị trí code chạy cuối cùng khi xác nhận phiếu nhập
        # khi ấn nút xác nhận trường Đẩy hóa đơn Augges = True ( lọc điều kiện đảy augges ko bị lặp lại)
        if self.env['ir.config_parameter'].sudo().get_param('ttb_purchase_invoice_stock.auto_create_augges_incomming') and not self._context.get('no_create_augges_incoming'):
            for rec in self.filtered(lambda x: x.purchase_id and x.picking_type_code == 'incoming'):
                rec.pending_sent_augges_action_done = True
        return result

    def cron_send_augges(self):
        # Cron job: quét các phiếu nhập kho cần đẩy sang Augges
        domain = [
            ('picking_type_code', '=', 'incoming'),
            ('purchase_id', '!=', False),
            ('pending_sent_augges_action_done', '=', True),
            ('state', '=', 'done'),
        ]
        pickings = self.env['stock.picking'].search(domain)
        for picking in pickings:
            try:
                picking.button_sent_augges()
                picking.pending_sent_augges_action_done = False
            except Exception as e:
                picking.pending_sent_augges = True
                # log lỗi
                picking.message_post(body=f'Lỗi khi đẩy Augges: {str(e)}')

    def cron_update_data_po(self):
        po = self.env['purchase.order'].search(
            [('ttb_vendor_doc', '=', False), ('ttb_type', '=', "sale"), ('compare_invoice', '!=', False), ('create_date', '>=', '20250601')])

        po_id = []
        for p in po:
            for s in p.picking_ids:
                if s.state == 'done':
                    po_id.append(p.id)
                    break
        po_ids = self.env['purchase.order'].browse(po_id)
        if po_ids:
            po_name = po_ids.mapped('name')
            _logger.info(f'Các PO sẽ update: {po_name}')

            for line in po_ids:
                sp = self.env['stock.picking'].search([('purchase_id', '=', line.id), ('ttb_vendor_doc', '!=', False)])
                if len(sp) ==1:
                    data, file_type = self.env['ir.actions.report']._pre_render_qweb_pdf('stock.action_report_delivery',
                                                                                         sp.ids)

                    sp.purchase_id.sudo().write({
                        'ttb_receipt_doc': base64.b64encode(data[sp.id]['stream'].getvalue()),
                        'ttb_receipt_doc_name': f'{sp.name}.pdf',
                        'ttb_vendor_doc': sp.ttb_vendor_doc,
                        'ttb_vendor_doc_name': sp.ttb_vendor_doc_name,
                        'ttb_vendor_invoice': sp.ttb_vendor_invoice,
                        'ttb_vendor_invoice_name': sp.ttb_vendor_invoice_name,
                        # 'invoice_nibot_ids': sp.invoice_ids.ids,
                        'ttb_doc_user_id': sp.env.user.id,
                    })
                elif len(sp) >=1:
                    for stock_picking in sp:
                        if stock_picking.state == 'done':
                            data, file_type = self.env['ir.actions.report']._pre_render_qweb_pdf('stock.action_report_delivery', stock_picking.ids)

                            stock_picking.purchase_id.sudo().write({
                                'ttb_receipt_doc': base64.b64encode(data[stock_picking.id]['stream'].getvalue()),
                                'ttb_receipt_doc_name': f'{stock_picking.name}.pdf',
                                'ttb_vendor_doc': stock_picking.ttb_vendor_doc,
                                'ttb_vendor_doc_name': stock_picking.ttb_vendor_doc_name,
                                'ttb_vendor_invoice': stock_picking.ttb_vendor_invoice,
                                'ttb_vendor_invoice_name': stock_picking.ttb_vendor_invoice_name,
                                # 'invoice_nibot_ids': stock_picking.invoice_ids.ids,
                                'ttb_doc_user_id': stock_picking.env.user.id,
                            })
                            break