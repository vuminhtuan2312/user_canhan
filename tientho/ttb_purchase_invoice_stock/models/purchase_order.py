from odoo import api, fields, models, _
import json
from datetime import timedelta, date, datetime
import logging
_logger = logging.getLogger(__name__)

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    is_purchase_invoice = fields.Boolean(string='Có hóa đơn', default=False, copy=False)
    is_button_confirm_invoice = fields.Boolean(string='Ẩn button xác nhận hóa đơn', compute='_compute_is_button_confirm_invoice')
    is_create_picking = fields.Boolean(string='Đã sinh tồn kho', help='Trường dùng để đánh dấu đã sinh tồn kho cho kho hoá đơn')
    difference_amount = fields.Float('Độ lệch tiền')

    #Hóa đơn, công nợ
    compare_invoice = fields.Selection([('quantity', 'Lệch số lượng'), ('money', "Lệch tiền"), ('no_invoice_vendor', "Nhà cung cấp không xuất hóa đơn"),
                                        ('matching', "Khớp"), ('none', "Hoá đơn không đi cùng hàng")], copy=False, tracking=True,
                                       readonly=True, string="Khớp hóa đơn đỏ", compute='_compute_compare_invoice', store=True,)
    no_invoice = fields.Boolean(string="Khách không xuất hóa đơn", related='partner_id.ttb_no_invoice', readonly=True,
                                store=False)
    vat = fields.Char(string = "Mã số thuế", related='partner_id.vat', readonly=True, store =False)
    invoice_nibot_ids = fields.Many2many(string='Hoá đơn đỏ', comodel_name='ttb.nimbox.invoice', copy=False, tracking=True,
                                   relation='ttb_nimbox_invoice_purchase_rel', domain="[('ttb_vendor_vat', '=', '0')]",)
    nibot_ids = fields.Many2many(string='Hoá đơn đỏ', comodel_name='ttb.nimbox.invoice', compute='_compute_nibot_ids')
    alert_po = fields.Boolean(string='Thông báo', help='Cảnh báo đơn hàng cần xử lý', default=False)
    date_deadline = fields.Date(string='Ngày khớp với hóa đơn đỏ',
                                     help='Ngày hoá đơn được tạo từ Nimbox', compute='_compute_date_invoice_nibot', store=True)
    nimbox_pdf_files = fields.Many2many(
        'ir.attachment',
        'purchase_order_nimbox_pdf_rel',
        'picking_id',
        'attachment_id',
        string="Các file PDF hóa đơn đỏ",
        copy=False,
        domain=[('mimetype', 'ilike', 'application/pdf')])

    notice = fields.Char(string="Ghi chú sai số lượng", help="Thống kê sai lệch số lượng giữa hóa đơn đỏ và nhận hàng thực tế",
                         copy=False, tracking=True)

    ttb_vendor_invoice_date = fields.Date(string='Ngày hóa đơn NCC', copy=False, compute="compute_invoice_date",
                                          readonly=True, store=True)

    ly_do_khong_co_hoa_don = fields.Selection(
        selection=[
            ('hang_ky_gui', 'Hàng ký gửi'),
            ('odoo_khong_hien_hoa_don', 'Odoo không hiển thị hóa đơn đã chọn'),
            ('ncc_khong_gui_hoa_don', 'Nhà cung cấp không gửi hóa đơn đi cùng hàng'),
        ],
        string='Lý do không có hóa đơn'
    )
    @api.depends('invoice_nibot_ids')
    def compute_invoice_date(self):
        for rec in self:
            if not rec.invoice_nibot_ids:
                rec.ttb_vendor_invoice_date = None
            else:
                if not rec.ttb_vendor_invoice_date:
                   rec.ttb_vendor_invoice_date = rec.invoice_nibot_ids[0].ttb_vendor_invoice_date if rec.invoice_nibot_ids and rec.invoice_nibot_ids[0].ttb_vendor_invoice_date else None

    @api.depends('compare_invoice')
    def _compute_date_invoice_nibot(self):
        for rec in self:
            if rec.compare_invoice in ['quantity', 'money', 'none']:
                params = self.env['ir.config_parameter'].sudo()
                deadline = int(params.get_param('ttb_invoice.date_deadline', 3))
                rec.date_deadline = date.today() + timedelta(days=deadline)
            else:
                rec.date_deadline = None

    @api.depends('vat', 'no_invoice')
    def _compute_nibot_ids(self):
        for rec in self:
            rec.nibot_ids = self.env['ttb.nimbox.invoice'].search(
                [('ttb_vendor_vat', '=', rec.vat), ('status_mapping', '=', False)],order='ttb_price_unit DESC')

    @api.depends('is_purchase_invoice', 'order_line', 'order_line.qty_received')
    def _compute_is_button_confirm_invoice(self):
        for rec in self:
            is_button_confirm_invoice = False
            # if self.order_line.filtered_domain([('qty_received', '>', 0)]) and not rec.is_purchase_invoice:
            #     is_button_confirm_invoice = True
            rec.is_button_confirm_invoice = is_button_confirm_invoice

    def button_confirm_purchase_invoice(self):
        for line in self.order_line.filtered_domain([('qty_received', '>', 0)]):
            self.env['ttb.purchase.invoice.stock.line'].create({'name': self.name,
                                                                'ttb_branch_id': self.ttb_branch_id.id,
                                                                'warehouse_id': self.warehouse_id.id,
                                                                'purchase_order_line_id': line.id,
                                                                'product_id': line.product_id.id,
                                                                'qty': line.qty_received,
                                                                })
        self.write({'is_purchase_invoice': True})

    received_amount_total = fields.Monetary(string='Tổng tiền đã nhận', store=True, readonly=True, compute='_compute_received_amount_total')

    @api.depends('order_line.price_subtotal', 'company_id', 'order_line.qty_received')
    def _compute_received_amount_total(self):
        AccountTax = self.env['account.tax']
        for order in self:
            order_lines = order.order_line.filtered(lambda x: not x.display_type)
            base_lines = [line._prepare_base_line_received_for_taxes_computation() for line in order_lines]
            AccountTax._add_tax_details_in_base_lines(base_lines, order.company_id)
            AccountTax._round_base_lines_tax_details(base_lines, order.company_id)
            tax_totals = AccountTax._get_tax_totals_summary(
                base_lines=base_lines,
                currency=order.currency_id or order.company_id.currency_id,
                company=order.company_id,
            )
            order.received_amount_total = tax_totals['total_amount_currency']

    def compare_many_po_one_nimbox(self, nimbox):
        """So trạng thái khớp hoá đơn:
            _ 1 hoá đơn 1 PO
            _ 1 hoá đơn nhiều PO
            """
        received_amount_total = 0
        received_qty_total = 0
        for po in nimbox.po_ids:
            received_amount_total += po.received_amount_total
            for line in po.order_line:
                received_qty_total += line.qty_received
        stock_picking = self.env['stock.picking']
        stock_picking.change_compare_invoice(received_amount_total, nimbox.ttb_price_unit, received_qty_total, int(nimbox.count_product), nimbox.po_ids)

    def compare_one_po_many_nimbox(self, nimbox, purchase_order):
        """So trạng thái khớp hoá đơn:
            _ 1 PO nhiều hoá đơn
            """
        received_amount_total = purchase_order.received_amount_total
        received_qty_total = sum(purchase_order.order_line.mapped('qty_received'))
        invoice_amount_total = sum(nimbox.mapped('ttb_price_unit'))
        invoice_qty_total = sum(int(x) for x in nimbox.mapped('count_product') if x)
        stock_picking = self.env['stock.picking']
        stock_picking.change_compare_invoice(received_amount_total, invoice_amount_total, received_qty_total, invoice_qty_total, purchase_order)


    @api.depends('received_amount_total')
    def _compute_compare_invoice(self):
        # Kiểm tra lại trạng thái khớp hoá đơn khi thay đổi tiền
        for rec in self:
            if rec.invoice_nibot_ids:
                if len(rec.invoice_nibot_ids) == 1:
                    # 1 hoá đơn với 1 PO hoặc nhiều PO
                    self.compare_many_po_one_nimbox(rec.invoice_nibot_ids)
                else:
                    # Nhiều hoá đơn với 1 PO
                    self.compare_one_po_many_nimbox(rec.invoice_nibot_ids, rec)



    ttb_vendor_invoice_no_lstrip = fields.Char(string='Số hoá đơn mã hoá', help='Loại bỏ dấu cách và số 0 ở đầu', compute='_compute_ttb_vendor_invoice_no_lstrip', store=True)

    @api.depends('ttb_vendor_invoice_no')
    def _compute_ttb_vendor_invoice_no_lstrip(self):
        for rec in self:
            if rec.ttb_vendor_invoice_no:
                rec.ttb_vendor_invoice_no_lstrip = rec.ttb_vendor_invoice_no.replace(" ", "").lstrip('0')
            else:
                rec.ttb_vendor_invoice_no_lstrip = False

    ttb_product_ids = fields.Many2many(comodel_name='product.product', string='Sản phẩm', compute='_compute_ttb_product_ids', store=True)
    count_ttb_product = fields.Integer(compute='_compute_ttb_product_ids', string='Tổng sản phẩm', store=True)

    @api.depends('order_line', 'order_line.product_id', 'order_line.qty_received')
    def _compute_ttb_product_ids(self):
        for rec in self:
            productes = rec.order_line.filtered(lambda x: x.qty_received > 0).mapped('product_id')
            rec.ttb_product_ids = productes.ids
            rec.count_ttb_product = len(productes)

    def button_apply_nimbox_invoice(self):
        res_id = self._context.get('res_id', False)
        if res_id:
            nimbox = self.env['ttb.nimbox.invoice'].browse(res_id)
            if nimbox.exists():
                po_ids = self.ids
                if nimbox.po_ids:
                    po_ids = list(set(nimbox.po_ids.ids + po_ids))
                nimbox.write({'po_ids': [(6,0,po_ids)]})

    def fill_invoice_to_stock_picking(self):
        stock_picking = self.env['stock.picking'].search([('origin', '=', self.name)])
        if stock_picking:
            stock_picking.write({
                'invoice_ids': [(6,0,self.invoice_nibot_ids.ids)],
                'has_invoice': False
            })
    def remove_id_from_config(self):
        """
        Xóa PO khỏi danh sách các PO cần check số lượng chênh lệch nếu nó được đổi sang trạng thái khác lệch số lượng
        và đang nằm trong danh sách các PO cần check số lượng chênh lệch
        """
        self.write({
            'notice': None
        })
        config_value = self.env['list.po.need.check'].search([('need_check', '=', True), ('purchase_id', '=', self.id)])
        if config_value:
            config_value.write({
                'need_check': False
            })

    def write(self, vals):
        res = super().write(vals)
        if 'invoice_nibot_ids' in vals:
            removed_ids = []
            for cmd in vals['invoice_nibot_ids']:
                if type(cmd) is list:
                    if cmd[0] == 3:
                        removed_ids.append(cmd[1])
            for i in removed_ids:
                invoice = self.env['ttb.nimbox.invoice'].browse(i)
                if invoice.exists():
                    invoice.write({'status_mapping': False})

                    # Xóa pdf hóa đơn với PO
                    for r in self.nimbox_pdf_files:
                        if r.datas == invoice.pdf_file:
                            r.unlink()

            # đổi trạng thái so sánh hóa đơn
            if len(self.invoice_nibot_ids) == 0:
                self.write({'compare_invoice': None})
            else:
                if len(self.invoice_nibot_ids) == 1:
                    # 1 hoá đơn với 1 PO hoặc nhiều PO
                    self.compare_many_po_one_nimbox(self.invoice_nibot_ids)
                else:
                    # Nhiều hoá đơn với 1 PO
                    self.compare_one_po_many_nimbox(self.invoice_nibot_ids, self)
        for rec in self:
            if rec.compare_invoice == 'none' and rec.invoice_nibot_ids:
                rec.fill_invoice_to_stock_picking()
            if rec.compare_invoice != 'quantity' and 'compare_invoice' in vals:
                rec.remove_id_from_config()

        return res

    def _prepare_invoice(self):
        """Thêm xử lý gán trạng thái khớp hóa đơn đỏ cho hóa đơn, giá trị được lấy từ trạng thái khớp hóa đơn của PO
        """
        self.ensure_one()
        move_type = self._context.get('default_move_type', 'in_invoice')

        partner_invoice = self.env['res.partner'].browse(self.partner_id.address_get(['invoice'])['invoice'])
        partner_bank_id = self.partner_id.commercial_partner_id.bank_ids.filtered_domain(['|', ('company_id', '=', False), ('company_id', '=', self.company_id.id)])[:1]

        invoice_vals = {
            'ref': self.partner_ref or '',
            'move_type': move_type,
            'narration': self.notes,
            'currency_id': self.currency_id.id,
            'partner_id': partner_invoice.id,
            'fiscal_position_id': (self.fiscal_position_id or self.fiscal_position_id._get_fiscal_position(partner_invoice)).id,
            'payment_reference': self.partner_ref or '',
            'partner_bank_id': partner_bank_id.id,
            'invoice_origin': self.name,
            'invoice_payment_term_id': self.payment_term_id.id,
            'invoice_line_ids': [],
            'company_id': self.company_id.id,
            'compare_invoice': self.compare_invoice,
        }
        return invoice_vals

    def _check_alert_po_deadline(self):
        """Cron job: Kiểm tra deadline và set alert cho PO"""
        today = date.today()

        # Lấy tất cả PO có compare_invoice là 'money', 'none' hoặc 'quantity'
        purchase_orders = self.search([
            ('compare_invoice', 'in', ['money', 'quantity', 'none']), ('alert_po', '=', False), ('ttb_type', '=', 'sale'),
            ('partner_id.ttb_show_report', '=', True),
        ])

        po_to_alert = self.browse()
        for po in purchase_orders:
            if po.date_deadline:
                days_remaining = (po.date_deadline - today).days

                if days_remaining <= 1:
                    po_to_alert |= po

        if po_to_alert:
            po_to_alert.write({'alert_po': True})
        _logger.info(f"Cron job completed: {len(po_to_alert)} PO alerted")

    def cron_compare_invoice_po(self):
        purchase_order = self.env['purchase.order'].search([
            ('ttb_vendor_invoice_no', '!=', False), ('create_date', '>=', '2025-06-01 00:00:00'),
        ])
        for nimbox in purchase_order:
            vat_cleaned = nimbox.ttb_vendor_invoice_no.lstrip('0') if nimbox.vat else ''
            nibot = self.env['ttb.nimbox.invoice'].search(
                [('ttb_vendor_invoice_no', '=', vat_cleaned), ('ttb_vendor_vat', '=', nimbox.vat),
                 ('ttb_vendor_invoice_date', '=', nimbox.ttb_vendor_invoice_date),
                 ('ttb_vendor_invoice_code', '=', nimbox.ttb_vendor_invoice_code)], )

            if len(nibot.ids) == 1:
                if nibot:
                    params = self.env['ir.config_parameter'].sudo()
                    if not params.get_param('ttb_invoice.money_difference'):
                        params.set_param('ttb_invoice.money_difference', '50000')
                    money_difference = float(params.get_param('ttb_invoice.money_difference', 50000))
                    invoice_amount_total = nibot.ttb_price_unit
                    invoice_qty_total = nibot.count_product
                    received_qty_total = 0
                    received_amount_total = nimbox.received_amount_total

                    if (invoice_amount_total - money_difference < received_amount_total):
                        nibot.write({'status_mapping': True})

                    for line in nimbox.order_line:
                        received_qty_total = received_qty_total + line.qty_received

                    if not params.get_param('ttb_invoice.invoice_difference'):
                        params.set_param('ttb_invoice.invoice_difference', '5')
                    if abs(received_amount_total - invoice_amount_total) <= float(params.get_param('ttb_invoice.invoice_difference', 5)):
                        nimbox.write({
                            'compare_invoice': 'matching',
                            'invoice_nibot_ids': nibot.ids
                        })
                    else:
                        if received_qty_total != invoice_qty_total:
                            nimbox.write({
                                'compare_invoice': 'quantity',
                                'invoice_nibot_ids': nibot.ids
                            })
                        else:
                            nimbox.write({
                                'compare_invoice': 'money',
                                'invoice_nibot_ids': nibot.ids
                            })
                else:
                    nimbox.write({
                        'compare_invoice': 'none',
                    })

    def check_data_diff_po_invoice(self):
        list_check = self.env['list.po.need.check'].search([('need_check', '=', True)])
        if not list_check:
            _logger.info('Không có PO cần xử lý chênh lệch.')
            return
        list_check_ids = list_check.mapped('purchase_id').ids
        list_check_id = set(list_check_ids)
        invoice = self.env['ttb.nimbox.invoice']
        list_error = []
        for id in list_check_id:
            try:
                purchase = self.env['purchase.order'].search([('id', '=', id), ('compare_invoice', '=', 'quantity')])
                if purchase:
                    _logger.info(f'Xử lý đơn {purchase.name}')
                    if not purchase.invoice_nibot_ids:
                        purchase.write({
                            'notice': 'Đơn hàng không có hóa đơn khi kiểm tra chênh lệch.'
                        })
                        continue
                    if len(purchase.invoice_nibot_ids) > 1:
                        #Nhiều hóa đơn ghép 1 po
                        invoice.compare_quantity_invoice(purchase)
                    else:
                        #Nhiều PO/ 1 PO ghép 1 hóa đơn
                        purchase_ids = purchase.invoice_nibot_ids.po_ids
                        invoice.compare_quantity_invoice(purchase_ids)
                    _logger.info(f'Xử lý xong đơn {purchase.name}')
                else:
                    purchase_other = self.env['purchase.order'].browse(id)
                    _logger.info(f'Đơn hàng {purchase_other.name} có trạng thái khác lệch số lượng.')
            except ValueError as e:
                _logger.error(e)
                list_error.append(id)
        list_check.write({
            'need_check': False,
            'check_date': fields.Datetime.now()
        })
        _logger.info(f'Đã xử lý {len(list_check)} đơn hàng bị lệch số lượng.')
        if list_error:
            _logger.info(f'Các đơn hàng lỗi cần xem xét {list_error}.')

    def push_invoices_po(self):
        _logger.info("Bắt đầu chạy đẩy hóa đơn liên kết với po không đi cùng hàng lên augges")
        # Tìm các PO có trạng thái là 'Hóa đơn không đi cùng hàng' và có hóa đơn liên kết
        unmatched_po = self.search([
            ('compare_invoice', '=', 'none'),
            ('invoice_nibot_ids', '!=', False)
        ])

        if not unmatched_po:
            _logger.info("Không có đơn hàng nào")
            return

        for po in unmatched_po:
            try:
                _logger.info(f"ĐƠn hàng: {po.name}")
                po.picking_ids.update_augges_invoice(auto_create=False, invoices_to_push=po.invoice_nibot_ids)
                _logger.info(f"Đẩy thành công hóa đơn của đơn hàng: {po.name}")
            except Exception as e:
                _logger.error(f"Lỗi đẩy hóa đơn của đơn hàng {po.name}: {e}")
        _logger.info("Kết thúc đẩy hóa đơn liên kết với po không đi cùng hàng lên augges")

    # def update_augges_invoice_info(self):
    #     for picking in self.picking_ids:
    #         if picking.id_augges:
    #             field_update = f"Mau_So='{picking.ttb_vendor_invoice_code}', Ky_Hieu='{picking.ttb_vendor_invoice_code}', So_Ct='{picking.ttb_vendor_invoice_no}'"
    #             self.env['ttb.augges'].update_record('SlNxM', picking.id_augges, field_update)


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _prepare_base_line_received_for_taxes_computation(self):
        self.ensure_one()
        return self.env['account.tax']._prepare_base_line_for_taxes_computation(
            self,
            tax_ids=self.taxes_id,
            quantity=self.qty_received,
            partner_id=self.order_id.partner_id,
            currency_id=self.order_id.currency_id or self.order_id.company_id.currency_id,
            rate=self.order_id.currency_rate,
        )
