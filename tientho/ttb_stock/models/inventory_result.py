from odoo import *
import math
import random

class InventoryResult(models.Model):
    _name='inventory.result'
    _description='Kết quả kiểm kê'

    name=fields.Char(string='Tên', readonly=True)
    branch_id=fields.Many2one('ttb.branch', string='Cơ sở')
    pid_location_id=fields.Many2one('stock.location', string='PID', required=True)
    datetime_count=fields.Datetime(string='Thời gian kiểm kê')
    datetime_check=fields.Datetime(string='Thời gian hậu kiểm')
    user_count_id=fields.Many2one('res.users',string='Nhân viên kiểm kê', required=True)
    user_check_id=fields.Many2one('res.users',string='Nhân viên hậu kiểm', required=False)
    check_percentage=fields.Float(string='Phần trăm hậu kiểm', related='session_id.check_percentage', required=False)
    session_id=fields.Many2one('inventory.session',string='Phiên kiểm kê',required=True)
    session_line_id = fields.Many2one('inventory.session.lines', string='Chi tiết kiểm kê')
    lines_ids =fields.One2many('inventory.result.lines', string='Chi tiết kiểm kê', inverse_name='inventory_result_id')
    state = fields.Selection(
        selection=[
            ('count_process', 'Đang kiểm kê'),
            ('count_done', 'Hoàn thành kiểm kê'),
            ('check_process', 'Đang hậu kiểm'),
            ('check_done', 'Hoàn thành hậu kiểm'),
            ('complete', 'Chốt kết quả'),
            ('cancel', 'Hủy'),
        ],
        string='Trạng thái',
        default='count_process'
    )

    def write(self, vals):
        res = super().write(vals)
        if 'state' in vals and vals['state'] == 'count_done':
            self._compute_check_percentage()
        return res

    def _compute_check_percentage(self):
        for rec in self:
            rec.lines_ids.check = False
            all_lines = rec.lines_ids
            count_to_select = math.ceil(len(all_lines) * rec.check_percentage)
            if count_to_select > 0:
                selected_records = random.sample(all_lines, count_to_select)
                for line in selected_records:
                    line.check = True

    def button_confirm(self):
        for rec in self:
            #Hương confirm chỉ chuyển trạng thái
            # invalid_lines = rec.line_ids.filtered(lambda l: l.quantity_count != l.quantity_check)
            # invalid_count = len(invalid_lines)
            # if invalid_count == 1:
                # TODO: Làm thông báo khi có 1 sản phẩm bị lệch tới nhân viên
                # return
            # elif invalid_count >= 2:
                # TODO: Chờ xác nhận 1 trong 2 phương án
                # return
            rec.state = 'complete'

    def button_cancel(self):
        self.state = 'cancel'

class InventoryResultLines(models.Model):
    _name='inventory.result.lines'
    _description ='Chi tiết kết quả kiểm kê'

    stock_location_detail_lines_id=fields.Many2one(comodel_name='stock.location.detail.lines', string='Vị trí PID')
    inventory_result_id = fields.Many2one(string='Chi tiết kiểm kê', comodel_name='inventory.result', required=True)
    order_number = fields.Integer(related='stock_location_detail_lines_id.order_number', string='Vị trí')
    product_id = fields.Many2one(comodel_name='product.product', string='Sản phẩm')
    code = fields.Char(string='Mã sản phẩm', compute='_compute_code')
    quantity_count = fields.Integer(string='Số lượng kiểm kê',store=True)
    quantity_check = fields.Integer(string='Số lượng hậu kiểm',store=True)
    quantity_final = fields.Integer(string='Số lượng chốt',compute='_check_quantity_final', store=True, readonly=False)
    destination_location_id = fields.Many2one(comodel_name='stock.location', string='Địa điểm lưu tồn kho', related = 'stock_location_detail_lines_id.destination_location_id')
    check = fields.Boolean(string='Hậu kiểm')

    @api.depends('product_id.barcode', 'product_id.default_code')
    def _compute_code(self):
        for rec in self:
            rec.code = rec.product_id.barcode or rec.product_id.default_code

    @api.depends('quantity_count', 'quantity_check', 'check')
    def _check_quantity_final(self):
        for rec in self:
            if rec.quantity_count == rec.quantity_check or not rec.check:
                rec.quantity_final = rec.quantity_count
            else:
                rec.quantity_final = 0
