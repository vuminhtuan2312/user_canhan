from odoo import fields, models, api
from datetime import datetime
from dateutil.relativedelta import relativedelta
from collections import defaultdict

from odoo.exceptions import UserError


class KvcInventorySession(models.Model):
    _name = 'kvc.inventory.session'
    _description = 'Phiên Kiểm tồn khu vui chơi'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(default=lambda self: self.env['ir.sequence'].next_by_code('kvc.inventory.session'), string='Mã phiên')
    branch_id = fields.Many2one(string='Cơ sở', comodel_name='ttb.branch', required=True)
    create_date = fields.Datetime(string='Ngày tạo')
    state = fields.Selection(
        string="Trạng thái kiểm",
        selection=[
            ('draft', 'Đang chờ'),
            ('done', 'Hoàn thành')
        ],
        default='draft', traking=True
    )
    user_by = fields.Many2one('res.users', string='Người thực hiện', tracking=True)
    done_date = fields.Datetime(string='Ngày hoàn thành', tracking=True)
    inventory_line_ids = fields.One2many('kvc.inventory.line', 'session_id', string='Chi tiết kiểm kê')
    week_number = fields.Integer(string='Tuần', required=True)
    line_ids = fields.One2many('kvc.inventory.line', inverse_name='session_id', string='Danh sách kiểm kê')
    product_code = fields.Char(string='Mã sản phẩm')
    check_update_stock_button = fields.Boolean(compute='_compute_check_update_stock_button')
    product_sector = fields.Char(string='Nhóm hàng', related='line_ids.product_sector', store=True)
    product_name = fields.Many2one(string='Tên hàng', related='line_ids.product_name', store=True)
    def action_done(self):
        for rec in self:
            if any(line.state_check == 'draft' for line in rec.line_ids):
                raise UserError("Vui lòng kiểm hết sản phẩm trong phiên kiểm.")

            rec.state = 'done'
            rec.done_date = fields.Datetime.now()
            rec.user_by = self.env.user.id

    @api.depends('branch_id')
    def _compute_check_update_stock_button(self):
        for record in self:
            user = self.env.user
            employee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
            record.check_update_stock_button = False

            if employee and employee.job_id.name == 'Giám đốc Nhà sách' and record.branch_id.id in employee.ttb_branch_ids.ids:
                record.check_update_stock_button = True

    @api.model
    def cron_generate_weekly_kvc_session(self, target_date=None):
        if target_date:
            today = fields.Date.from_string(target_date)
        else:
            today = (datetime.now() + relativedelta(hours=7)).date()

        if today.weekday() == 6:
            week = int(today.strftime("%U")) + 1
            product_configs = self.env['kvc.inventory.config'].search([])

            for config in product_configs:
                sector_groups = defaultdict(list)
                for line in config.product_line_ids:
                    sector_groups[line.product_sector].append(line)

                for sector, lines in sector_groups.items():
                    existing_session = self.search([
                        ('branch_id', '=', config.branch_id.id),
                        ('week_number', '=', week),
                        ('line_ids.product_sector', '=', sector)
                    ], limit=1)
                    if existing_session:
                        continue
                    session_vals = {
                        'branch_id': config.branch_id.id,
                        'week_number': week,
                        'create_date': today,
                        'line_ids': []
                    }
                    for line in lines:
                        session_vals['line_ids'].append((0, 0, {
                            'product_sector': line.product_sector,
                            'product_code': line.product_code,
                            'product_code_1': line.product_code_1,
                            'barcode': line.barcode,
                            'barcode_k': line.barcode_k,
                            'product_name': line.product_name.id,
                            'uom': line.uom,
                        }))

                    self.create(session_vals)
    def button_update_stock_to_augges(self):
        for line in self.line_ids.filtered(lambda l: l.diff_qty > 0):
            conn = self.env['ttb.tools'].get_mssql_connection_send()
            cursor = conn.cursor()
            try:
                product_augges_id = line.product_id.product_tmpl_id.augges_id
                warehouse_augges_id = line.session_id.branch_id.warehouse_id.id_augges
                if not product_augges_id or not warehouse_augges_id:
                    continue
                sql = f"""
                        UPDATE TEN_BANG SET TEN_COT = ISNULL(TEN_COT, 0) + {line.diff_qty}
                        WHERE ID_KHO = {warehouse_augges_id} AND ID_HANG = {product_augges_id}
                        """
                cursor.execute(sql)
            finally:
                conn.commit()
                cursor.close()
                conn.close()
class KvcInventoryLine(models.Model):
    _name = 'kvc.inventory.line'
    _description = 'Chi tiết phiên kiểm khu vui chơi'

    session_id = fields.Many2one('kvc.inventory.session', string='Phiên kiểm kê')
    product_sector = fields.Char(string='Nhóm hàng')
    product_code = fields.Char(string='Mã hàng')
    product_code_1 = fields.Char(string='Mã hàng 1')
    barcode = fields.Char(string='Mã vạch')
    barcode_k = fields.Char(string='Mã vạch k')
    product_name = fields.Many2one(string='Tên hàng', comodel_name='product.product')
    uom = fields.Char(string='Đơn vị tính')
    qty_real = fields.Float(string='Số lượng thực tế', readonly=1)
    diff_qty = fields.Float(string='Lệch', compute='_compute_diff_qty', store=True, readonly=1)
    stock_qty = fields.Float(string='Số lượng tồn', readonly=1)
    can_check_inventory = fields.Boolean(
        compute='_compute_can_check_inventory'
    )
    state = fields.Selection(string='Trạng thái', related='session_id.state', store=True, readonly=1)
    last_qty_add = fields.Float(string="SL bổ sung cuối", readonly=1)
    state_check = fields.Selection(
        string='Trạng thái kiểm từng dòng', selection=[
            ('draft', 'Chưa kiểm'),
            ('done', 'Đã kiểm')
        ],
        default='draft', readonly=1)
    is_update_augges = fields.Boolean(string="Đã cập nhật tồn", default=False)
    @api.depends('state_check')
    def _compute_can_check_inventory(self):
        for rec in self:
            rec.can_check_inventory = rec.state_check == 'done'

    def open_check_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Cập nhật tồn',
            'res_model': 'check.kvc.inventory.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_line_id': self.id,
                'default_qty_real': self.qty_real
            }
        }
    def open_add_qty_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Nhập bổ sung',
            'res_model': 'add.qty.kvc.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_line_id': self.id,
            }
        }
    @api.depends('qty_real', 'stock_qty')
    def _compute_diff_qty(self):
        for line in self:
            line.diff_qty = (line.qty_real or 0.0) - (line.stock_qty or 0.0)