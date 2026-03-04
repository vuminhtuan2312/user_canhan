from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
from datetime import datetime, timedelta
import pytz
import uuid
from odoo.addons.ttb_tools.models.ttb_tcvn3 import unicode_to_tcvn3

_logger = logging.getLogger(__name__)

dict_consume_type = {
    'nvl': [57,'TDX'],
    'tool': [114,'XCCDC2'],
    'repair': [115,'XCT2'],
    'ho_vpp': [87,'XHT'],
    'marketing': [96,'XMKT'],
    'internal': [76,'XNB'],
    'charity': [85,'XNG'],
    'benefit': [91,'XPL'],
    'benefit_ho': [111,'XPLHO'],
    'sale_other': [99,'XPVBH-KHAC'],
    'sale_cost': [86,'XPVBH-VTTH'],
    'gift': [93,'XTANG'],
    'decorate': [84,'XTT'],
}

class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    ttb_return_request_id = fields.Many2one('ttb.return.request', string='Yêu cầu trả lại', copy=False)
    pickup_status = fields.Selection(
        [('picking', 'Nhặt hàng'), ('waiting_packing', 'Điều chuyển nội bộ'), ('packing', 'Đóng gói'),
         ('dc', 'Vận chuyển DC'), ('dc_received', 'Kho DC nhận hàng'), ('back_to_supplier', 'Trả NCC')],
        string='Trạng thái nhặt',
        help='Trạng thái waiting_packing là quá trình điều chuyển nội bộ về kho văn phòng trước khi đóng gói', )
    quantity_total = fields.Float(string='Tổng số', compute='_compute_quantity_total')

    @api.depends('move_ids', 'move_ids.quantity')
    def _compute_quantity_total(self):
        for rec in self:
            rec.quantity_total = sum(rec.move_ids.mapped('quantity'))

    def create_stock_picking_ticket(self, location_id, location_dest_id, picking_type_id, pickup_status):
        self.ensure_one()
        move_ids_val = []
        for move in self.move_ids:
            move_ids_val.append((0, 0, {
                'name': move.name,
                'product_id': move.product_id.id,
                'product_uom': move.product_uom.id,
                'product_uom_qty': move.ttb_return_request_line_id.qty_picked,
                'picking_type_id': picking_type_id.id,
                'quantity': move.ttb_return_request_line_id.qty_picked,  # Giữ nguyên số lượng đã nhặt
                'ttb_return_request_line_id': move.ttb_return_request_line_id.id,
                'origin': move.origin,
                'location_id': location_id if location_id else picking_type_id.default_location_src_id.id,
                'location_dest_id': location_dest_id if location_dest_id else picking_type_id.default_location_dest_id.id,
            }))
        picking = self.env['stock.picking'].create({
            'move_ids': move_ids_val,
            'partner_id': self.partner_id.id,
            'picking_type_id': picking_type_id.id,
            'location_id': location_id if location_id else picking_type_id.default_location_src_id.id,
            'location_dest_id': location_dest_id if location_dest_id else picking_type_id.default_location_dest_id.id,
            'ttb_return_request_id': self.ttb_return_request_id.id,
            'origin': self.ttb_return_request_id.name,
            'pickup_status': pickup_status,
            'user_id': self.user_id.id,
        })
        picking.action_confirm()
        return picking

    def action_confirm_picking_ticket(self):
        for move in self.move_ids:
            if move.ttb_return_request_line_id:
                move.ttb_return_request_line_id.qty_picked = move.quantity - move.reject_qty_total
                move.ttb_return_request_line_id.qty_fail = move.reject_qty_total
        if not self.ttb_return_request_id.picking_ids.filtered(lambda p: p.pickup_status == 'picking' and p.state != 'done'):
            picking_ids = self.ttb_return_request_id.picking_ids.filtered(lambda p: p.pickup_status == 'picking').mapped('id')
            line_ids = self.env['stock.move'].search([('picking_id', 'in', picking_ids)])
            sum_qty_pass = sum(line_ids.mapped('achieved_qty'))
            if sum_qty_pass != 0:
                self.ttb_return_request_id.state = 'wait_move'
            else:
                reason = self.ttb_return_request_id.reason
                reason += '\nLưu ý: Không nhặt được hàng trả lại.'
                self.ttb_return_request_id.write({
                    'state': 'done',
                    'reason': reason
                })

    def update_qty_return_request(self):
        for move in self.move_ids:
            if move.ttb_return_request_line_id:
                move.ttb_return_request_line_id.qty_vp_received = move.achieved_qty
                move.ttb_return_request_line_id.qty_fail += move.reject_qty_total
        packing_tickets = self.ttb_return_request_id.picking_ids.filtered(lambda p: p.pickup_status == 'packing' and p.state != 'done')
        if len(packing_tickets) == 0:
            if not self.ttb_return_request_id.is_transit_dc:
                self.ttb_return_request_id.state = 'wait_return'
            else:
                self.ttb_return_request_id.state = 'wait_transfer'

    def action_confirm_waiting_packing_ticket(self):
        picking_tickets = self.ttb_return_request_id.picking_ids.filtered(lambda p: p.pickup_status == 'picking' and p.state == 'done')
        waiting_packing_tickets = self.ttb_return_request_id.picking_ids.filtered(lambda p: p.pickup_status == 'waiting_packing' and p.state == 'done')
        if len(picking_tickets) == len(waiting_packing_tickets):
            self.ttb_return_request_id.state = 'wait_pack'
            picking_type_id = self.ttb_return_request_id.stock_warehouse_id.pack_type_id
            for stock_picking in waiting_packing_tickets:
                stock_picking.create_stock_picking_ticket(False, False, picking_type_id, 'packing')

    def _get_user_id(self, conn, user_id):
        odoo_login = self.env['res.users'].browse(user_id).login
        user_data = self.env['ttb.augges'].get_records(
            table='DmUser',
            domain=f"LogName = '{odoo_login}'",
            field_list=['ID'],
            get_dict=True,
            pair_conn=conn
        )
        if not user_data:
            raise UserError(f"Không tìm thấy người dùng Augges với LogName = {odoo_login}")
        return user_data[0]['id']

    def confirm_augges_return_ticket(self, table, state):
        self.ensure_one()
        params = self.env['ir.config_parameter'].sudo()
        if not params.get_param('ttb_return_request.confirm_augges_ticket'):
            params.set_param('ttb_return_request.confirm_augges_ticket', '0')
        if not params.get_param('ttb_return_request.confirm_augges_ticket') == '1':
            return

        conn = self.env['ttb.tools'].get_mssql_connection_send()

        data_update ={
            'UserIDXN': 2698,
            'NgayXn': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        id_augges = self.ttb_return_request_id.picking_ids.filtered(lambda p: p.pickup_status == state)[:1].id_augges
        if not id_augges:
            raise UserError("Phiếu trả hàng Augges chưa được tạo.")
        self.env['ttb.augges'].update_record(table, data_update, id_augges)

    def button_validate(self):
        self = self.with_context(no_check_invoice=True, create_augges_picking_ticket=True)
        res = super(StockPicking, self).button_validate()
        if self.pickup_status == 'picking':
            self.action_confirm_picking_ticket()
        elif self.pickup_status == 'waiting_packing':
            self.action_confirm_waiting_packing_ticket()
            self.confirm_augges_return_ticket('SlDcM', 'waiting_packing')
        elif self.pickup_status == 'packing':
            self.update_qty_return_request()
        elif self.pickup_status == 'dc':
            self.ttb_return_request_id.state = 'wait_dc_receive'
        elif self.pickup_status == 'dc_received':
            self.ttb_return_request_id.state = 'wait_return'
            self.confirm_augges_return_ticket('SlDcM', 'dc')
        elif self.pickup_status == 'back_to_supplier':
            self.ttb_return_request_id.state = 'wait_supplier_approve'
            self.create_auggest_back_to_supplier_ticket()
        else:
            check = 'nx'
            id_nx = False
            diengiai = False

            if self.consume_request_id and self.picking_type_code=='outgoing':
                id_nx = dict_consume_type[self.consume_request_id.consume_type][0]
                diengiai = f'Xuat dung - {self.consume_request_id.name} - {self.name}'
            elif self.cancel_request_id and self.picking_type_code=='outgoing':
                id_nx = 79
                diengiai = f'Xuat huy - {self.cancel_request_id.name} - {self.name}'
            elif self.cancel_request_id and self.picking_type_code=='internal':
                id_nx = 14
                diengiai = f'DCXH - {self.cancel_request_id.name} - {self.name}'
                check = 'dc'
            elif self.transfer_request_id and self.picking_type_code=='internal':
                id_nx = 14
                diengiai = f'DCCS - {self.transfer_request_id.name} - {self.name}'
                check = 'dc'
            elif self.inventory_origin_id and self.picking_type_code=='internal':
                id_nx = 14
                diengiai = f'DCBL  - {self.name}'
                check = 'dc'
            elif self.barcode_request_id and self.picking_type_code == 'outgoing':
                id_nx = 97
                diengiai = f'XCM - {self.barcode_request_id.name} - {self.name}'
            elif self.barcode_request_id and self.picking_type_code == 'incoming':
                id_nx = 100
                diengiai = f'XCM - {self.barcode_request_id.name} - {self.name}'

            # Chỉ gọi hàm nếu các biến đã được khởi tạo
            if id_nx and diengiai:
                if check == 'nx':
                    self.create_auggest_back_to_supplier_ticket(False, False, id_nx, diengiai, 'out')
                else:
                    self.create_auggest_return_ticket(False, False, id_nx, False, diengiai)

        return res

    def action_view_picking_ticket(self):
        self.ensure_one()
        pickings = self.env['stock.picking'].search([
            ('ttb_return_request_id', '=', self.ttb_return_request_id.id),
            ('pickup_status', '=', 'packing')
        ])
        if not pickings:
            raise UserError("Không tìm thấy phiếu đóng gói nào liên quan đến yêu cầu trả lại này.")
        return {
            'name': 'Phiếu đóng gói',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': pickings.id,
        }

    # Mốc thời gian cho SLA điều chuyển nội bộ
    rr_internal_start_date = fields.Date(
        string="Ngày bắt đầu phiếu điều chuyển nội bộ",
        copy=False,
        help="Dùng cho phiếu internal ở draft/waiting quá lâu."
    )
    rr_internal_assigned_date = fields.Date(
        string="Ngày phiếu internal sẵn sàng (assigned)",
        copy=False,
        help="Dùng cho phiếu internal ở assigned chờ DC nhận."
    )

    def write(self, vals):
        prev_states = {p.id: p.state for p in self}
        res = super(StockPicking, self).write(vals)

        if "state" in vals:
            today = fields.Date.context_today(self)
            for p in self:
                old_state = prev_states.get(p.id)
                new_state = p.state
                if old_state == new_state:
                    continue

                # Chỉ quan tâm phiếu internal có link tới đề nghị trả hàng
                if not p.ttb_return_request_id or p.picking_type_code != "internal":
                    continue

                if new_state in ("draft", "waiting") and not p.rr_internal_start_date:
                    p.rr_internal_start_date = today

                if new_state == "assigned" and not p.rr_internal_assigned_date:
                    p.rr_internal_assigned_date = today

        return res

    @api.depends('move_ids_without_package', 'move_ids_without_package.ttb_price_unit',
                 'move_ids_without_package.quantity', 'ttb_return_request_id.total_amount')
    def _compute_ttb_amount_total(self):
        for rec in self:
            if rec.pickup_status != 'back_to_supplier':
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
            else:
                rec.ttb_amount_tax = 0
                rec.ttb_amount_total = rec.ttb_return_request_id.total_amount

    def _rr_internal_deadline(self, start_date, work_days):
        RRModel = self.env["ttb.return.request"]
        return RRModel._compute_deadline_work_days(
            start_date,
            work_days,
            employee=None,
        )

    def _rr_compute_deadline(self, start_date, work_days):
        """Dùng _compute_deadline_work_days của ttb.return.request cho thống nhất."""
        RR = self.env["ttb.return.request"]
        return RR._compute_deadline_work_days(start_date, work_days, employee=None)

    @api.model
    def _cron_rr_ruleA_return_pick_confirm_qty(self):
        """

        - picking_type_id.rr_role = 'return_pick'
        - state hiện tại = 'assigned' (Sẵn sàng)
        - rr_internal_assigned_date đã có
        - Sau 1 ngày làm việc kể từ rr_internal_assigned_date mà vẫn chưa 'done'
          → gửi thông báo.
        """
        today = fields.Date.today()

        pickings = self.search([
            ("state", "=", "assigned"),
            ("rr_internal_assigned_date", "!=", False),
        ])

        for picking in pickings:
            deadline = picking._rr_compute_deadline(
                picking.rr_internal_assigned_date,
                1,
            )
            if not (deadline and today >= deadline):
                continue

            # Lấy GĐ nhà sách theo Đề nghị trả hàng

            req = picking.ttb_return_request_id
            partners = req._get_partners_by_job_and_branch("Giám đốc nhà sách", req.branch_id)
            if not partners:
                continue

            subject = _("Hiện đang có phiếu nhặt hàng %s cần xác nhận số lượng") % picking.name
            body = _("Hiện đang có phiếu nhặt hàng %s cần xác nhận số lượng") % picking.name


            req.message_notify(
                partner_ids=partners.ids,
                subject=subject,
                body=body,
            )

    @api.model
    def _cron_rr_ruleC_D_internal(self):
        """
        Rule C:
          - Phiếu internal (picking_type_code = 'internal')
          - state in ('draft', 'waiting')
          - rr_internal_start_date != False
          - Đề nghị: is_transit_dc = False, return_type = 'ship' (Chuyển tới NCC)
          - Sau 2 ngày làm việc -> gửi GĐ Nhà sách (branch của ĐNT)

        Rule D:
          - Phiếu internal (picking_type_code = 'internal')
          - state = 'assigned'
          - rr_internal_assigned_date != False
          - Đề nghị: is_transit_dc = True
          - Sau 8/10/14 ngày làm việc tùy vùng -> gửi TN kho DC + GĐ khối cung ứng
        """
        today = fields.Date.today()
        RR = self.env["ttb.return.request"]

        # ---------- RULE C ----------
        pickings_c = self.search([
            ("picking_type_code", "=", "internal"),
            ("state", "in", ("draft", "waiting")),
            ("rr_internal_start_date", "!=", False),
            ("ttb_return_request_id", "!=", False),
        ])

        for p in pickings_c:
            req = p.ttb_return_request_id
            if not req or req.is_transit_dc or req.return_type != "ship":
                continue

            deadline = p._rr_internal_deadline(p.rr_internal_start_date, 2)
            if not (deadline and today >= deadline):
                continue

            partners = req._get_partners_by_job_and_branch("Giám đốc nhà sách", req.branch_id)
            if not partners:
                continue

            subject = _("Hiện đang có Đề nghị trả hàng %s cần điều chuyển đến DC") % req.name
            body = _("Hiện đang có Đề nghị trả hàng %s cần điều chuyển đến DC") % req.name

            req.message_notify(
                partner_ids=partners.ids,
                subject=subject,
                body=body,
            )

        # ---------- RULE D ----------
        pickings_d = self.search([
            ("picking_type_code", "=", "internal"),
            ("state", "=", "assigned"),
            ("rr_internal_assigned_date", "!=", False),
            ("ttb_return_request_id", "!=", False),
        ])

        for p in pickings_d:
            req = p.ttb_return_request_id
            if not req or not req.is_transit_dc:
                continue

            # SLA theo vùng – anh có thể thay bằng map thực tế
            branch = req.branch_id
            if getattr(branch, "ttb_branch_region", False) == "HN":
                sla_days = 1
            elif getattr(branch, "ttb_branch_region", False) == "MB":
                sla_days = 3
            else:
                sla_days = 7

            deadline = p._rr_internal_deadline(p.rr_internal_assigned_date, sla_days)
            if not (deadline and today >= deadline):
                continue

            partners = RR._get_partners_by_job("TN kho DC") | RR._get_partners_by_job("Giám đốc khối cung ứng")
            if not partners:
                continue

            subject = _("Hiện đang có phiếu điều chuyển nội bộ %s cần xác nhận") % p.name
            body = _("Hiện đang có phiếu điều chuyển nội bộ %s cần xác nhận") % p.name

            req.message_notify(
                partner_ids=partners.ids,
                subject=subject,
                body=body,
            )


    def _rr_rule2_get_employee_for_user(self):
        """
        Trả về tất cả hr.employee thỏa các điều kiện:
        - Gắn với picking.user_id
        - job_id.name ilike 'Quản lí nhà sách'
        - Có ttb_branch_ids chứa branch_id của Đề nghị trả hàng
        - Có ttb_categ_ids giao với ttb_categ_ids của NCC trong Đề nghị trả hàng
        """
        self.ensure_one()
        Emp = self.env["hr.employee"]

        if not self.ttb_return_request_id:
            return Emp  # empty recordset

        req = self.ttb_return_request_id
        partner = getattr(req, "partner_id", False)

        domain = [
            ("active", "=", True),
            ("job_id.name", "ilike", "Quản lý Nhà sách"),
        ]

        # Cơ sở: employee.ttb_branch_ids phải chứa branch_id của đề nghị trả hàng
        if req.branch_id:
            domain.append(("ttb_branch_ids", "in", req.branch_id.id))

        # Quầy: employee.ttb_categ_ids phải giao với ttb_categ_ids của NCC
        if partner and partner.ttb_categ_ids:
            domain.append(("ttb_categ_ids", "in", partner.ttb_categ_ids.ids))

        employees = Emp.sudo().search(domain)
        return employees

    def _rr_rule2_render_body(self):
        """Nội dung Rule 2 – gửi cho user_id khi được phân công phiếu nhặt."""
        self.ensure_one()
        return _(
            "Hiện đang có phiếu nhăt hàng %s cần phân công"
        ) % {
            "picking": self.name,
        }

    def _rr_rule3_render_body(self):
        """
        Nội dung thông báo Rule 3:
        - Sau 2 ngày làm việc kể từ khi phiếu nhặt được tạo
        - Vẫn đang ở trạng thái Nháp
        """
        self.ensure_one()
        return _(
            "Hiện đang có phiếu nhặt hàng %s cần thực hiện"
        ) % {
            "picking": self.name,
        }

    def _rr_rule2_log_and_notify(self):
        """
        Gửi message_notify cho user_id (nếu đủ điều kiện)
        và log lại với rule_code = 'RR02'.
        """
        # Log = self.env["ttb.return.notification.log"]
        # RULE_CODE = "RR02"

        for picking in self:
            req = picking.ttb_return_request_id
            if not req:
                continue

            # Đã gửi lần nào chưa?
            # exists = Log.search_count([
            #     ("model", "=", picking._name),
            #     ("res_id", "=", picking.id),
            #     ("rule_code", "=", RULE_CODE),
            # ])
            # if exists:
            #     continue

            # Tìm employee tương ứng và check quyền
            employees = picking._rr_rule2_get_employee_for_user()
            if not employees:
                continue

            partner_ids = employees.mapped("user_id.partner_id.id")
            partner_ids = [pid for pid in partner_ids if pid]
            if not partner_ids:
                continue

            # partner = picking.user_id.partner_id
            # if not partner:
            #     continue

            subject = _("Phiếu nhặt hàng %s được phân công cho bạn") % picking.name
            body = picking._rr_rule2_render_body()

            picking.message_notify(
                partner_ids=partner_ids,
                subject=subject,
                body=body,
            )

            # Log.create({
            #     "model": picking._name,
            #     "res_id": picking.id,
            #     "rule_code": RULE_CODE,
            #     "state_at_send": picking.state,
            # })

    def _rr_rule3_log_and_notify(self):
        """
        Gửi message_notify cho user_id nếu user_id thỏa điều kiện,
        và log vào ttb.return.notification.log với rule_code = 'RR03'.
        """
        # Log = self.env["ttb.return.notification.log"]
        # RULE_CODE = "RR03"

        for picking in self:
            req = picking.ttb_return_request_id
            if not req or not picking.user_id:
                continue

            # Tránh gửi trùng
            # exists = Log.search_count([
            #     ("model", "=", picking._name),
            #     ("res_id", "=", picking.id),
            #     ("rule_code", "=", RULE_CODE),
            # ])
            # if exists:
            #     continue

            employees = picking._rr_rule2_get_employee_for_user()
            if not employees:
                # user_id không phải Quản lí nhà sách đúng cơ sở/quầy -> bỏ qua
                continue

            partner = picking.user_id.partner_id
            if not partner:
                continue

            subject = _("Phiếu nhặt hàng %s cần được xử lý") % picking.name
            body = picking._rr_rule3_render_body()

            picking.message_notify(
                partner_ids=[partner.id],
                subject=subject,
                body=body,
            )

            # Log.create({
            #     "model": picking._name,
            #     "res_id": picking.id,
            #     "rule_code": RULE_CODE,
            #     "state_at_send": picking.state,
            # })

    @api.model
    def _cron_rr_rule3(self):
        """
        Rule 3 – Sau 2 ngày LÀM VIỆC kể từ khi Phiếu nhặt hàng được tạo,
        nếu state vẫn là 'draft' thì gửi notify cho user_id
        (với điều kiện user_id là Quản lí nhà sách đúng cơ sở & quầy).
        """
        today = fields.Date.today()

        # Chọn candidate: phiếu nhặt thuộc đề nghị trả hàng, đang Nháp, có create_date
        candidates = self.search([
            ("ttb_return_request_id", "!=", False),
            ("state", "=", "draft"),
            ("create_date", "!=", False),
        ])

        to_notify = self.browse()
        RRModel = self.env["ttb.return.request"]

        for picking in candidates:
            # Tìm employee tương ứng user_id, đúng job + branch + quầy
            employees = picking._rr_rule2_get_employee_for_user()
            employee_for_calendar = employees[:1] if employees else None
            if not employee_for_calendar:
                # Nếu user_id không đúng tiêu chí thì không gửi rule này
                continue

            base_dt = picking.create_date  # datetime
            deadline = RRModel._compute_deadline_work_days(
                base_dt,
                2,
                employee=employee_for_calendar,
            )
            if deadline and today >= deadline:
                to_notify |= picking

        if to_notify:
            to_notify._rr_rule3_log_and_notify()

    @api.model
    def create(self, vals):
        pickings = super(StockPicking, self).create(vals)

        for picking in pickings:
            if picking.picking_type_code and picking.picking_type_code == 'outgoing' and not picking.partner_id:
                partner_id = self.env['res.partner'].search([('property_stock_customer', '=', picking.location_id.id)], limit=1)
                if partner_id:
                    picking.partner_id = partner_id
                else:
                    raise UserError(f"Không tìm thấy đối tác có địa điểm khách hàng là {picking.location_id.name}. Vui lòng kiểm tra lại.")

        # chỉ áp dụng cho phiếu nhặt thuộc đề nghị trả hàng
        pickings.filtered(lambda p: p.ttb_return_request_id)._rr_rule2_log_and_notify()
        return pickings

    def create_auggest_return_ticket(self, pair_conn=False, re_create=False, id_nx=None, type_ticket=False, diengiai=None):
        self.ensure_one()
        params = self.env['ir.config_parameter'].sudo()
        if not params.get_param('ttb_return_request.create_augges_ticket'):
            params.set_param('ttb_return_request.create_augges_ticket', '1')
        if not params.get_param('ttb_return_request.create_augges_ticket') == '1':
            return

        if not self._context.get('create_augges_picking_ticket', False): return
        if self.id_augges and not re_create: return

        augges_ref = self.partner_id.ref
        if not augges_ref:
            raise UserError("Nhà cung cấp chưa có mã tham chiếu.")

        domain = f"Ma_Dt = '{augges_ref}'"
        partner_augges = self.env['ttb.augges'].get_partner(domain)
        if not partner_augges:
            message = 'Không tìm thấy nhà cung cấp ở Augges'
            self.write({'pending_sent_augges': True,
                        'pending_sent_augges_message': f"{self.pending_sent_augges_message or ''}\n{message}"})
            return
        augges_id = partner_augges[0]['id']

        owns_conn = False
        conn, cursor = None, None
        if pair_conn:
            conn = pair_conn
        else:
            conn = self.env['ttb.tools'].get_mssql_connection_send()
            owns_conn = True
        cursor = conn.cursor()

        for rec_stock in self:
            _logger.info('Tạo phiếu nhập Augges cho phiếu nhập odoo id: %s, name: %s', rec_stock.id, rec_stock.name)
            rec = rec_stock.ttb_return_request_id

            day = datetime.now().astimezone(pytz.UTC).replace(tzinfo=None)
            sql_day = day.strftime("%Y-%m-%d 00:00:00")
            sngay = day.strftime("%y%m%d")
            if diengiai:
                dien_giai = diengiai
            elif type_ticket == 'dcnb':
                dien_giai = f'HTL - Dieu chuyen VP"{rec_stock.origin} - {rec_stock.name}'
            elif type_ticket == 'dc':
                dien_giai = f'HTL - Dieu chuyen DC" {rec_stock.origin} - {rec_stock.name}'
            else:
                dien_giai = f'Phiếu Augges cho đề nghị hàng trả lại {rec.name} - {rec_stock.name}'

            if re_create and rec_stock.sp_augges:
                value_sp = rec_stock.sp_augges
            else:
                cursor.execute(f"""select Top 1 sp from SlDcM order by sp desc""")
                result_sp = cursor.fetchall()
                value_sp = int(result_sp[0][0]) + 1 if result_sp else 1

            ID_KhoX = rec_stock.location_id.warehouse_id.id_augges
            if rec_stock.pickup_status == 'waiting_packing' or not rec_stock.pickup_status:
                ID_KhoN = rec_stock.location_dest_id.warehouse_id.id_augges
            else:
                ID_KhoN = rec_stock.ttb_return_request_id.central_location_id.warehouse_id.id_augges

            _logger.info(f'location_id: {rec_stock.location_id.id}, location_dest_id: {rec_stock.location_dest_id.id}')

            if not ID_KhoX:
                raise UserError("Kho xuất chưa có Id Augges.")
            if not ID_KhoN:
                raise UserError("Kho nhập chưa có Id Augges.")

            quantity_total = sum(rec_stock.move_ids.mapped('quantity'))
            amount_total = 0
            dict_prd_amout = {}
            for line in rec_stock.move_ids:
                product_id = line.product_id.id
                if product_id not in dict_prd_amout:
                    po_line = self.env['purchase.order.line'].search([
                        ('product_id', '=', product_id),
                        ('order_id.state', 'in', ['purchase', 'done']),
                    ], order='create_date desc', limit=1)
                    if po_line:
                        dict_prd_amout[product_id] = po_line.price_unit
                        amount_total += po_line.price_unit * line.quantity
                    else:
                        dict_prd_amout[product_id] = line.product_id.product_tmpl_id.last_price
            insert_date = datetime.utcnow() + timedelta(hours=7)

            data = {
                'ID_Dv': 0,
                'IP_ID': 0,
                'Ngay': sql_day,
                'Sngay': sngay,
                'Ngay_Ct': '',
                'ID_Nx': id_nx,
                'Sp': value_sp,
                'ID_Tt': 1,
                'Ty_Gia': 0,
                'ID_Dt': augges_id,
                'ID_KhoX': ID_KhoX,
                'ID_KhoN': ID_KhoN,
                'Cong_SlQd': quantity_total,
                'Cong_Sl': quantity_total,
                'Tong_Tien': amount_total,
                'Dien_Giai': dien_giai,
                'InsertDate': insert_date,
                'LastEdit': insert_date,
                'Printed': 0,
                'UserID': 2698,
                'LoaiCt': ''
            }
            _logger.warning(f"Job hàng trả lại 1 lần: Dữ liệu chuẩn bị chèn vào SlDcM: {data}")
            sldcm_id = self.env['ttb.augges'].insert_record('SlDcM', data, conn)
            cursor.execute(f"""select top 1 No_Tk, Co_Tk from DmNx where id = {id_nx}""")
            result_tk = cursor.fetchall()
            if result_tk:
                No_tk = result_tk[0][0] if result_tk[0][0] else '1561'
                Co_tk = result_tk[0][1] if result_tk[0][1] else '1561'

            count = 1
            for line in rec_stock.move_ids:
                if line.quantity == 0: continue
                price_unit = dict_prd_amout[line.product_id.id] if line.product_id.id in dict_prd_amout else 0
                price = price_unit * line.quantity

                data = {
                    'ID': sldcm_id,
                    'Stt': count,
                    'Sngay': sngay,
                    'ID_KhoX': ID_KhoX,
                    'ID_KhoN': ID_KhoN,
                    'ID_Hang': line.product_id.product_tmpl_id.augges_id,
                    'Sl_Qd': line.quantity,
                    'So_Luong': line.quantity,
                    'Ty_Gia': 0,
                    'Gia_Qd': price_unit,
                    'Don_Gia': price_unit,
                    'T_Tien': price,
                    'Tien_Cp': 0,
                    'Tyle_Ck': 1,
                    'Tien_Ck': price * 0.01,
                    'Don_Gia1': price_unit,
                    'T_Tien1': price,
                    'Don_Gia2': price_unit,
                    'T_Tien2': price,
                    'No_Tk': No_tk,
                    'Co_Tk': Co_tk,
                    'Md': '',
                    'hs_qd': '',
                }
                _logger.info(f"Job hàng trả lại 1 lần: Dữ liệu chuẩn bị chèn vào SlDcM: {data}")
                # Gọi hàm insert, không cần lấy ID vì đã có ID + Stt
                self.env['ttb.augges'].insert_record("SlDcD", data, conn, False)
                line.write({'stt_augges': count})
                count += 1

            rec_stock.write({
                'id_augges': sldcm_id,
                'is_sent_augges': True,
                'sp_augges': value_sp,
            })

        if owns_conn:
            conn.commit()
            cursor.close()
            conn.close()

    def create_auggest_back_to_supplier_ticket(self, pair_conn=False, re_create=False, id_nx=None, diengiai=None, type_ticket=None):
        """
        Có hiện tượng phiếu nhập kho ở Augges bị giá trị 0 ở So_Luong, Thanh_Tien
        Dự đoán nguyên nhân do 1 dòng bất kỳ có So_Luong là 0 thì Augges reset hết về 0
        """
        self.ensure_one()
        AccountTax = self.env['account.tax']
        params = self.env['ir.config_parameter'].sudo()
        if not params.get_param('ttb_return_request.create_augges_ticket'):
            params.set_param('ttb_return_request.create_augges_ticket', '1')
        if not params.get_param('ttb_return_request.create_augges_ticket') == '1':
            return

        if self.state != 'done':
            raise UserError('Phiếu chưa hoàn thành')
        if self.id_augges and not re_create: return

        for picking in self:
            augges_ref = picking.partner_id.ref
            is_outgoing = picking.picking_type_id.code == 'outgoing'
            is_scrap_or_consume = bool(picking.cancel_request_id or picking.consume_request_id)

            if not picking.partner_id or not augges_ref:
                if is_outgoing and is_scrap_or_consume:
                    _logger.info("Skipping Augges Reference check for Scrap/Consume Picking: %s", picking.name)
                    continue
                raise UserError("Nhà cung cấp không có thông tin Mã tham chiếu.")

        domain = f"Ma_Dt = '{augges_ref}'"
        partner_augges = self.env['ttb.augges'].get_partner(domain)
        if not partner_augges:
            message = 'Không tìm thấy nhà cung cấp ở Augges'
            self.write({'pending_sent_augges': True,
                        'pending_sent_augges_message': f"{self.pending_sent_augges_message or ''}\n{message}"})
            return
        augges_id = partner_augges[0]['id']

        owns_conn = False
        conn, cursor = None, None
        if pair_conn:
            conn = pair_conn
        else:
            conn = self.env['ttb.tools'].get_mssql_connection_send()
            owns_conn = True
        cursor = conn.cursor()

        for rec_stock in self:
            _logger.info('Tạo phiếu nhập Augges cho phiếu nhập odoo id: %s, name: %s', rec_stock.id, rec_stock.name)
            invoice_date = rec_stock.date_done
            if invoice_date:
                day = invoice_date
                invoice_date = invoice_date.strftime("%Y-%m-%d")
            else:
                day = (rec_stock.date_done or datetime.now()).astimezone(pytz.UTC).replace(tzinfo=None)
                invoice_date = ''
            sql_day = day.strftime("%Y-%m-%d 00:00:00")
            sngay = day.strftime("%y%m%d")
            rec_currency_id = rec_stock.currency_id or rec_stock.company_id.currency_id
            currency_id = rec_currency_id.id_augges or 1

            qty_received = sum(rec_stock.move_ids_without_package.mapped('quantity'))
            dien_giai = diengiai or f'HTL - Xuat tra NCC "{rec_stock.origin}" - {rec_stock.name}'
            if re_create and rec_stock.sp_augges:
                value_sp = rec_stock.sp_augges
            else:
                cursor.execute(f"""select Top 1 sp from SlNxM order by sp desc""")
                result_sp = cursor.fetchall()
                value_sp = int(result_sp[0][0]) + 1 if result_sp else 1
            sp_has_tax = rec_stock.move_ids_without_package.filtered(lambda x: x.ttb_taxes_id)[:1]
            if not sp_has_tax:
                taxes_id_all = None
            else:
                taxe_id = sp_has_tax.ttb_taxes_id[:1]
                if taxe_id.id_augges:
                    taxes_id_all = taxe_id.id_augges
                else:
                    taxes_id_all = None
                    _logger.warn('Không tìm thấy thuế Augges cho thuế Odoo có id: %s', taxe_id.id)

            #vòng for tính tổng tiền và thuế ( xác nhận chấp nhận for 2 lần để hoàn thành task sớm)
            tax_total = 0
            ttb_amount_total = 0

            for line in rec_stock.move_ids_without_package:
                if line.quantity == 0: continue
                ttb_amount_total += line.ttb_return_request_line_id.confirm_vendor_price * line.quantity if line.ttb_return_request_line_id else 0

                tax_total += line.price_tax

            ttb_amount_total = ttb_amount_total + tax_total

            if not rec_stock.location_id.warehouse_id.id_augges:
                raise UserError(f"Địa điểm {rec_stock.location_id.name} chưa có Id Augges.")
            if not type_ticket:
                id_kho = rec_stock.location_id.warehouse_id.id_augges
            elif type_ticket == 'in':
                id_kho = rec_stock.location_dest_id.warehouse_id.id_augges
            elif type_ticket == 'out':
                id_kho = rec_stock.location_id.warehouse_id.id_augges
            insert_date = datetime.utcnow() + timedelta(hours=7)
            user_id = self._get_user_id(pair_conn, self.user_id.id)

            data = {
                "ID_LrTd": 0,
                "ID_Dv": 0,
                "Ngay": sql_day,
                "Sngay": sngay,
                "Ngay_Ct": invoice_date,
                "Mau_so": rec_stock.ttb_vendor_invoice_code or "",
                "Ky_Hieu": rec_stock.ttb_vendor_invoice_code or "",
                "So_Ct": rec_stock.ttb_vendor_invoice_no or "",
                "NgayKK": '',
                "ID_Nx": id_nx or 62,
                "ID_Tt": currency_id,
                "ID_Dt": augges_id,
                "ID_Kho": id_kho,
                "InsertDate": insert_date,
                "nSo_Ct": 0,
                "So_Bk": "",
                "SttSp": 0,
                "Sp": value_sp,
                "SpTc": 0,
                "Ty_Gia": 0,
                "IP_ID": 0,
                "Tien_hang": ttb_amount_total - tax_total,
                "Tong_Tien": ttb_amount_total,
                "Tien_Gtgt": tax_total,
                "Cong_SlQd": qty_received,
                "Cong_Sl": qty_received,
                "LastEdit": insert_date,
                "IsEHD": 0,
                "Tong_Nt": 0,
                "Vs": '250103',
                "Tien_Cp": 0,
                "Dien_Giai": dien_giai,
                "ID_Uni": str(uuid.uuid4()),
                "LoaiCt": '',
                "UserID": user_id,
                "No_Vat": '1331',
                "Co_Vat": '331',
                "ID_Thue": taxes_id_all,
                "UserIDXN": '',
                'NgayXn': '',
            }
            # no_tk_default, co_tk_default = self.env['ttb.augges'].get_no_co_from_dmnx(data['ID_Nx'], cursor)
            slnxm_id = self.env['ttb.augges'].insert_record('SlNxM', data, conn)

            count = 1

            list_insert = f"""(
                ID, stt, md, Sngay, ID_Dt, 
                ID_Kho, ID_Hang, Sl_Qd, So_Luong, So_LuongT, Gia_Vat,

                Gia_Kvat, Gia_Qd, Don_Gia, T_Tien, Tyle_Ck, 
                ID_Tt, Ty_Gia, ID_Thue, Tien_GtGt, Hs_Qd,

                Don_Gia1, T_Tien1, Sl_Yc, Gia_Nt, Tien_Nt, 
                Tien_Ck, Tien_CKPb, No_Tk, Co_Tk, No_Tk1, Co_Tk1, Stt_Dh, Ghi_Chu
            ) """
            # for line in rec.order_line:
            for line in rec_stock.move_ids_without_package:
                if line.quantity == 0: continue
                taxes_id = line.ttb_taxes_id.mapped('id_augges')
                price_total = line.ttb_return_request_line_id.confirm_vendor_price * line.quantity if line.ttb_return_request_line_id else 0

                base_lines = [line._prepare_base_line_for_taxes_computation()]
                AccountTax._add_tax_details_in_base_lines(base_lines, rec_stock.company_id)
                AccountTax._round_base_lines_tax_details(base_lines, rec_stock.company_id)
                tax_totals = AccountTax._get_tax_totals_summary(
                    base_lines=base_lines,
                    currency=rec_stock.currency_id or rec_stock.company_id.currency_id,
                    company=rec_stock.company_id,
                )
                amount_tax = tax_totals['tax_amount_currency']
                tax_total += amount_tax

                data = {
                    'ID': slnxm_id,
                    'Stt': count,
                    'md': '',
                    'Sngay': sngay,
                    'ID_Dt': augges_id,

                    'ID_Kho': id_kho,
                    'ID_Hang': line.product_id.product_tmpl_id.augges_id,
                    'Sl_Qd': line.quantity,
                    'So_Luong': line.quantity,
                    'So_LuongT': line.quantity,
                    'Gia_Vat': line.ttb_return_request_line_id.confirm_vendor_price if line.ttb_return_request_line_id else 0,

                    'Gia_Kvat': line.ttb_return_request_line_id.confirm_vendor_price if line.ttb_return_request_line_id else 0,
                    'Gia_Qd': line.ttb_return_request_line_id.confirm_vendor_price if line.ttb_return_request_line_id else 0,
                    'Don_Gia': line.ttb_return_request_line_id.confirm_vendor_price if line.ttb_return_request_line_id else 0,
                    'T_Tien': price_total,
                    'Tyle_Ck': line.ttb_discount,

                    'ID_Tt': currency_id,
                    'Ty_Gia': 0,
                    'ID_Thue': taxes_id[0] if taxes_id else None,
                    'Tien_GtGt': amount_tax,
                    'Hs_Qd': '',

                    'Don_Gia1': line.ttb_return_request_line_id.confirm_vendor_price if line.ttb_return_request_line_id else 0,
                    'T_Tien1': price_total,
                    'Sl_Yc': line.quantity,
                    'Gia_Nt': 0,
                    'Tien_Nt': 0,

                    'Tien_Ck': line.ttb_discount_amount * line.quantity,
                    'Tien_CKPb': 0,
                    'No_Tk': 331,
                    'Co_Tk': 1561,
                    'No_Tk1': '',
                    'Co_Tk1': '',
                    'Stt_Dh': 0,
                    'Ghi_Chu': '',
                }
                # Gọi hàm insert, không cần lấy ID vì đã có ID + Stt
                self.env['ttb.augges'].insert_record("SlNxD", data, conn, False)
                line.write({'stt_augges': count})
                count += 1

            if tax_total:
                data = {
                    'ID': slnxm_id,
                    'Stt': count,
                    'md': 7,
                    'Sngay': sngay,
                    'ID_Dt': augges_id,

                    'ID_Kho': rec_stock.location_id.warehouse_id.id_augges,
                    'ID_Hang': None,
                    'Sl_Qd': 0,
                    'So_Luong': 0,
                    'So_LuongT': 0,
                    'Gia_Vat': 0,

                    'Gia_Kvat': 0,
                    'Gia_Qd': 0,
                    'Don_Gia': 0,
                    'T_Tien': tax_total,
                    'Tyle_Ck': 0,

                    'ID_Tt': currency_id,
                    'Ty_Gia': 0,
                    'ID_Thue': taxes_id_all,
                    'Tien_GtGt': 0,
                    'Hs_Qd': '',

                    'Don_Gia1': 0,
                    'T_Tien1': 0,
                    'Sl_Yc': 0,
                    'Gia_Nt': 0,
                    'Tien_Nt': 0,

                    'Tien_Ck': 0,
                    'Tien_CKPb': 0,
                    'No_Tk': '331',
                    'Co_Tk': '1331',
                    'No_Tk1': '',
                    'Co_Tk1': '',
                    'Stt_Dh': 0,
                    'Ghi_Chu': unicode_to_tcvn3("Thuế GTGT"),
                }
                self.env['ttb.augges'].insert_record("SlNxD", data, conn, False)
                count += 1

            rec_stock.write({
                'id_augges': slnxm_id,
                'is_sent_augges': True,
                'sp_augges': value_sp,
            })


        if owns_conn:
            conn.commit()
            cursor.close()
            conn.close()
