from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, date, time, timedelta
from odoo.tools.misc import format_date
import logging
import io
import base64
import xlsxwriter

_logger = logging.getLogger(__name__)

class TtbReturnRequest(models.Model):
    _name = 'ttb.return.request'
    _description = "Đề nghị trả hàng"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'ttb.approval.mixin']

    name = fields.Char(string='Mã dự trù', required=True, readonly=True, copy=False, default='Mới')
    requester_id = fields.Many2one('res.users', string='Người đề nghị', default=lambda self: self.env.user)
    request_date = fields.Date(string='Ngày đề nghị', default=fields.Date.today)
    branch_id = fields.Many2one('ttb.branch', string='Cơ sở', required=True, tracking=True)
    supplier_id = fields.Many2one('res.partner', string='Nhà cung cấp', required=True, tracking=True, domain="[('supplier_rank', '>', 0)]")
    reason = fields.Text(string='Lý do trả hàng', required=True)
    return_type = fields.Selection([('pickup', 'NCC đến lấy'), ('ship', 'Chuyển tới NCC')], string='Loại hình trả', tracking=True)
    state = fields.Selection([
        ('draft', 'Mới'),
        ('pending', 'Đang duyệt'),
        ('wait_pick', 'Đợi nhặt hàng'),
        ('wait_move', 'Đợi điều chuyển VP'),
        ('wait_pack', 'Đợi đóng gói'),
        ('wait_transfer', 'Đợi trung chuyển'),
        ('wait_dc_receive', 'Đợi DC nhận hàng'),
        ('wait_return', 'Đợi trả NCC'),
        ('wait_supplier_approve', 'Đợi NCC xác nhận'),
        ('wait_supplier_return', 'Đợi hoàn hàng'),
        ('wait_invoice', 'Đợi xuất hóa đơn'),
        ('done', 'Hoàn thành'),
        ('cancel', 'Hủy')
    ], string='Trạng thái', default='draft', tracking=True)
    line_ids = fields.One2many('ttb.return.request.line', inverse_name='request_id', string='Chi tiết trả hàng', copy=True)
    office_transfer_number = fields.Char(string="Số phiếu điều chuyển kho văn phòng")
    dc_transfer_number = fields.Char(string="Số phiếu điều chuyển kho DC")
    supplier_return_number = fields.Char(string="Số phiếu trả hàng NCC")
    supplier_receive_return_number = fields.Char(string="Số phiếu NCC trả hàng")
    central_location_id = fields.Many2one(string="Kho DC", comodel_name='stock.location', domain="[('name', 'ilike', 'Tồn kho')]", tracking=True)
    plan_tl_id = fields.Many2one(comodel_name='plan.return.request', string='Phiếu hàng trả lại')
    need_right_invoice_qty = fields.Boolean(string='Cần xuất hóa đơn đúng số lượng')
    is_transit_dc = fields.Boolean(string='Trung chuyển qua DC')
    debt_status = fields.Selection([
        ('waiting_invoice', 'Chờ xuất hoá đơn'),
        ('invoiced', 'Đã xuất hoá đơn'),
        ('cleared', 'Đã cấn trừ công nợ'),
    ], string='Trạng thái công nợ', default='waiting_invoice')

    picking_ids = fields.One2many(comodel_name='stock.picking', inverse_name='ttb_return_request_id', string='Phiếu nhặt hàng')
    count_picking_ids = fields.Integer(string='Số phiếu nhặt hàng', compute='_compute_count_picking_ids')
    stock_warehouse_id = fields.Many2one('stock.warehouse', string='Kho', domain="[('ttb_branch_id', '=', branch_id)]",
                                         required=True, tracking=True)
    total_quantity = fields.Float(string='Tổng số lượng sản phẩm', compute='_compute_total_quantity')
    total_actual_return = fields.Float(string='Tổng số lượng trả thực tế', compute='_compute_total_actual_return')
    total_amount = fields.Float(string='Tổng tiền', compute='_compute_total_amount')
    ttb_categ_ids =  fields.Many2many('product.category', string='Ngành', domain="[('category_level', '=', 1)]",
                                      compute='_compute_ttb_categ_ids', store=True, readonly=False)

    current_state = fields.Text('Trạng thái hiện tại')
    old_id_auggess = fields.Text('Số phiếu Auggess cũ')

    @api.depends('supplier_id')
    def _compute_ttb_categ_ids(self):
        for rec in self:
            if rec.supplier_id:
                rec.ttb_categ_ids = rec.supplier_id.ttb_categ_ids

    @api.depends('line_ids.qty_supplier_received')
    def _compute_total_actual_return(self):
        for rec in self:
            rec.total_actual_return = sum(rec.line_ids.mapped('qty_supplier_received'))

    @api.depends('line_ids.amount')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = sum(rec.line_ids.mapped('amount'))

    @api.depends('line_ids.quantity')
    def _compute_total_quantity(self):
        for rec in self:
            rec.total_quantity = sum(rec.line_ids.mapped('quantity'))

    @api.depends('picking_ids')
    def _compute_count_picking_ids(self):
        for rec in self:
            rec.count_picking_ids = len(rec.picking_ids)

    def action_view_pickings(self):
        self.ensure_one()
        context = {
            'default_ttb_return_request_id': self.id,
            'from_return_request': True,  # Dùng để làm điều kiện ẩn/hiện cột
        }
        if len(self.picking_ids) == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'stock.picking',
                'view_mode': 'form',
                'res_id': self.picking_ids.id,
                'context': context,
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'stock.picking',
                'view_mode': 'list,form',
                'domain': [('id', 'in', self.picking_ids.ids)],
                'context': context,
            }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == 'Mới':
                vals['name'] = self.env['ir.sequence'].next_by_code('ttb.return.request') or 'Mới'
        return super().create(vals_list)

    def action_import_product(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'import',
            'target': 'new',
            'name': 'Nhập sản phẩm',
            'params': {
                'context': {'default_request_id': self.id},
                'active_model': 'ttb.return.request.line',
            }
        }

    def action_export_product(self):
        self.ensure_one()

        lines = self.env['ttb.return.request.line'].search([
            ('request_id', '=', self.id)
        ])
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Chi tiết trả hàng')

        header_format = workbook.add_format({
            'bold': True,
            'border': 1,
            'align': 'center'
        })
        text_format = workbook.add_format({'border': 1})
        number_format = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})

        headers = [
            'Mã sản phẩm',
            'Sản phẩm',
            'Tên sản phẩm NCC',
            'Đơn giá trả',
            'Số lượng',
            'Đơn vị',
            'Thuế',
            'Tiền thuế',
            '% CK',
            'CK tiền',
            'Thành tiền',
        ]

        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
            worksheet.set_column(col, col, 20)

        row = 1
        for line in lines:
            worksheet.write(row, 0, line.default_code or '', text_format)
            worksheet.write(row, 1, line.product_id.name or '', text_format)
            worksheet.write(row, 2, line.vendor_product_name or '', text_format)
            worksheet.write(row, 3, line.unit_price or 0.0, number_format)
            worksheet.write(row, 4, line.quantity or 0.0, number_format)
            worksheet.write(row, 5, line.product_id.uom_id.name or '', text_format)
            worksheet.write(row, 6, ', '.join(line.ttb_taxes_id.mapped('name')) or '', text_format)
            worksheet.write(row, 7, line.price_tax or 0.0, number_format)
            worksheet.write(row, 8, line.discount or 0.0, number_format)
            worksheet.write(row, 9, line.ttb_discount_amount or 0.0, number_format)
            worksheet.write(row, 10, line.amount or 0.0, number_format)
            row += 1

        workbook.close()
        output.seek(0)

        attachment = self.env['ir.attachment'].create({
            'name': f'Chi_tiet_tra_hang_{self.name}.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(output.read()),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def action_update_price_from_excel(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'import',
            'target': 'new',
            'name': 'Cập nhật giá từ Excel',
            'params': {
                'model': 'ttb.return.request.line',
                'context': {
                    'default_request_id': self.id,
                    'import_mode': 'update_price',
                },
            }
        }

    def product_distribution(self):
        total_line = len(self.line_ids)
        number_of_ticket = (total_line // 1000) + 1
        number_line_of_ticket = total_line//number_of_ticket
        surplus = total_line % number_of_ticket
        return number_of_ticket, number_line_of_ticket, surplus

    def action_create_picking_ticket(self, line_ids, picking_type, user_id, case_normal, create_move_line, state):
        """
        Với case_normal = True thì sẽ lấy dữ liệu từ số lượng nhặt trong phiếu trả hàng cho số lượng nhu cầu và số lượng trong phiếu điều chuyển
        Với case_normal = False thì số lượng nhu cầu sẽ bằng 0
        """
        if state == 'dc':
            location_id = self.stock_warehouse_id.pack_type_id.default_location_dest_id.id
            location_dest_id = self.env.company.return_warehouse_id.id
            if not location_dest_id:
                raise UserError("Công ty chưa cấu hình kho đi đường trả lại.")
        elif state == 'dc_received':
            location_id = self.env.company.return_warehouse_id.id
            location_dest_id = self.central_location_id.id
            if not location_dest_id:
                raise UserError("Công ty chưa cấu hình kho đi đường trả lại.")
        elif state == 'back_to_supplier':
            location_id = self.central_location_id.id if self.is_transit_dc else self.picking_ids.filtered(lambda p: p.pickup_status == 'packing').location_dest_id.id
            location_dest_id = picking_type.default_location_dest_id.id
        else:
            location_id = picking_type.default_location_src_id.id
            location_dest_id = picking_type.default_location_dest_id.id

        picking_vals = {
            'picking_type_id': picking_type.id,
            'partner_id': self.supplier_id.id,
            'origin': self.name,
            'location_id': location_id,
            'location_dest_id': location_dest_id,
            'ttb_return_request_id': self.id,
            'user_id': user_id.user_id.id if user_id else False,
            'pickup_status': state,
        }
        picking = self.env['stock.picking'].create(picking_vals)
        for line in line_ids:
            if not case_normal:
                qty = 0
            elif state in ('dc', 'back_to_supplier'):
                qty = line.qty_supplier_received
            else:
                qty = line.qty_picked

            move_vals = {
                'picking_id': picking.id,
                'name': line.product_id.display_name,
                'product_id': line.product_id.id,
                'product_uom_qty': qty,
                'quantity': qty,
                'product_uom': line.product_id.uom_id.id,
                'location_id': picking_type.default_location_src_id.id,
                'location_dest_id': picking_type.default_location_dest_id.id,
                'ttb_return_request_line_id': line.id,
                'ttb_required_qty': line.quantity if state == 'picking' else 0,
                'return_price_unit': line.unit_price if state == 'back_to_supplier' else 0,
                'confirm_vendor_price': line.confirm_vendor_price if state == 'back_to_supplier' else 0
            }
            move = self.env['stock.move'].create(move_vals)
            if create_move_line:
                move_line_vals = move._prepare_move_line_vals(quantity=0.0, reserved_quant=None)

                # đảm bảo các giá trị đúng với nghiệp vụ phiếu trả (đếm lại từ 0)
                move_line_vals.update({
                    'qty_done': 0.0,
                    'location_id': picking_type.default_location_src_id.id,
                    'location_dest_id': picking_type.default_location_dest_id.id,
                    'picking_id': picking.id,
                })
                self.env['stock.move.line'].create(move_line_vals)
        #thông báo cho quản lý nhà sách phụ trách quầy trả hàng
        if user_id:
            message = _("Hiện đang có phiếu nhăt hàng %s cần phân công") % (
                self.name)
            self.sudo().message_post(
                body=message,
                partner_ids=[user_id.user_id.partner_id.id]
            )
        return picking

    def action_send_approve(self):
        if self.state != 'draft': return
        if not self.sent_ok: return

        list_field_require = ''
        if not self.branch_id:
            list_field_require += 'Cơ sở\n'
        if not self.stock_warehouse_id:
            list_field_require += '- Kho\n'
        if not self.supplier_id:
            list_field_require += '- Nhà cung cấp\n'
        if not self.return_type:
            list_field_require += '- Loại hình trả\n'
        if list_field_require:
            raise UserError(f'Bạn cần điền đầy đủ các thông tin sau trước khi gửi duyệt:\n{list_field_require}')

        process_id, approval_line_ids = self.get_approval_line_ids()
        self.write({'process_id': process_id.id,
                    'date_sent': fields.Datetime.now(),
                    'state': 'pending',
                    'approval_line_ids': [(5, 0, 0)] + approval_line_ids})
        if self.env.user.id not in self.current_approve_user_ids.ids:
            self.send_notify(message='Bạn cần duyệt yêu cầu trả hàng', users=self.current_approve_user_ids, subject='Yêu cầu trả hàng cần duyệt')
        self.action_approve()
        return True

    def action_approve(self):
        self.ensure_one()
        if self.state != 'pending':
            return

        self.state_change('approved')

        all_approved = not self.rule_line_ids.filtered(lambda l: not l.notif_only and l.state != 'approved')
        if all_approved:
            self.sudo().write({
                'state': 'wait_pick',
                'date_approved': fields.Datetime.now()
            })
            self.send_notify(
                message='Yêu cầu trả hàng của bạn đã được duyệt',
                users=self.requester_id,
                subject='Yêu cầu trả hàng đã duyệt'
            )
            #tạo phiếu nhặt hàng
            picking_type = self.stock_warehouse_id.return_type_id
            if not picking_type:
                raise UserError(f"Kho '{self.stock_warehouse_id.name}' chưa cấu hình Loại trả lại.")
            params = self.env['ir.config_parameter'].sudo()
            if not params.get_param('ttb_return.job_id'):
                params.set_param('ttb_return.job_id', '79')
            job_id = int(params.get_param('ttb_return.job_id'))
            user_id = self.env['hr.employee'].sudo().search(
                [('ttb_branch_ids', 'in', self.branch_id.id), ('job_id', '=', job_id),
                 ('ttb_categ_ids', 'in', self.supplier_id.ttb_categ_ids.ids)], limit=1)
            number_of_ticket, number_line_of_ticket, surplus = self.product_distribution()
            _logger.info(f'Tạo mới {number_of_ticket} phiếu nhặt hàng, với trung bìnhh {number_line_of_ticket} sản phẩm 1 phiếu và dư {surplus}')
            list_line_ids = self.line_ids.ids
            _logger.info(f'Id các line cần tạo phiếu: {list_line_ids}')
            while number_of_ticket > 0:
                end_point = number_line_of_ticket + 1 if surplus > 0 else number_line_of_ticket
                surplus -= 1
                number_of_ticket -= 1
                list_move_create = list_line_ids[0:end_point]
                _logger.info(f'Id các line được tạo phiếu: {list_move_create}')
                del list_line_ids[0:end_point]
                move_ids = self.line_ids.filtered(lambda l: l.id in list_move_create)
                self.action_create_picking_ticket(move_ids, picking_type, user_id, False, True, 'picking')

        return True

    def action_cancel(self):
        for rec in self:
            if rec.state in ['draft', 'pending', 'wait_pick']:
                rec.state = 'cancel'

    wait_ncc_date = fields.Date(
        string="Ngày chuyển Đợi trả NCC",
        copy=False,
        help="Ngày Đề nghị trả hàng chuyển sang trạng thái 'Đợi trả NCC'. Dùng cho SLA Rule 4-5-6.",
    )

    # --- MỐC THỜI GIAN CHO CÁC TRẠNG THÁI SLA MỚI ---
    wait_pick_date = fields.Date(
        string="Ngày chuyển Đợi nhặt hàng",
        copy=False,
        help="Ngày phiếu chuyển sang 'Đợi nhặt hàng' – dùng cho rule phiếu nhặt cần xác nhận SL."
    )
    wait_pack_date = fields.Date(
        string="Ngày chuyển Đợi đóng gói",
        copy=False,
        help="Ngày phiếu chuyển sang 'Đợi đóng gói' – dùng cho rule phiếu đóng gói cần hoàn thành."
    )
    wait_supplier_approve_date = fields.Date(
        string="Ngày chuyển Đợi NCC xác nhận",
        copy=False,
        help="Ngày phiếu chuyển sang 'Đợi NCC xác nhận' – dùng cho rule chờ NCC xác nhận SL."
    )
    wait_supplier_return_date = fields.Date(
        string="Ngày chuyển Đợi hoàn hàng",
        copy=False,
        help="Ngày phiếu chuyển sang 'Đợi hoàn hàng' – dùng cho rule nhập lại hàng NCC không nhận."
    )
    wait_invoice_date = fields.Date(
        string="Ngày chuyển Đợi xuất hóa đơn",
        copy=False,
        help="Ngày phiếu chuyển sang 'Đợi xuất hóa đơn' – dùng cho rule nhắc Kế toán xuất hóa đơn."
    )

    def write(self, vals):
        """
        - Giữ nguyên logic cũ set wait_ncc_date khi vào state 'wait_return'
        - Bổ sung set ngày cho:
            + wait_pick_date           khi state -> 'wait_pick'
            + wait_pack_date           khi state -> 'wait_pack'
            + wait_supplier_approve_date khi state -> 'wait_supplier_approve'
            + wait_supplier_return_date khi state -> 'wait_supplier_return'
            + wait_invoice_date        khi state -> 'wait_invoice'
        """
        prev_states = {r.id: r.state for r in self}
        res = super().write(vals)

        if "is_transit_dc" in vals and not self.central_location_id and "central_location_id" not in vals:
            raise UserError("Bạn cần chọn kho DC khi trung chuyển qua kho DC.")

        if "state" in vals:
            today = fields.Date.context_today(self)
            for rec in self:
                old_state = prev_states.get(rec.id)
                new_state = rec.state
                if old_state == new_state:
                    continue

                # Rule 4-5-6: Đợi trả NCC
                if new_state == "wait_return" and not rec.wait_ncc_date:
                    rec.wait_ncc_date = today

                # Rule A: Đợi nhặt hàng
                if new_state == "wait_pick" and not rec.wait_pick_date:
                    rec.wait_pick_date = today

                # Rule B: Đợi đóng gói
                if new_state == "wait_pack" and not rec.wait_pack_date:
                    rec.wait_pack_date = today

                # Rule E: Đợi NCC xác nhận
                if new_state == "wait_supplier_approve" and not rec.wait_supplier_approve_date:
                    rec.wait_supplier_approve_date = today

                # Rule F: Đợi NCC hoàn hàng
                if new_state == "wait_supplier_return" and not rec.wait_supplier_return_date:
                    rec.wait_supplier_return_date = today

                # Rule G: Đợi xuất hóa đơn
                if new_state == "wait_invoice" and not rec.wait_invoice_date:
                    rec.wait_invoice_date = today

                if new_state == 'pending':
                    if not rec.supplier_id.ttb_categ_ids:
                        rec.supplier_id.ttb_categ_ids = rec.ttb_categ_ids
                if new_state == "wait_move":
                    picking_type_id = rec.stock_warehouse_id.int_type_id
                    for line in rec.picking_ids:
                        picking = line.create_stock_picking_ticket(False, False, picking_type_id, 'waiting_packing')
                        picking.with_context(create_augges_picking_ticket=True).create_auggest_return_ticket(False, False,103, 'dcnb')
                if new_state in ('pending', 'wait_pick') and not rec.ttb_categ_ids:
                    raise UserError(f'Bạn cần thiết lập Ngành cho đề nghị trả hàng {rec.name} trước khi gửi duyệt hoặc nhặt hàng!')
                if new_state == "wait_transfer":
                    picking_type_id = rec.stock_warehouse_id.int_type_id
                    picking = rec.action_create_picking_ticket(rec.line_ids, picking_type_id, False, True, False, 'dc')
                    picking.with_context(create_augges_picking_ticket=True).create_auggest_return_ticket(False, False, 103, 'dc')
                if new_state == "wait_dc_receive":
                    picking_type_id = rec.stock_warehouse_id.int_type_id
                    picking = rec.action_create_picking_ticket(rec.line_ids, picking_type_id, False, True, False, 'dc_received')
                if new_state == "wait_return":
                    picking_type_id = rec.stock_warehouse_id.out_type_id
                    rec.action_create_picking_ticket(rec.line_ids, picking_type_id, False, True, False, 'back_to_supplier')

        return res

    @api.model
    def _compute_deadline_work_days(self, start_date, work_days, employee=None):
        """
        Trả về ngày deadline sau `work_days` NGÀY LÀM VIỆC kể từ `start_date`.

        Ưu tiên:
          1. employee.resource_calendar_id (nếu có)
          2. env.company.resource_calendar_id
          3. fallback Mon–Fri (bỏ T7/CN)
        """
        if not start_date or not work_days or work_days <= 0:
            return start_date

        # Chuẩn hoá start_date về date
        if isinstance(start_date, datetime):
            base_date = start_date.date()
        elif isinstance(start_date, date):
            base_date = start_date
        else:
            base_date = fields.Date.from_string(start_date)

        # 1) Lấy calendar
        calendar = None
        if employee and employee.resource_calendar_id:
            calendar = employee.resource_calendar_id
        elif self.env.company.resource_calendar_id:
            calendar = self.env.company.resource_calendar_id

        if calendar:
            hours_per_day = calendar.hours_per_day or 8.0
            hours = work_days * hours_per_day

            # Ghép base_date + 08:00 -> datetime
            start_dt = datetime.combine(base_date, time(8, 0, 0))

            # truyền trực tiếp datetime vào plan_hours (KHÔNG convert sang string)
            deadline_dt = calendar.plan_hours(
                hours,
                start_dt,
                compute_leaves=True,
            )
            # deadline_dt là datetime -> trả về date
            return deadline_dt.date()

        # 2) Fallback: tự tính ngày làm việc Mon–Fri
        current = base_date
        remaining = work_days
        while remaining > 0:
            current += timedelta(days=1)
            if current.weekday() in (5, 6):  # T7, CN
                continue
            remaining -= 1
        return current

    def _get_employee_by_job(self, job_name):
        """
        Trả về 1 hr.employee đầu tiên có job_id.name giống job_name.
        Vì hệ thống đảm bảo 100% nhân viên có job_id nên không cần xml_id.
        """
        Emp = self.env["hr.employee"]

        if not job_name:
            return Emp

        # Tìm employee theo tên chức vụ (ilike để hỗ trợ viết hoa/thường)
        employee = Emp.sudo().search([
            ("job_id.name", "ilike", job_name),
        ])

        return employee

    def _get_partners_by_job(self, job_name):
        employees = self._get_employee_by_job(job_name)
        return employees.mapped("user_id.partner_id")

    def _get_employees_by_job_and_branch(self, job_name, branch):
        """
        Lấy tất cả employee:
        - job_id.name ilike job_name
        - ttb_branch_ids chứa branch.id
        """
        Emp = self.env["hr.employee"]
        if not job_name or not branch:
            return Emp
        return Emp.sudo().search([
            ("active", "=", True),
            ("job_id.name", "ilike", job_name),
            ("ttb_branch_ids", "in", branch.id),
            ("user_id", "!=", False),
        ])

    def _get_partners_by_job_and_branch(self, job_name, branch):
        employees = self._get_employees_by_job_and_branch(job_name, branch)
        return employees.mapped("user_id.partner_id")

    @api.model
    def _cron_rr_rule1(self):
        """
        Sau 2 ngày LÀM VIỆC kể từ request_date,
        nếu Đề nghị trả hàng vẫn ở trạng thái 'draft' (Mới) thì gửi thông báo.
        """
        today = fields.Date.today()

        # lấy 1 nhân viên có job Trưởng nhóm mua hàng để dùng calendar
        employees_for_sla = self._get_employee_by_job(job_name="Trưởng nhóm mua hàng")
        employee_for_calendar = employees_for_sla[:1] if employees_for_sla else None

        candidates = self.search([
            ("state", "=", "draft"),
            ("request_date", "!=", False),
            ("request_date", "<=", today),
        ])

        to_notify = self.browse()
        for req in candidates:
            deadline = self._compute_deadline_work_days(
                req.request_date,
                2,
                employee=employee_for_calendar or None,
            )
            if deadline and today >= deadline:
                to_notify |= req

        if to_notify:
            to_notify._rr_rule1_log_and_notify()

    def _rr_rule1_render_body(self):
        """Sinh nội dung HTML cho Rule 1 (RR01)."""
        self.ensure_one()
        return _(
            "Hiện đang có Đề nghị trả hàng %s cần Hoàn thiện"
        ) % (self.name)

    def _rr_rule1_get_recipients(self):
        """
        Người nhận Rule 1:
        - Tất cả nhân viên có Job = 'Trưởng nhóm mua hàng'
        """
        self.ensure_one()
        partners = self._get_partners_by_job(job_name="Trưởng nhóm mua hàng")
        if partners:
            return partners
        # fallback: người đề nghị
        if getattr(self, "requester_id", False) and self.requester_id.partner_id:
            return self.requester_id.partner_id
        return self.env["res.partner"]

    def _rr_rule1_log_and_notify(self):
        """
        Gửi message_notify + ghi log cho các phiếu trong self theo Rule 1.
        """
        # Log = self.env["ttb.return.notification.log"]
        # RULE_CODE = "RR01"

        for rec in self:
            # tránh gửi trùng
            # exists = Log.search_count([
            #     ("model", "=", rec._name),
            #     ("res_id", "=", rec.id),
            #     ("rule_code", "=", RULE_CODE),
            # ])
            # if exists:
            #     continue

            partners = rec._rr_rule1_get_recipients()
            if not partners:
                continue

            body = rec._rr_rule1_render_body()
            subject = _("Đề nghị trả hàng %s cần hoàn thiện") % rec.name

            rec.message_notify(
                partner_ids=partners.ids,
                body=body,
                subject=subject,
            )

            # Log.create({
            #     "model": rec._name,
            #     "res_id": rec.id,
            #     "rule_code": RULE_CODE,
            #     "state_at_send": rec.state,
            # })

        # ---------------- RULE 4 ----------------

    def _rr_rule4_render_body(self):
        """Rule 4 – gửi cho Người tạo Đề nghị trả hàng."""
        self.ensure_one()
        date_str = format_date(self.env, self.wait_ncc_date) if self.wait_ncc_date else ""
        return _(
            "Hiện đang có Đề nghị trả hàng %s cần NCC đến lấy"
        ) % (self.name)

    def _rr_rule4_get_recipients(self):
        self.ensure_one()
        Partner = self.env["res.partner"]
        if getattr(self, "requester_id", False) and self.requester_id.partner_id:
            return self.requester_id.partner_id
        return Partner  # rỗng

    def _rr_rule4_log_and_notify(self):
        # Log = self.env["ttb.return.notification.log"]
        # RULE_CODE = "RR04"

        for req in self:
            recipients = req._rr_rule4_get_recipients()
            if not recipients:
                continue

            # đã gửi chưa?
            # exists = Log.search_count([
            #     ("model", "=", req._name),
            #     ("res_id", "=", req.id),
            #     ("rule_code", "=", RULE_CODE),
            # ])
            # if exists:
            #     continue

            body = req._rr_rule4_render_body()
            subject = _("Hiện đang có Đề nghị trả hàng %s cần NCC đến lấy") % req.name

            req.message_notify(
                partner_ids=recipients.ids,
                subject=subject,
                body=body,
            )

            # Log.create({
            #     "model": req._name,
            #     "res_id": req.id,
            #     "rule_code": RULE_CODE,
            #     "state_at_send": req.state,
            # })

        # ---------------- RULE 5 ----------------

    def _rr_rule5_render_body(self):
        """Rule 5 – gửi cho Giám đốc nhà sách cùng cơ sở."""
        self.ensure_one()
        return _("Hiện đang có Đề nghị trả hàng %s cần ship đến NCC") % self.name

    def _rr_rule5_get_recipients(self):
        """
        User có chức vụ 'Giám đốc nhà sách', Cơ sở giống với Cơ sở trong Đề nghị trả hàng.
        """
        self.ensure_one()
        if not self.branch_id:
            return self.env["res.partner"]
        return self._get_partners_by_job_and_branch("Giám đốc nhà sách", self.branch_id)

    def _rr_rule5_log_and_notify(self):
        # Log = self.env["ttb.return.notification.log"]
        # RULE_CODE = "RR05"

        for req in self:
            recipients = req._rr_rule5_get_recipients()
            if not recipients:
                continue

            # exists = Log.search_count([
            #     ("model", "=", req._name),
            #     ("res_id", "=", req.id),
            #     ("rule_code", "=", RULE_CODE),
            # ])
            # if exists:
            #     continue

            body = req._rr_rule5_render_body()
            subject = _("Hiện đang có Đề nghị trả hàng %s cần ship đến NCC") % req.name

            req.message_notify(
                partner_ids=recipients.ids,
                subject=subject,
                body=body,
            )

            # Log.create({
            #     "model": req._name,
            #     "res_id": req.id,
            #     "rule_code": RULE_CODE,
            #     "state_at_send": req.state,
            # })

    # ---------------- RULE 6 ----------------
    def _rr_rule6_render_body(self):
        self.ensure_one()
        date_str = format_date(self.env, self.wait_ncc_date) if self.wait_ncc_date else ""
        return _(
            "Đề nghị trả hàng %s (Trung chuyển DC, loại hình: NCC đến lấy) "
            "đã ở trạng thái Đợi trả NCC từ ngày %s và sau 2 ngày làm việc vẫn chưa được xử lý."
        ) % (self.name, date_str)

    def _rr_rule6_get_recipients(self):
        """
        Người nhận: TN kho DC (hiện chưa có, cứ để code),
                    Giám đốc khối cung ứng.
        """
        self.ensure_one()
        partners = self.env["res.partner"]

        # TODO: sau này khi có chức danh 'TN kho DC', chỉ cần đảm bảo job_name đúng
        partners |= self._get_partners_by_job("TN kho DC")

        # Giám đốc khối cung ứng
        partners |= self._get_partners_by_job("Giám đốc khối cung ứng")

        return partners

    def _rr_rule6_log_and_notify(self):
        # Log = self.env["ttb.return.notification.log"]
        # RULE_CODE = "RR06"

        for req in self:
            recipients = req._rr_rule6_get_recipients()
            if not recipients:
                continue

            # exists = Log.search_count([
            #     ("model", "=", req._name),
            #     ("res_id", "=", req.id),
            #     ("rule_code", "=", RULE_CODE),
            # ])
            # if exists:
            #     continue

            body = req._rr_rule6_render_body()
            subject = _("Hiện đang có Đề nghị trả hàng %s cần NCC đến lấy") % req.name

            req.message_notify(
                partner_ids=recipients.ids,
                subject=subject,
                body=body,
            )

            # Log.create({
            #     "model": req._name,
            #     "res_id": req.id,
            #     "rule_code": RULE_CODE,
            #     "state_at_send": req.state,
            # })

    # =========================
    # HELPER CHUNG CHO CÁC RULE SLA ĐƠN GIẢN
    # =========================
    def _rr_simple_state_sla(
        self,
        state,
        date_field,
        work_days,
        recipient_getter,
        subject_builder,
        body_builder,
    ):
        """
        Helper dùng chung cho các rule:
        - Filter theo state
        - Lấy ngày từ date_field
        - Sau work_days ngày làm việc thì gửi notify

        recipient_getter(rec) -> res.partner recordset (người nhận)
        subject_builder(rec)  -> string
        body_builder(rec)     -> string (HTML/text)
        """
        today = fields.Date.today()
        Model = self.env["ttb.return.request"]

        candidates = self.search([
            ("state", "=", state),
            (date_field, "!=", False),
        ])

        for rec in candidates:
            start_date = getattr(rec, date_field)
            deadline = Model._compute_deadline_work_days(
                start_date,
                work_days,
                employee=None,
            )
            if not (deadline and today >= deadline):
                continue

            partners = recipient_getter(rec)
            if not partners:
                continue

            subject = subject_builder(rec)
            body = body_builder(rec)

            rec.message_notify(
                partner_ids=partners.ids,
                subject=subject,
                body=body,
            )

    # @api.model
    # def _cron_rr_ruleA_wait_pick(self):
    #     """
    #     Rule A:
    #     - state = 'wait_pick'
    #     - sau 1 ngày làm việc kể từ wait_pick_date
    #     - gửi GĐ Nhà sách của branch_id
    #     """
    #     def _recipients(rec):
    #         return rec._get_partners_by_job_and_branch("Giám đốc nhà sách", rec.branch_id)
    #
    #     def _subject(rec):
    #         return _("Đề nghị trả hàng %s cần xác nhận số lượng") % rec.name
    #
    #     def _body(rec):
    #         return _(
    #             "Đề nghị trả hàng <b>%s</b> đã ở trạng thái <b>Đợi nhặt hàng</b> "
    #             "từ ngày <b>%s</b> nhưng sau 1 ngày làm việc vẫn chưa được xác nhận."
    #         ) % (rec.name, rec.wait_pick_date or "")
    #
    #     self._rr_simple_state_sla(
    #         state="wait_pick",
    #         date_field="wait_pick_date",
    #         work_days=1,
    #         recipient_getter=_recipients,
    #         subject_builder=_subject,
    #         body_builder=_body,
    #     )

    @api.model
    def _cron_rr_ruleB_wait_pack(self):
        """
        Rule B:
        - state = 'wait_pack'
        - sau 1 ngày làm việc kể từ wait_pack_date
        - gửi GĐ Nhà sách của branch_id
        """
        def _recipients(rec):
            return rec._get_partners_by_job_and_branch("Giám đốc nhà sách", rec.branch_id)

        def _subject(rec):
            return _("Hiện đang có đề nghị trả hàng %s có phiếu đóng gói cần hoàn thành") % rec.name

        def _body(rec):
            return _("Hiện đang có đề nghị trả hàng %s có phiếu đóng gói cần hoàn thành") % rec.name

        self._rr_simple_state_sla(
            state="wait_pack",
            date_field="wait_pack_date",
            work_days=1,
            recipient_getter=_recipients,
            subject_builder=_subject,
            body_builder=_body,
        )

    @api.model
    def _cron_rr_rule12_wait_supplier_approve(self):
        """
        Rule 12A:
        - is_transit_dc = True
        - return_type = 'ship'
        - state = 'wait_pack'
        - quá 2 ngày làm việc kể từ wait_pack_date
        - chưa chuyển sang wait_supplier_approve
        - notify Giám đốc nhà sách
        """

        def _recipients(rec):
            partners = rec._get_partners_by_job("TN kho DC")
            partners |= rec._get_partners_by_job("Giám đốc khối cung ứng")
            return partners

        def _subject(rec):
            return _("Hiện đang có Đề nghị trả hàng %s cần ship đến NCC") % rec.name

        def _body(rec):
            return _("Hiện đang có Đề nghị trả hàng %s cần ship đến NCC") % rec.name

        recs = self.search([
            ("state", "=", "wait_pack"),
            ("is_transit_dc", "=", True),
            ("return_type", "=", "ship"),
            ("wait_pack_date", "!=", False),
        ])

        today = fields.Date.today()
        for rec in recs:
            # State chưa chuyển sang wait_supplier_approve
            if rec.state != "wait_pack":
                continue

            deadline = self._compute_deadline_work_days(rec.wait_pack_date, 2)
            if deadline and today >= deadline:
                partners = _recipients(rec)
                if partners:
                    rec.message_notify(
                        partner_ids=partners.ids,
                        subject=_subject(rec),
                        body=_body(rec),
                    )

    @api.model
    def _cron_rr_ruleE_wait_supplier_approve(self):
        """
        Rule E:
        - state = 'wait_supplier_approve'
        - sau 3 ngày làm việc kể từ wait_supplier_approve_date
        - gửi TN kho DC + GĐ khối cung ứng
        """
        def _recipients(rec):
            partners = rec._get_partners_by_job("TN kho DC")
            partners |= rec._get_partners_by_job("Giám đốc khối cung ứng")
            return partners

        def _subject(rec):
            return _("Hiện đang có Đề nghị trả hàng %scần NCC xác nhận số lượng") % rec.name

        def _body(rec):
            return _("Hiện đang có Đề nghị trả hàng %scần NCC xác nhận số lượng") % rec.name

        self._rr_simple_state_sla(
            state="wait_supplier_approve",
            date_field="wait_supplier_approve_date",
            work_days=3,
            recipient_getter=_recipients,
            subject_builder=_subject,
            body_builder=_body,
        )

    @api.model
    def _cron_rr_ruleF_wait_supplier_return(self):
        """
        Rule F:
        - state = 'wait_supplier_return'
        - sau 30 ngày (có thể đổi sang ngày làm việc nếu muốn) kể từ wait_supplier_return_date
        - gửi TN kho DC + GĐ khối cung ứng
        """
        def _recipients(rec):
            partners = rec._get_partners_by_job("TN kho DC")
            partners |= rec._get_partners_by_job("Giám đốc khối cung ứng")
            return partners

        def _subject(rec):
            return _("Hiện đang có Đề nghị trả hàng %s cần nhận hàng từ NCC") % rec.name

        def _body(rec):
            return _(
                _("Hiện đang có Đề nghị trả hàng %s cần nhận hàng từ NCC") % rec.name)

        # nếu anh muốn 30 NGÀY LÀM VIỆC: dùng work_days=30
        # nếu 30 ngày lịch: có thể tự tính ngoài helper. Ở đây em dùng work_days=30 cho nhất quán.
        self._rr_simple_state_sla(
            state="wait_supplier_return",
            date_field="wait_supplier_return_date",
            work_days=30,
            recipient_getter=_recipients,
            subject_builder=_subject,
            body_builder=_body,
        )

    @api.model
    def _cron_rr_rules_request_sla(self):
        self._cron_rr_rule1()
        self._cron_rr_rule4_5_6()
        # self._cron_rr_ruleA_wait_pick()
        self._cron_rr_ruleB_wait_pack()
        self._cron_rr_ruleE_wait_supplier_approve()
        self._cron_rr_rule12_wait_supplier_approve()
        self._cron_rr_ruleF_wait_supplier_return()

    @api.model
    def _cron_rr_rule4_5_6(self):
        """
        Cron xử lý:
        - Rule 4: is_transit_dc = False, return_type = NCC đến lấy -> gửi Người tạo
        - Rule 5: is_transit_dc = False, return_type = Chuyển tới NCC -> gửi GĐ Nhà sách (cùng cơ sở)
        - Rule 6: is_transit_dc = True,  return_type = NCC đến lấy -> gửi TN kho DC + GĐ khối cung ứng
        """
        today = fields.Date.today()
        STATE_WAIT_RETURN_NCC = "wait_return"
        RETURN_TYPE_NCC_PICKUP = "pickup"
        RETURN_TYPE_SHIP_TO_NCC = "ship"

        # chỉ xử lý những phiếu đang ở Đợi trả NCC và có ngày mốc
        candidates = self.search([
            ("state", "=", STATE_WAIT_RETURN_NCC),
            ("wait_ncc_date", "!=", False),
        ])

        to_rule4 = self.browse()
        to_rule5 = self.browse()
        to_rule6 = self.browse()

        for req in candidates:
            # deadline = 2 ngày làm việc kể từ wait_ncc_date
            deadline = self._compute_deadline_work_days(req.wait_ncc_date, 2, employee=None)
            if not (deadline and today >= deadline):
                continue

            if not req.is_transit_dc and req.return_type == RETURN_TYPE_NCC_PICKUP:
                to_rule4 |= req
            elif not req.is_transit_dc and req.return_type == RETURN_TYPE_SHIP_TO_NCC:
                to_rule5 |= req
            elif req.is_transit_dc and req.return_type == RETURN_TYPE_NCC_PICKUP:
                to_rule6 |= req

        if to_rule4:
            to_rule4._rr_rule4_log_and_notify()
        if to_rule5:
            to_rule5._rr_rule5_log_and_notify()
        if to_rule6:
            to_rule6._rr_rule6_log_and_notify()

    def action_waiting_export_invoice(self):
        self.ensure_one()
        if self.state != 'wait_supplier_approve':
            raise UserError('Bạn chỉ có thể chuyên sang Đợi xuất hóa đơn từ trạng thái Đợi NCC xác nhận')
        self.state = 'wait_invoice'

    def action_done(self):
        for rec in self:
            rec.write({
                'state': 'done'
            })

    def action_adjust(self):
        for rec in self:
            rec.write({
                'state': 'draft'
            })

    def copy(self):
        res = super().copy()
        res.write({
            'requester_id': self.env.uid,
            'request_date': fields.Date.today(),
        })
        return res

    def update_stock_system(self):
        for rec in self:
            if not rec.stock_warehouse_id.id_augges:
                raise UserError('Kho bạn chọn chưa được cấu hình ID Augges')
            stock_cache = {}

            for line in rec.line_ids:
                if not line.product_id or not line.product_id.augges_id:
                    continue
                id_kho = rec.stock_warehouse_id.id_augges
                id_hang = line.product_id.augges_id

                key = (id_kho, id_hang)
                if key not in stock_cache:
                    try:
                        stock_cache[key] = line.get_augges_quantity(id_kho, id_hang)
                    except Exception:
                        stock_cache[key] = 0.0

                line.stock_system = stock_cache[key]
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
