from pytz import timezone, utc
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class InventorySession(models.Model):
    _name = 'inventory.session'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Quản lý phiên kiểm kê'

    name = fields.Char(string='Phiên kiểm kê', required=True)
    branch_id = fields.Many2one(string='Cơ sở', comodel_name='ttb.branch', required=True)
    warehouse_location_id = fields.Many2one(string='Kho hàng', comodel_name='stock.location', required=True)
    domain_stock_location = fields.Binary(string='Domain kho hàng', compute='_compute_domain_stock_location')

    @api.depends('branch_id')
    def _compute_domain_stock_location(self):
        for rec in self:
            domain = [('id', '=', False)]
            if rec.branch_id:
                domain = [('warehouse_id.ttb_branch_id', '=', rec.branch_id.id), ('usage', '=', 'internal'), ('location_id.usage', '=', 'view')]
            rec.domain_stock_location = domain

    date_assign = fields.Datetime(string='Ngày thực hiện', required=True, default=fields.Datetime.now)
    user_created_id = fields.Many2one(string='Người tạo', comodel_name='res.users', required=True, default=lambda self: self.env.user)
    check_percentage = fields.Float(string='Phần trăm hậu kiểm', required=True)
    code = fields.Char(string='Mã phiên', compute='_compute_code', store=True)

    @api.depends('branch_id', 'date_assign')
    def _compute_code(self):
        for rec in self:
            date_assign = ''
            if rec.date_assign:
                user_tz = self.env.user.tz or 'UTC'
                date_assign_user_tz = utc.localize(rec.date_assign).astimezone(timezone(user_tz))
                date_assign = date_assign_user_tz.strftime('%Y%m%d%H')
            rec.code = f"{rec.branch_id.code or ''}{date_assign}"

    state = fields.Selection(string='Trạng thái', selection=[('new', 'Mới'), ('assign', 'Phân công'), ('ready', 'Sẵn sàng'), ('done', 'Hoàn thành')], default='new')
    inventory_session_line_ids = fields.One2many(string='Chi tiết phiên kiểm kê', comodel_name='inventory.session.lines', inverse_name='inventory_session_id')
    show_button_create = fields.Boolean(string='Hiện button tạo phiên', compute='_compute_show_button_create')

    @api.depends('inventory_session_line_ids', 'state')
    def _compute_show_button_create(self):
        for rec in self:
            show_button_create = False
            if rec.state == 'assign' and rec.inventory_session_line_ids and all(line.user_count_id and line.user_check_id for line in rec.inventory_session_line_ids):
                show_button_create = True
            rec.show_button_create = show_button_create

    show_button_start_count = fields.Boolean(string='Hiện button kiểm kê', compute='_compute_show_button_start_count')

    @api.depends('inventory_session_line_ids', 'inventory_session_line_ids.user_count_id', 'state')
    @api.depends_context('uid')
    def _compute_show_button_start_count(self):
        for rec in self:
            show_button_start_count = False
            user_count_ids = rec.inventory_session_line_ids.mapped('user_count_id').ids
            user = self.env.user.id
            if rec.state == 'ready' and user in user_count_ids:
                show_button_start_count = True
            rec.show_button_start_count = show_button_start_count

    show_button_start_check = fields.Boolean(string='Hiện button hậu kiểm', compute='_compute_show_button_start_check')

    @api.depends('inventory_session_line_ids', 'inventory_session_line_ids.user_check_id', 'state')
    @api.depends_context('uid')
    def _compute_show_button_start_check(self):
        for rec in self:
            show_button_start_check = False
            user_check_ids = rec.inventory_session_line_ids.mapped('user_check_id').ids
            user = self.env.user.id
            if rec.state == 'ready' and user in user_check_ids:
                show_button_start_check = True
            rec.show_button_start_check = show_button_start_check

    show_button_done = fields.Boolean(string='Hiện button hoàn thành', compute='_compute_show_button_done')

    @api.depends()
    def _compute_show_button_done(self):
        for rec in self:
            show_button_done = False
            if rec.state == 'ready' and rec.inventory_session_line_ids and all(line.status == 'complete' for line in rec.inventory_session_line_ids):
                show_button_done = True
            rec.show_button_done = show_button_done

    def button_assign(self):
        pid_location_ids = self.env['stock.location'].search([('location_id', '=', self.warehouse_location_id.id)]).ids
        if not pid_location_ids:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'sticky': True,
                    'message': f"Lỗi: Không tìm thấy PID nào tại kho {self.warehouse_location_id.display_name}, vui lòng kiểm tra lại",
                }
            }
        for pid_location_id in pid_location_ids:
            self.env['inventory.session.lines'].create({'inventory_session_id': self.id, 'pid_location_id': pid_location_id})
        self.state = 'assign'

    def button_create(self):
        users = self.inventory_session_line_ids.mapped('user_count_id') + self.inventory_session_line_ids.mapped('user_check_id')
        self.message_notify(subject='Kiểm kê', body='Bạn được phân công kiểm kê', partner_ids=users.mapped('partner_id').ids)
        self.state = 'ready'

    def button_start_count(self):
        pass
        #Todo Duy sẽ code phần ra giao diện quét

    def button_start_check(self):
        pass
        # Todo Duy sẽ code phần ra giao diện quét

    def button_done(self):
        for line in self.inventory_session_line_ids:
            for detail_line in line.pid_location_id.stock_location_detail_line_ids:
                quantes = self.env['stock.quant'].sudo().search([('location_id', '=', detail_line.destination_location_id.id), ('inventory_quantity', '!=', 0)])
                for quant in quantes:
                    quant.sudo().write({'inventory_quantity': 0})
                    quant.sudo().action_apply_inventory()
            for result_lines in line.inventory_result_id.lines_ids:
                qty = result_lines.quantity_final
                location_id = result_lines.destination_location_id
                product_id = result_lines.product_id
                quant = self.env['stock.quant'].sudo().search([('location_id', '=', location_id.id), ('product_id', '=', product_id.id)], limit=1)
                if quant:
                    quant.sudo().write({'inventory_quantity': qty})
                    quant.sudo().action_apply_inventory()
                else:
                    self.env['stock.quant'].sudo().create({'inventory_quantity': qty, 'product_id': product_id.id, 'location_id': location_id.id}).action_apply_inventory()
        self.state = 'done'

    #Tạo mới kết quả kiểm kê
    def create_inventory_result(self, pid_location_id=False):
        if not pid_location_id:
            raise UserError('Chưa có mã địa điểm')
        count_inventory_result = '%02d' % (self.env['inventory.result'].search_count([('session_id', '=', self.id)]) + 1)
        inventory_result = self.env['inventory.result'].create({'branch_id': self.branch_id.id,
                                             'name': f'{self.code}{pid_location_id.barcode or ""}{count_inventory_result}',
                                             'state': 'count_process',
                                             'pid_location_id': pid_location_id.id,
                                             'user_count_id': self.env.user.id,
                                             'datetime_count': fields.Datetime.now(),
                                             'session_id': self.id
                                             })
        inventory_session_lines = self.inventory_session_line_ids.filtered_domain([('pid_location_id', '=', pid_location_id.id)])
        if inventory_session_lines:
            inventory_session_lines.write({'inventory_result_id': inventory_result.id})
        return inventory_result

    #Kiểm tra người kiểm kê có được phân công vào quầy kiểm kê hay không
    def check_pid_location_start_count(self, pid_location_id=False):
        if not pid_location_id:
            raise UserError('Chưa có mã địa điểm')
        inventory_session_lines = self.inventory_session_line_ids.filtered_domain([('pid_location_id', '=', pid_location_id.id), ('user_count_id', '=', self.env.user.id)])
        if not inventory_session_lines:
            raise UserError('Quầy không thuộc khu vực được phân công')

    #kiểm tra người hậu kiểm có được phân công hay không
    def check_pid_location_start_check(self, pid_location_id=False):
        if not pid_location_id:
            raise UserError('Chưa có mã địa điểm')
        inventory_session_lines = self.inventory_session_line_ids.filtered_domain([('pid_location_id', '=', pid_location_id.id), ('user_check_id', '=', self.env.user.id)])
        if not inventory_session_lines:
            raise UserError('Quầy không thuộc khu vực được phân công')

    #Kiểm tra kết quả kiểm kê
    def check_inventory_result_start_count(self, pid_location_id=False):
        if not pid_location_id:
            raise UserError('Chưa có mã địa điểm')
        inventory_session_line = self.inventory_session_line_ids.filtered_domain([('pid_location_id', '=', pid_location_id.id)])[:1]
        if inventory_session_line:
            inventory_result = inventory_session_line.inventory_result_id
            if inventory_session_line.status != 'cancel' and inventory_result and len(pid_location_id.stock_location_detail_line_ids) == len(inventory_result.lines_ids):
                raise UserError('Quầy đã được kiểm kê')

    # Kiểm tra kết quả hậu kiểm
    def check_inventory_result_start_check(self, pid_location_id=False):
        if not pid_location_id:
            raise UserError('Chưa có mã địa điểm')
        inventory_session_line = self.inventory_session_line_ids.filtered_domain([('pid_location_id', '=', pid_location_id.id)])[:1]
        if inventory_session_line:
            inventory_result = inventory_session_line.inventory_result_id
            if inventory_session_line.status != 'cancel' and inventory_result and all(inventory_result.lines_ids.filtered(lambda x: x.quantity_check > 0)):
                raise UserError('Quầy đã được hậu kiểm')

    @api.model
    def get_product_by_session_id(self, session_id):
        inventory_session_lines = self.browse(session_id).inventory_session_line_ids
        if inventory_session_lines:
            for inventory_line in inventory_session_lines:
                stock_location_lines = self.env['stock.location'].search([('id', '=', inventory_line.pid_location_id.id)]).stock_location_detail_line_ids
                details = []
                for stock_detail in stock_location_lines:
                    detail_dict = {
                        'order_number': stock_detail.order_number,
                        'product_id': stock_detail.product_id.id,
                        'product_name': stock_detail.product_id.display_name,
                        'quantity': stock_detail.quantity
                    }
                    details.append(detail_dict)
            return details
        return []

    @api.model
    def filter_on_barcode(self, barcode):
        pid = self.env['stock.location'].search([('barcode', '=', barcode)], limit=1)
        if pid:
            action = self.env.ref("ttb_stock.stock_location_form_inherit").sudo().read()[0]
            action['res_id'] = pid.id
            return {'action': action}

        return {
            'warning': {
                'message': _("Quét sai quầy, vui lòng thử lại")
            }
        }

    # @api.model
    # def filter_on_barcode(self, barcode):
    #     product = self.env['product.product'].search([('barcode', '=', barcode)], limit=1)
    #     uid = self.env.context.get('uid')
    #     if product:
    #         inventory_session_lines = self.browse(uid).inventory_session_line_ids
    #         for line in inventory_session_lines:
    #             detail_lines = self.env['stock.location'].search([('id', '=', line.pid_location_id.id)]).stock_location_detail_line_ids
    #             for detail in detail_lines:
    #                 if product.id in detail.mapped('product_id.id'):
    #                     return {
    #                         'stock_location_id': detail.id,
    #                         'product': product.id,
    #                         'order_number': detail.order_number,
    #                         'quantity': detail.quantity,
    #                     }
    #                 # for detail in detail_lines:
    #                 #     detail_dict = {
    #                 #         'order_number': detail.order_number,
    #                 #         'product_id': detail.product_id.id,
    #                 #         'quantity': detail.quantity
    #                 #     }
    #                 #     action = self.env["ir.actions.actions"]._for_xml_id("ttb_inventory_barcode_kiem_ke.action_product_popup_form")
    #                 #     ctx.update({'default_product_id': product.id})
    #                 #     action['context'] = ctx
    #                 #     return {'action': action}
    #         return {
    #             'warning': {
    #                     'message': _("Sản phẩm này không có trong phiên kiểm kê, vui lòng kiểm tra lại")
    #                 }
    #             }

class InventorySessionLines(models.Model):
    _name = 'inventory.session.lines'
    _description = 'Chi tiết phiên kiểm kê'

    inventory_session_id = fields.Many2one(string='Phiên kiểm kê', comodel_name='inventory.session', required=True)
    pid_location_id = fields.Many2one(string='PID', comodel_name='stock.location')
    user_count_id = fields.Many2one(string='Nhân viên kiểm kê', comodel_name='res.users')
    user_check_id = fields.Many2one(string='Nhân viên hậu kiểm', comodel_name='res.users')
    branch_id = fields.Many2one(string='Cơ sở', related='inventory_session_id.branch_id', store=True)
    domain_user = fields.Binary(string='Domain nhân viên', compute='_compute_domain_user')

    @api.depends('branch_id')
    def _compute_domain_user(self):
        for rec in self:
            rec.domain_user = [('ttb_branch_id', '=', rec.branch_id.id)]

    inventory_result_id = fields.Many2one(string='Kết quả kiểm kê', comodel_name='inventory.result')
    status = fields.Selection(string='Tiến trình', related='inventory_result_id.state', store=True)
