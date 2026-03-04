from odoo import api, fields, models, _
from odoo import tools
import logging
_logger = logging.getLogger(__name__)
from odoo.exceptions import UserError
from collections import defaultdict
from datetime import datetime, timedelta, time
import random

import traceback
from odoo.addons.ttb_tools.ai import product_similar_matcher as ttb_ai

USE_SND_MCH1_IDS = [10, 11, 12]
RATE_TARGET = 0.85
CASH_RATE = 0.08
CASH_RATE_MIN = 0.06
CASH_RATE_MAX = 0.1

class TtbPosInvoice(models.Model):
    _inherit = 'ttb.pos.invoice'

    branch_id = fields.Many2one('ttb.branch', 'Cơ sở', tracking=True)
    is_auto = fields.Boolean('Phiên tự động', default=False)
    pos_line_ids = fields.Many2many('pos.order.line', 'Dòng đơn hàng', compute='compute_pos_line_ids')
    pos_transfer_type = fields.Selection([('bank', 'Chuyển khoản'), ('cash', 'Tiền mặt')], 'Loại phiên')

    def compute_pos_line_ids(self):
        for rec in self:
            lines = self.env['pos.order.line']
            for pos in rec.pos_ids:
                lines |= pos.lines
            rec.pos_line_ids = lines

    def remove_0_vnd(self):
        for rec in self:
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

    def process_stock_not_enought(self):
        # Lấy danh sách sản phẩm không thay thế
        no_change_product_ids = {item.product_id.id for item in self.env['ttb.pos.product.no.change'].search([])}

        result_lines = []
        for pos in self.pos_ids.filtered(lambda x: not x.is_invoice_origin):
            warehouse = pos.warehouse_id
            location = warehouse.lot_stock_id
            
            is_changable_lines = pos.lines.filtered(lambda x: x.product_id.is_storable and x.qty != 0 and not x.product_id.ttb_bom_ids and x.product_id.id not in no_change_product_ids)
            for line in is_changable_lines:
                reserved_qty = sum(self.env['stock.move'].search([
                    ('pos_order_line_id', '=', line.id),
                    ('state', 'not in', ['cancel'])
                ]).mapped('quantity'))

                if reserved_qty < line.qty:
                    result_lines.append({
                        'pos_line_id': line.id,
                        'location_id': location.id,
                        'qty_to_replace': line.qty - reserved_qty
                    })

        return result_lines

    def get_available_stock_map(self, available_stock_map):
        # tồn kho hdt
        if not available_stock_map:
            location_id = self.branch_id.vat_warehouse_id.lot_stock_id.id
            stock_quants = self.env['stock.quant'].sudo().search([('location_id', '=', location_id), ('product_id.sale_ok', '=', True)])
            for stock_quant in stock_quants:
                product_id = stock_quant.product_id.id

                available_stock_map[product_id] = available_stock_map.get(product_id, {
                    'product': stock_quant.product_id,
                    'available_qty': 0
                })
                available_stock_map[product_id]['available_qty'] += stock_quant.quantity - stock_quant.reserved_quantity

        return available_stock_map

    def get_available_stock_map_snd(self, available_stock_map_snd):
        # tồn kho snd        
        if not available_stock_map_snd:
            location_id = self.branch_id.snd_location_id.id
            stock_quants = self.env['stock.quant'].sudo().search([('location_id', '=', location_id)]) if location_id else self.env['stock.location']
            for stock_quant in stock_quants:
                product_id = stock_quant.product_id.id

                available_stock_map_snd[product_id] = available_stock_map_snd.get(product_id, {
                    'product': stock_quant.product_id,
                    'available_qty': 0
                })
                available_stock_map_snd[product_id]['available_qty'] += stock_quant.quantity - stock_quant.reserved_quantity

        return available_stock_map_snd

    def make_sure_ai_vector(self, product):
        if not product.ai_vector:
            product._compute_ai_vector()
        if not product.ai_vector:
            raise UserError('Sản phẩm không có tên')

        return product.ai_vector

    def _find_candidate_product_common(self, available_stock_map, line, rate=False):
        qty_to_replace = line['qty_to_replace']
        pos_line = self.env['pos.order.line'].browse(line['pos_line_id'])
        original_product = pos_line.product_id
        original_product_id = original_product.id
        original_template = original_product.product_tmpl_id
        original_ai_vector = self.make_sure_ai_vector(original_template)

        product_ids = []
        product_ai_vectors = []
        for product_id in available_stock_map:
            if available_stock_map[product_id]['available_qty'] >= qty_to_replace:
                product_ids.append(product_id)
                product_ai_vectors.append(self.make_sure_ai_vector(available_stock_map[product_id]['product']))

        line['stock_name_number'] = len(product_ai_vectors)
        line['diff_name'] = 0
        product_change_id = False
        if product_ai_vectors:
            max_index, max_score = ttb_ai.get_candidate(original_ai_vector, product_ai_vectors)
            if not rate or max_score >= rate:
                product_change_id = product_ids[max_index]
                # Ghi nhận mảng kết quả và trừ số lượng đã sử dụng
                line['diff_name'] = max_score
                line['product_change_id'] = product_change_id
                available_stock_map[product_change_id]['available_qty'] -= qty_to_replace

        return product_change_id

    def find_candidate_product_hdt(self, available_stock_map, line, rate=False):
        return self._find_candidate_product_common(available_stock_map, line, rate)

    def find_candidate_product_snd(self, available_stock_map_snd, line):
        return self._find_candidate_product_common(available_stock_map_snd, line)

    def find_candidate_product(self, input_lines):
        """
        Đầu vào: danh sách dict {'pos_line_id', 'location_id', 'qty_to_replace'}
        Đầu ra: tạo record trong ttb.pos.product.invoice.change

        Logic xử lý:
        - Dựa vào bảng sản phẩm thay thế để lấy ra sản phẩm thay thế.
        - Trường hợp không tìm được sản phẩm thay thế thì lưu dữ liệu ra tab riêng
        """
        Quant = self.env['stock.quant']
        ChangeModel = self.env['ttb.pos.product.invoice.change']

        # Xoá dữ liệu liên kết cũ của invoice này
        ChangeModel.search([('pos_change_id', '=', self.id)]).unlink()
        ChangeModel.search([('pos_not_change_id', '=', self.id)]).unlink()

        # Lấy ra các sản phẩm thay thế cố định
        fix_change_product_ids = {item.product_id.id: item.change_product_id.id for item in self.env['ttb.pos.product.fix.change'].search([])}

        line_map = {}  # pos_line_id -> product_id
        product_to_subs = {}  # product_id -> list[ttb.substitute.product]

        quant_use = defaultdict(float)

        results = {}
        available_stock_map = {}
        available_stock_map_snd = {}
        _logger.info('Xuất HDDT sptt: Bắt đầu tìm sản phẩm thay thế. Số lượng: %s', len(input_lines))
        i = 0
        for line in input_lines:
            i += 1
            _logger.info('Xuất HDDT sptt: Cơ sở %s-%s, ca %s-%s, Xuất HDDT sptt Tìm sản phẩm thay thế cho sản phẩm %s/%s', self.branch_id.name, self.pos_transfer_type, self.context.get('xuat_hddt_time_from'), self.context.get('xuat_hddt_time_to'), i, len(input_lines))

            pos_line = self.env['pos.order.line'].browse(line['pos_line_id'])
            original_product = pos_line.product_id

            # Thay thế cố định
            if original_product.id in fix_change_product_ids:
                product_change_id = fix_change_product_ids[original_product.id].id
                line['product_change_id'] = product_change_id
                if product_change_id not in available_stock_map:
                    available_stock_map[product_change_id] = {
                        'product': fix_change_product_ids[original_product.id],
                        'available_qty': 0
                    }

                available_stock_map[product_change_id]['available_qty'] -= line['qty_to_replace']
                continue

            if original_product.product_tmpl_id.categ_id_level_1.id in USE_SND_MCH1_IDS:
                self.find_candidate_product_snd(self.get_available_stock_map_snd(available_stock_map_snd), line) \
                    or self.find_candidate_product_hdt(self.get_available_stock_map(available_stock_map), line)
            # Tạm thời tối ưu bằng cách tìm 1 vòng, không tìm 2 vòng 0.85 rồi tìm full nữa.
            # else:
            #     self.find_candidate_product_hdt(self.get_available_stock_map(available_stock_map), line, RATE_TARGET) \
            #         or self.find_candidate_product_snd(self.get_available_stock_map_snd(available_stock_map_snd), line) \
            #         or self.find_candidate_product_hdt(self.get_available_stock_map(available_stock_map), line)
            else:
                self.find_candidate_product_hdt(self.get_available_stock_map(available_stock_map), line) \
                    or self.find_candidate_product_snd(self.get_available_stock_map_snd(available_stock_map_snd), line)


        # Bắt đầu xử lý từng dòng
        for line in input_lines:
            pos_line_id = line['pos_line_id']
            qty_to_replace = line['qty_to_replace']
            pos_line = self.env['pos.order.line'].browse(pos_line_id)

            vals = {
                'pos_id': pos_line.order_id.id,
                'pos_line_id': pos_line_id,
                'product_origin_id': pos_line.product_id.id,
                'qty_origin': pos_line.qty,
                'qty_needed': qty_to_replace,
                'diff_name' : line['diff_name'],
                'stock_name_number' : line['stock_name_number'],
            }
            if line.get('product_change_id'):
                vals['pos_change_id'] = self.id
                vals['product_change_id'] = line['product_change_id']
            else:
                line['pos_not_change_id'] = self.id
            ChangeModel.create(vals)

    def button_done_auto(self):
        errors = []
        if any(not line.product_change_id for line in self.product_change_ids) or any(not line.product_change_id for line in self.product_not_change_ids):
            errors.append('Bạn chưa điền sản phẩm thay thế, vui lòng kiểm tra lại.')
        if errors:
            raise UserError(' '.join(errors))

        self.apply_tax_and_change_product()

        self.write({'state': 'waiting'})

    def apply_tax_and_stock(self):
        # Áp dụng thuế và tạo stock.picking
        for pos in self.pos_ids:
            # _logger.info('Xuất chi tiết HDDT. Xử lý thuế. Phiên %s. Đơn %s', str(self.mapped('name')), pos.id)
            for line in pos.lines:
                product_id = line.product_id
                tax_ids = False

                # ('4', 'Thuế sản phẩm (Odoo)'),
                if not tax_ids:
                    tax_ids = product_id.taxes_id
                    tax_case = '4'

                # ('1', 'MCH5'),
                if not tax_ids:
                    tax_ids = product_id.categ_id_level_5.ttb_tax_id
                    tax_case = '1'

                # ('3', 'Kế toán điền ở tab dòng không thuế'),
                if not tax_ids:
                    last_line = self.env['ttb.pos.product.invoice.change'].search([
                        ('pos_notax_id', '!=', False), 
                        ('product_origin_id', '=', product_id.id), 
                        ('tax_ids', '!=', False)
                    ], order='id desc', limit=1)
                    if last_line:
                        tax_ids = last_line.tax_ids
                    tax_case = '3'

                # # ('2', 'Thuế sản phẩm (Augges)'),
                # if not tax_ids:
                #     tax_ids = line.tax_ids
                #     tax_case = '2'

                # ('5', 'Thuế cố định 8%'),
                if not tax_ids:
                    tax_ids = self.env['account.tax'].browse(12) # thuế 8%
                    tax_case = '5'

                line.tax_ids = tax_ids
                line.tax_case = tax_case

                line._onchange_amount_line_all()
            pos._compute_prices()

            pos._create_order_picking()

    def apply_tax_and_change_product(self):
        # product_notax_ids = self.product_notax_ids.filtered(lambda x: not x.tax_ids)
        
        # for line in self.product_notax_ids:
        #     tax_ids = line.tax_ids
        #     product_id = line.product_origin_id.id

        #     if not tax_ids:
        #         last_line = self.env['ttb.pos.product.invoice.change'].search([('product_origin_id', '=', product_id), ('tax_ids', '!=', False)], order='id desc', limit=1)
        #         if last_line:
        #             tax_ids = last_line.tax_ids
        #     if not tax_ids:
        #         tax_ids = line.product_origin_id.taxes_id

        #     if not tax_ids:
        #         tax_ids = self.env['account.tax'].browse(11) # thuế 10%

        #     # Gán thuế
        #     pos_line_id = line.pos_line_id
        #     pos_line_id.tax_ids = tax_ids
        #     pos_line_id._onchange_amount_line_all()
        #     pos_line_id.order_id._compute_prices()

        # for line in self.product_hastax_ids.filtered(lambda x: x.tax_ids and x.pos_line_id.tax_ids != x.tax_ids):
        #     tax_ids = line.tax_ids
        #     # Gán thuế
        #     pos_line_id = line.pos_line_id
        #     pos_line_id.tax_ids = tax_ids
        #     pos_line_id._onchange_amount_line_all()
        #     pos_line_id.order_id._compute_prices()

        # sản phẩm thay thế
        # pos_ids = self.product_change_ids.pos_line_id.order_id
        _logger.info('Xuất HDDT. Bắt đầu tự động bước Thay sản phẩm thay thế. Phiên %s', str(self.mapped('name')))
        for line in self.product_change_ids:
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
                # 'tax_ids': [(6, 0, tax_ids)],
            }
            new_line = self.env['pos.order.line'].create(vals)
            # new_line._onchange_amount_line_all()

            if line.pos_line_id.qty <= line.qty_needed:
                #Nếu số lượng line mà bằng số lượng cần tức là phải xóa line, và chỉ thay thế sản phẩm
                line.pos_line_id.with_context(allow_delete=True).unlink()
            else:
                # Nếu số lượng line mà nhỏ hơn số lượng cần thì sinh line thay thế sản phẩm và sửa tồn cần
                line.pos_line_id.write({'qty': line.pos_line_id.qty - line.qty_needed})
                # line.pos_line_id._onchange_amount_line_all()

            # pos_ids._compute_prices()

        _logger.info('Xuất HDDT. Bắt đầu tự động bước Áp dụng thuế và tạo stock picking. Phiên %s', str(self.mapped('name')))
        self.apply_tax_and_stock()

    def process_bom_product(self, pos):
        location_id = self.branch_id.vat_warehouse_id.lot_stock_id.id
        picking_type = pos.config_id.picking_type_id
        dest_location = self.env.ref('stock.stock_location_production', raise_if_not_found=False) or picking_type.default_location_dest_id

        bom_pos_line_ids = pos.lines.filtered(lambda x: x.product_id.ttb_bom_ids)
        move_vals = {}
        for pos_line in bom_pos_line_ids:
            product_id = pos_line.product_id
            bom_id = product_id.ttb_bom_ids[0]
            components = bom_id.ttb_explode(pos_line.qty)

            all_product_ids = self.env['product.product']

            required_materials = defaultdict(float)
            for component_line, data in components:
                if component_line.product_id.type != 'service':
                    all_product_ids |= component_line.product_id
                    required_materials[component_line.product_id] += data['qty']

            all_product_ids |= all_product_ids.alternative_product_ids.product_variant_id
            stock_quants = self.env['stock.quant'].sudo().search([('location_id', '=', location_id), ('product_id', 'in', all_product_ids.ids)])
            available_stock_map = {}
            for stock_quant in stock_quants:
                product_id = stock_quant.product_id.id

                available_stock_map[product_id] = available_stock_map.get(product_id, {
                    'product': stock_quant.product_id,
                    'available_qty': 0
                })
                available_stock_map[product_id]['available_qty'] += stock_quant.quantity - stock_quant.reserved_quantity

            move_vals = []
            for component_line, data in components:
                product_id = component_line.product_id
                qty = data['qty']

                product_ids = product_id | product_id.alternative_product_ids.product_variant_id
                for product in product_ids:
                    product_id = product.id
                    available_qty = available_stock_map[product_id]['available_qty'] if product_id in available_stock_map else 0

                    use_qty = min(available_qty, qty)
                    if product_id in available_stock_map and use_qty != 0:
                        available_stock_map[product_id]['available_qty'] -= use_qty
                    qty -= use_qty

                    if use_qty > 0:
                        move_vals.append({
                            'name': _('NVL cho PoS: %s') % product.display_name,
                            'product_id': product_id,
                            'product_uom': product.uom_id.id,
                            'product_uom_qty': use_qty,
                            'picking_type_id': picking_type.id,
                            'location_id': location_id,
                            'location_dest_id': dest_location.id,
                            'company_id': self.env.company.id,
                        })

                    if qty <= 0:
                        break
            if move_vals:
                picking = self.env['stock.picking'].create({
                    'pos_order_id': pos.id,
                    'picking_type_id': picking_type.id,
                    'location_id': location_id,
                    'location_dest_id': dest_location.id,
                    'origin': pos.name,
                    # 'move_ids_without_package': move_vals
                })
                for vals in move_vals:
                    vals['picking_id'] = picking.id

                moves = self.env['stock.move'].create(move_vals)
                moves._action_confirm()
                picking._action_done()
                picking.button_validate()

    def stock_reserve(self, pos_ids):
        Picking = self.env['stock.picking'].with_context(ignore_merge_moves=True)

        for pos in pos_ids:
            warehouse = pos.warehouse_id
            location = warehouse.lot_stock_id
            picking_type = self.env['stock.picking.type'].search([
                ('code', '=', 'internal'),
                ('warehouse_id', '=', warehouse.id)
            ], limit=1)

            move_vals = []
            # Giữ tồn cho các Sản phẩm lưu kho
            is_storable_lines = pos.lines.filtered(lambda x: x.product_id.is_storable and x.qty != 0)

            for line in is_storable_lines:
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
                picking.action_assign() # ThienTD: Tại sao phải asssign?

    def stock_unreserve(self):
        for pos in self.pos_ids:
            if pos.reserve_picking_ids:
                pos.reserve_picking_ids.action_cancel()

    def button_ready_auto(self):
        for pos_invoice in self:
            pos_invoice.remove_0_vnd()
            # pos_invoice.process_line_notax()
            
            # Giữ tồn cho sản phẩm trong live
            pos_invoice.stock_reserve(pos_invoice.pos_ids.filtered(lambda x: x.is_invoice_origin))
            pos_invoice.stock_reserve(pos_invoice.pos_ids.filtered(lambda x: not x.is_invoice_origin))

            result_lines = pos_invoice.process_stock_not_enought()
            pos_invoice.find_candidate_product(result_lines)

            pos_invoice.stock_unreserve()
            pos_invoice.state = 'waiting_approve'

    def xuat_hddt_tu_dong(self, branch_ids, to_step=4, kvc=True, time_from=False, time_to=False):
        config_name = 'xuat_hddt.thoi_gian_xuat_gan_nhat'
        today = datetime.today().date()

        if time_to:
            hour = int(time_to)
            minute = int(round((time_to - hour) * 60))
            # Không phải UTC nên phải trừ đi 7h
            new_ngay_xuat = datetime.combine(today, time(hour, minute, 0)) - timedelta(hours=7)
        else:
            # UTC
            new_ngay_xuat = datetime.now() - timedelta(seconds=10)


        if time_from:
            hour = int(time_from)
            minute = int(round((time_from - hour) * 60))
            # Không phải UTC nên phải trừ đi 7h
            old_ngay_xuat = datetime.combine(today, time(hour, minute, 0)) - timedelta(hours=7)
        else:
            old_ngay_xuat_str = self.env["ir.config_parameter"].sudo().get_param(config_name)
            if old_ngay_xuat_str:
                old_ngay_xuat = datetime.fromisoformat(old_ngay_xuat_str)
            else:
                # Không phải UTC nên phải trừ đi 7h
                old_ngay_xuat = datetime.combine(today, time(6, 0, 0)) - timedelta(hours=7)

        IrConfig = self.env['ir.config_parameter'].sudo()
        configured_11220 = IrConfig.get_param('ttb_purchase_invoice_stock.augges_no_tk')

        if not configured_11220:
            raise UserError('Chưa cấu hình tài khoản chuyển khản (112220)')

        domain = [
            ('create_date', '>=', old_ngay_xuat),
            ('create_date', '<', new_ngay_xuat),
            ('augges_no_tk', '=', configured_11220),
            ('amount_total', '>', 1),
            ('name', 'ilike', 'HDT'),
            ('ttb_einvoice_manual', '!=', True),
            # todo: check đk 
            # ("state", "=", "draft")
            '|', ('ttb_einvoice_state', '=', 'new'), ('ttb_einvoice_state', '=', False)
        ]
        if not kvc:
            domain += [("id_quay_augges", "not ilike", "kvc")]

        # Lấy ra các cơ sở
        branchs = branch_ids or self.env['ttb.branch'].sudo().search([])
        for branch in branchs:
            vat_warehouse_id = branch.vat_warehouse_id
            note = 'Tự động xuất hoá đơn chuyển khoản.\nThời gian %s -> %s' % (
                (old_ngay_xuat + timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S"), 
                (new_ngay_xuat + timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S"), 
            )
            pos_invoice = self.sudo().search([
                ('branch_id', '=', branch.id),
                ('note', 'ilike', note)
            ])

            if pos_invoice:
                continue

            pos_ids = self.env['pos.order'].search(domain + [('ttb_branch_id', '=', branch.id), ('warehouse_id', '=', vat_warehouse_id.id), '|', ('ttb_einvoice_state', '=', 'new'), ('ttb_einvoice_state', '=', False)])
            if pos_ids:
                pos_invoice = self.create({
                    'branch_id': branch.id,
                    'pos_ids': pos_ids.ids,
                    'note': note,
                    'is_auto': True,
                    'pos_transfer_type': 'bank',
                })

                _logger.info('Xuất HDDT CK. Bắt đầu tự động bước 1. Tạo Phiên %s. Cơ sở: %s', pos_invoice.name, pos_invoice.branch_id.name)

                if to_step >= 2:
                    _logger.info('Xuất HDDT CK. Bắt đầu tự động bước 2. Phiên %s. Cơ sở %s', pos_invoice.name, pos_invoice.branch_id.name)
                    pos_invoice.button_ready_auto()
                    # pos_invoice.state = 'waiting_approve'
                if to_step >= 3:
                    _logger.info('Xuất HDDT CK. Bắt đầu tự động bước 3. Phiên %s. Cơ sở %s', pos_invoice.name, pos_invoice.branch_id.name)
                    pos_invoice.apply_tax_and_change_product()
                    pos_invoice.write({'state': 'waiting'})
                if to_step >= 4:
                    _logger.info('Xuất HDDT CK. Bắt đầu tự động bước 4. Phiên %s. Cơ sở %s', pos_invoice.name, pos_invoice.branch_id.name)
                    pos_invoice.button_create_public_einvoice()

        if not time_from and not time_to:
            self.env["ir.config_parameter"].sudo().set_param(config_name, new_ngay_xuat.isoformat())

    def process_cash_rate(self, cash_amount):
        amount_all = sum(pos.amount_total for pos in self.pos_ids)
        _logger.info('Xuất HDDT TM. Tổng tiền phiên: %s. Mục tiêu: %s', amount_all, cash_amount)

        # sorted_pos_ids = self.pos_ids.sorted('amount_total', reverse=True)
        # Tính riêng đơn xuất hoá đơn nguyên bản
        pos_ids = self.pos_ids.filtered(lambda x: x.is_invoice_origin)
        amount = sum(pos_ids.mapped('amount_total'))
        if amount < cash_amount:
            for pos in self.pos_ids.filtered(lambda x: not x.is_invoice_origin):
                amount += pos.amount_total
                _logger.info('Sử dụng đơn %s', pos.id)
                pos_ids |= pos

                if amount > cash_amount:
                    break

        self.pos_ids = pos_ids

    def xuat_hddt_tu_dong_tien_mat(self, branch_ids, to_step=4, kvc=True, time_from=False, time_to=False, khop_tien_mat=False):
        today = datetime.today().date()

        if time_to:
            hour = int(time_to)
            minute = int(round((time_to - hour) * 60))
            # Không phải UTC nên phải trừ đi 7h
            new_ngay_xuat = datetime.combine(today, time(hour, minute, 0)) - timedelta(hours=7)
        else:
            # UTC
            new_ngay_xuat = datetime.now() - timedelta(seconds=10)

        if time_from:
            hour = int(time_from)
            minute = int(round((time_from - hour) * 60))
            # Không phải UTC nên phải trừ đi 7h
            old_ngay_xuat = datetime.combine(today, time(hour, minute, 0)) - timedelta(hours=7)
        else:
            # Không phải UTC nên phải trừ đi 7h
            old_ngay_xuat = datetime.combine(today, time(6, 0, 0)) - timedelta(hours=7)

        IrConfig = self.env['ir.config_parameter'].sudo()
        configured_11220 = IrConfig.get_param('ttb_purchase_invoice_stock.augges_no_tk')

        if not configured_11220:
            raise UserError('Chưa cấu hình tài khoản chuyển khản (112220)')

        domain_common = [
            ('create_date', '>=', old_ngay_xuat),
            ('create_date', '<', new_ngay_xuat),
            ('augges_no_tk', '!=', configured_11220),
            ('amount_total', '>', 1),
            ('name', 'ilike', 'HDT'),
            ('ttb_einvoice_manual', '!=', True),
            # todo: check đk 
            # ("state", "=", "draft")
            '|', ('ttb_einvoice_state', '=', 'new'), ('ttb_einvoice_state', '=', False)
        ]
        if not kvc:
            domain_common += [("id_quay_augges", "not ilike", "kvc")]

        # Lấy ra các cơ sở
        branchs = branch_ids or self.env['ttb.branch'].sudo().search([])
        for branch in branchs:
            vat_warehouse_id = branch.vat_warehouse_id
            note = 'Tự động xuất hoá đơn tiền mặt.\nThời gian %s -> %s' % (
                (old_ngay_xuat + timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S"), 
                (new_ngay_xuat + timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S"), 
            )
            pos_invoice = self.sudo().search([
                ('branch_id', '=', branch.id),
                ('note', 'ilike', note)
            ])

            if pos_invoice:
                continue

            domain_branch = [('ttb_branch_id', '=', branch.id), ('warehouse_id', '=', vat_warehouse_id.id)]
            pos_ids = self.env['pos.order'].search(domain_common + domain_branch)
            if pos_ids:
                pos_invoice = self.create({
                    'branch_id': branch.id,
                    'pos_ids': pos_ids.ids,
                    'note': note,
                    'is_auto': True,
                    'pos_transfer_type': 'cash',
                })

                _logger.info('Xuất HDDT TM. Bắt đầu tự động bước 1. Tạo Phiên %s', pos_invoice.name)

                if to_step >= 2:
                    _logger.info('Xuất HDDT TM. Bắt đầu tự động bước 2. Phiên %s', pos_invoice.name)
                    pos_invoice.button_ready()
                    # pos_invoice.state = 'waiting_approve'

                    # Tính tiền ck từ đầu ngày
                    start_of_day = datetime.combine(today, time(6, 0, 0)) - timedelta(hours=7)
                    domain_bank = [
                        ('create_date', '>=', start_of_day),
                        ('create_date', '<', new_ngay_xuat),
                        ('augges_no_tk', '=', configured_11220),
                        ('amount_total', '>', 1),
                        ('name', 'ilike', 'HDT'),
                    ]
                    if not kvc:
                        domain_bank += [("id_quay_augges", "not ilike", "kvc")]
                    bank_pos_ids = self.env['pos.order'].search(domain_bank + domain_branch)
                    bank_amount_all = sum(pos.amount_total for pos in bank_pos_ids)

                    # Tính tiền ck của phiên hiện tại
                    domain_bank = [
                        ('create_date', '>=', old_ngay_xuat),
                        ('create_date', '<', new_ngay_xuat),
                        ('augges_no_tk', '=', configured_11220),
                        ('amount_total', '>', 1),
                        ('name', 'ilike', 'HDT'),
                    ]
                    if not kvc:
                        domain_bank += [("id_quay_augges", "not ilike", "kvc")]
                    bank_pos_ids = self.env['pos.order'].search(domain_bank + domain_branch)
                    bank_amount_current = sum(pos.amount_total for pos in bank_pos_ids)
                    
                    # Tính tiền tiền mặt đã xuất từ đầu ngày
                    domain_cash_invoiced = [
                        ('create_date', '>=', start_of_day),
                        ('create_date', '<', new_ngay_xuat),
                        ('augges_no_tk', '!=', configured_11220),
                        ('name', 'ilike', 'HDT'),
                        ('ttb_einvoice_state', 'in', ('created', 'published'))
                    ]
                    cash_invoiced_pos_ids = self.env['pos.order'].search(domain_cash_invoiced + domain_branch)
                    cash_invoiced_amount = sum(pos.amount_total for pos in cash_invoiced_pos_ids)

                    cash_amount_all = round(CASH_RATE * bank_amount_all)
                    cash_amount_target = cash_amount_all - cash_invoiced_amount
                    cash_amount_min = round(CASH_RATE_MIN * bank_amount_current)
                    cash_amount_max = round(CASH_RATE_MAX * bank_amount_current)


                    cash_case = ''
                    if cash_amount_target <= cash_amount_min:
                        cash_amount = cash_amount_min
                        cash_case = f'Nhỏ hơn {CASH_RATE_MIN * 100}%'
                    elif cash_amount_target >= cash_amount_max:
                        cash_amount = cash_amount_max
                        cash_case = f'Lớn hơn {CASH_RATE_MAX*100}%'
                    else:
                        if khop_tien_mat:
                            cash_amount = cash_amount_target
                            cash_case = 'Khớp tiền mặt'
                        else:
                            cash_amount = random.randint(cash_amount_min, cash_amount_max)
                            cash_case = f'Ngẫu nhiên trong khoảng ({CASH_RATE_MIN * 100}%, {CASH_RATE_MAX*100}%)'

                    _logger.info('Xuất HDDT TM. Tổng ck từ đầu ngày: %s. Tổng ck phiên hiện tại: %s. Tổng tm đã xuất hoá đơn từ đầu ngày: %s. Tiền cần xuất: %s. Case tạo: %s', 
                        bank_amount_all, 
                        bank_amount_current, 
                        cash_invoiced_amount,
                        cash_amount,
                        cash_case
                    )

                    pos_invoice.process_cash_rate(cash_amount)
                if to_step >= 3:
                    _logger.info('Xuất HDDT TM. Bắt đầu tự động bước 3. Phiên %s', pos_invoice.name)
                    # pos_invoice.apply_tax_and_change_product()
                    # Gọi 2 hàm giống nhau nhưng để cho chắc ăn gọi hàm chỉ xử lý thuế và tạo stock_picking
                    pos_invoice.apply_tax_and_stock()
                    pos_invoice.write({'state': 'waiting'})
                if to_step >= 4:
                    _logger.info('Xuất HDDT TM. Bắt đầu tự động bước 4. Phiên %s', pos_invoice.name)
                    pos_invoice.button_create_public_einvoice()

    def cron_finish_pos_invoice(self):
        pos_invoices = self.sudo().search([('date', '>', fields.Date.today()), ('state', '=', 'waiting_approve'), ('note', 'ilike', 'Tự động')])

        for pos_invoice in pos_invoices:
            _logger.info('Xác nhận tự động phiên: %s' % pos_invoice.name)
            try:
                pos_invoice.button_done_auto()
                self.env.cr.commit()
                pos_invoice.button_create_public_einvoice()
            except Exception as e:
                self.env.cr.rollback()
                pos_invoice.message_post(body='Xác nhận phiên lỗi %s' % str(e))
                self.env.cr.commit()

    def refresh_invoice_number(self):
        for error_pos in self.pos_ids.filtered(lambda x: x.amount_total > 0 and x.account_move.ttb_einvoice_state != 'published'):
            error_pos.account_move.auto_invoice_number()
            
        if all(pos.amount_total == 0 or pos.account_move.ttb_einvoice_state == 'published' for pos in self.pos_ids):
            self.state = 'done'

    def cron_retry_pos_invoice(self):
        pos_invoices = self.sudo().search([('date', '>', fields.Date.today()), ('state', '=', 'done_partial')])

        for pos_invoice in pos_invoices:
            pos_invoice.refresh_invoice_number()
            if pos_invoice.state != 'done':
                pos_invoice.create_public_einvoice()
                pos_invoice.refresh_invoice_number()
