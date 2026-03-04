# -*- coding: utf-8 -*-
import uuid
import pytz, math
from datetime import datetime
from odoo import Command, models, fields, api, _
from odoo.tools import html2plaintext, is_html_empty
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta

import logging
from datetime import datetime, timedelta
_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    shelf_location = fields.Char(string='Thứ tự kiểm Quầy/Kệ')
    inventory_origin_id = fields.Many2one('stock.picking', 'Phiếu kiểm kê gốc', index=True)
    inventory_related_ids = fields.One2many('stock.picking', 'inventory_origin_id', 'Phiếu kiểm kê liên quan')

    diff_product_count = fields.Integer(string='Số mặt hàng lệch', help='Đếm số lượng sản phẩm bị lệch')
    diff_product_rate = fields.Float('Tỉ lệ lệch(%)', store=True, default=0)
    total_diff_qty = fields.Float(string='Tổng chênh lệch', store=True)
    support_user_ids = fields.Many2many(
        'res.users',
        'stock_picking_support_user_rel',
        'picking_id',
        'user_id',
        string='Người phụ trách hỗ trợ',
        help='Những người phụ trách hỗ trợ cho phiếu kiểm kê này',
        tracking=True
    )
    disable_inventory = fields.Boolean(string='Là phiếu kiểm trùng', help='Nếu được chọn, phiếu kiểm kê này là phiếu có nhiệm vụ bổ sung các sản phẩm còn thiếu sau khi kiểm kê.')
    inventory_duplicate_product = fields.Many2one('stock.picking', string='Phiếu kiểm trùng')
    create_inventory_picking = fields.Many2one('stock.picking',string='Đã sinh phiếu hậu kiểm lại')
    inventory_scan_start_time = fields.Datetime(string='Thời gian bắt đầu quét', help='Thời gian bắt đầu quét mã vạch')
    has_diff_qty = fields.Boolean(
        string='Có chênh lệch',
        compute='_compute_has_diff_qty',
        store=True,
        help='Kiểm tra nếu có bất kỳ dòng nào có chênh lệch số lượng'
    )
    is_recheck_inventory_origin = fields.Boolean('Là phiếu kiểm lại', help='Đánh dấu nếu phiếu kiểm này là phiếu kiểm kê lại của một phiếu kiểm kê khác')
    recheck_inventory_id = fields.Many2one('stock.picking', 'Phiếu được kiểm kê lại')
    shelf_location_id = fields.Many2one('shelf.location', string='Quầy/kệ', help='Chọn quầy kệ cho phiếu kiểm kê', tracking=True)
    mch_category_id = fields.Many2one('product.category', string='Mã MCH2', tracking=True)
    waiting_to_push_augges = fields.Boolean(string='Đang chờ đẩy Augges', help='Đánh dấu phiếu đang chờ đẩy sang Augges sau khi hoàn thành', tracking=True)
    @api.onchange('shelf_location_id')
    def _onchange_shelf_location_id(self):
        for rec in self:
            rec.shelf_location = 'Kiểm kê ' + (rec.shelf_location_id.name or '')

    period_inventory_id = fields.Many2one('period.inventory', string='Đợt kiểm kê', help='Chọn đợt kiểm kê cho phiếu này', tracking=True)

    @api.depends('move_ids_without_package.diff_qty')
    def _compute_has_diff_qty(self):
        for record in self:
            record.has_diff_qty = any(move.diff_qty != 0 for move in record.move_ids_without_package)
    min_products_to_check = fields.Integer(
        string='Số lượng sản phẩm cần kiểm kê tối thiểu',
        help='Số lượng sản phẩm tối thiểu cần được kiểm kê trong phiếu này',
        default=0, readonly=1
    )
    percent_products_to_check = fields.Float(
        string='Tỉ lệ sản phẩm cần kiểm kê (%)',
        help='Tỉ lệ % sản phẩm cần được kiểm kê trong phiếu này',
        default=0.0
    )


    inventory_time_minutes = fields.Float(
        string='Thời gian kiểm kê (phút)',
        compute='_compute_inventory_time_minutes',
        help='Thời gian từ scheduled_date đến date_done (phút)',
        store=True
    )

    @api.depends('inventory_scan_start_time', 'date_done')
    def _compute_inventory_time_minutes(self):
        for record in self:
            if record.date_done and record.inventory_scan_start_time:
                # Calculate difference in minutes
                time_diff = (record.date_done - record.inventory_scan_start_time).total_seconds() / 60
                record.inventory_time_minutes = time_diff
            else:
                record.inventory_time_minutes = 0

    # Đè hàm của base để hỗ trợ 4 trường barcode
    @api.model
    def filter_on_barcode(self, barcode):
        """ Searches ready pickings for the scanned product/package/lot.
        """
        barcode_type = None
        nomenclature = self.env.company.nomenclature_id
        if nomenclature.is_gs1_nomenclature:
            parsed_results = nomenclature.parse_barcode(barcode)
            if parsed_results:
                # filter with the last feasible rule
                for result in parsed_results[::-1]:
                    if result['rule'].type in ('product', 'package', 'lot'):
                        barcode_type = result['rule'].type
                        break

        active_id = self.env.context.get('active_id')
        picking_type = self.env['stock.picking.type'].browse(self.env.context.get('active_id'))
        base_domain = [
            ('picking_type_id', '=', picking_type.id),
            ('state', 'not in', ['cancel', 'done', 'draft'])
        ]

        picking_nums = 0
        additional_context = {'active_id': active_id}
        if barcode_type == 'product' or not barcode_type:

            product = self.env['product.product'].search([
                '|', '|', '|',
                ('barcode', '=', barcode),
                ('default_code', '=', barcode),
                ('barcode_vendor', '=', barcode),
                ('barcode_k', '=', barcode),
            ], limit=1)

            if product:
                picking_nums = self.search_count(base_domain + [('product_id', '=', product.id)])
                additional_context['search_default_product_id'] = product.id
        if self.env.user.has_group('stock.group_tracking_lot') and (barcode_type == 'package' or (not barcode_type and not picking_nums)):
            package = self.env['stock.quant.package'].search([('name', '=', barcode)], limit=1)
            if package:
                pack_domain = ['|', ('move_line_ids.package_id', '=', package.id), ('move_line_ids.result_package_id', '=', package.id)]
                picking_nums = self.search_count(base_domain + pack_domain)
                additional_context['search_default_move_line_ids'] = barcode
        if self.env.user.has_group('stock.group_production_lot') and (barcode_type == 'lot' or (not barcode_type and not picking_nums)):
            lot = self.env['stock.lot'].search([
                ('name', '=', barcode),
                ('company_id', '=', picking_type.company_id.id),
            ], limit=1)
            if lot:
                lot_domain = [('move_line_ids.lot_id', '=', lot.id)]
                picking_nums = self.search_count(base_domain + lot_domain)
                additional_context['search_default_lot_id'] = lot.id
        if not barcode_type and not picking_nums:  # Nothing found yet, try to find picking by name.
            picking_nums = self.search_count(base_domain + [('name', '=', barcode)])
            additional_context['search_default_name'] = barcode

        if not picking_nums:
            if barcode_type:
                return {
                    'warning': {
                        'message': _("No %(picking_type)s ready for this %(barcode_type)s", picking_type=picking_type.name, barcode_type=barcode_type),
                    }
                }
            return {
                'warning': {
                    'title': _('No product, lot or package found for barcode %s', barcode),
                    'message': _('Scan a product, a lot/serial number or a package to filter the transfers.'),
                }
            }

        action = picking_type._get_action('stock_barcode.stock_picking_action_kanban')
        action['context'].update(additional_context)
        return {'action': action}

    def prepare_augges_values(self):
        day = (self.date_done or datetime.now()).astimezone(pytz.UTC).replace(tzinfo=None)
        sql_day = day.strftime("%Y-%m-%d 00:00:00")
        sngay = day.strftime("%y%m%d")

        rec_currency_id = self.currency_id or self.company_id.currency_id
        currency_id = rec_currency_id.id_augges or 1

        id_dt = False

        augges_ref = self.partner_id.ref
        if augges_ref:
            domain = f"Ma_Dt = '{augges_ref}'"
            partner_augges = self.env['ttb.augges'].get_partner(domain)
            if partner_augges:
                id_dt = partner_augges[0]['id']
        insert_date = datetime.utcnow() + timedelta(hours=7)
        data = {
            'ID_Dt': id_dt,
            'Ngay': sql_day,
            'Sngay': sngay,
            'NgayKK': sql_day,
            'ID_Nx': 100,
            'ID_Tt': currency_id,
            'ID_Kho': self.location_dest_id.warehouse_id.id_augges,
            'Dien_Giai': 'Cap nhat kiem ke %s' % self.name,

            "Tien_Hang": 0,
            "Tien_GtGt": 0,
            "Tong_Tien": 0,
            "ID_LrTd": 0,
            "ID_Dv": 0,
            "So_Ct": 0,
            "nSo_Ct": 0,
            "So_Bk": "",
            "SttSp": 0,
            "SpTc": 0,
            "Ty_Gia": 0,
            "IP_ID": 0,
            "IsEHD": 0,
            "Tong_Nt": 0,
            "Vs": '250103',
            "Tien_Cp": 0,
            "ID_Uni": str(uuid.uuid4()),
            "LoaiCt": '',
            "UserID": self.env['ttb.augges'].get_user_id_augges(),
            "InsertDate": insert_date,
        }

        return data


    def button_sent_augges_kiem_ke(self, pair_conn=False):
        """
        Tách 2 loại âm, dương
        âm: tạo phiếu nhập
        dương: tạo phiếu xuất
        """
        self.ensure_one()

        if self.state != 'done':
            raise UserError('Phiếu chưa hoàn thành')

        owns_conn = False
        conn, cursor = None, None
        if pair_conn:
            conn = pair_conn
        else:
            conn = self.env['ttb.tools'].get_mssql_connection_send()
            owns_conn = True
        cursor = conn.cursor()

        _logger.info('Tạo phiếu nhập Augges cho phiếu kiểm kê odoo id: %s, name: %s', self.id, self.name)
        master_data = self.prepare_augges_values()
        in_detail_datas = []
        out_detail_datas = []
        if self.is_recheck_inventory_origin and self.shelf_location and 'hậu kiểm' not in self.shelf_location.lower():
            stock_move_ids = self.get_exists_stock_move()
            existing_product_ids = stock_move_ids.mapped('product_id')
            for line in self.move_ids_without_package.filtered(lambda x: x.quantity > 0):
                price_product = line.product_id.get_price_pol()
                if self.recheck_inventory_id.create_inventory_picking and self.recheck_inventory_id.create_inventory_picking.create_inventory_picking and self.recheck_inventory_id.create_inventory_picking.create_inventory_picking.date_done:
                    if line.product_id.id in self.recheck_inventory_id.create_inventory_picking.create_inventory_picking.move_ids_without_package.mapped('product_id').ids:
                        origin_quantity_qty_last = sum(self.recheck_inventory_id.create_inventory_picking.create_inventory_picking.move_ids_without_package.filtered(lambda x: x.product_id.id == line.product_id.id).mapped('quantity_qty_last'))
                        if line.quantity > origin_quantity_qty_last:
                            in_detail_datas.append(
                                line.prepare_augges_values(line.quantity - origin_quantity_qty_last, price_product * line.quantity))
                        if line.quantity < origin_quantity_qty_last:
                            out_detail_datas.append(
                                line.prepare_augges_values(-line.quantity + origin_quantity_qty_last, price_product * line.quantity))
                elif self.recheck_inventory_id.create_inventory_picking and self.recheck_inventory_id.create_inventory_picking.date_done:
                    if line.product_id.id in self.recheck_inventory_id.create_inventory_picking.move_ids_without_package.mapped('product_id').ids:
                        origin_quantity_qty_last = sum(
                            self.recheck_inventory_id.create_inventory_picking.move_ids_without_package.filtered(
                                lambda x: x.product_id.id == line.product_id.id).mapped('quantity_qty_last'))
                        if line.quantity > origin_quantity_qty_last:
                            in_detail_datas.append(
                                line.prepare_augges_values(line.quantity - origin_quantity_qty_last, price_product * line.quantity))
                        if line.quantity < origin_quantity_qty_last:
                            out_detail_datas.append(
                                line.prepare_augges_values(-line.quantity + origin_quantity_qty_last, price_product * line.quantity))
                elif line.product_id.id in self.recheck_inventory_id.move_ids_without_package.mapped('product_id').ids:
                    origin_quantity_qty_last = sum(self.recheck_inventory_id.move_ids_without_package.filtered(lambda x: x.product_id.id == line.product_id.id).mapped('quantity_qty_last'))
                    if line.quantity > origin_quantity_qty_last:
                        in_detail_datas.append(line.prepare_augges_values(line.quantity - origin_quantity_qty_last, price_product * line.quantity))
                    if line.quantity < origin_quantity_qty_last:
                        out_detail_datas.append(line.prepare_augges_values(-line.quantity + origin_quantity_qty_last, price_product * line.quantity))
                else:
                    if line.product_id.id in existing_product_ids.ids:
                        in_detail_datas.append(line.prepare_augges_values(line.quantity, price_product * line.quantity))
                    else:
                        if line.quantity > line.stock_qty:
                            in_detail_datas.append(
                                line.prepare_augges_values(line.quantity - line.stock_qty, price_product * line.quantity))
                        if line.quantity < line.stock_qty:
                            out_detail_datas.append(
                                line.prepare_augges_values(-line.quantity + line.stock_qty, price_product * line.quantity))
        else:
            if self.inventory_origin_id:
                for line in self.move_ids_without_package:
                    price_product = line.product_id.get_price_pol()
                    if line.quantity == 0: continue
                    # stock_move_ids = self.get_exists_stock_move()
                    # existing_product_ids = stock_move_ids.mapped('product_id')
                    # check = line.product_id.id not in self.inventory_origin_id.move_ids_without_package.mapped('product_id').ids # Sp không có trong phiếu gốc
                    # if check and line.product_id.id not in existing_product_ids.ids: # Sp không có trong phiếu gốc và không có trong phiếu khác
                    #     if line.quantity > line.stock_qty:
                    #         in_detail_datas.append(line.prepare_augges_values(line.quantity - line.stock_qty, thanh_tien))
                    #     if line.quantity < line.stock_qty:
                    #         out_detail_datas.append(line.prepare_augges_values(-line.quantity + line.stock_qty, thanh_tien)) # s
                    # elif check and line.product_id.id in existing_product_ids.ids: #Sp không có trong phiếu gốc nhưng có trong phiếu khác
                    #     if self.shelf_location and 'hậu kiểm lần 2' in self.shelf_location.lower():
                    #         list_origin_product = self.inventory_origin_id.inventory_origin_id.move_ids_without_package.filtered(lambda x: x.quantity > 0 and x.product_id.id == line.product_id.id)
                    #     else:
                    #         list_origin_product = []
                    #     if not list_origin_product:
                    #         in_detail_datas.append(line.prepare_augges_values(line.quantity, thanh_tien))
                    #     else:
                    #         origin_quantity = sum(list_origin_product.mapped('quantity'))
                    #         if line.quantity > origin_quantity:
                    #             in_detail_datas.append(line.prepare_augges_values(line.quantity - origin_quantity, thanh_tien))
                    #         if line.quantity < origin_quantity:
                    #             out_detail_datas.append(line.prepare_augges_values(-line.quantity + origin_quantity, thanh_tien))
                    # else: # Sp có trong phiếu gốc
                    #     origin_quantity = sum(self.inventory_origin_id.move_ids_without_package.filtered(lambda x: x.product_id.id == line.product_id.id).mapped('quantity'))
                    #     if line.quantity > origin_quantity:
                    #         in_detail_datas.append(line.prepare_augges_values(line.quantity - origin_quantity, thanh_tien))
                    #     if line.quantity < origin_quantity:
                    #         out_detail_datas.append(line.prepare_augges_values(-line.quantity + origin_quantity, thanh_tien))
                    if line.quantity > line.stock_qty:
                        in_detail_datas.append(line.prepare_augges_values(line.quantity - line.stock_qty, price_product * line.quantity))
                    if line.quantity < line.stock_qty:
                        out_detail_datas.append(line.prepare_augges_values(-line.quantity + line.stock_qty, price_product * line.quantity))
            else:
                stock_move_ids = self.get_exists_stock_move()
                existing_product_ids = stock_move_ids.mapped('product_id')
                for line in self.move_ids_without_package.filtered(lambda x: x.quantity > 0):
                    price_product = line.product_id.get_price_pol()

                    if line.product_id.id in existing_product_ids.ids:
                        in_detail_datas.append(line.prepare_augges_values(line.quantity, price_product * line.quantity))
                    else:
                        if line.quantity > line.stock_qty:
                            in_detail_datas.append(line.prepare_augges_values(line.quantity - line.stock_qty, price_product * line.quantity))
                        if line.quantity < line.stock_qty:
                            out_detail_datas.append(line.prepare_augges_values(-line.quantity + line.stock_qty, price_product * line.quantity))
        slnxm_id = False
        if in_detail_datas:
            master_data['ID_Nx'] = 52
            slnxm_id = self.env['ttb.augges'].create_slnx(master_data, in_detail_datas)
        if out_detail_datas:
            master_data['ID_Nx'] = 82
            slnxm_id = self.env['ttb.augges'].create_slnx(master_data, out_detail_datas)

        self.write({
            'id_augges': slnxm_id,
            # 'sp_augges': value_sp,
            'is_sent_augges': True,
        })

        if owns_conn:
            conn.commit()
            cursor.close()
            conn.close()


    def create_recheck(self):
        branch_id = self.picking_type_id.warehouse_id.ttb_branch_id
        product_ids = self.mapped('move_line_ids.product_id')

        percent_str = self.env['ir.config_parameter'].sudo().get_param('kiem_ke.product_recheck_percentage', default='15')
        percent = float(percent_str)
        n = math.ceil(len(product_ids) * percent / 100.0)

        augges_ids = product_ids.mapped('augges_id')
        augges_ids_str = str(augges_ids).replace('[', '(').replace(']', ')')

        query = f"""
            select top {n} id_hang
            from slnxd
            where id_hang in {augges_ids_str} and id_kho = {self.location_dest_id.warehouse_id.id_augges}
            group by id_hang
            order by sum(T_Tien) desc

        """
        augges_products = self.env['ttb.augges'].do_query(query)
        top_products = []
        product_maps = {product.augges_id: product for product in product_ids}

        priority_product_ids = self.env['product.product']
        for item in augges_products:
            priority_product_ids |= product_maps[item['id_hang']]

        if len(priority_product_ids) < n:
            missing_count = n - len(priority_product_ids)
            remaining_lines = self.move_ids_without_package.filtered(
                lambda l: l.product_id not in priority_product_ids
            )
            remaining_lines = remaining_lines.sorted(key=lambda l: l.quantity, reverse=True)
            fill_products = remaining_lines.mapped('product_id')[:missing_count]
            priority_product_ids |= fill_products

        # priority_product_ids = self.env['inventory.product.recheck'].search([('branch_id', '=', branch_id.id), ('product_id', 'in', product_ids.ids)], limit=7).product_id
        # if len(priority_product_ids) < 7:
        #     remain_lines = self.move_ids_without_package.filtered(lambda line: line.product_id not in priority_product_ids)
        #     other_product_ids = remain_lines[:7 - len(priority_product_ids)].product_id
        #     priority_product_ids = priority_product_ids | other_product_ids
        moves = self.move_ids_without_package.filtered(lambda line: line.diff_qty != 0)

        # Tạo danh sách move mới từ những move có chênh lệch
        move_vals = []
        for move in moves:
            move_vals.append(Command.create({
                'name': move.name,
                'product_id': move.product_id.id,
                'product_uom': move.product_uom.id,
                'product_uom_qty': abs(move.diff_qty),
                'quantity': abs(move.diff_qty),
                'location_id': move.location_id.id,
                'location_dest_id': move.location_dest_id.id,
                'is_cong_don': move.is_cong_don,
                'move_line_ids': [Command.create({
                    'product_id': move.product_id.id,
                    'product_uom_id': move.product_uom.id,
                    'quantity': 0,
                })]
            }))

        stock_inventory_check = self.sudo().create([{
            'picking_type_id': self.picking_type_id.id,
            'shelf_location': 'HẬU KIỂM ' + (self.shelf_location or self.name),
            'inventory_origin_id': self.id,
            'min_products_to_check': self.min_products_to_check,
            'mch_category_id': self.mch_category_id.id,
            'period_inventory_id': self.period_inventory_id.id,
            'is_recheck_inventory_origin': self.is_recheck_inventory_origin,
            'move_ids_without_package': move_vals,
        }])
        self.create_inventory_picking = stock_inventory_check.id

    def get_exists_stock_move(self):
        """Lấy các phiếu kiểm kê đã tồn tại cho location_dest_id"""
        self.ensure_one()

        stocks = self.env['stock.picking'].search([('state', 'in', ['done']),
                                                   ('picking_type_id.code', '=', 'inventory_counting'),
                                                   ('disable_inventory', '=', False),
                                                   ('location_dest_id', '=', self.location_dest_id.id),
                                                   ('id', '!=', self.id),
                                                   ]).filtered(lambda x: x.period_inventory_id and x.period_inventory_id.id == self.period_inventory_id.id)
        self_products = self.move_ids_without_package.filtered(lambda x: x.quantity > 0).mapped('product_id').ids
        existing_move_ids = self.env['stock.move'].search([
            ('state', '=', 'done'),
            ('picking_id', 'in', stocks.ids),
            ('product_id', 'in', self_products),
            ('quantity', '>', 0)
        ])
        return existing_move_ids

    def _action_done(self):
        result = super()._action_done()
        # Khi xác nhận phiếu kiểm kê, tự động đẩy sang Augges
        # Việc đẩy sang augges không rollback được nên để ở vị trí code này để đảm bảo đây là vị trí code chạy cuối cùng khi xác nhận phiếu nhập
        for rec in self.filtered(lambda x: x.picking_type_id.code == 'inventory_counting'):
            if rec.period_inventory_id and rec.period_inventory_id.state != 'in_progress':
                raise ValidationError("Đợt kiểm kê đang không được mở, vui lòng xem lại đợt kiểm kê hiện tại!!!")
            total_quantity_products = sum(line.quantity for line in rec.move_ids_without_package)
            if rec.inventory_origin_id:
                total_diff = 0
                for line in rec.move_ids_without_package.filtered(lambda x: x.quantity > 0):
                    product_origin_quantity = sum(
                        m.quantity
                        for m in rec.inventory_origin_id.move_ids_without_package
                        if m.product_id.id == line.product_id.id
                    )
                    line.diff_qty1 = abs(product_origin_quantity - line.quantity)
                    total_diff += abs(product_origin_quantity - line.quantity)
                    if line.product_id.id in rec.inventory_origin_id.move_ids_without_package.filtered(lambda x: x.is_cong_don).mapped('product_id').ids:
                        line.write({'is_cong_don': True})
                rec.diff_product_rate = total_diff / sum(
                    rec.move_ids_without_package.mapped('quantity')) * 100 if sum(
                    rec.inventory_origin_id.move_ids_without_package.mapped('quantity')) != 0 else 0
                rec.total_diff_qty = total_diff
                for line in rec.move_ids_without_package:
                    line.write({
                        'quantity_qty_last': line.quantity
                    })
                if rec.shelf_location and 'hậu kiểm lần 2' in rec.shelf_location.lower():
                    for line in rec.inventory_origin_id.move_ids_without_package:
                        line.write({'quantity_qty_last': 0})
            else:
                # Lấy tất cả product_id từ các phiếu kiểm kê khác có ngày kế hoạch > 20/10/2025
                self_products = rec.move_ids_without_package.filtered(lambda x: x.quantity > 0)
                stock_move_ids = rec.get_exists_stock_move()
                existing_product_ids = stock_move_ids.mapped('product_id').ids
                for line in self_products:
                    if line.product_id.id in existing_product_ids:
                        line.write({'is_cong_don': True})
                # # Kiểm tra sản phẩm hiện tại có trùng với các phiếu khác không
                # if existing_stock_ids and not rec.disable_inventory:
                #     # Tạo thông báo chi tiết cho từng phiếu
                #     error_details = []
                #     for stock in existing_stock_ids:
                #         # Lấy các sản phẩm trùng lặp trong phiếu này
                #         duplicate_in_stock = self.env['stock.move'].search([
                #             ('state', '=', 'done'),
                #             ('picking_id', '=', stock.id),
                #             ('product_id', 'in', self_products),
                #             ('quantity', '>', 0)
                #         ]).mapped('product_id')
                #
                #         if duplicate_in_stock:
                #             product_info = [f"{p.display_name} - {p.barcode or 'Không có mã vạch'}" for p in
                #                             duplicate_in_stock]
                #             product_names = ', '.join(product_info)
                #             error_details.append(
                #                 f"Phiếu {stock.name} ({stock.shelf_location or 'N/A'}): {product_names}")
                #
                #     error_message = '\n'.join(error_details)
                #     raise UserError(
                #         f'Các sản phẩm sau đã tồn tại trong phiếu kiểm kê khác:\n{error_message}\n'
                #         f'Hãy kiểm tra hoặc xóa những sản phẩm này ra khỏi phiếu!!!'
                #     )
                rec.diff_product_rate = 0
                rec.total_diff_qty = 0
            if total_quantity_products < rec.min_products_to_check:
                raise ValidationError('Bạn chưa quét đủ số lượng sản phẩm!!!')

            if rec.shelf_location and 'hậu kiểm lần 2' in rec.shelf_location.lower():
                rec.diff_product_rate = 0
                for line in rec.move_ids_without_package:
                    product = line.product_id

                    # Lấy HKL1 và HKL2
                    inv_hkl2 = rec.inventory_origin_id
                    inv_hkl1 = inv_hkl2.inventory_origin_id

                    # Lấy quantity của product ở HKL1 và HKL2 (chỉ lọc 1 lần mỗi nơi)
                    qty_hkl2 = sum(inv_hkl2.move_ids_without_package
                                   .filtered(lambda l: l.product_id == product)
                                   .mapped('quantity'))

                    qty_hkl1 = sum(inv_hkl1.move_ids_without_package
                                   .filtered(lambda l: l.product_id == product)
                                   .mapped('quantity'))

                    # Tính chênh lệch
                    diff_hkl2 = abs(line.quantity - qty_hkl2)
                    diff_hkl1 = abs(qty_hkl2 - qty_hkl1)

                    # Apply vào từng move_line
                    for move_line in line.move_line_ids:
                        move_line.diff_kk_than_hkl2 = diff_hkl2
                        move_line.diff_kk_than_hkl1 = diff_hkl1

            if total_quantity_products > 0 and (rec.shelf_location and 'hậu kiểm' not in rec.shelf_location.lower()):
                rec.min_products_to_check = int(rec.percent_products_to_check * total_quantity_products / 100)
            # Tính toán tồn kho Augges
            diff_product_count = 0
            diff_product_sum = 0
            product_sum = 0
            for line in rec.move_ids_without_package:
                line.stock_qty = self.env['ttb.augges'].get_augges_quantity(rec.location_dest_id.warehouse_id.id_augges, line.product_id.augges_id)
                line.diff_qty = line.quantity - line.stock_qty
                diff_product_sum += abs(line.diff_qty)
                product_sum += line.quantity
                line.quantity_qty_last = line.quantity
                if line.diff_qty != 0:
                    diff_product_count += 1
            rec.diff_product_count = diff_product_count
            # sinh phiếu hậu kiểm
            if (not rec.shelf_location or 'hậu kiểm' not in rec.shelf_location.lower()) and not rec.disable_inventory:
                rec.create_recheck()
            # name = (rec.name or '').lower()
            # shelf_location = (rec.shelf_location or '').lower()
            # if (rec.shelf_location and 'hậu kiểm' in shelf_location):
            if self.env['ir.config_parameter'].sudo().get_param('kiem_ke.send_augges_direct'):
                rec.button_sent_augges_kiem_ke()
            else:
                rec.pending_sent_augges_action_done = True
            # else:
            #     if 'kcl' in name:
            #         rec.waiting_to_push_augges = True
        return result
    def action_push_augges(self):
        pass
    #     for rec in self.filtered(lambda x: x.waiting_to_push_augges and not x.id_augges):
    #         try:
    #             rec.button_sent_augges_kiem_ke()
    #             rec.pending_sent_augges_action_done = True
    #             rec.waiting_to_push_augges = True
    #         except Exception as e:
    #             # log lỗi
    #             rec.message_post(body=f'Lỗi khi đẩy Augges: {str(e)}')


    def cron_send_augges_kiem_ke(self):
        # Quét các phiếu kiểm kê cần đẩy sang Augges
        domain = [
            ('picking_type_id.code', '=', 'inventory_counting'),
            ('pending_sent_augges_action_done', '=', True),
            ('state', '=', 'done'),
        ]
        pickings = self.env['stock.picking'].search(domain)
        for picking in pickings:
            try:
                picking.button_sent_augges_kiem_ke()
                picking.pending_sent_augges_action_done = False
            except Exception as e:
                # log lỗi
                picking.message_post(body=f'Lỗi khi đẩy Augges: {str(e)}')

    @api.model
    def action_open_new_picking(self):
        context = self.env.context
        if context.get('active_model') == 'stock.picking.type':
            picking_type = self.env['stock.picking.type'].browse(context.get('active_id'))
            if picking_type.exists() and picking_type.code == 'inventory_counting':
                if not self.env.user.has_group('base.group_system'):
                    raise UserError('Không tạo phiếu kiểm kê bằng chức năng này. Hãy liên hệ quản lý hoặc IT')
        return super().action_open_new_picking()

    def action_generate_inventory_picking(self):
        """Sinh phiếu kiểm kê từ phiếu hiện tại"""
        self.ensure_one()
        product_diff = {}
        percent_diff = self.env['ir.config_parameter'].sudo().get_param('ttb_stock_barcode_incoming.percent_diff', default='15')
        shelf_location = self.shelf_location or ''
        if self.create_inventory_picking:
            raise UserError('Phiếu hậu kiểm lần 2 đã được tạo trước đó.')
        if self.diff_product_rate != 0:
            hkl1_product = self.move_ids_without_package.filtered(lambda x: x.quantity > 0).mapped('product_id')
            for line in self.move_ids_without_package:
                origin_quantity = sum(m.quantity for m in self.inventory_origin_id.move_ids_without_package if m.product_id.id == line.product_id.id)
                if line.quantity != origin_quantity:
                    diff_qty = line.quantity - origin_quantity
                    product_diff[line.product_id] = diff_qty
            if self.period_inventory_id.is_full_recheck_inventory:
                for line_origin in self.inventory_origin_id.move_ids_without_package:
                    if line_origin.product_id not in hkl1_product:
                        diff_qty = line_origin.quantity
                        product_diff[line_origin.product_id] = diff_qty
        if self.diff_product_rate < float(percent_diff):
            # tạo các dòng có sản phẩm bị lệch
            line_vals = []
            for product in product_diff:
                # move_line = self.move_ids_without_package.filtered(lambda l: l.product_id.id == product.id)[0]
                line_vals.append(Command.create({
                    'name': f'Kiểm kê {product.name}',
                    'product_id': product.id,
                    'product_uom': product.uom_id.id,
                    'product_uom_qty': abs(product_diff[product]),
                    'quantity': abs(product_diff[product]),
                    'location_id': self.location_id.id,
                    'location_dest_id': self.location_dest_id.id,
                    # 'is_cong_don': move_line.is_cong_don,
                    'move_line_ids': [Command.create({
                        'product_id': product.id,
                        'product_uom_id': product.uom_id.id,
                        'quantity': 0,
                    })]
                }))
            if not line_vals:
                raise UserError('Không có sản phẩm nào bị lệch để tạo phiếu hậu kiểm.')
            stock_inventory_check = self.env['stock.picking'].create({
                'shelf_location': 'HẬU KIỂM LẦN 2 ' + shelf_location.replace('HẬU KIỂM', '').strip(),
                'picking_type_id': self.picking_type_id.id,
                'inventory_origin_id': self.id,
                'move_ids_without_package': line_vals,
                'mch_category_id': self.mch_category_id.id,
                'period_inventory_id': self.period_inventory_id.id,
                'is_recheck_inventory_origin': self.is_recheck_inventory_origin,
            })
            self.create_inventory_picking = stock_inventory_check.id
            # Trả về thông báo cho người dùng
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Thành công'),
                    'message': _('Đã tạo phiếu hậu kiểm %s với %s sản phẩm') % (
                    stock_inventory_check.name, len(product_diff)),
                    'type': 'success'
                }
            }
        else:
            shelf_location = self.shelf_location or ''
            stock_inventory_check = self.env['stock.picking'].create({
                'shelf_location': 'HẬU KIỂM LẦN 2 ' + shelf_location.replace('HẬU KIỂM', '').strip(),
                'picking_type_id': self.picking_type_id.id,
                'inventory_origin_id': self.id,
                'min_products_to_check': 0,
                'mch_category_id': self.mch_category_id.id,
                'period_inventory_id': self.period_inventory_id.id,
                'is_recheck_inventory_origin': self.is_recheck_inventory_origin,
            })
            self.create_inventory_picking = stock_inventory_check.id
            # Trả về thông báo cho người dùng
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Thành công'),
                    'message': _('Đã tạo phiếu hậu kiểm %s với tỉ lệ kiểm kê cả quầy %s%%') % (
                    stock_inventory_check.name, self.percent_products_to_check),
                    'type': 'success'
                }
            }

    def send_notify(self, message='', users=None, subject='Thông báo'):
        """Gửi thông báo cho người dùng"""
        if not users:
            return

        if isinstance(users, int):
            users = self.env['res.users'].browse(users)
        elif not isinstance(users, type(self.env['res.users'])):
            users = self.env['res.users'].browse([users.id] if hasattr(users, 'id') else [])

        # Tạo activity để có thể click vào thông báo
        self.activity_schedule(
            'mail.mail_activity_data_todo',
            user_id=users[0].id if len(users) == 1 else self.env.user.id,
            summary=subject,
            note=message
        )

        # Hoặc dùng message_post với partner_ids
        partner_ids = users.mapped('partner_id')
        self.message_post(
            body=message,
            subject=subject,
            partner_ids=partner_ids.ids,
            message_type='notification',
            subtype_xmlid='mail.mt_note'
        )

    def write(self, vals):
        result = super(StockPicking, self).write(vals)
        if 'user_id' in vals:
            for rec in self:
                new_user = rec.user_id
                # Gửi thông báo cho user mới
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                record_url = f"{base_url}/web#id={rec.id}&model=stock.picking&view_type=form"
                message = f'Bạn đã được gắn làm người phụ trách phiếu <a href="{record_url}">{rec.name}</a>.'

                rec.send_notify(
                    message=message,
                    users=new_user,  # chỉ một người
                    subject='Thông báo phiếu kiểm kê'
                )


        if 'support_user_ids' in vals:
            for rec in self:
                new_users = rec.support_user_ids # hợp rồi trừ cũ

                if not new_users:
                    continue

                # Gửi một lần duy nhất cho mỗi user mới
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                record_url = f"{base_url}/web#id={rec.id}&model=stock.picking&view_type=form"
                message = (
                    f'Bạn đã được gắn vào phiếu '
                    f'<a href="{record_url}" style="font-weight: bold; color: #1976d2;">{rec.name}</a>.'
                )

                rec.send_notify(
                    message=message,
                    users=new_users,  # gửi một lượt
                    subject='Thông báo phiếu kiểm kê'
                )

        return result

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('shelf_location_id') and not vals.get('shelf_location'):
                shelf = self.env['shelf.location'].browse(vals['shelf_location_id'])
                vals['shelf_location'] = 'Kiểm kê ' + (shelf.name or '')
        records = super(StockPicking, self).create(vals_list)

        for rec in records:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            action_id = self.env.ref('stock_barcode.stock_picking_action_kanban').sudo().id
            record_url = f"{base_url}/web#action={action_id}&model=stock.picking&view_type=kanban&active_id={rec.id}"

            # --- Thông báo cho user_id (người phụ trách chính)
            if rec.user_id:
                message_main = (
                    f'Bạn đã được gắn làm <b>người phụ trách chính</b> của phiếu '
                    f'<a href="{record_url}">{rec.name}</a>.'
                )
                rec.send_notify(
                    message=message_main,
                    users=rec.user_id,
                    subject='Thông báo phiếu kiểm kê'
                )

            # --- Thông báo cho support_user_ids (người hỗ trợ)
            if rec.support_user_ids:
                message_support = (
                    f'Bạn đã được thêm làm <b>người hỗ trợ</b> trong phiếu '
                    f'<a href="{record_url}">{rec.name}</a>.'
                )
                rec.send_notify(
                    message=message_support,
                    users=rec.support_user_ids,
                    subject='Thông báo phiếu kiểm kê'
                )

        return records

    def action_go_to_scanbarcode(self):
        """Mở giao diện quét mã vạch cho phiếu kiểm kê"""
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('stock_barcode.stock_picking_action_kanban')

        # Ghi đè hoàn toàn context và domain
        action['context'] = {
            'default_picking_id': self.id,
            'active_id': self.id,
            'search_default_name': self.name,
        }
        action['domain'] = [('id', '=', self.id)]

        # Xóa các filter/groupby mặc định nếu có
        action.pop('search_view_id', None)

        return action

    def _get_stock_barcode_data(self):
        data = super()._get_stock_barcode_data()

        def to_id(value):
            if isinstance(value, (tuple, list)) and len(value) > 0:
                return value[0]
            return value

        if 'stock.picking' in data.get('records', {}):
            picking_records = data['records']['stock.picking']
            if picking_records:
                picking_records[0]['min_products_to_check'] = self.min_products_to_check

        # Thêm xử lý cho phiếu kiểm kê inventory_counting
        if self.picking_type_id.code == 'inventory_counting':
            move_fields = self.env['stock.move']._get_fields_stock_barcode()
            # Đảm bảo trường diff_qty được bao gồm
            for f in ['product_uom_qty', 'quantity', 'create_uid', 'write_uid', 'product_id', 'diff_qty', 'stock_qty']:
                if f not in move_fields: move_fields.append(f)

            # Cập nhật dữ liệu moves với trường diff_qty
            if 'moves' in data:
                for move_data in data['moves']:
                    move_id = move_data.get('id')
                    if move_id:
                        move = self.env['stock.move'].browse(move_id)
                        if move.exists():
                            move_data['diff_qty'] = move.diff_qty
                            move_data['stock_qty'] = move.stock_qty

        # 2. Logic Return Request
        if self.ttb_return_request_id:
            current_user = self.env.user
            spoof_uid = (current_user.id, current_user.name)

            valid_moves = self.move_ids.filtered(lambda m: m.state not in ['done', 'cancel'])

            if valid_moves:

                move_fields = self.env['stock.move']._get_fields_stock_barcode()
                for f in ['product_uom_qty', 'quantity', 'create_uid', 'write_uid', 'product_id']:
                    if f not in move_fields: move_fields.append(f)

                if 'ttb_required_qty' not in move_fields and 'ttb_required_qty' in self.env['stock.move']._fields:
                    move_fields.append('ttb_required_qty')

                moves_data = valid_moves.sudo().read(move_fields)

                picking_rec = data['records']['stock.picking'][0] if 'stock.picking' in data['records'] and \
                                                                     data['records']['stock.picking'] else None
                pick_loc_id = to_id(picking_rec.get('location_id')) if picking_rec else False
                pick_dest_id = to_id(picking_rec.get('location_dest_id')) if picking_rec else False

                for m_data in moves_data:
                    if pick_loc_id: m_data['location_id'] = pick_loc_id
                    if pick_dest_id: m_data['location_dest_id'] = pick_dest_id

                    if 'product_id' in m_data: m_data['product_id'] = to_id(m_data['product_id'])
                    if 'product_uom' in m_data: m_data['product_uom'] = to_id(m_data['product_uom'])

                    m_data['create_uid'] = spoof_uid
                    m_data['write_uid'] = spoof_uid
                    m_data.update({'package_id': False, 'result_package_id': False, 'owner_id': False, 'lot_id': False})

                    qty_demand = m_data.get('product_uom_qty', 0)
                    if not m_data.get('ttb_required_qty') and qty_demand > 0:
                        m_data['ttb_required_qty'] = qty_demand
                    if qty_demand > 0:
                        m_data['reserved_uom_qty'] = qty_demand

                if 'moves' not in data: data['moves'] = []
                data['moves'] = [m for m in data['moves'] if m['id'] not in valid_moves.ids]
                data['moves'].extend(moves_data)

                lines = valid_moves.mapped('move_line_ids')
                if lines:
                    line_fields = self.env['stock.move.line']._get_fields_stock_barcode()
                    for f in ['create_uid', 'write_uid', 'owner_id', 'product_id', 'product_uom_id', 'move_id']:
                        if f not in line_fields: line_fields.append(f)

                    lines_data = lines.sudo().read(line_fields)

                    for l_data in lines_data:
                        l_data['create_uid'] = spoof_uid
                        l_data['write_uid'] = spoof_uid
                        l_data['owner_id'] = False

                        if pick_loc_id: l_data['location_id'] = pick_loc_id
                        if pick_dest_id: l_data['location_dest_id'] = pick_dest_id

                        if 'product_id' in l_data: l_data['product_id'] = to_id(l_data['product_id'])
                        if 'product_uom_id' in l_data: l_data['product_uom_id'] = to_id(l_data['product_uom_id'])

                        if 'move_id' in l_data: l_data['move_id'] = to_id(l_data['move_id'])

                    if 'stock.move.line' not in data['records']: data['records']['stock.move.line'] = []
                    current_line_ids = {l['id'] for l in lines_data}
                    data['records']['stock.move.line'] = [l for l in data['records']['stock.move.line'] if
                                                          l['id'] not in current_line_ids]
                    data['records']['stock.move.line'].extend(lines_data)

                if 'product.product' not in data['records']: data['records']['product.product'] = []
                products_needed = valid_moves.mapped('product_id')
                prod_fields = self.env['product.product']._get_fields_stock_barcode()
                full_prod_data = products_needed.sudo().read(prod_fields)
                for p in full_prod_data:
                    if 'uom_id' in p: p['uom_id'] = to_id(p['uom_id'])
                    if 'uom_po_id' in p: p['uom_po_id'] = to_id(p['uom_po_id'])

                existing_p_ids = {p['id'] for p in data['records']['product.product']}
                data['records']['product.product'].extend([p for p in full_prod_data if p['id'] not in existing_p_ids])

                if 'uom.uom' not in data['records']: data['records']['uom.uom'] = []
                uoms_needed = valid_moves.mapped('product_uom')
                uom_fields = ['name', 'display_name', 'rounding', 'factor', 'uom_type', 'category_id', 'active']
                uom_data = uoms_needed.sudo().read(uom_fields)
                for u in uom_data:
                    if 'category_id' in u: u['category_id'] = to_id(u['category_id'])

                existing_u_ids = {u['id'] for u in data['records']['uom.uom']}
                data['records']['uom.uom'].extend([u for u in uom_data if u['id'] not in existing_u_ids])

                if 'uom.category' not in data['records']: data['records']['uom.category'] = []
                cats_needed = uoms_needed.mapped('category_id')
                cat_data = cats_needed.sudo().read(['name', 'display_name'])
                existing_c_ids = {c['id'] for c in data['records']['uom.category']}
                data['records']['uom.category'].extend([c for c in cat_data if c['id'] not in existing_c_ids])

                if picking_rec:
                    picking_record = data['records']['stock.picking'][0]
                    current_move_ids = set(picking_record.get('move_ids', []))
                    current_move_ids.update(valid_moves.ids)
                    picking_record['move_ids'] = list(current_move_ids)

                    moves_no_pack = valid_moves.filtered(lambda m: not m.package_level_id)
                    current_move_no_pack_ids = set(picking_record.get('move_ids_without_package', []))
                    current_move_no_pack_ids.update(moves_no_pack.ids)
                    picking_record['move_ids_without_package'] = list(current_move_no_pack_ids)

        return data

    def action_move_product_duplicate(self):
        pass
        # self.ensure_one()
        # stock_move_ids = self.get_exists_stock_move()
        # existing_product_ids = stock_move_ids.mapped('product_id')
        # # Kiểm tra sản phẩm hiện tại có trùng với các phiếu khác không
        # line_vals = []
        # if not self.disable_inventory and self.inventory_duplicate_product:
        #     for line in self.move_ids_without_package.filtered(lambda x: x.quantity > 0 and x.product_id.id in existing_product_ids.ids):
        #         line_vals.append(line.product_id.id)
        # else:
        #     raise UserError('Đây là phiếu kiểm trùng hoặc chưa có phiếu trắng, không thể chuyển sản phẩm trùng lặp!!!')
        # if line_vals:
        #     moves = []
        #     picking = self.inventory_duplicate_product
        #     # Lấy các dòng move hiện có
        #     existing_moves = {
        #         move.product_id.id: move for move in picking.move_ids_without_package
        #     }
        #     for pid in line_vals:
        #         product = self.env['product.product'].browse(pid)
        #         if not product.exists():
        #             continue
        #         # Nếu đã có sản phẩm này trong move, cộng dồn số lượng
        #         if product.id in existing_moves:
        #             move = existing_moves[product.id]
        #             # Cộng dồn số lượng (tuỳ theo bạn muốn cộng vào trường nào)
        #             move.quantity += self.move_ids_without_package.filtered(lambda l: l.product_id.id == product.id).quantity
        #         else:
        #             # Tạo dòng mới
        #             moves.append((0, 0, {
        #                 'name': f'Kiểm kê {product.name}',
        #                 'product_id': product.id,
        #                 'product_uom': product.uom_id.id,
        #                 'quantity': self.move_ids_without_package.filtered(lambda l: l.product_id.id == product.id).quantity,
        #                 'location_id': self.location_id.id,
        #                 'location_dest_id': self.location_dest_id.id,
        #                 'is_cong_don': True,
        #                 'move_line_ids': [(0, 0, {
        #                     'product_id': product.id,
        #                     'product_uom_id': product.uom_id.id,
        #                     'qty_done': self.move_ids_without_package.filtered(
        #                         lambda l: l.product_id.id == product.id).quantity,
        #                 })],
        #             }))
        #     # Ghi log vào phiếu
        #     user = self.env.user
        #     now = fields.Datetime.now()
        #     message = f"Người dùng {user.name} ({user.login}) đã cập nhật phiếu lúc {now.strftime('%H:%M %d/%m/%Y')}."
        #     if moves:
        #         picking.write({'move_ids_without_package': moves})
        #         picking.message_post(body=message)
        #     # xóa các dòng trùng ở phiếu cũ
        #     for line in self.move_ids_without_package.filtered(lambda x: x.product_id.id in line_vals):
        #         line.unlink()
        #     return {
        #         'type': 'ir.actions.client',
        #         'tag': 'display_notification',
        #         'params': {
        #             'title': _('Thành công'),
        #             'message': _('Đã chuyển %s sản phẩm trùng lặp sang phiếu kiểm trùng %s') % (
        #             len(line_vals), self.inventory_duplicate_product.name),
        #             'type': 'success'
        #         }
        #     }
        # else:
        #     raise UserError('Không có sản phẩm trùng lặp để chuyển!!!')

    def action_create_recheck(self):
        """Tạo phiếu kiểm kê lại"""
        # user = self.env.user
        # group_inventory_manager = self.env.ref('stock.group_stock_manager')
        # if user not in group_inventory_manager.users:
        #     raise UserError('Chỉ người quản lý kho mới có quyền tạo phiếu kiểm kê lại!')
        self.ensure_one()
        if self.shelf_location and 'hậu kiểm' in self.shelf_location.lower():
            raise UserError('Phiếu hậu kiểm không thể tạo phiếu kiểm kê lại!')
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'create.recheck.inventory.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_id': self.id},
        }
    def log_inventory_skip(self):
        user = self.env.user
        for rec in self:
            rec.message_post(
                body=f"{user.name} mã {user.login} vừa thêm sản phẩm phiếu kiểm kê",
                subtype_xmlid="mail.mt_note",
            )
    # def remove_line_when_remove_in_frontend(self, product_id):
    #     """Xoá dòng khi người dùng xoá từ giao diện frontend"""
    #     self.ensure_one()
    #     if not product_id:
    #         return
    #     lines = self.move_ids_without_package.filtered(lambda l: l.product_id.id == product_id)
    #     if lines:
    #         lines.unlink()

    def _get_fields_stock_barcode(self):
        fields = super()._get_fields_stock_barcode()
        # Nếu module ttb_return_request có field này → thêm vào barcode payload
        if 'ttb_return_request_id' in self._fields:
            fields.append('ttb_return_request_id')

        if 'create_uid' not in fields:
            fields.append('create_uid')

        if 'pickup_status' in self._fields and 'pickup_status' not in fields:
            fields.append('pickup_status')
        return fields

    @api.model
    def save_barcode_data(self, model, res_id, write_field, write_vals):
        result = super().save_barcode_data(model, res_id, write_field, write_vals)
        return result



    # Thêm bản clone để phục vụ kiểm kê lại các ngày quá khứ
    def get_exists_stock_move1(self):
        """Lấy các phiếu kiểm kê đã tồn tại cho location_dest_id"""
        self.ensure_one()
        stocks = self.env['stock.picking'].search([('state', 'in', ['done']),
                                                   ('picking_type_id.code', '=', 'inventory_counting'),
                                                   ('disable_inventory', '=', False),
                                                   ('location_dest_id', '=', self.location_dest_id.id),
                                                   ('id', '!=', self.id),('date_done', '<=', self.date_done)
                                                   ]).filtered(lambda x: x.period_inventory_id and x.period_inventory_id.id == self.period_inventory_id.id)

        self_products = self.move_ids_without_package.filtered(lambda x: x.quantity > 0).mapped('product_id').ids
        existing_move_ids = self.env['stock.move'].search([
            ('state', '=', 'done'),
            ('picking_id', 'in', stocks.ids),
            ('product_id', 'in', self_products),
            ('quantity', '>', 0)
        ])
        return existing_move_ids

    # Thêm bản clone để phục vụ kiểm kê lại các ngày quá khứ
    def button_sent_augges_kiem_ke1(self, pair_conn=False):
        """
        Tách 2 loại âm, dương
        âm: tạo phiếu nhập
        dương: tạo phiếu xuất
        """
        self.ensure_one()

        if self.state != 'done':
            raise UserError('Phiếu chưa hoàn thành')

        owns_conn = False
        conn, cursor = None, None
        if pair_conn:
            conn = pair_conn
        else:
            conn = self.env['ttb.tools'].get_mssql_connection_send()
            owns_conn = True
        cursor = conn.cursor()

        _logger.info('Tạo phiếu nhập Augges cho phiếu kiểm kê odoo id: %s, name: %s', self.id, self.name)
        master_data = self.prepare_augges_values()
        in_detail_datas = []
        out_detail_datas = []
        if self.is_recheck_inventory_origin:
            if self.inventory_origin_id:
                for line in self.move_ids_without_package:
                    if line.quantity == 0: continue
                    origin_quantity = sum(self.inventory_origin_id.move_ids_without_package.filtered(lambda x: x.product_id.id == line.product_id.id).mapped('quantity'))
                    if line.quantity > origin_quantity:
                        in_detail_datas.append(line.prepare_augges_values(line.quantity - origin_quantity))
                    if line.quantity < origin_quantity:
                        out_detail_datas.append(line.prepare_augges_values(-line.quantity + origin_quantity))
            else:
                stock_move_ids = self.get_exists_stock_move1()
                existing_product_ids = stock_move_ids.mapped('product_id')
                for line in self.move_ids_without_package.filtered(lambda x: x.quantity > 0):
                    if line.product_id.id in self.recheck_inventory_id.move_ids_without_package.mapped('product_id').ids:
                        if self.recheck_inventory_id.create_inventory_picking and self.recheck_inventory_id.create_inventory_picking.create_inventory_picking:
                            origin_quantity_qty_last = sum(self.recheck_inventory_id.create_inventory_picking.create_inventory_picking.move_ids_without_package.filtered(lambda x: x.product_id.id == line.product_id.id).mapped('quantity_qty_last'))
                        elif self.recheck_inventory_id.create_inventory_picking:
                            origin_quantity_qty_last = sum(self.recheck_inventory_id.create_inventory_picking.move_ids_without_package.filtered(lambda x: x.product_id.id == line.product_id.id).mapped('quantity_qty_last'))
                        else:
                            origin_quantity_qty_last = 0
                        if line.quantity > origin_quantity_qty_last:
                            in_detail_datas.append(line.prepare_augges_values(line.quantity - origin_quantity_qty_last))
                        if line.quantity < origin_quantity_qty_last:
                            out_detail_datas.append(line.prepare_augges_values(-line.quantity + origin_quantity_qty_last))
                    else:
                        if line.product_id.id in existing_product_ids.ids:
                            in_detail_datas.append(line.prepare_augges_values(line.quantity))
        else:
            if self.inventory_origin_id:
                for line in self.move_ids_without_package:
                    if line.quantity == 0: continue
                    if line.is_cong_don:
                        origin_quantity = sum(self.inventory_origin_id.move_ids_without_package.filtered(lambda x: x.product_id.id == line.product_id.id).mapped('quantity'))
                        if line.quantity > origin_quantity:
                            in_detail_datas.append(line.prepare_augges_values(line.quantity - origin_quantity))
                        if line.quantity < origin_quantity:
                            out_detail_datas.append(line.prepare_augges_values(-line.quantity + origin_quantity))
                    else:
                        stock_move_ids = self.get_exists_stock_move()
                        existing_product_ids = stock_move_ids.mapped('product_id')
                        check = line.product_id.id not in self.inventory_origin_id.move_ids_without_package.mapped('product_id').ids
                        if check and line.product_id.id not in existing_product_ids.ids:
                            if line.quantity > line.stock_qty:
                                in_detail_datas.append(line.prepare_augges_values(line.quantity - line.stock_qty))
                            if line.quantity < line.stock_qty:
                                out_detail_datas.append(line.prepare_augges_values(-line.quantity + line.stock_qty))
                        elif check and line.product_id.id in existing_product_ids.ids:
                            in_detail_datas.append(line.prepare_augges_values(line.quantity))
                        else:
                            origin_quantity = sum(self.inventory_origin_id.move_ids_without_package.filtered(lambda x: x.product_id.id == line.product_id.id).mapped('quantity'))
                            if line.quantity > origin_quantity:
                                in_detail_datas.append(line.prepare_augges_values(line.quantity - origin_quantity))
                            if line.quantity < origin_quantity:
                                out_detail_datas.append(line.prepare_augges_values(-line.quantity + origin_quantity))
            else:
                stock_move_ids = self.get_exists_stock_move()
                existing_product_ids = stock_move_ids.mapped('product_id')
                for line in self.move_ids_without_package.filtered(lambda x: x.quantity > 0):
                    if line.product_id.id in existing_product_ids.ids:
                        in_detail_datas.append(line.prepare_augges_values(line.quantity))
                    else:
                        if line.quantity > line.stock_qty:
                            in_detail_datas.append(line.prepare_augges_values(line.quantity - line.stock_qty))
                        if line.quantity < line.stock_qty:
                            out_detail_datas.append(line.prepare_augges_values(-line.quantity + line.stock_qty))
        slnxm_id = False
        if in_detail_datas:
            master_data['ID_Nx'] = 52
            slnxm_id = self.env['ttb.augges'].create_slnx(master_data, in_detail_datas)
        if out_detail_datas:
            master_data['ID_Nx'] = 82
            slnxm_id = self.env['ttb.augges'].create_slnx(master_data, out_detail_datas)

        self.write({
            'id_augges': slnxm_id,
            # 'sp_augges': value_sp,
            'is_sent_augges': True,
        })

        if owns_conn:
            conn.commit()
            cursor.close()
            conn.close()


    def recheck_inventory_pass(self, date, warehouse_id):
        self.ensure_one()
        similar_pickings_map = {}  # {picking_id: [picking_id, ...]}
        warehouse = self.env['stock.warehouse'].browse(warehouse_id)
        date = fields.Date.from_string(date)

        start_date = fields.Datetime.to_datetime(date)
        end_date = start_date + relativedelta(days=1)
        stock_pickings = self.env['stock.picking'].search([
            ('date_done', '!=', False),
            ('date_done', '>=', start_date),
            ('date_done', '<', end_date),
            ('picking_type_id.code', '=', 'inventory_counting'),
            ('location_dest_id.warehouse_id', '=', warehouse.id),
            ('inventory_origin_id', '=', False),
        ], order='date_done desc')
        SIMILAR_PERCENT = 15


        # Tìm các phiếu kiểm kê có sản phẩm trùng lặp > 15%
        for picking in stock_pickings:
            products_1 = set(picking.move_ids_without_package.mapped('product_id').ids)
            if not products_1:
                continue

            similar_pickings = []

            for other in stock_pickings:
                if other.id == picking.id:
                    continue

                products_2 = set(other.move_ids_without_package.mapped('product_id').ids)
                if not products_2:
                    continue

                common_products = products_1 & products_2
                percent_same = (len(common_products) / len(products_1)) * 100

                if percent_same > SIMILAR_PERCENT:
                    similar_pickings.append(other)
                    stock_pickings -= other
                    break

            if similar_pickings:
                similar_pickings_map[picking] = similar_pickings
        in_detail_datas = []
        out_detail_datas = []
        slnxm_id = False


        # Không có phiếu trùng  > 15%
        for picking in stock_pickings:
            for line in picking.move_ids_without_package:
                stock_move_ids = picking.get_exists_stock_move1()
                existing_product_ids = stock_move_ids.mapped('product_id')
                if line.product_id.id in existing_product_ids.ids:
                    in_detail_datas.append(line.prepare_augges_values(line.quantity))
                else: # Sản phẩm không trùng so sánh với augges
                    if line.quantity > line.stock_qty:
                        in_detail_datas.append(line.prepare_augges_values(line.quantity - line.stock_qty))
                    if line.quantity < line.stock_qty:
                        out_detail_datas.append(line.prepare_augges_values(-line.quantity + line.stock_qty))
            _logger.info('Tạo phiếu nhập Augges quá khứ cho phiếu kiểm kê odoo id: %s, name: %s', picking.id, picking.name)
            picking.write({
                'id_augges': slnxm_id,
                # 'sp_augges': value_sp,
                'is_sent_augges': True,
                'pending_sent_augges_action_done': False
            })


        # Có phiếu trùng  > 15%
        for picking in similar_pickings_map:
            for line in picking.move_ids_without_package:
                product = line.product_id
                total_qty = line.quantity

                for similar_picking in similar_pickings_map[picking]:
                    similar_quantity = sum(line.quantity for line in similar_picking.move_ids_without_package if line.product_id == product)
                    if total_qty > similar_quantity:
                        in_detail_datas.append(line.prepare_augges_values(line.quantity - similar_quantity))
                    if line.quantity < similar_quantity:
                        out_detail_datas.append(line.prepare_augges_values(-line.quantity + similar_quantity))
            _logger.info('Tạo phiếu nhập Augges quá khứ cho phiếu kiểm kê odoo id: %s, name: %s', picking.id, picking.name)
            picking.write({
                'id_augges': slnxm_id,
                # 'sp_augges': value_sp,
                'is_sent_augges': True,
                'pending_sent_augges_action_done': False
            })

        #Các phiếu có phiếu gốc
        stock_picking_has_inventory_origin = self.env['stock.picking'].search([
            ('date_done', '!=', False),
            ('date_done', '>=', date),
            ('date_done', '<=', date),
            ('picking_type_id.code', '=', 'inventory_counting'),
            ('location_dest_id.warehouse_id', '=', warehouse.id),
            ('inventory_origin_id', '!=', False),
        ], order='date_done desc')
        for picking in stock_picking_has_inventory_origin:
            for line in picking.move_ids_without_package:
                if line.quantity == 0: continue
                if line.product_id not in picking.inventory_origin_id.move_ids_without_package.mapped('product_id'):
                    if not picking.inventory_origin_id.inventory_origin_id:
                        move = self.env['stock.move'].search([
                            ('picking_id', '!=', picking.id),
                            ('product_id', '=', line.product_id.id),
                            ('quantity', '>', 0),
                            ('state', '=', 'done'),
                            ('location_dest_id', '=', picking.location_dest_id.id),
                            ('picking_id.date_done', '<=', picking.date_done),
                        ], limit=1)
                        if move:
                            if move.quantity >= line.quantity:
                                out_detail_datas.append(line.prepare_augges_values(move.quantity - line.quantity))
                            if move.quantity < line.quantity:
                                in_detail_datas.append(line.prepare_augges_values(line.quantity - move.quantity))
                        else:
                            if line.quantity > line.stock_qty:
                                in_detail_datas.append(line.prepare_augges_values(line.quantity - line.stock_qty))
                            if line.quantity < line.stock_qty:
                                out_detail_datas.append(line.prepare_augges_values(-line.quantity + line.stock_qty))
                    else:
                        if line.product_id in picking.inventory_origin_id.inventory_origin_id.move_ids_without_package.mapped('product_id'):
                            origin_quantity = sum(picking.inventory_origin_id.inventory_origin_id.move_ids_without_package.filtered(lambda x: x.product_id.id == line.product_id.id).mapped('quantity'))
                            if line.quantity > origin_quantity:
                                in_detail_datas.append(line.prepare_augges_values(line.quantity - origin_quantity))
                            if line.quantity < origin_quantity:
                                out_detail_datas.append(line.prepare_augges_values(-line.quantity + origin_quantity))
                        else:
                            stock_move_ids = picking.get_exists_stock_move1()
                            existing_product_ids = stock_move_ids.mapped('product_id')
                            if line.product_id.id in existing_product_ids.ids:
                                in_detail_datas.append(line.prepare_augges_values(line.quantity))
                            else:
                                if line.quantity > line.stock_qty:
                                    in_detail_datas.append(line.prepare_augges_values(line.quantity - line.stock_qty))
                                if line.quantity < line.stock_qty:
                                    out_detail_datas.append(line.prepare_augges_values(-line.quantity + line.stock_qty))

                else:
                    origin_quantity = sum(picking.inventory_origin_id.move_ids_without_package.filtered(lambda x: x.product_id.id == line.product_id.id).mapped('quantity'))
                    if line.quantity > origin_quantity:
                        in_detail_datas.append(line.prepare_augges_values(line.quantity - origin_quantity))
                    if line.quantity < origin_quantity:
                        out_detail_datas.append(line.prepare_augges_values(-line.quantity + origin_quantity))
            _logger.info('Tạo phiếu nhập Augges quá khứ cho phiếu kiểm kê odoo id: %s, name: %s', picking.id, picking.name)
            picking.write({
                'id_augges': slnxm_id,
                # 'sp_augges': value_sp,
                'is_sent_augges': True,
                'pending_sent_augges_action_done': False
            })
        pair_conn = False
        owns_conn = False
        conn, cursor = None, None
        if pair_conn:
            conn = pair_conn
        else:
            conn = self.env['ttb.tools'].get_mssql_connection_send()
            owns_conn = True
        cursor = conn.cursor()

        master_data = self.prepare_augges_values()
        if in_detail_datas:
            master_data['ID_Nx'] = 52
            slnxm_id = self.env['ttb.augges'].create_slnx(master_data, in_detail_datas)
        if out_detail_datas:
            master_data['ID_Nx'] = 82
            slnxm_id = self.env['ttb.augges'].create_slnx(master_data, out_detail_datas)



        if owns_conn:
            conn.commit()
            cursor.close()
            conn.close()
    def check_product_inventory_origin(self):
        """Kiểm tra sản phẩm có trong phiếu gốc không"""
        self.ensure_one()
        if not self.inventory_origin_id:
            for line in self.move_ids_without_package:
                stock_qty = self.env['ttb.augges'].get_augges_quantity(self.location_dest_id.warehouse_id.id_augges, line.product_id.augges_id)
                if line.quantity != stock_qty:
                    return True
        return False

    def get_products_with_inventory_mismatch(self):
        self.ensure_one()
        result = []

        for line in self.move_ids_without_package:
            stock_qty = self.env['ttb.augges'].get_augges_quantity(
                self.location_dest_id.warehouse_id.id_augges,
                line.product_id.augges_id
            )
            if line.quantity != stock_qty:
                result.append({
                    'product_name': line.product_id.display_name,
                    'counted_quantity': line.quantity,
                })

        return result
