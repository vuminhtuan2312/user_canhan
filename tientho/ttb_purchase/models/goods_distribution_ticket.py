from odoo import *
from odoo import api, Command, fields, models, SUPERUSER_ID, _
from odoo.exceptions import UserError, ValidationError
from collections import defaultdict

from datetime import datetime, timedelta, date
import pytz
import logging


_logger = logging.getLogger(__name__)

class GoodsDistributionTicket(models.Model):
    _name = 'goods.distribution.ticket'
    _description = 'Goods Distribution Ticket'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Mã phiếu', required=True, copy=False, default=lambda self: _('New'))
    po_id = fields.Many2one('purchase.order', string='Đơn mua hàng', required=True, readonly=True)
    stock_picking_id = fields.Many2one('stock.picking', string='Phiếu nhập kho', required=True, readonly=True)
    partner_id = fields.Many2one('res.partner', related='po_id.partner_id', string='Nhà cung cấp', store=True)
    goods_distribution_ticket_line_ids = fields.One2many('goods.distribution.ticket.line', 'goods_distribution_ticket_id', string='Chi tiết phiếu phân phối hàng')
    state =  fields.Selection([('draft', 'Nháp'),
                               ('confirmed', 'Đã xác nhận'),
                               ('cancel', 'Đã hủy')], string='Trạng thái', default='draft', tracking=True)
    has_picking = fields.Boolean(string='Đã chia hàng cơ sở', default=False)
    company_id = fields.Many2one('res.company', related='po_id.company_id', string='Công ty', store=True)
    user_confirm = fields.Many2one('res.users', string='Người xác nhận', tracking=True, readonly=True)

    # python
    def _create_augges_sldc(self, picking):
        """Tạo 1 SlDcM và các SlDcD trong Augges tương ứng với 1 picking (1 chi nhánh)."""
        self.ensure_one()
        po = self.po_id
        dc_picking = self.stock_picking_id  # Phiếu nhập kho DC

        # Kho xuất: Kho hàng Giao hàng đến PO (location_dest của phiếu nhập DC)
        wh_source = po.picking_type_id.warehouse_id
        ID_KhoX = wh_source.id_augges
        if not ID_KhoX:
            _logger.warning('Kho xuất (Giao hàng đến PO) chưa có ID Augges, bỏ qua tạo phiếu Augges.')
            return

        # Kho nhận: Kho của picking (chi nhánh)
        wh_dest = picking.location_dest_id.warehouse_id or picking.picking_type_id.warehouse_id
        if not wh_dest or not wh_dest.id_augges:
            _logger.warning('Kho nhận (chi nhánh) chưa có ID Augges, bỏ qua.')
            return
        ID_KhoN = wh_dest.id_augges

        augges_ref = po.partner_id.ref
        if not augges_ref:
            _logger.warning('Nhà cung cấp chưa có mã tham chiếu (ref), bỏ qua tạo phiếu Augges.')
            return
        partner_augges = self.env['ttb.augges'].get_partner(f"Ma_Dt = '{augges_ref}'")
        if not partner_augges:
            _logger.warning('Không tìm thấy đối tượng ở Augges với Ma_Dt=%s', augges_ref)
            return
        augges_id = partner_augges[0]['id']

        inv_date = po.ttb_vendor_invoice_date if po.ttb_vendor_invoice_date else None
        if not inv_date and hasattr(dc_picking, 'invoice_ids') and dc_picking.invoice_ids:
            inv_date = getattr(dc_picking.invoice_ids[:1], 'ttb_vendor_invoice_date', None)
        day = (inv_date or dc_picking.date_done or fields.Datetime.now())
        if day and hasattr(day, 'astimezone'):
            day = day.astimezone(pytz.UTC).replace(tzinfo=None)
        elif day and hasattr(day, 'strftime'):
            if isinstance(day, date) and not isinstance(day, datetime):
                day = datetime.combine(day, datetime.min.time())
        sql_day = day.strftime("%Y-%m-%d 00:00:00")
        sngay = day.strftime("%y%m%d")
        insert_date = datetime.utcnow() + timedelta(hours=7)
        user_augges_id = self.env['ttb.augges'].get_user_id_augges(user=self.env.user) or 0

        # Chi tiết từ move_ids của picking (stock.move: quantity, product_id, purchase_line_id)
        moves = picking.move_ids.filtered(lambda m: m.quantity > 0)

        if not moves:
            _logger.warning('Picking %s không có dòng hàng, bỏ qua tạo Augges.', picking.name)
            return

        cong_sl = sum(moves.mapped('quantity'))
        tong_tien = 0
        for move in moves:
            if move.purchase_line_id:
                price_unit = move.purchase_line_id.price_unit - (move.purchase_line_id.ttb_discount_amount or 0)
            else:
                price_unit = move.product_id.product_tmpl_id.last_price or 0
            tong_tien += price_unit * move.quantity

        ma_kho_x = wh_source.code_augges or wh_source.name or str(ID_KhoX)
        ma_kho_n = wh_dest.code_augges or wh_dest.name or str(ID_KhoN)
        dien_giai = f"{dc_picking.name} {ma_kho_x} xuat {ma_kho_n}"

        conn = self.env['ttb.tools'].get_mssql_connection_send()
        cursor = conn.cursor()
        try:
            id_nx = 0
            try:
                cursor.execute("SELECT TOP 1 ID FROM DmNx WHERE Ma_Ct = 'DC'")
                row = cursor.fetchone()
                if row:
                    id_nx = row[0]
            except Exception as e:
                _logger.warning('Không lấy được ID_Nx cho DC: %s', e)

            cursor.execute("SELECT TOP 1 Sp FROM SlDcM ORDER BY Sp DESC")
            result_sp = cursor.fetchall()
            value_sp = int(result_sp[0][0]) + 1 if result_sp else 1

            master_data = {
                'ID_Dv': 0,
                'IP_ID': 0,
                'Ngay': sql_day,
                'Sngay': sngay,
                'Ngay_Ct': day.strftime("%Y-%m-%d") if hasattr(day, 'strftime') else sql_day[:10],
                'ID_Nx': id_nx,
                'Sp': value_sp,
                'ID_Tt': 1,
                'Ty_Gia': 0,
                'ID_Dt': augges_id,
                'ID_KhoX': ID_KhoX,
                'ID_KhoN': ID_KhoN,
                'Cong_SlQd': cong_sl,
                'Cong_Sl': cong_sl,
                'Tong_Tien': tong_tien,
                'Dien_Giai': dien_giai,
                'InsertDate': insert_date,
                'LastEdit': insert_date,
                'Printed': 0,
                'LoaiCt': '',
                'So_Bk': '',
                'UserID': 2698,
            }
            sldcm_id = self.env['ttb.augges'].insert_record('SlDcM', master_data, conn)
            _logger.warning('Augges ID, SlDcM', sldcm_id)
            picking.write({'id_augges': sldcm_id,
                           'sp_augges': value_sp,
                           })

            No_tk, Co_tk = '1561', '1561'
            detail_stt = 1
            for move in moves:
                if move.purchase_line_id:
                    price_unit = move.purchase_line_id.price_unit - (move.purchase_line_id.ttb_discount_amount or 0)
                else:
                    price_unit = move.product_id.product_tmpl_id.last_price or 0
                qty = move.quantity
                price_total = price_unit * qty
                augges_product_id = move.product_id.product_tmpl_id.augges_id
                if not augges_product_id:
                    _logger.warning('Sản phẩm %s chưa có Augges ID, bỏ qua dòng.', move.product_id.display_name)
                    continue
                detail_data = {
                    'ID': sldcm_id,
                    'Stt': detail_stt,
                    'Sngay': sngay,
                    'ID_KhoX': ID_KhoX,
                    'ID_KhoN': ID_KhoN,
                    'ID_Hang': augges_product_id,
                    'Sl_Qd': qty,
                    'So_Luong': qty,
                    'Ty_Gia': 0,
                    'Gia_Qd': price_unit,
                    'Don_Gia': price_unit,
                    'T_Tien': price_total,
                    'Tien_Cp': 0,
                    'Tyle_Ck': 0,
                    'Tien_Ck': 0,
                    'Don_Gia1': price_unit,
                    'T_Tien1': price_total,
                    'Don_Gia2': price_unit,
                    'T_Tien2': price_total,
                    'No_Tk': No_tk,
                    'Co_Tk': Co_tk,
                    'Md': '',
                    'HS_QD': '',
                }
                self.env['ttb.augges'].insert_record('SlDcD', detail_data, conn, get_id=False)
                detail_stt += 1

            conn.commit()
        except Exception as e:
            _logger.exception('Lỗi tạo phiếu điều chuyển Augges: %s', e)
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    def create_shipping_branch_ticket(self):
        # tạo mới các phiếu vận chuyển về kho cơ sở theo từng cơ sở sau khi xác nhận phiếu nhập DC
        branch_dict = defaultdict(list)
        StockPicking = self.env['stock.picking']
        for line in self.goods_distribution_ticket_line_ids:
            branch_dict[line.branch_id].append(line)

        purchase_order = self.po_id
        location_id = self.env.company.import_warehouse_id.lot_stock_id.id
        location_dest_id = self.env.company.shipping_warehouse_id.id
        for branch, lines in branch_dict.items():
            picking_type = self.env['stock.warehouse'].search(
                [('ttb_branch_id', '=', branch.id), ('ttb_type', '=', 'sale')], limit=1).int_type_id
            move_ids_val = []
            for move in lines:
                move_ids_val.append((0, 0, {
                    'name': move.product_id.product_tmpl_id.name,
                    'product_id': move.product_id.id,
                    'product_uom_qty': move.actual_qty,
                    'quantity': move.actual_qty,
                    'picking_type_id': picking_type.id,
                    'location_id': location_id,
                    'location_dest_id': location_dest_id,
                    'purchase_line_id': move.po_line_id.id,
                    'origin': purchase_order.name,
                }))
            picking = StockPicking.with_user(SUPERUSER_ID).create({
                'partner_id': purchase_order.partner_id.id,
                'move_ids': move_ids_val,
                'picking_type_id': picking_type.id,
                'user_id': False,
                'date': purchase_order.date_order,
                'origin': purchase_order.name,
                'location_id': location_id,
                'location_dest_id': location_dest_id,
                'company_id': purchase_order.company_id.id,
                'ttb_stage': '5',
                'ttb_type': purchase_order.ttb_type,
                'state': 'assigned',
                'goods_distribution_ticket_id': self.id,
                'scheduled_date': fields.Datetime.now(),
            })
            try:
                _logger.warning('Picking create augges: %s', picking)
                self._create_augges_sldc(picking)
            except Exception as e:
                _logger.exception('Lỗi tạo phiếu điều chuyển Augges: %s', e)
                # Không chặn luồng chính, chỉ log

    def button_confirm(self):
        self.ensure_one()

        wizard = self.env['goods.distribution.confirm.wizard'].create({
            'ticket_id': self.id,
        })

        return {
            'name': _('Xác nhận phiếu chia hàng'),
            'type': 'ir.actions.act_window',
            'res_model': 'goods.distribution.confirm.wizard',
            'view_mode': 'form',
            'res_id': wizard.id,
            'target': 'new',
            'context': self.env.context,
        }

    def button_cancel(self):
        self.state = 'cancel'
        self.stock_picking_id.has_ticket = False
        pass

    def action_view_stock_picking(self):
        self.ensure_one()
        picking_ids = self.env['stock.picking'].search(
            [('origin', '=', self.po_id.name), ('ttb_stage', '=', '5')], )
        if not picking_ids:
            raise UserError('Chưa có phiếu nhập kho cơ sở. Vui lòng kiểm tra lại!!!')
        return {
            'name': 'Phiếu chia hàng cơ sở',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'list,form',
            'domain': [('id', 'in', picking_ids.ids)],
            'target': 'current',
        }

    def write(self, vals):
        res = super().write(vals)
        return res

