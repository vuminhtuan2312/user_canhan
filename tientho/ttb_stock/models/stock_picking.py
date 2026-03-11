from odoo import *
import io, xlsxwriter, base64, pytz
import logging
from odoo.exceptions import UserError
_logger = logging.getLogger(__name__)
import datetime
from datetime import timedelta

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    transfer_request_id = fields.Many2one(
        'stock.transfer.request',
        string='Phiếu đề nghị điều chuyển'
    )

    career_inventory = fields.Boolean(string="Kiểm kê hướng nghiệp")
    consume_request_id = fields.Many2one('stock.consume.request', string='Phiếu đề nghị xuất dùng')
    barcode_request_id = fields.Many2one('barcode.change.request', string='Phiếu đề nghị chuyển mã')

    priority_level = fields.Integer(string='Mức độ ưu tiên', compute='_compute_priority_level',  store=True)

    @api.onchange('career_inventory')
    def _onchange_career_inventory(self):
        if self.career_inventory:
            products = self.env['product.product'].search([
                ('inventory_career', '=', True)
            ])
            lines = []
            for product in products:
                lines.append((0,0, {
                    'name': product.display_name,
                    'product_id': product.id,
                    'product_uom_qty': product.default_stock_qty,
                    'product_uom': product.uom_id.id,
                    'location_id': self.location_id.id,
                    'location_dest_id': self.location_dest_id.id,
                }))
            self.move_ids_without_package = lines
    @api.depends('state')
    def _compute_priority_level(self):
        for rec in self:
            if rec.state == 'draft':
                rec.priority_level = 0
            elif rec.state == 'assigned':
                rec.priority_level = 1
            elif rec.state == 'done':
                rec.priority_level = 2
            elif rec.state == 'cancel':
                rec.priority_level = 3
            elif rec.state == 'confirmed':
                rec.priority_level = 4
            else:
                rec.priority_level = 5

    def _action_done(self):
        res = super()._action_done()
        for record in self:
            if record.state == 'done':
                record.write({'user_id': self.env.user.id})
        return res

    def do_print_picking(self):
        res = super().do_print_picking()
        if any(rec.picking_type_code == 'incoming' for rec in self):
            return self.action_incoming_template()
        return res

    def action_incoming_template(self):
        return {
            'type': 'ir.actions.act_url',
            'name': 'Phiếu nhập hàng',
            'url': f'/web/content/{self._name}/{self.id}/incoming_template/{self.name.replace("/", "_")}.xlsx',
        }

    incoming_template = fields.Binary('Phiếu nhập hàng', compute="_compute_incoming_template", compute_sudo=True)

    def _compute_incoming_template(self):
        result = io.BytesIO()
        workbook = xlsxwriter.Workbook(result)
        font = workbook.add_format({'font_name': 'Times New Roman', 'font_size': 11})
        set_columns = [[0, 0, 29 / 7, font], [1, 1, 110 / 7, font],
                       [2, 2, 89 / 7, font], [3, 3, 195 / 7, font],
                       [4, 4, 43 / 7, font], [5, 5, 45 / 7, font],
                       [6, 6, 81 / 7, font], [7, 7, 93 / 7, font],
                       [8, 8, 39 / 7, font], [9, 9, 96 / 7, font]]
        for rec in self:
            result = io.BytesIO()
            workbook = xlsxwriter.Workbook(result)
            worksheet = workbook.add_worksheet()
            for col in set_columns:
                worksheet.set_column(col[0], col[1], col[2], col[3])
            addr = ['street', 'street2', 'city', 'state_code', 'zip', 'country_name']
            warehouse_addr = []
            partner_addr = []
            for add in addr:
                if rec.partner_id.read([add])[0].get(add):
                    partner_addr += [rec.partner_id.read([add])[0].get(add)]
                if rec.picking_type_id.warehouse_id.partner_id.read([add])[0].get(add):
                    warehouse_addr += [rec.picking_type_id.warehouse_id.partner_id.read([add])[0].get(add)]

            worksheet.write(0, 1, rec.picking_type_id.warehouse_id.partner_id.name or '', workbook.add_format({"font_name": "Times New Roman", "bold": True, "align": "left", "valign": "vcenter", }))
            worksheet.write(0, 5, 'Điện thoại', workbook.add_format({"font_name": "Times New Roman", "align": "left", "valign": "vcenter", }))
            worksheet.write(0, 7, rec.picking_type_id.warehouse_id.partner_id.phone or '', workbook.add_format({"font_name": "Times New Roman", "align": "left", "valign": "vcenter", }))
            worksheet.write(1, 0, '', workbook.add_format({"font_name": "Times New Roman", "bottom": True, "align": "left", "valign": "vcenter", }))
            worksheet.write(1, 1, f'Địa chỉ: {", ".join(warehouse_addr) if warehouse_addr else ""}', workbook.add_format({"font_name": "Times New Roman", "bottom": True, "align": "left", "valign": "vcenter", }))
            worksheet.write(1, 2, '', workbook.add_format({"font_name": "Times New Roman", "bottom": True, "align": "left", "valign": "vcenter", }))
            worksheet.write(1, 3, '', workbook.add_format({"font_name": "Times New Roman", "bottom": True, "align": "left", "valign": "vcenter", }))
            worksheet.write(1, 4, '', workbook.add_format({"font_name": "Times New Roman", "bottom": True, "align": "left", "valign": "vcenter", }))
            worksheet.write(1, 5, 'Email', workbook.add_format({"font_name": "Times New Roman", "bottom": True, "align": "left", "valign": "vcenter", }))
            worksheet.write(1, 6, '', workbook.add_format({"font_name": "Times New Roman", "bottom": True, "align": "left", "valign": "vcenter", }))
            worksheet.write(1, 7, rec.picking_type_id.warehouse_id.partner_id.email, workbook.add_format({"font_name": "Times New Roman", "bottom": True, "align": "left", "valign": "vcenter", }))
            worksheet.write(1, 8, '', workbook.add_format({"font_name": "Times New Roman", "bottom": True, "align": "left", "valign": "vcenter", }))
            worksheet.write(1, 9, '', workbook.add_format({"font_name": "Times New Roman", "bottom": True, "align": "left", "valign": "vcenter", }))
            worksheet.merge_range("A4:J4", "PHIẾU NHẬP HÀNG", workbook.add_format({"font_name": "Times New Roman", "bold": True, 'font_size': 16, "align": "center", "valign": "vcenter", }))
            worksheet.merge_range("A5:J5", f"Ngày lập phiếu: {rec.create_date.astimezone(pytz.timezone(self.env.user.tz)).strftime('%d/%m/%Y')}", workbook.add_format({"font_name": "Times New Roman", "align": "center", "valign": "vcenter", }))

            worksheet.write(5, 0, 'Nhà cung cấp:', workbook.add_format({"font_name": "Times New Roman", "align": "left", "valign": "vcenter", }))
            worksheet.write(5, 2, rec.partner_id.name or '', workbook.add_format({"font_name": "Times New Roman", "align": "left", "valign": "vcenter", }))
            worksheet.write(5, 7, 'Số hóa đơn', workbook.add_format({"font_name": "Times New Roman", "align": "left", "valign": "vcenter", }))
            worksheet.write(5, 8, rec.name or '', workbook.add_format({"font_name": "Times New Roman", "align": "left", "valign": "vcenter", }))

            worksheet.write(6, 0, 'Địa chỉ:', workbook.add_format({"font_name": "Times New Roman", "align": "left", "valign": "vcenter", }))
            worksheet.write(6, 2, f'{", ".join(partner_addr) if partner_addr else ""}', workbook.add_format({"font_name": "Times New Roman", "align": "left", "valign": "vcenter", }))
            worksheet.write(6, 7, 'Ngày in phiếu', workbook.add_format({"font_name": "Times New Roman", "align": "left", "valign": "vcenter", }))
            worksheet.write(6, 8, fields.Datetime.now().astimezone(pytz.timezone(self.env.user.tz)).strftime('%d/%m/%Y %H:%M:%S'), workbook.add_format({"font_name": "Times New Roman", "align": "left", "valign": "vcenter", }))

            worksheet.write(7, 0, 'Điện thoại:', workbook.add_format({"font_name": "Times New Roman", "align": "left", "valign": "vcenter", }))
            worksheet.write(7, 2, rec.partner_id.phone or '', workbook.add_format({"font_name": "Times New Roman", "align": "left", "valign": "vcenter", }))

            worksheet.write(8, 0, 'Mã số thuế:', workbook.add_format({"font_name": "Times New Roman", "align": "left", "valign": "vcenter", }))
            worksheet.write(8, 2, rec.partner_id.vat or '', workbook.add_format({"font_name": "Times New Roman", "align": "left", "valign": "vcenter", }))

            worksheet.write(9, 8, 'ĐVT:', workbook.add_format({"font_name": "Times New Roman", "italic": True, "align": "left", "valign": "vcenter", }))
            worksheet.write(9, 9, 'Đồng Việt Nam', workbook.add_format({"font_name": "Times New Roman", "italic": True, "align": "left", "valign": "vcenter", }))

            worksheet.write(10, 0, 'TT', workbook.add_format({"font_name": "Times New Roman", "border": True, "bold": True, "align": "center", "valign": "vcenter", }))
            worksheet.write(10, 1, 'Mã vạch', workbook.add_format({"font_name": "Times New Roman", "border": True, "bold": True, "align": "center", "valign": "vcenter", }))
            worksheet.merge_range("C11:D11", "Tên hàng", workbook.add_format({"font_name": "Times New Roman", "border": True, "bold": True, "align": "center", "valign": "vcenter", }))
            worksheet.write(10, 4, 'ĐVT', workbook.add_format({"font_name": "Times New Roman", "border": True, "bold": True, "align": "center", "valign": "vcenter", }))
            worksheet.write(10, 5, 'SL', workbook.add_format({"font_name": "Times New Roman", "border": True, "bold": True, "align": "center", "valign": "vcenter", }))
            worksheet.write(10, 6, 'Giá bìa', workbook.add_format({"font_name": "Times New Roman", "border": True, "bold": True, "align": "center", "valign": "vcenter", }))
            worksheet.write(10, 7, 'Thành tiền', workbook.add_format({"font_name": "Times New Roman", "border": True, "bold": True, "align": "center", "valign": "vcenter", }))
            worksheet.write(10, 8, '% CK', workbook.add_format({"font_name": "Times New Roman", "border": True, "bold": True, "align": "center", "valign": "vcenter", }))
            worksheet.write(10, 9, 'Thanh toán', workbook.add_format({"font_name": "Times New Roman", "border": True, "bold": True, "align": "center", "valign": "vcenter", }))
            row = 1
            for line in rec.move_ids:
                if line.quantity <= 0: continue
                worksheet.write(10 + row, 0, row, workbook.add_format({"font_name": "Times New Roman", "left": True, "right": True, "align": "center", "valign": "vcenter", }))
                worksheet.write(10 + row, 1, line.ttb_product_code, workbook.add_format({"font_name": "Times New Roman", "left": True, "right": True, "align": "left", "valign": "vcenter", }))
                worksheet.merge_range(f"C{11 + row}:D{11 + row}", line.product_id.display_name, workbook.add_format({"font_name": "Times New Roman", "left": True, "right": True, "text_wrap": True, "align": "left", "valign": "vcenter", }))
                worksheet.write(10 + row, 4, line.product_uom.name, workbook.add_format({"font_name": "Times New Roman", "left": True, "right": True, "align": "left", "valign": "vcenter", }))
                worksheet.write(10 + row, 5, line.quantity, workbook.add_format({"font_name": "Times New Roman", "left": True, "num_format": "#,##0", "right": True, "align": "right", "valign": "vcenter", }))
                worksheet.write(10 + row, 6, line.ttb_price_unit, workbook.add_format({"font_name": "Times New Roman", "left": True, "num_format": "#,##0", "right": True, "align": "right", "valign": "vcenter", }))
                worksheet.write(10 + row, 7, f'=F{11 + row}*G{11 + row}', workbook.add_format({"font_name": "Times New Roman", "left": True, "num_format": "#,##0", "right": True, "align": "right", "valign": "vcenter", }))
                worksheet.write(10 + row, 8, line.ttb_discount, workbook.add_format({"font_name": "Times New Roman", "left": True, "num_format": "#,##0", "right": True, "align": "right", "valign": "vcenter", }))
                worksheet.write(10 + row, 9, f'=H{11 + row}*(1-I{11 + row}/100)', workbook.add_format({"font_name": "Times New Roman", "left": True, "num_format": "#,##0", "right": True, "align": "right", "valign": "vcenter", }))
                row += 1
            worksheet.write(10 + row, 0, '', workbook.add_format({"font_name": "Times New Roman", "left": True, "top": True, "align": "center", "valign": "vcenter", }))
            worksheet.write(10 + row, 1, '', workbook.add_format({"font_name": "Times New Roman", "top": True, "align": "center", "valign": "vcenter", }))
            worksheet.write(10 + row, 2, '', workbook.add_format({"font_name": "Times New Roman", "top": True, "align": "center", "valign": "vcenter", }))
            worksheet.write(10 + row, 3, '', workbook.add_format({"font_name": "Times New Roman", "top": True, "align": "center", "valign": "vcenter", }))
            worksheet.write(10 + row, 4, '', workbook.add_format({"font_name": "Times New Roman", "top": True, "align": "center", "valign": "vcenter", }))
            worksheet.write(10 + row, 5, f'=SUM(F12:F{10 + row})', workbook.add_format({"font_name": "Times New Roman", "top": True, "num_format": "#,##0", "bold": True, "align": "right", "valign": "vcenter", }))
            worksheet.write(10 + row, 6, '', workbook.add_format({"font_name": "Times New Roman", "top": True, "align": "center", "valign": "vcenter", }))
            worksheet.write(10 + row, 7, 'Tổng tiền giá bìa', workbook.add_format({"font_name": "Times New Roman", "top": True, "bold": True, "align": "left", "valign": "vcenter", }))
            worksheet.write(10 + row, 8, '', workbook.add_format({"font_name": "Times New Roman", "top": True, "align": "right", "valign": "vcenter", }))
            worksheet.write(10 + row, 9, f'=SUM(H12:H{10 + row})', workbook.add_format({"font_name": "Times New Roman", "top": True, "num_format": "#,##0", "left": True, "right": True, "bold": True, "align": "right", "valign": "vcenter", }))

            worksheet.write(11 + row, 0, '', workbook.add_format({"font_name": "Times New Roman", "left": True, "align": "center", "valign": "vcenter", }))
            worksheet.write(11 + row, 7, 'Chiết khấu', workbook.add_format({"font_name": "Times New Roman", "align": "left", "valign": "vcenter", }))
            worksheet.write(11 + row, 9, f'=SUMPRODUCT(H12:H{10 + row};I12:I{10 + row})/100', workbook.add_format({"font_name": "Times New Roman", "left": True, "num_format": "#,##0", "right": True, "align": "right", "valign": "vcenter", }))

            worksheet.write(12 + row, 0, '', workbook.add_format({"font_name": "Times New Roman", "left": True, "align": "center", "valign": "vcenter", }))
            worksheet.write(12 + row, 7, 'Thuế', workbook.add_format({"font_name": "Times New Roman", "align": "left", "valign": "vcenter", }))
            worksheet.write(12 + row, 9, rec.amount_tax, workbook.add_format({"font_name": "Times New Roman", "left": True, "num_format": "#,##0", "right": True, "align": "right", "valign": "vcenter", }))

            worksheet.write(13 + row, 0, '', workbook.add_format({"font_name": "Times New Roman", "left": True, "bottom": True, "align": "center", "valign": "vcenter", }))
            worksheet.write(13 + row, 1, '', workbook.add_format({"font_name": "Times New Roman", "bottom": True, "align": "center", "valign": "vcenter", }))
            worksheet.write(13 + row, 2, '', workbook.add_format({"font_name": "Times New Roman", "bottom": True, "align": "center", "valign": "vcenter", }))
            worksheet.write(13 + row, 3, '', workbook.add_format({"font_name": "Times New Roman", "bottom": True, "align": "center", "valign": "vcenter", }))
            worksheet.write(13 + row, 4, '', workbook.add_format({"font_name": "Times New Roman", "bottom": True, "align": "center", "valign": "vcenter", }))
            worksheet.write(13 + row, 5, '', workbook.add_format({"font_name": "Times New Roman", "bottom": True, "num_format": "#,##0", "bold": True, "align": "right", "valign": "vcenter", }))
            worksheet.write(13 + row, 6, '', workbook.add_format({"font_name": "Times New Roman", "bottom": True, "align": "center", "valign": "vcenter", }))
            worksheet.write(13 + row, 7, 'Tổng thanh toán', workbook.add_format({"font_name": "Times New Roman", "bottom": True, "bold": True, "align": "left", "valign": "vcenter", }))
            worksheet.write(13 + row, 8, '', workbook.add_format({"font_name": "Times New Roman", "bottom": True, "align": "right", "valign": "vcenter", }))
            worksheet.write(13 + row, 9, f'=J{11 + row}-J{12 + row}+J{13 + row}', workbook.add_format({"font_name": "Times New Roman", "bottom": True, "num_format": "#,##0", "left": True, "right": True, "bold": True, "align": "right", "valign": "vcenter", }))

            worksheet.write(14 + row, 1, 'Tổng số tiền (viết bằng chữ)', workbook.add_format({"font_name": "Times New Roman", "bold": True, "align": "left", "valign": "vcenter", }))
            worksheet.write(14 + row, 3, rec.currency_id.amount_to_text(rec.amount_total).replace('Dong', 'Đồng'), workbook.add_format({"font_name": "Times New Roman", "italic": True, "align": "left", "valign": "vcenter", }))

            worksheet.write(16 + row, 1, 'Kế toán', workbook.add_format({"font_name": "Times New Roman", "bold": True, "align": "left", "valign": "vcenter", }))
            worksheet.write(16 + row, 3, 'Người kiểm hàng', workbook.add_format({"font_name": "Times New Roman", "bold": True, "align": "left", "valign": "vcenter", }))
            worksheet.write(16 + row, 5, 'Người nhập hàng', workbook.add_format({"font_name": "Times New Roman", "bold": True, "align": "left", "valign": "vcenter", }))
            worksheet.write(16 + row, 8, 'Người lập phiếu', workbook.add_format({"font_name": "Times New Roman", "bold": True, "align": "left", "valign": "vcenter", }))
            worksheet.write(22 + row, 8, self.env.user.name, workbook.add_format({"font_name": "Times New Roman", "bold": True, "align": "left", "valign": "vcenter", }))
            workbook.close()
            excel_file = base64.b64encode(result.getvalue())
            rec.incoming_template = excel_file

    message_body = fields.Html(string='Ghi chú', related='message_ids.body')
    ttb_inspector_id = fields.Many2one(string='Người kiểm hàng', comodel_name='res.users')
    ttb_partner_ref = fields.Char(string='Mã phiếu của NCC', related='purchase_id.partner_ref', store=True)
    ttb_branch_id = fields.Many2one(related='picking_type_id.warehouse_id.ttb_branch_id', store=True)
    ttb_vendor_doc = fields.Binary(string='Phiếu giao hàng NCC', copy=False)
    ttb_vendor_doc_ids = fields.Many2many(
        comodel_name='ir.attachment',
        string="Phiếu giao hàng NCC",
        help="Upload hoặc kéo thả các tài liệu, chứng từ liên quan vào đây."
    )
    ttb_vendor_doc_name = fields.Char(string='Tên Phiếu giao hàng NCC', copy=False)
    ttb_vendor_invoice = fields.Binary(string='Hóa đơn GTGT', copy=False)
    ttb_vendor_invoice_name = fields.Char(string='Tên Hóa đơn GTGT', copy=False)
    ttb_vendor_invoice_no = fields.Char(string='Số hóa đơn NCC', copy=False)
    ttb_vendor_invoice_code = fields.Char(string='Ký hiệu hóa đơn NCC', copy=False)
    ttb_vendor_invoice_date = fields.Date(string='Ngày hóa đơn NCC', copy=False)
    ttb_document_done = fields.Boolean(string='Đầy đủ chứng từ', compute='_compute_ttb_document_done', store=True)

    # cheat: Khai báo lại trường ttb_type
    ttb_type = fields.Selection(string='Loại đơn mua', selection=[('sale', 'Mua hàng kinh doanh'), ('not_sale', 'Mua hàng không kinh doanh'), ('material', 'Mua nguyên vật liệu')])
    ttb_vendor_delivery = fields.Binary(string='Biên bản bàn giao', copy=False)
    ttb_acceptance_report = fields.Binary(string='Biên bản nghiệm thu', copy=False)

    @api.depends(lambda self: [name for name, field in self._fields.items() if field.store and name not in ['ttb_document_done']])
    def _compute_ttb_document_done(self):
        for rec in self:
            ttb_document_done = rec.ttb_document_done

            if rec.ttb_vendor_doc and rec.ttb_vendor_invoice and not ttb_document_done:
                ttb_document_done = True

            rec.ttb_document_done = ttb_document_done

    ttb_accountant_accept = fields.Selection(string='Xác nhận của kế toán', selection=[('not_ok', 'Chứng từ cần điều chỉnh'), ('ok', 'Chứng từ hợp lệ')])
    ttb_accountant_note = fields.Text(string='Ghi chú của kế toán')
    ttb_doc_user_id = fields.Many2one(string='Người tải tài liệu', compute='_compute_ttb_doc_user_id', store=True, comodel_name='res.users')
    # augges_id = fields.Integer(string='Mã Augges tương ứng')

    @api.depends('ttb_vendor_doc', 'ttb_vendor_invoice')
    def _compute_ttb_doc_user_id(self):
        for rec in self:
            if rec.ttb_vendor_doc == rec._origin.ttb_vendor_doc and rec.ttb_vendor_invoice == rec._origin.ttb_vendor_invoice:
                rec.ttb_doc_user_id = rec._origin.ttb_doc_user_id
                continue
            rec.ttb_doc_user_id = self.env.user.id if rec._origin.id or rec.ttb_vendor_doc or rec.ttb_vendor_invoice else False

    ttb_sent_doc = fields.Boolean(string='Đã gửi tài liệu', default=False, copy=False, readonly=False)

    ttb_state_sequence = fields.Integer(string='State Sequence', compute='_compute_ttb_state_sequence', store=True)

    @api.depends('state')
    def _compute_ttb_state_sequence(self):
        """Compute state sequence for custom ordering"""
        state_order = {
            'assigned': 1,
            'confirmed': 2,
            'draft': 3,
            'done': 4,
            'cancel': 5,
            'waiting': 6,
        }
        for rec in self:
            rec.ttb_state_sequence = state_order.get(rec.state, 999)

    def sync_outgoing_stock_picking(self):
        conn = self.env['ttb.tools'].get_mssql_connection()
        cursor = conn.cursor()
        last_sync_outgoing_stock_date = str(self.env['ttb.tools'].get_mssql_config("mssql.last_sync_outgoing_stock_date", ""))
        sync_date_from = str(self.env['ttb.tools'].get_mssql_config("mssql.sync_date_from", "2023-10-02 00:00:00"))
        latest_date = last_sync_outgoing_stock_date
        date_to = fields.Datetime.now() - datetime.timedelta(seconds=10) + datetime.timedelta(hours=10)
        date_to = fields.Datetime.to_string(date_to)

        sql_date_from = f"AND SlNxM.InsertDate >= '{latest_date}'" if latest_date else ''
        sql_date_to = f"AND SlNxM.InsertDate <= '{date_to}'" if date_to else ''
        sql_sync_date_from = f"AND SlNxM.InsertDate >= '{sync_date_from}'"

        outgoing_stock_picking_query = f"""
                SELECT SlNxM.ID, SlNxM.Ngay_Ct, SlNxM.InsertDate, SlNxM.ID_Kho FROM SlNxM
                LEFT JOIN DmNx ON SlNxM.ID_Nx = DmNx.ID
                WHERE DmNx.Ma_Ct = 'PX'
                {sql_sync_date_from}
                {sql_date_from} {sql_date_to}
                ORDER BY SlNxM.ID ASC
                """
        cursor.execute(outgoing_stock_picking_query)
        res = cursor.fetchall()
        if not res: return

        for row in res:
            _logger.info(f"""Bắt đầu đồng bộ phiếu ID={row.ID}""")
            if not row.ID_Kho:
                _logger.info(f"Không thể đồng bộ phiếu xuất kho do ID_Kho có giá trị NULL ở ID: {row.ID}")
                continue
            if self.env['stock.picking'].search([('augges_id', '=', row.ID)]):
                _logger.info(f"Tìm thấy phiếu xuất kho có augges ID trùng với bản ghi {row.ID}, bỏ qua.")
                continue
            location_id = self.env['stock.warehouse'].sudo().with_context(active_test=False).search([('id_augges', '=', row.ID_Kho)], limit=1).lot_stock_id
            picking_type_id = self.env['stock.warehouse'].sudo().with_context(active_test=False).search([('id_augges', '=', row.ID_Kho)], limit=1).out_type_id
            if not location_id or not picking_type_id:
                _logger.info(f"""Không thể tìm được tồn kho tương ứng với ID_Kho = {row.ID_Kho} ở ID = {row.ID}""")
                continue
            stock_picking = self.env['stock.picking'].create({
                'augges_id': row.ID,
                'location_id': location_id.id,
                'picking_type_id': picking_type_id.id,
                'scheduled_date': row.Ngay_Ct,
                'origin': row.ID,
            })

            cursor.execute(f"""SELECT ID_Hang, So_Luong FROM SlNxD where ID = {row.ID} and ID_Hang is NOT NULL""")
            lines = cursor.fetchall()
            move_ids = []

            for line in lines:
                product_id = self.env['product.product'].sudo().with_context(active_test=False).search([('product_tmpl_id.augges_id', '=', line.ID_Hang)])
                if not product_id:
                    _logger.info(f"""Không tìm được sản phẩm có ID Augges = {line.ID_Hang} ở ID = {row.ID}""")
                    continue

                move_ids.append({
                    'name': product_id.display_name,
                    'location_id': stock_picking.location_id.id,
                    'location_dest_id': stock_picking.location_dest_id.id,
                    'product_id': product_id.id,
                    'product_uom_qty': float(line.So_Luong)
                })
            move_ids_list = []
            move_ids_list += [Command.create(move_id) for move_id in move_ids]
            stock_picking.move_ids = move_ids_list

            try:
                stock_picking.button_validate()
            except Exception as e:
                self.env.cr.rollback()
                _logger.info(f"""Không xác nhận được phiếu xuất kho tại ID = {row.ID}""")
                continue

            self.env.cr.commit()
            _logger.info(f"""Phiếu ID={row.ID} đã được đồng bộ""")
        # end đồng bộ

        latest_date = fields.Datetime.to_string(res[-1].InsertDate)
        self.env['ir.config_parameter'].sudo().set_param('mssql.last_sync_outgoing_stock_date', latest_date)
        cursor.close()
        conn.close()
        _logger.info("Sync phiếu xuất thành công")

    def sync_internal_stock_picking(self):
        conn = self.env['ttb.tools'].get_mssql_connection()
        cursor = conn.cursor()
        last_sync_internal_stock_date = str(self.env['ttb.tools'].get_mssql_config("mssql.last_sync_internal_stock_date", ""))
        latest_date = last_sync_internal_stock_date
        date_to = fields.Datetime.now() - datetime.timedelta(seconds=10) + datetime.timedelta(hours=10)
        date_to = fields.Datetime.to_string(date_to)
        sync_date_from = str(self.env['ttb.tools'].get_mssql_config("mssql.sync_date_from", "2023-10-02 00:00:00"))

        sql_date_from = f"AND InsertDate >= '{latest_date}'" if latest_date else ""
        sql_date_to = f"AND InsertDate <= '{date_to}'" if date_to else ""
        sql_sync_date_from = f"InsertDate >= '{sync_date_from}'"

        internal_stock_query = f"""
                SELECT ID, ID_KhoN, ID_KhoX, Ngay_Ct, InsertDate 
                FROM SlDcM WHERE {sql_sync_date_from} {sql_date_from} {sql_date_to} ORDER BY ID ASC"""

        cursor.execute(internal_stock_query)
        res = cursor.fetchall()
        if not res:
            _logger.info(f"""Không còn lệnh điều chuyển nội bộ để đồng bộ""")
            return
        for row in res:
            _logger.info(f"""Bắt đầu đồng bộ phiếu ID={row.ID}""")
            if not row.ID_KhoX or not row.ID_KhoN:
                _logger.info(f"Không thể đồng bộ phiếu điều chuyển nội bộ do ID_KhoX/ID_KhoN có giá trị NULL ở ID: {row.ID}")
                continue
            # To do: sửa lại logic tìm phiếu có augges_jd trùng
            if self.env['stock.picking'].search([('augges_id', '=', row.ID), ('picking_type_code', '=', 'internal')]):
                _logger.info(f"Tìm thấy phiếu nhập kho có augges ID trùng với bản ghi {row.ID}, bỏ qua.")
                continue
            location_id = self.env['stock.warehouse'].sudo().with_context(active_test=False).search([('id_augges', '=', row.ID_KhoX)]).lot_stock_id.id
            if not location_id:
                _logger.info(f"""Không thể tìm được tồn kho tương ứng với ID_KhoX = {row.ID_KhoX} ở ID = {row.ID}""")
                continue
            location_dest_id = self.env['stock.warehouse'].sudo().with_context(active_test=False).search([('id_augges', '=', row.ID_KhoN)]).lot_stock_id.id
            if not location_dest_id:
                _logger.info(f"""Không thể tìm được tồn kho tương ứng với ID_KhoN = {row.ID_KhoN} ở ID = {row.ID}""")
                continue
            picking_type_id = self.env['stock.warehouse'].sudo().with_context(active_test=False).search([('id_augges', '=', row.ID_KhoX)]).int_type_id.id

            cursor.execute(f"""SELECT ID_Hang, So_Luong FROM SlDcD WHERE ID={row.ID} AND ID_Hang IS NOT NULL""")
            lines = cursor.fetchall()
            move_ids = []
            for line in lines:
                product_id = self.env['product.product'].sudo().with_context(active_test=False).search([('product_tmpl_id.augges_id', '=', line.ID_Hang)])
                if not product_id:
                    _logger.info(f"""Không tìm được sản phẩm có ID Augges = {line.ID_Hang} ở ID = {row.ID}""")
                    continue
                move_ids.append({
                    'name': product_id.display_name,
                    'location_id': location_id,
                    'location_dest_id': location_dest_id,
                    'product_id': product_id.id,
                    'product_uom_qty': float(line.So_Luong)
                })

            stock_picking = self.env['stock.picking'].create({
                'augges_id': row.ID,
                'location_id': location_id,
                'location_dest_id': location_dest_id,
                'picking_type_id': picking_type_id,
                'scheduled_date': row.Ngay_Ct,
                'move_ids': [(0, 0, move_id) for move_id in move_ids],
                'origin': row.ID,
            })
            try:
                stock_picking.button_validate()
            except Exception as e:
                _logger.info(f"""Không xác nhận được phiếu xuất kho tại ID = {row.ID}""")
                self.env.cr.rollback()
                continue

            self.env.cr.commit()
            _logger.info(f"""Phiếu ID={row.ID} đã được đồng bộ""")

        latest_date = fields.Datetime.to_string(res[-1].InsertDate)
        self.env['ir.config_parameter'].sudo().set_param('mssql.last_sync_internal_stock_date', latest_date)
        cursor.close()
        conn.close()
        _logger.info("Sync phiếu nhập nội bộ thành công")

    def sync_return_stock_picking(self):
        conn = self.env['ttb.tools'].get_mssql_connection()
        cursor = conn.cursor()
        last_sync_return_stock_date = str(self.env['ttb.tools'].get_mssql_config("mssql.last_sync_return_stock_date", ""))
        latest_date = last_sync_return_stock_date
        date_to = fields.Datetime.now() - datetime.timedelta(seconds=10) + datetime.timedelta(hours=10)
        date_to = fields.Datetime.to_string(date_to)
        sync_date_from = str(self.env['ttb.tools'].get_mssql_config("mssql.sync_date_from", "2023-10-02 00:00:00"))

        sql_sync_date_from = f"AND SlNxM.InsertDate >= '{sync_date_from}'"
        sql_date_from = f"AND SlNxM.InsertDate >= '{latest_date}'" if latest_date else ""
        sql_date_to = f"AND SlNxM.InsertDate <= '{date_to}'" if date_to else ""

        return_stock_query = f"""
                    SELECT SlNxM.ID, SlNxM.Ngay_Ct, SlNxM.InsertDate, SlNxM.ID_Kho from SlNxM
                    LEFT JOIN DmNx  ON SlNxM.ID_Nx = DmNx.ID
                    WHERE DmNx.Ma_Ct = 'XL'
                    {sql_date_from} {sql_date_to}
                    {sql_sync_date_from}
                    ORDER BY ID ASC
                    """
        cursor.execute(return_stock_query)
        res = cursor.fetchall()
        if not res:
            _logger.info(f"""Không còn lệnh điều chuyển trả hàng cho nhà cung cấp để đồng bộ""")
            return
        for row in res:
            _logger.info(f"""Bắt đầu đồng bộ phiếu ID={row.ID}""")
            if not row.ID_Kho:
                _logger.info(f"Không thể đồng bộ phiếu điều chuyển nội bộ do ID_Kho có giá trị NULL ở ID: {row.ID}")
                continue
            if self.env['stock.picking'].search([('augges_id', '=', row.ID)]):
                _logger.info(f"Tìm thấy phiếu nhập kho có augges ID trùng với bản ghi {row.ID}, bỏ qua.")
                continue

            location_id = self.env['stock.warehouse'].sudo().with_context(active_test=False).search([('id_augges', '=', row.ID_Kho)]).lot_stock_id.id
            picking_type_id = self.env['stock.warehouse'].sudo().with_context(active_test=False).search([('id_augges', '=', row.ID_Kho)]).out_type_id.id
            if not location_id or not picking_type_id:
                _logger.info(f"""Không thể tìm được tồn kho tương ứng với ID_Kho = {row.ID_Kho} ở ID = {row.ID}""")
                continue

            cursor.execute(f"""SELECT ID_Hang, So_Luong FROM SlNxD WHERE ID={row.ID} AND ID_Hang IS NOT NULL""")
            lines = cursor.fetchall()
            move_ids = []
            for line in lines:
                product_id = self.env['product.product'].sudo().with_context(active_test=False).search([('product_tmpl_id.augges_id', '=', line.ID_Hang)])
                if not product_id:
                    _logger.info(f"""Không tìm được sản phẩm có ID Augges = {line.ID_Hang} ở ID = {row.ID}""")
                    continue
                move_ids.append({
                    'name': product_id.display_name,
                    'location_id': location_id,
                    'product_id': product_id.id,
                    'product_uom_qty': float(line.So_Luong)
                })

            stock_picking = self.env['stock.picking'].create({
                'augges_id': row.ID,
                'location_id': location_id,
                'picking_type_id': picking_type_id,
                'scheduled_date': row.Ngay_Ct,
                'move_ids': [(0, 0, move_id) for move_id in move_ids],
                'origin': row.ID,
            })
            try:
                stock_picking.button_validate()
            except Exception as e:
                _logger.info(f"""Không xác nhận được phiếu xuất kho tại ID = {row.ID}""")
                self.env.cr.rollback()
                continue

            self.env.cr.commit()
            _logger.info(f"""Phiếu ID={row.ID} đã được đồng bộ""")

        latest_date = fields.Datetime.to_string(res[-1].InsertDate)
        self.env['ir.config_parameter'].sudo().set_param('mssql.last_sync_return_stock_date', latest_date)
        cursor.close()
        conn.close()
        _logger.info("Sync phiếu trả hàng thành công")

    def sync_incoming_stock_picking(self):
        conn = self.env['ttb.tools'].get_mssql_connection()
        cursor = conn.cursor()
        last_sync_incoming_stock_date = str(self.env['ttb.tools'].get_mssql_config("mssql.last_sync_incoming_stock_date", ""))
        latest_date = last_sync_incoming_stock_date
        date_to = fields.Datetime.now() - datetime.timedelta(seconds=10) + datetime.timedelta(hours=10)
        date_to = fields.Datetime.to_string(date_to)
        sync_date_from = str(self.env['ttb.tools'].get_mssql_config("mssql.sync_date_from", "2023-10-02 00:00:00"))

        sql_date_from = f"AND SlNxM.InsertDate >= '{latest_date}'" if latest_date else ''
        sql_date_to = f"AND SlNxM.InsertDate <= '{date_to}'" if date_to else ''
        sql_sync_date_from = f"AND SlNxM.InsertDate >= '{sync_date_from}'"

        incoming_stock_picking_query = f"""
                    SELECT SlNxM.ID, SlNxM.Ngay_Ct, SlNxM.InsertDate, SlNxM.ID_Kho FROM SlNxM
                    LEFT JOIN DmNx ON SlNxM.ID_Nx = DmNx.ID
                    WHERE DmNx.Ma_Ct = 'PN'
                    {sql_date_from} {sql_date_to}
                    {sql_sync_date_from}
                    ORDER BY SlNxM.ID ASC"""

        cursor.execute(incoming_stock_picking_query)
        result = cursor.fetchall()
        if not result: return
        for row in result:
            _logger.info(f"""Bắt đầu đồng bộ phiếu ID={row.ID}""")
            if not row.ID_Kho:
                _logger.info(f"Không thể đồng bộ phiếu nhập do ID_Kho có giá trị NULL ở ID: {row.ID}")
                continue
            if self.env['stock.picking'].search([('augges_id', '=', row.ID)]):
                _logger.info(f"Tìm thấy phiếu nhập kho có augges ID trùng với bản ghi {row.ID}, bỏ qua.")
                continue
            location_dest_id = self.env['stock.warehouse'].sudo().with_context(active_test=False).search([('id_augges', '=', row.ID_Kho)], limit=1).lot_stock_id
            if not location_dest_id:
                _logger.info(f"Không tìm được kho có ID Augges = {row.ID_Kho} ở bản ghi = {row.ID}, bỏ qua.")
                continue
            picking_type_id = self.env['stock.warehouse'].sudo().with_context(active_test=False).search([('id_augges', '=', row.ID_Kho)], limit=1).in_type_id

            stock_picking = self.env['stock.picking'].create({
                'augges_id': row.ID,
                'location_dest_id': location_dest_id.id,
                'picking_type_id': picking_type_id.id,
                'scheduled_date': row.Ngay_Ct,
                'origin': row.ID,
            })
            cursor.execute(f"""SELECT ID_Hang, So_Luong FROM SlNxD where ID = {row.ID} and ID_Hang is NOT NULL""")
            lines = cursor.fetchall()
            move_ids = []

            for line in lines:
                product_id = self.env['product.product'].sudo().with_context(active_test=False).search([('product_tmpl_id.augges_id', '=', line.ID_Hang)])
                if not product_id:
                    _logger.info(f"Không tìm thấy sản phẩm khớp với ID_Hang: {line.ID_Hang} ở ID: {row.ID}")
                    continue

                move_ids.append({
                    'name': product_id.display_name,
                    'location_id': stock_picking.location_id.id,
                    'location_dest_id': location_dest_id.id,
                    'product_id': product_id.id,
                    'product_uom_qty': float(line.So_Luong)
                })

            move_ids_list = []
            move_ids_list += [Command.create(move_id) for move_id in move_ids]

            stock_picking.move_ids = move_ids_list
            try:
                stock_picking.with_context(no_check_document=True).button_validate()
            except Exception as e:
                print(e)
                _logger.info(f"""Không xác nhận được ở ID = {row.ID}""")
                self.env.cr.rollback()
                continue

            self.env.cr.commit()
            _logger.info(f"""Phiếu ID={row.ID} đã được đồng bộ""")

        latest_date = fields.Datetime.to_string(result[-1].InsertDate)
        self.env['ir.config_parameter'].sudo().set_param('mssql.last_sync_incoming_stock_date', latest_date)
        cursor.close()
        conn.close()
        _logger.info("Sync phiếu nhập thành công")

    def button_validate(self):
        res = super().button_validate()

        for picking in self:
            if picking.career_inventory:
               products_ticket = self.env['product.product'].search([
                   ('categ_id.name', 'in', [
                       'Vé KVC',
                       'Vé nhà tuyết',
                       'Vé xe điện, thú điện',
                       'Vé tháng'
                   ])
               ])
               pos_lines = self.env['pos.order.line'].search([
                   ('product_id', 'in', products_ticket.ids),
                   ('order_id.state', 'in', ['paid', 'done', 'invoiced'])
               ])
               total_ticket = sum(pos_lines.mapped('qty'))
               expected_loss = (total_ticket / 8000) * 50
               for move in picking.move_ids_without_package:
                   product = move.product_id
                   if not product.inventory_career:
                       continue

                    # Hao hụt thực tế
                   actual_loss = move.quantity - product.default_stock_qty

                   # Chênh lệch
                   diff = expected_loss - actual_loss

                   # Tỷ lệ
                   rate = 0
                   if expected_loss:
                       rate = diff / expected_loss

                   move.diff_qty = diff
                   move.diff_rate = rate

            if picking._is_internal_out_picking():
                picking._create_internal_in_picking()

            elif picking._is_internal_in_picking():
                picking._mark_request_received()

            self._update_consume_request_done()
        return res

    def _is_internal_out_picking(self):
        self.ensure_one()
        req = self.transfer_request_id

        return bool(
            req
            and self.picking_type_id.code == 'internal'
            and self in req.picking_ids
            and req.state == 'approved'
            and not req.in_picking_id
        )

    def _create_internal_in_picking(self):
        self.ensure_one()
        request = self.transfer_request_id

        if request.in_picking_id:
            return request.in_picking_id

        warehouse_src = request.source_warehouse_id
        warehouse_dest = request.dest_warehouse_id

        if not warehouse_dest:
            raise UserError('Phiếu đề nghị chưa có kho đích.')

        picking_type = self.env['stock.picking.type'].sudo().search([
            ('code', '=', 'internal'),
            ('warehouse_id', '=', warehouse_dest.id)
        ], limit=1)

        if not picking_type:
            raise UserError('Không tìm thấy loại điều chuyển nội bộ của kho đích.')

        moves = []
        for move in self.move_ids_without_package:
            done_qty = sum(move.move_line_ids.mapped('qty_done'))

            if done_qty <= 0:
                continue

            moves.append((0, 0, {
                'name': move.name,
                'product_id': move.product_id.id,
                'product_uom': move.product_uom.id,
                'product_uom_qty': done_qty,
                'location_id': warehouse_src.view_location_id.id,
                'location_dest_id': warehouse_dest.lot_stock_id.id,
            }))

        if not moves:
            raise UserError('Chưa có sản phẩm nào được xuất kho.')

            # Create incoming picking without auto-assigning a responsible user
        in_picking = self.env['stock.picking'].with_context(no_assign_user=True).create({
            'picking_type_id': picking_type.id,
            'location_id': warehouse_src.transit_location.id,
            'location_dest_id': warehouse_dest.lot_stock_id.id,
            'scheduled_date': fields.Datetime.now(),
            'origin': request.name,
            'transfer_request_id': request.id,
            'move_ids_without_package': moves,
            'user_id': False,  # Do not assign responsible user at creation
        })

        request.sudo().write({
            'in_picking_id': in_picking.id,
            'state': 'transfered'
        })

        return in_picking

    def _is_internal_in_picking(self):
        self.ensure_one()
        req = self.transfer_request_id

        return bool(
            req
            and self.picking_type_id.code == 'internal'
            and self.id == req.in_picking_id.id
            and req.state == 'transfered'
        )

    def _mark_request_received(self):
        self.ensure_one()
        request = self.transfer_request_id

        request.sudo().write({
            'state': 'cs_receive'
        })

    def _update_consume_request_done(self):
        self.ensure_one()
        for picking in self:
            if picking.picking_type_id.code != 'outgoing':
                continue

            request = picking.consume_request_id
            if not request:
                continue

            if request.state == 'approved':
                request.sudo().write({
                    'state': 'done'
                })

    def create(self, vals_list):
        # If caller requested to avoid assigning a responsible user on create,
        # remove user_id from the vals so no user is set by defaults/automation.
        if self.env.context.get('no_assign_user'):
            processed_vals_list = []
            for vals in vals_list:
                # Tạo bản sao dictionary để không làm ảnh hưởng đến dữ liệu gốc của hàm gọi
                new_vals = dict(vals) 
                new_vals.pop('user_id', None)
                processed_vals_list.append(new_vals)
            
            # Gán lại danh sách đã xử lý
            vals_list = processed_vals_list

        # 3. Gọi super().create với danh sách (multi-create)
        # Lưu ý: Kết quả trả về của super().create trong Odoo 18 là một Recordset
        pickings = super().create(vals_list)
        return pickings
