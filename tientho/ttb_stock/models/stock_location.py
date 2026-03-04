import io
import json
import xlsxwriter
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class StockLocation(models.Model):
    _inherit = 'stock.location'

    qr_image = fields.Binary(string="Hình ảnh QR", compute='_compute_qr_image', store=True)
    stock_location_detail_line_ids = fields.One2many(comodel_name='stock.location.detail.lines',
                                                     inverse_name='stock_location_id', store=True)
    show_button_print = fields.Boolean(string='Hiện button In tem', compute='_compute_show_button_print')

    @api.depends('stock_location_detail_line_ids.select')
    def _compute_show_button_print(self):
        for rec in self:
            if rec.stock_location_detail_line_ids.filtered_domain([('select', '=', True)]):
                rec.show_button_print = True
            else:
                rec.show_button_print = False

    @api.depends('barcode')
    def _compute_qr_image(self):
        for rec in self:
            rec.qr_image = rec.generate_qr_code(rec.barcode)

    def get_xlxs_report(self, data):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        cell_format = workbook.add_format(
            {'font_size': '12px', 'align': 'center'}
        )
        header_format = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '20px'})

        headers = ['STT', 'Mã sản phẩm', 'Tên sản phẩm', 'Giá', 'MCH5']

        worksheet = workbook.add_worksheet()

        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)

        worksheet.set_column(1, 1, 20)
        worksheet.set_column(2, 2, 40)
        worksheet.set_column(4, 4, 40)

        for key, val in enumerate(data, start=1):
            worksheet.write(key, 0, key, cell_format)
            worksheet.write(key, 1, val.get('code', ''), cell_format)
            worksheet.write(key, 2, val.get('product_name', ''), cell_format)
            worksheet.write(key, 3, val.get('price', ''), cell_format)
            worksheet.write(key, 4, val.get('mch_code', ''), cell_format)

        workbook.close()
        output.seek(0)

        return output.read()

    def button_print(self):
        self.ensure_one()
        selected = self.stock_location_detail_line_ids.filtered(lambda r: r.select == True)

        if selected:
            data = []
            for line in selected:
                data.append({
                    'code': line.code,
                    'product_name': line.product_id.display_name or '',
                    'price': line.product_id.product_tmpl_id.standard_price or '',
                    'mch_code': line.product_id.product_tmpl_id.categ_id_level_5.display_name or '',
                })

            action = {
                'type': 'ir.actions.act_url',
                'url': '/ttb_xlsx_report?model=stock.location&data=%s' % json.dumps(data),
            }

            for rec in selected:
                rec.select = False

        else:
            action = {
                'warning': {
                    'title': _("Warning"),
                    'message': _("Vui lòng chọn ít nhất một sản phẩm để in.")
                }
            }

        return action

    def button_discharge(self):
        self.ensure_one()
        lines = self.stock_location_detail_line_ids
        if lines:
            data = []
            for line in lines:
                data.append({
                    'code': line.code,
                    'product_name': line.product_id.display_name or '',
                    'price': line.product_id.product_tmpl_id.standard_price or '',
                    'mch_code': line.product_id.product_tmpl_id.categ_id_level_5.display_name or '',
                })

            return {
                'type': 'ir.actions.act_url',
                'url': '/ttb_xlsx_report?model=stock.location&data=%s' % json.dumps(data),
            }

        return {
            'warning': {
                'title': _("Warning"),
                'message': _("Không có sản phẩm để in")
            }
        }


class StockLocationDetailLines(models.Model):
    _name = 'stock.location.detail.lines'
    _order = 'order_number, id'
    _description = 'Quản lý danh sách PID'
    _rec_name = 'destination_location_id'

    @api.constrains('order_number')
    def _check_order_number(self):
        for rec in self:
            new_order_number = rec.order_number

            if self.search([('order_number', '=', new_order_number), ('id', '!=', rec.id), ('stock_location_id', '=', rec.stock_location_id.id)]):
                raise ValidationError('Vị trí này đã tồn tại')

    @api.depends('stock_location_id')
    def _compute_order_number(self):
        for rec in self:
            if rec.stock_location_id.stock_location_detail_line_ids:
                rec.order_number = max(rec.stock_location_id.stock_location_detail_line_ids.mapped('order_number')) + 1
            else:
                rec.order_number = 1

    stock_location_id = fields.Many2one(comodel_name='stock.location', string='Địa điểm')
    order_number = fields.Integer(string='Vị trí', compute='_compute_order_number', store=True, readonly=False,
                                  precompute=True)
    product_id = fields.Many2one(string='Sản phẩm', comodel_name='product.product')
    code = fields.Char(string='Mã sản phẩm', compute='_compute_code', store=True)
    destination_location_id = fields.Many2one(string='Địa điểm tồn kho', comodel_name='stock.location', readonly=True)

    quantity = fields.Float(string='Số lượng tồn', default=0)
    select = fields.Boolean(string='In tem', default=False)

    @api.model_create_multi
    def create(self, vals_list):
        res = super(StockLocationDetailLines, self).create(vals_list)
        res._compute_destination_location_id()
        return res

    def write(self, values):
        res = super().write(values)
        if 'order_number' in values:
            self._compute_destination_location_id()
        return res

    @api.depends('product_id.barcode', 'product_id.default_code')
    def _compute_code(self):
        for rec in self:
            if rec.product_id.barcode:
                rec.code = rec.product_id.barcode
            else:
                rec.code = rec.product_id.default_code

    def _compute_destination_location_id(self):
        for rec in self:
            domain = ['&', '&', ('name', '=', rec.order_number),
                      ('location_id', '=', rec.stock_location_id.id),
                      ('usage', '=', 'internal')]
            destination = self.env['stock.location'].sudo().search(domain)

            if destination:
                rec.destination_location_id = destination.id

            else:
                if not rec.stock_location_id.barcode:
                    raise ValidationError(f'Địa điểm tồn kho {rec.stock_location_id.name} chưa có mã địa điểm!')
                rec.destination_location_id = self.env['stock.location'].sudo().create({
                    'name': rec.order_number,
                    'location_id': rec.stock_location_id.id,
                    'usage': 'internal',
                    'scrap_location': False,
                    'replenish_location': False,
                    'barcode': f"{rec.stock_location_id.barcode or ''}{rec.order_number:04d}"
                })