class GoodsDistributionTicketLine(models.Model):
    _name = 'goods.distribution.ticket.line'
    _description = 'Goods Distribution Ticket Line'
    _order = 'product_id, branch_id'

    goods_distribution_ticket_id = fields.Many2one('goods.distribution.ticket', string='Phiếu phân phối hàng', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Sản phẩm', required=True)
    product_qty = fields.Float(string='Số lượng', required=True, readonly=True)
    actual_qty = fields.Float(string='Số lượng thực tế')
    branch_id = fields.Many2one('ttb.branch', string='Chi nhánh', required=True)
    branch_code = fields.Char(related='branch_id.code', string='Mã cơ sở', readonly=True, store=True)
    po_line_id = fields.Many2one('purchase.order.line', string='Dòng đơn mua hàng')
    ttb_request_line_id = fields.Many2one(related='po_line_id.ttb_request_line_id',
                                          string='Dòng yêu cầu mua hàng', store=True)
    prd_image = fields.Binary(related='ttb_request_line_id.product_image', string='Ảnh sản phẩm', readonly=True)
    default_code = fields.Char(related='ttb_request_line_id.default_code', string='Mã sản phẩm', readonly=True)

    def action_plus(self):
        self.actual_qty += 1

    def action_minus(self):
        self.actual_qty -= 1

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            new_quantity = sum(rec.goods_distribution_ticket_id.goods_distribution_ticket_line_ids.filtered(lambda l: l.product_id == rec.product_id).mapped('actual_qty'))
            rec.goods_distribution_ticket_id.stock_picking_id.move_ids.filtered(lambda m: m.product_id == rec.product_id).write({'quantity': new_quantity})
        return res

class GoodsDistributionTicketTemplate(models.Model):
    _name = 'goods.distribution.ticket.template'
    _description = 'Goods Distribution Ticket Template'

    name = fields.Char(string='Tên mẫu', required=True)
    goods_distribution_ticket_template_line_ids = fields.One2many('goods.distribution.ticket.template.line', 'goods_distribution_ticket_template_id', string='Chi tiết mẫu phiếu chia hàng')
    proportion_total = fields.Float(string='Tổng tỷ lệ (%)', compute='_compute_proportion_total')
    branch_ids = fields.Many2many('ttb.branch', string='Các chi nhánh', compute='_compute_branch_ids')

    @api.depends('goods_distribution_ticket_template_line_ids.branch_id', 'goods_distribution_ticket_template_line_ids')
    def _compute_branch_ids(self):
        for rec in self:
            rec.branch_ids = rec.goods_distribution_ticket_template_line_ids.mapped('branch_id')

    @api.depends('goods_distribution_ticket_template_line_ids.proportion', 'goods_distribution_ticket_template_line_ids')
    def _compute_proportion_total(self):
        for rec in self:
            rec.proportion_total = sum(line.proportion for line in rec.goods_distribution_ticket_template_line_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            proportion_total = 0
            for line in val.get('goods_distribution_ticket_template_line_ids', []):
                if isinstance(line, (list, tuple)) and len(line) > 2 and isinstance(line[2], dict):
                    proportion_total += line[2].get('proportion', 0)
            if proportion_total != 100:
                raise ValidationError(_('Tổng tỷ lệ phân phối phải bằng 100%. Vui lòng kiểm tra lại!'))
        return super().create(vals_list)

    def write(self, vals):
        result = super().write(vals)

        for rec in self:
            proportion_total = sum(line.proportion for line in rec.goods_distribution_ticket_template_line_ids)
            if proportion_total != 100:
                raise ValidationError(_('Tổng tỷ lệ phân phối phải bằng 100%. Vui lòng kiểm tra lại!'))
        return result

class GoodsDistributionTicketTemplateLine(models.Model):
    _name = 'goods.distribution.ticket.template.line'
    _description = 'Goods Distribution Ticket Template Line'

    goods_distribution_ticket_template_id = fields.Many2one('goods.distribution.ticket.template', string='Mẫu phiếu phân phối hàng', required=True, ondelete='cascade')
    branch_id = fields.Many2one('ttb.branch', string='Chi nhánh', required=True)
    prioritize = fields.Integer(string='Thứ tự ưu tiên', default=0)
    proportion = fields.Float(string='Tỷ lệ (%)', default=0)
