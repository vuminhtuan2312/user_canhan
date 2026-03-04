from odoo import *
from odoo import api, Command, fields, models, SUPERUSER_ID, _
from odoo.exceptions import UserError
import io, xlsxwriter, base64
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    #hàm này đã được overide lại trong module ttb_purchase_invoice_stock
    # def ttb_send_accounting_info(self):
    #     if not self.env.user.has_group('ttb_stock.group_accounting_info_sender'):
    #         return
    #     if self.ttb_sent_doc or not self.ttb_document_done or not self.purchase_id or self.picking_type_code != 'incoming':
    #         return
    #     self = self.sudo()
    #     self.write({'ttb_sent_doc': True})
    #     data, file_type = self.env['ir.actions.report']._pre_render_qweb_pdf('stock.action_report_delivery', self.ids)
    #
    #     self.purchase_id.write({
    #         'ttb_receipt_doc': base64.b64encode(data[self.id]['stream'].getvalue()),
    #         'ttb_receipt_doc_name': f'{self.name}.pdf',
    #         'ttb_vendor_doc': self.ttb_vendor_doc,
    #         'ttb_vendor_doc_name': self.ttb_vendor_doc_name,
    #         'ttb_vendor_invoice': self.ttb_vendor_invoice,
    #         'ttb_vendor_invoice_name': self.ttb_vendor_invoice_name,
    #         'ttb_vendor_invoice_no': self.ttb_vendor_invoice_no,
    #         'ttb_vendor_invoice_code': self.ttb_vendor_invoice_code,
    #         'ttb_vendor_invoice_date': self.ttb_vendor_invoice_date,
    #         'ttb_doc_user_id': self.env.user.id,
    #     })

    @api.depends("name", 'purchase_id')
    def _compute_display_name(self):
        for rec in self:
            if rec.sudo().purchase_id:
                rec.display_name = f"{rec.name} - [{rec.sudo().purchase_id.name}]"
            else:
                rec.display_name = f"{rec.name}"

    ttb_accountant_accept = fields.Selection(related='purchase_id.ttb_accountant_accept', store=True)
    ttb_accountant_note = fields.Text(related='purchase_id.ttb_accountant_note', store=True)
    ttb_type = fields.Selection(string='Loại đơn mua', related='purchase_id.ttb_type')
    ttb_stage = fields.Selection(string='Giai đoạn', selection=[('1', 'Nhập kho quốc tế'),
                                                                ('2', 'Vận chuyển quốc tế'),
                                                                ('3', 'Nhập kho nội địa'),
                                                                ('4', 'Nhập kho DC'),
                                                                ('5', 'Vận chuyển cơ sở'),
                                                                ('6', 'Nhập kho cơ sở'),])
    bill_supplier = fields.Binary(string='Bill vận chuyển NCC')
    wire_transfer = fields.Binary(string='Điện chuyển tiền')

    date_of_shipment = fields.Date(string='Ngày xuất kho')
    expected_arrival_date = fields.Date(string='Ngày dự kiến hàng về')
    number_of_trips = fields.Integer(string='Số chuyến hàng')

    import_photos = fields.Binary(string='Ảnh hàng về')
    import_photos_dc = fields.Binary(string='Ảnh hàng về')

    cbm_total = fields.Float(string='Tổng CBM', related='purchase_id.cbm_total')
    number_of_cases_total = fields.Float(string='Tổng số kiện', related='purchase_id.number_of_cases_total')
    goods_distribution_ticket_id = fields.Many2one('goods.distribution.ticket', string='Phiếu chia hàng cơ sở', copy=False, readonly=True)
    id_augges_sldc = fields.Integer(string='ID SlDcM Augges', copy=False, tracking=True,
        help='ID phiếu điều chuyển Augges - cập nhật UserXN, NgayXn, số lượng khi hoàn tất')

    check_goods_ticket = fields.Binary(string='Phiếu kiểm hàng')
    imported_ticket = fields.Binary(string='Phiếu nhập hàng')

    cost_inland_china = fields.Float(string='Chi phí vận chuyển nội địa TQ', related='purchase_id.cost_inland_china')
    cost_international_shipping = fields.Float(string='Chi phí vận chuyển quốc tế', related='purchase_id.cost_international_shipping')
    cost_shipping_total = fields.Float(string='Tổng chi phí vận chuyển', related='purchase_id.cost_shipping_total')
    description = fields.Char(string='Diễn giải', related='purchase_id.description')

    attachment = fields.Binary(string='File đính kèm', related='purchase_id.attachment')

    ttb_received_date = fields.Datetime(string='Ngày nhận hàng', readonly=True, copy=False)
    ttb_received_packages = fields.Integer(string='Tổng số kiện (Thực tế)', readonly=True, copy=False)
    has_branch_warehousing_picking = fields.Boolean(string='Có phiếu nhập kho cơ sở', compute='_compute_has_branch_warehousing_picking')

    ttb_require_confirm_receipt = fields.Boolean(
        string="Cần xác nhận hàng về",
        compute="_compute_ttb_require_confirm_receipt"
    )

    @api.depends('picking_type_code', 'location_id.usage', 'state')
    def _compute_ttb_require_confirm_receipt(self):
        for picking in self:
            if picking.state in ('done', 'cancel'):
                picking.ttb_require_confirm_receipt = False
                continue

            require_confirm = False
            if picking.picking_type_code == 'incoming':
                require_confirm = True
            elif picking.picking_type_code == 'internal':
                if picking.location_id.usage == 'transit':
                    require_confirm = True

            picking.ttb_require_confirm_receipt = require_confirm

    @api.depends('purchase_id', 'origin')
    def _compute_has_branch_warehousing_picking(self):
        for rec in self:
            if rec.purchase_id:
                branch_pickings = self.env['stock.picking'].search([
                    ('purchase_id', '=', rec.purchase_id.id),
                    ('ttb_stage', '=', '6')
                ], limit=1)
                rec.has_branch_warehousing_picking = bool(branch_pickings)
            elif rec.origin:
                branch_pickings = self.env['stock.picking'].search([
                    ('origin', '=', rec.origin),
                    ('ttb_stage', '=', '6')
                ], limit=1)
                rec.has_branch_warehousing_picking = bool(branch_pickings)
            else:
                rec.has_branch_warehousing_picking = False

    def action_open_confirm_receipt_wizard(self):
        self.ensure_one()
        return {
            'name': _('Xác nhận hàng về'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking.confirm.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_picking_id': self.id},
        }

    def get_infor_location(self, next_index, purchase_order):
        if next_index == 2:
            location_id = purchase_order.china_stock_location.id
            location_dest_id = purchase_order.shipping_warehouse_id.id
        elif next_index == 3:
            location_id = purchase_order.shipping_warehouse_id.id
            location_dest_id = purchase_order.vietnam_stock_location.id
        elif next_index == 4:
            location_id = purchase_order.shipping_warehouse_id.id
            location_dest_id = purchase_order._get_destination_location()
        elif next_index == 6:
            location_id = purchase_order.shipping_warehouse_id.id
            location_dest_id = self.picking_type_id.default_location_dest_id.id

        return location_id, location_dest_id

    def create_shipping_ticket(self):
        self.ensure_one()
        StockPicking = self.env['stock.picking']
        if int(self.ttb_stage) < 4 or int(self.ttb_stage) == 5:
            id_augges = False
            sp_augges = False
            next_index = int(self.ttb_stage) + 1
            purchase_order = self.purchase_id
            if not purchase_order:
                purchase_order = self.env['purchase.order'].search([('name', '=', self.origin)], limit=1)
            if self.ttb_stage == '3':
                picking_type = purchase_order.picking_type_id
                location_id = picking_type.default_location_src_id.id
                location_dest_id = picking_type.default_location_dest_id.id
            elif self.ttb_stage == '5':
                picking_type = self.picking_type_id
                location_id = self.env.company.shipping_warehouse_id.id
                location_dest_id = self.picking_type_id.warehouse_id.lot_stock_id.id
                id_augges = self.id_augges
                sp_augges = self.sp_augges
            else:
                picking_type = self.env['stock.warehouse'].browse(self.ttb_branch_id.vat_warehouse_id.id).in_type_id
                location_id, location_dest_id = self.get_infor_location(next_index, purchase_order)
            move_ids_val = []
            for move in self.move_ids:
                if not move.quantity > 0:
                    continue
                move_ids_val.append((0, 0, {
                    'name': move.name,
                    'product_id': move.product_id.id,
                    'product_uom': move.product_uom.id,
                    'product_uom_qty': move.product_uom_qty,
                    'picking_type_id': picking_type.id ,
                    'quantity': move.quantity,  # Giữ nguyên số lượng đã nhận
                    'location_id': location_id,
                    'location_dest_id': location_dest_id,
                    'purchase_line_id': move.purchase_line_id.id,
                    'origin': move.origin,
                }))
            picking = StockPicking.with_user(SUPERUSER_ID).create({
                'partner_id': purchase_order.partner_id.id,
                'move_ids': move_ids_val,
                'picking_type_id': purchase_order.picking_type_id.id if self.ttb_stage != '5' else picking_type.id,
                'user_id': False,
                'date': purchase_order.date_order,
                'origin': purchase_order.name,
                'location_id': location_id,
                'location_dest_id': location_dest_id,
                'company_id': purchase_order.company_id.id,
                'ttb_stage': str(next_index),
                'ttb_type': purchase_order.ttb_type,
                'state': 'assigned',
                'purchase_id': purchase_order.id,
                'scheduled_date': fields.Datetime.now(),
                'id_augges_sldc': id_augges,
                'id_augges': id_augges,
                'sp_augges': sp_augges,
            })
            picking._compute_scheduled_date()

    def confirm_shipping_ticket(self):
        self.ensure_one()
        if self.ttb_stage == '1' and ( not self.bill_supplier or not self.wire_transfer):
            raise UserError('Vui lòng cập nhật Chứng từ nhập kho quốc tế trước khi xác nhận phiếu')
        if self.ttb_stage == '2' and (not self.date_of_shipment or not self.expected_arrival_date or not self.number_of_trips):
            raise UserError('Vui lòng cập nhật chứng từ vận chuyển quốc tế trước khi xác nhận phiếu')
        if self.ttb_stage == '5':
            res = self.with_context(no_check_invoice=True).button_validate()
        else:
            res = self.with_context(no_check_invoice=True, no_create_augges_incoming=True).button_validate()
        self.create_shipping_ticket()
        return res

    def action_to_po(self):
        action = self.env["ir.actions.actions"]._for_xml_id("purchase.act_res_partner_2_purchase_order")
        action['context'] = {'create': 0}
        action['views'] = [(self.env.ref('purchase.purchase_order_form', False).id, 'form')]
        action['res_id'] = self.purchase_id.id
        return action

    augges_template = fields.Binary('Augges Template', compute="_compute_augges_template", compute_sudo=True)

    def _compute_augges_template(self):
        result = io.BytesIO()
        workbook = xlsxwriter.Workbook(result)
        header_style = workbook.add_format({"bold": True, "align": "center", "valign": "vcenter", })
        text_style = workbook.add_format({"text_wrap": True, "align": "center", "valign": "vcenter"})
        number_style = workbook.add_format({"text_wrap": True, "align": "right", "valign": "vcenter", "num_format": "#,##0", })
        colnfield = {
            0: ('Mã Hàng', text_style, 'line.product_id.barcode'),
            1: ('Tên hàng', text_style, 'line.product_id.name'),
            2: ('ĐVT', text_style, False),
            3: ('Số lượng', number_style, 'line.quantity'),
            4: ('Đơn giá\n(VNĐ OR NT)', number_style, 'line.purchase_line_id.price_unit'),
            5: ('Thành tiền\n(VNĐ OR NT)', number_style, 'line.purchase_line_id.price_unit*line.quantity'),
            6: ('Thuế', text_style, False),
            7: ('Tiền thuế', number_style, False),
            8: ('Thuế XNK (%CK)', text_style, False),
            9: ('Tiền XNK (Tiền CK)', number_style, False),
            10: ('Mã ĐT', text_style, False),
            11: ('Mã PB', text_style, False),
            12: ('Mã KMP', text_style, False),
            13: ('Mã kho', text_style, False),
            14: ('Mã lô', text_style, False),
            15: ('Tên lô', text_style, False),
            16: ('Ghi chú', text_style, False),
        }
        font = workbook.add_format({'font_name': 'Times New Roman', 'font_size': 13, 'text_wrap': 1})
        set_columns = [[0, 0, 15, font], [1, 1, 40, font],
                       [2, 2, 10, font], [3, 3, 10, font],
                       [4, 4, 15, font], [5, 5, 15, font],
                       [6, 6, 15, font], [7, 7, 15, font],
                       [8, 8, 15, font], [9, 9, 15, font],
                       [10, 10, 15, font], [11, 11, 15, font],
                       [12, 12, 15, font], [13, 13, 15, font],
                       [14, 14, 15, font], [15, 15, 15, font],
                       [16, 16, 15, font]]
        for rec in self:
            result = io.BytesIO()
            workbook = xlsxwriter.Workbook(result)
            worksheet = workbook.add_worksheet()
            for col in set_columns:
                worksheet.set_column(col[0], col[1], col[2], col[3])

            header_style = workbook.add_format({"bold": True, "text_wrap": True, "align": "center", "valign": "vcenter", })
            text_style = workbook.add_format({"text_wrap": True, "align": "center", "valign": "vcenter"})
            number_style = workbook.add_format({"text_wrap": True, "align": "right", "valign": "vcenter", "num_format": "#,##0", })
            for key, val in colnfield.items():
                worksheet.write(0, key, val[0], header_style)
            row = 1
            for line in rec.move_ids:
                if line.quantity <= 0: continue
                for key, val in colnfield.items():
                    if not val[2]: continue
                    localdict = {'line': line, 'value': None}
                    tools.safe_eval.safe_eval(f'value={val[2]}', localdict, mode="exec", nocopy=True)
                    value = localdict['value']
                    worksheet.write(row, key, value, val[1])
                row += 1
            workbook.close()
            excel_file = base64.b64encode(result.getvalue())
            rec.augges_template = excel_file

    ttb_augges_export = fields.Boolean(string='Đã xuất file Augges', copy=False, readonly=True, default=False)

    def action_ttb_augges_export(self):
        self.ttb_augges_export = True
        return {
            'type': 'ir.actions.act_url',
            'name': 'Augges',
            'url': f'/web/content/{self._name}/{self.id}/augges_template/Augges_{self.name.replace("/", "_")}.xlsx',
        }

    currency_id = fields.Many2one('res.currency', related='purchase_id.currency_id')
    amount_total = fields.Float(string='Tổng tiền', store=True, readonly=True, compute='_compute_amount_total')
    amount_tax = fields.Float(string='Tổng thuế', store=False, readonly=True, compute='_compute_amount_total')
    quantity = fields.Integer(string='Tổng số lượng', compute='_compute_amount_total', store=False)

    @api.depends('move_ids_without_package', 'move_ids_without_package.ttb_price_unit', 'move_ids_without_package.quantity',
                 'move_ids_without_package.ttb_taxes_id')
    def _compute_amount_total(self):
        AccountTax = self.env['account.tax']
        for rec in self:
            rec.quantity = len(rec.move_ids_without_package.mapped('product_id'))
            order_lines = rec.move_ids_without_package
            base_lines = [line._prepare_base_line_for_taxes_computation() for line in order_lines]
            AccountTax._add_tax_details_in_base_lines(base_lines, rec.company_id)
            AccountTax._round_base_lines_tax_details(base_lines, rec.company_id)
            tax_totals = AccountTax._get_tax_totals_summary(
                base_lines=base_lines,
                currency=rec.currency_id or rec.company_id.currency_id,
                company=rec.company_id,
            )
            rec.amount_tax = tax_totals['tax_amount_currency']
            rec.amount_total = tax_totals['total_amount']

    done_user_id = fields.Many2one(string='Người xác nhận phiếu', comodel_name='res.users', readonly=True, copy=False, help='Khi nhấn xác nhận thì lưu giá trị vào trường này và dùng để đẩy thông tin người dúng sang augges')

    def button_validate(self):

        # Logic kiểm tra điều kiện nhận hàng
        for rec in self:
            if rec.picking_type_code == 'incoming' and self.ttb_stage not in ('1', '2', '3', '5'):
                if not rec.ttb_received_packages or not rec.ttb_received_date:
                    raise UserError(
                        _("Vui lòng thực hiện 'Xác nhận hàng về' (nhập số kiện và ngày nhận) trước khi xác nhận phiếu."))
            if self.ttb_stage == '6' and self.id_augges_sldc:
                self._update_augges_sldc_on_done()
        # Kiểm tra chứng từ kế toán
        for rec in self:
            if rec.purchase_id and rec.picking_type_code == 'incoming' and not self._context.get('no_check_document', False):
                message = []
                if rec.purchase_id.ttb_type == 'not_sale':
                    check = {
                        'Phiếu giao hàng NCC': rec.ttb_vendor_doc,
                        'Biên bản bàn giao': rec.ttb_vendor_delivery,
                        'Biên bản nghiệm thu': rec.ttb_acceptance_report,
                    }
                elif rec.purchase_id.ttb_type == 'imported_goods':
                    check = {}
                else:
                    if rec.has_invoice or rec.purchase_id.partner_id.ttb_no_invoice:
                        check = {
                            'Phiếu giao hàng NCC': rec.ttb_vendor_doc or rec.ttb_vendor_doc_ids,
                            # 'Hoá đơn GTGT': rec.ttb_vendor_invoice,
                        }
                    else:
                        check = {
                            'Phiếu giao hàng NCC': rec.ttb_vendor_doc or rec.ttb_vendor_doc_ids,
                            # 'Hoá đơn GTGT': rec.ttb_vendor_invoice or '',
                            'Hóa đơn đỏ': rec.invoice_ids,
                        }

                for key in check:
                    if not check[key]:
                        message.append(key)

                if message:
                    raise UserError('Bạn chưa cập nhật Chứng từ kế toán. Vui lòng cập nhật đầy đủ chứng từ (%s) trước khi xác nhận' % ', '.join(message))

        res = super().button_validate()
        self.write({'done_user_id': self.env.user.id})
        for rec in self:
            if rec.ttb_type == 'not_sale':
                rec.purchase_id.write({
                    'ttb_vendor_delivery': rec.ttb_vendor_delivery,
                    'ttb_acceptance_report': rec.ttb_acceptance_report,
                })

        return res

    def _action_done(self):
        """
        Override _action_done để tạo phiếu vận chuyển cơ sở sau khi xác nhận phiếu nhập DC.
        Method này CHỈ được gọi khi phiếu thực sự được done (sau khi user chọn Create/No backorder).
        Điều này đảm bảo logic chỉ chạy khi user KHÔNG chọn Cancel trong wizard backorder.
        """
        res = super()._action_done()

        for picking in self:
            if picking.state == 'done' and picking.ttb_stage == '4' and picking.purchase_id.ttb_type == 'imported_goods':
                ticket = self.env['goods.distribution.ticket'].search([
                    ('stock_picking_id', '=', picking.id),
                    ('state', '=', 'confirmed')
                ], limit=1)

                if ticket:
                    ticket.create_shipping_branch_ticket()
                else:
                    raise UserError('Không tìm thấy phiếu chia hàng cơ sở đã được xác nhận. Vui lòng kiểm tra lại!!!')
        return res

    ttb_amount_total = fields.Float(string='Tổng tiền (ttb)', store=False, readonly=True, compute='_compute_ttb_amount_total')
    ttb_amount_tax = fields.Float(string='Tổng thuế (ttb)', store=False, readonly=True, compute='_compute_ttb_amount_total')

    @api.depends('move_ids_without_package', 'move_ids_without_package.ttb_price_unit', 'move_ids_without_package.quantity')
    def _compute_ttb_amount_total(self):
        AccountTax = self.env['account.tax']
        for rec in self:
            order_lines = rec.move_ids_without_package
            base_lines = []
            for line in order_lines:
                base_lines += [self.env['account.tax']._prepare_base_line_for_taxes_computation(
                    line,
                    tax_ids=line.ttb_taxes_id,
                    quantity=line.purchase_line_id.qty_received or line.quantity,
                    price_unit=line.ttb_price_unit,
                    currency_id=line.picking_id.currency_id or line.picking_id.company_id.currency_id,
                    discount=line.ttb_discount,
                )]
            AccountTax._add_tax_details_in_base_lines(base_lines, rec.company_id)
            AccountTax._round_base_lines_tax_details(base_lines, rec.company_id)
            tax_totals = AccountTax._get_tax_totals_summary(
                base_lines=base_lines,
                currency=rec.currency_id or rec.company_id.currency_id,
                company=rec.company_id,
            )
            rec.ttb_amount_tax = tax_totals['tax_amount_currency']
            rec.ttb_amount_total = tax_totals['total_amount']

    has_ticket = fields.Boolean("Đã có phiếu chia hàng", default=False)

    def action_view_ticket(self):
        self.ensure_one()
        ticket = self.env['goods.distribution.ticket'].search([('stock_picking_id', '=', self.id), ('state', 'in', ('draft', 'confirmed'))], limit=1)
        if not ticket:
            raise UserError('Chưa có phiếu chia hàng cơ sở. Vui lòng kiểm tra lại!!!')
        return {
            'name': 'Phiếu chia hàng cơ sở',
            'type': 'ir.actions.act_window',
            'res_model': 'goods.distribution.ticket',
            'view_mode': 'form',
            'res_id': ticket.id,
            'target': 'current',
        }

    def button_create_goods_istribution_ticket(self):
        self.ensure_one()
        ticket = self.env['prioritize.branch'].create({
            'po_id': self.purchase_id.id,
            'stock_picking_id': self.id,
        })
        return {
            'name': 'Chọn thứ tự cơ sở ưu tiên',
            'type': 'ir.actions.act_window',
            'res_model': 'prioritize.branch',
            'view_mode': 'form',
            'res_id': ticket.id,
            'target': 'new',
        }

    def action_create_complaint_ticket(self):
        self.ensure_one()
        ticket = self.env['complaint.ticket'].create({
            'stock_picking': self.id,
            'assigned_to': self.env.user.id,
        })
        return {
            'name': 'Phiếu khiếu nại',
            'type': 'ir.actions.act_window',
            'res_model': 'complaint.ticket',
            'view_mode': 'form',
            'res_id': ticket.id,
            'target': 'current',
        }

    def action_view_complaint_ticket(self):
        self.ensure_one()
        ticket = self.env['complaint.ticket'].search([('stock_picking', '=', self.id)])
        if not ticket:
            raise UserError('Phiếu vận chuyển này không có khiếu nại.')
        if len(ticket) == 1:
            return {
                'name': 'Phiếu khiếu nại',
                'type': 'ir.actions.act_window',
                'res_model': 'complaint.ticket',
                'view_mode': 'form',
                'res_id': ticket.id,
                'target': 'current',
            }
        return {
            'name': 'Phiếu khiếu nại',
            'type': 'ir.actions.act_window',
            'res_model': 'complaint.ticket',
            'view_mode': 'list,form',
            'domain': [('id', 'in', ticket.ids)],
            'target': 'current',
        }

    def _update_augges_sldc_on_done(self):
        """Cập nhật SlDcM (UserXN, Thời gian nhập) và SlDcD (Số lượng) khi phiếu nhập kho cơ sở hoàn tất."""
        self.ensure_one()
        if not self.id_augges_sldc:
            return

        user_augges_id = self.env['ttb.augges'].get_user_id_augges(user=self.env.user) or 0
        ngay_xn = (datetime.utcnow() + timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S")

        conn = self.env['ttb.tools'].get_mssql_connection_send()
        cursor = conn.cursor()
        cong_sl_total = 0
        try:
            # SlDcD: Số lượng từ move_ids (Hoạt động Phiếu nhập kho Cơ sở Odoo)
            _logger.warning('Picking move_ids_without_package: %s', self.move_ids_without_package)
            for move in self.move_ids_without_package:
                qty = move.quantity  # Số lượng: Hoạt động Phiếu nhập kho Cơ sở Odoo
                augges_product_id = move.product_id.product_tmpl_id.augges_id
                _logger.warning('LAT1232')
                _logger.warning('Picking id_augges augges: %s', self.id_augges)
                _logger.warning('Picking augges_product_id: %s', augges_product_id)
                cursor.execute(
                    "SELECT Stt FROM SlDcD WHERE ID = ? AND ID_Hang = ?",
                    (self.id_augges, augges_product_id)
                )
                row = cursor.fetchone()
                if row:
                    stt = row[0]
                    detail_update = {'So_Luong': qty, 'Sl_Qd': qty}
                    self.env['ttb.augges'].update_record(
                        'SlDcD', detail_update, self.id_augges, stt=stt, pair_conn=conn
                    )
                    cong_sl_total += qty

            # SlDcM: UserXN, Thời gian nhập (NgayXn), Cong_Sl
            _logger.warning('Picking user_augges_id: %s', user_augges_id)

            master_update = {
                'UserIDXN': 2698,   # UserXN: Tài khoản chuyển trạng thái sang Hoàn tất
                'NgayXn': ngay_xn,            # Thời gian nhập: Thời điểm chuyển sang Hoàn tất
            }
            if cong_sl_total > 0:
                master_update['Cong_Sl'] = cong_sl_total
                master_update['Cong_SlQd'] = cong_sl_total
            self.env['ttb.augges'].update_record('SlDcM', master_update, self.id_augges_sldc, pair_conn=conn)

            conn.commit()
        finally:
            cursor.close()
            conn.close()

    def confirm_shipping_ticket_dc(self):
        if (not self.imported_ticket or not self.check_goods_ticket or not self.import_photos_dc) and self.ttb_stage == '4':
            raise UserError('Vui lòng cập nhật chứng từ vận chuyển trước khi xác nhận phiếu')
        if not self.has_ticket:
                raise UserError('Phiếu nhập kho DC chưa có phiếu chia hàng nên không thể xác nhận. Vui lòng kiểm tra lại!!!')
        ticket = self.env['goods.distribution.ticket'].search(
            [('stock_picking_id', '=', self.id), ('state', '=', 'confirmed')], limit=1)
        if not ticket.state == 'confirmed':
            raise UserError('Phiếu chia hàng cơ sở chưa được xác nhận nên không thể xác nhận phiếu nhập kho DC. Vui lòng kiểm tra lại!!!')

        res = self.with_context(no_check_invoice=True).button_validate()

        return res

    def action_view_po(self):
        self.ensure_one()
        if not self.purchase_id.id:
            raise UserError('Không tìm thấy đơn mua hàng liên quan.')
        return {
            'name': 'Đơn mua hàng',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'res_id': self.purchase_id.id,
            'target': 'current',
        }

    def action_view_stock_picking_ticket(self):
        self.ensure_one()
        context = self.env.context.get('type_ticket', False)
        type_ticket = False
        if context == 'international_warehousing':
            type_ticket = '1'
        elif context == 'international_shipping':
            type_ticket = '2'
        elif context == 'domestic_warehousing':
            type_ticket = '3'
        st_id = self.env['stock.picking'].search([('purchase_id', '=', self.purchase_id.id), ('ttb_stage', '=', type_ticket)], limit=1)
        if not st_id:
            raise UserError('Không tìm thấy phiếu vận chuyển quốc tế liên quan.')
        return {
            'name': 'Phiếu vận chuyển',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': st_id.id,
            'target': 'current',
        }

    def action_view_dc_warehousing(self):
        self.ensure_one()
        if not self.purchase_id:
            raise UserError('Không tìm thấy đơn mua hàng liên quan.')

        dc_pickings = self.env['stock.picking'].search([
            ('purchase_id', '=', self.purchase_id.id),
            ('ttb_stage', '=', '4')
        ])

        if not dc_pickings:
            raise UserError('Không tìm thấy phiếu nhập kho DC liên quan.')

        if len(dc_pickings) == 1:
            return {
                'name': 'Phiếu nhập kho DC',
                'type': 'ir.actions.act_window',
                'res_model': 'stock.picking',
                'view_mode': 'form',
                'res_id': dc_pickings.id,
                'target': 'current',
            }
        else:
            return {
                'name': 'Phiếu nhập kho DC',
                'type': 'ir.actions.act_window',
                'res_model': 'stock.picking',
                'view_mode': 'list,form',
                'domain': [('id', 'in', dc_pickings.ids)],
                'target': 'current',
            }

    def action_view_branch_warehousing(self):
        self.ensure_one()

        if self.purchase_id:
            branch_pickings = self.env['stock.picking'].search([
                ('purchase_id', '=', self.purchase_id.id),
                ('ttb_stage', '=', '6')
            ])
        elif self.origin:
            branch_pickings = self.env['stock.picking'].search([
                ('origin', '=', self.origin),
                ('ttb_stage', '=', '6')
            ])
        else:
            raise UserError('Không tìm thấy thông tin đơn mua hàng.')

        if not branch_pickings:
            raise UserError('Không tìm thấy phiếu nhập kho cơ sở liên quan.')

        if len(branch_pickings) == 1:
            return {
                'name': 'Phiếu nhập kho cơ sở',
                'type': 'ir.actions.act_window',
                'res_model': 'stock.picking',
                'view_mode': 'form',
                'res_id': branch_pickings.id,
                'target': 'current',
            }
        else:
            return {
                'name': 'Phiếu nhập kho cơ sở',
                'type': 'ir.actions.act_window',
                'res_model': 'stock.picking',
                'view_mode': 'list,form',
                'domain': [('id', 'in', branch_pickings.ids)],
                'target': 'current',
            }

    def action_view_branch_shipping(self):
        self.ensure_one()

        if self.goods_distribution_ticket_id:
            branch_shipping_pickings = self.env['stock.picking'].search([
                ('goods_distribution_ticket_id', '=', self.goods_distribution_ticket_id.id),
                ('ttb_stage', '=', '5')
            ])
        elif self.purchase_id:
            branch_shipping_pickings = self.env['stock.picking'].search([
                ('purchase_id', '=', self.purchase_id.id),
                ('ttb_stage', '=', '5')
            ])
        elif self.origin:
            branch_shipping_pickings = self.env['stock.picking'].search([
                ('origin', '=', self.origin),
                ('ttb_stage', '=', '5')
            ])
        else:
            raise UserError('Không tìm thấy thông tin để tra cứu phiếu vận chuyển cơ sở.')

        if not branch_shipping_pickings:
            raise UserError('Không tìm thấy phiếu vận chuyển cơ sở liên quan.')

        if len(branch_shipping_pickings) == 1:
            return {
                'name': 'Phiếu vận chuyển cơ sở',
                'type': 'ir.actions.act_window',
                'res_model': 'stock.picking',
                'view_mode': 'form',
                'res_id': branch_shipping_pickings.id,
                'target': 'current',
            }
        else:
            return {
                'name': 'Phiếu vận chuyển cơ sở',
                'type': 'ir.actions.act_window',
                'res_model': 'stock.picking',
                'view_mode': 'list,form',
                'domain': [('id', 'in', branch_shipping_pickings.ids)],
                'target': 'current',
            }

    @api.depends('move_ids.state', 'move_ids.date', 'move_type', 'ttb_stage', 'ttb_type', 'purchase_id')
    def _compute_scheduled_date(self):
        for picking in self:
            if not picking.ttb_type == 'imported_goods':
                moves_dates = picking.move_ids.filtered(lambda move: move.state not in ('done', 'cancel')).mapped('date')
                if picking.move_type == 'direct':
                    picking.scheduled_date = min(moves_dates, default=picking.scheduled_date or fields.Datetime.now())
                else:
                    picking.scheduled_date = max(moves_dates, default=picking.scheduled_date or fields.Datetime.now())
            else:
                if picking.ttb_stage == '1':
                    picking.scheduled_date = picking.purchase_id.expected_date
                elif picking.ttb_stage == '3':
                    sp_id = self.env['stock.picking'].search(
                        [('purchase_id', '=', picking.purchase_id.id), ('ttb_stage', '=', '2')], limit=1)
                    picking.scheduled_date = sp_id.expected_arrival_date if sp_id else False