class TtbBranch(models.Model):
    _inherit = 'ttb.branch'

    purchase_order = fields.One2many('purchase.order', 'ttb_branch_id', string='Đơn hàng mua')
    so_don_khop = fields.Integer(string='Số đơn khớp', compute='_compute_so_don', store=True)
    so_don_lech_tien = fields.Integer(string='Số đơn lệch tiền', compute='_compute_so_don', store=True)
    sotien_khop = fields.Float(string='Số tiền khớp', compute='_compute_so_don', store=True)
    so_don_lech_so_luong = fields.Integer(string='Số đơn lệch số lượng', compute='_compute_so_don', store=True)
    sotien_lechtien = fields.Float(string='Số tiền lệch tiền', compute='_compute_so_don', store=True)
    sotien_lechsoluong = fields.Float(string='Số tiền lệch số lượng', compute='_compute_so_don', store=True)
    so_don_chua_co_hoa_don = fields.Integer(string='Số đơn chưa có hóa đơn', compute='_compute_so_don', store=True, help='Số đơn hàng chưa có hóa đơn')
    sotien_chuacohoadon = fields.Float(string='Số tiền chưa có hóa đơn', compute='_compute_so_don', store=True, help='Số tiền chưa có hóa đơn')
    sodon_alert = fields.Integer(string='Số đơn cần xử lý', compute='_compute_sodon_alert', store=True, help='Số đơn hàng cần xử lý, cảnh báo')
    sotien_alert = fields.Float(string='Số tiền cần xử lý', compute='_compute_sodon_alert', store=True, help='Số tiền cần xử lý, cảnh báo')
    graph_dashboard = fields.Text(compute='_compute_graph_dashboard')

    @api.depends('purchase_order.alert_po')
    def _compute_sodon_alert(self):
        for rec in self:
            rec.sodon_alert = len(rec.purchase_order.filtered(lambda x: x.alert_po == True))
            rec.sotien_alert = sum(rec.purchase_order.filtered(lambda x: x.alert_po == True).mapped('received_amount_total'))

    @api.depends('so_don_khop', 'so_don_lech_tien', 'so_don_lech_so_luong', 'so_don_chua_co_hoa_don')
    def _compute_graph_dashboard(self):
        for rec in self:
            graph_data = [{
                'key': 'Đơn mua hàng',
                'values': [
                    {'label': 'Khớp', 'value': rec.so_don_khop, },
                    {'label': 'Lệch tiền', 'value': rec.so_don_lech_tien,},
                    {'label': 'Lệch số lượng', 'value': rec.so_don_lech_so_luong, },
                    {'label': 'Chưa có hóa đơn', 'value': rec.so_don_chua_co_hoa_don, },
                ],
            }]
            rec.graph_dashboard = json.dumps(graph_data)

    @api.depends('purchase_order.compare_invoice')
    def _compute_so_don(self):
        for rec in self:
            rec.so_don_khop = len(rec.purchase_order.filtered(lambda x: (x.compare_invoice == 'matching'and x.state in ('purchase', 'done') and x.ttb_type == 'sale' and x.partner_id.ttb_show_report == True)
                                                              or (x.compare_invoice == 'matching'and x.invoice_status not in ('invoiced', 'no') and x.ttb_type == 'sale' and x.partner_id.ttb_show_report == True)))
            rec.so_don_lech_tien = len(rec.purchase_order.filtered(lambda x: x.compare_invoice == 'money' and x.ttb_type == 'sale' and x.partner_id.ttb_show_report == True))
            rec.so_don_lech_so_luong = len(rec.purchase_order.filtered(lambda x: x.compare_invoice == 'quantity' and x.ttb_type == 'sale' and x.partner_id.ttb_show_report == True))
            rec.so_don_chua_co_hoa_don = len(rec.purchase_order.filtered(lambda x: x.compare_invoice == 'none' and x.ttb_type == 'sale' and x.partner_id.ttb_show_report == True))
            rec.sotien_khop = sum(rec.purchase_order.filtered(lambda x: (x.compare_invoice == 'matching'and x.state in ('purchase', 'done') and x.ttb_type == 'sale' and x.partner_id.ttb_show_report == True)
                                                              or (x.compare_invoice == 'matching'and x.invoice_status not in ('invoiced', 'no') and x.ttb_type == 'sale' and x.partner_id.ttb_show_report == True)).mapped('received_amount_total'))
            rec.sotien_lechtien = sum(rec.purchase_order.filtered(lambda x: x.compare_invoice == 'money' and x.ttb_type == 'sale' and x.partner_id.ttb_show_report == True).mapped('received_amount_total'))
            rec.sotien_lechsoluong = sum(rec.purchase_order.filtered(lambda x: x.compare_invoice == 'quantity' and x.ttb_type == 'sale' and x.partner_id.ttb_show_report == True).mapped('received_amount_total'))
            rec.sotien_chuacohoadon = sum(rec.purchase_order.filtered(lambda x: x.compare_invoice == 'none' and x.ttb_type == 'sale' and x.partner_id.ttb_show_report == True).mapped('received_amount_total'))

    def get_so_don_khop(self):
        branch_id = self._context.get('branch_id', False)
        action = self.env.ref('ttb_purchase.purchase_order_sale_action').read()[0]
        action['domain'] = [
            ('partner_id.ttb_show_report', '=', True),
            ('ttb_branch_id', '=', branch_id),
            ('compare_invoice', '=', 'matching'),
            ('ttb_type', '=', 'sale'),
            '|',
                ('state', 'in', ['purchase', 'done']),
                ('invoice_status', 'not in', ['invoiced', 'no'])
        ]
        return action

    def get_so_don_lech_tien(self):
        self.ensure_one()
        branch_id = self._context.get('branch_id', False)
        action = self.env.ref('ttb_purchase.purchase_order_sale_action').read()[0]
        action['domain'] = [
            ('partner_id.ttb_show_report', '=', True),
            ('ttb_branch_id', '=', branch_id),
            ('compare_invoice', '=', 'money'),
            ('ttb_type', '=', 'sale')
        ]
        return action

    def get_so_don_lech_sluong(self):
        branch_id = self._context.get('branch_id', False)
        action = self.env.ref('ttb_purchase.purchase_order_sale_action').read()[0]
        action['domain'] = [
            ('partner_id.ttb_show_report', '=', True),
            ('ttb_branch_id', '=', branch_id),
            ('compare_invoice', '=', 'quantity'),
            ('ttb_type', '=', 'sale')
        ]
        return action

    def get_so_don_chua_co_hoa_don(self):
        branch_id = self._context.get('branch_id', False)
        action = self.env.ref('ttb_purchase.purchase_order_sale_action').read()[0]
        action['domain'] = [
            ('partner_id.ttb_show_report', '=', True),
            ('ttb_branch_id', '=', branch_id),
            ('compare_invoice', '=', 'none'),
            ('ttb_type', '=', 'sale')
        ]
        return action

    def get_so_don_lech_alert(self):
        branch_id = self._context.get('branch_id', False)
        action = self.env.ref('ttb_purchase.purchase_order_sale_action').read()[0]
        action['domain'] = [
            ('partner_id.ttb_show_report', '=', True),
            ('ttb_branch_id', '=', branch_id),
            ('alert_po', '=', True),
            ('ttb_type', '=', 'sale')
        ]
        return action


class Danhsachdonhangcankiemtra(models.Model):
    _name = 'list.po.need.check'
    _description = 'Danh sách các PO cần kiểm tra sai lệch với hóa đơn'

    purchase_id = fields.Many2one('Đơn hàng', 'purchase.order')
    need_check = fields.Boolean('Cần check', default=True)
    check_date = fields.Datetime('Ngày kiểm tra')