from odoo import api, fields, models

class ErrorTicket(models.Model):
    _name = 'error.ticket'
    _description = 'Phiếu lỗi HRW'

    ticket_code = fields.Char(string="Mã phiếu", required=True, index=True)
    ticket_name = fields.Char(string="Tên phiếu")
    deadline = fields.Date(string="Thời hạn xử lý")
    handler_id = fields.Many2one('res.users', string="Người xử lý")
    approver_id = fields.Many2one('res.users', string="Người duyệt")
    deducted_points = fields.Float(string="Điểm trừ")
    related_score_ticket = fields.Char(string="Phiếu chấm điểm phát sinh")
    store_name = fields.Char(string="Tên cửa hàng")
    address = fields.Char(string="Địa chỉ")
    store_manager = fields.Char(string="Cửa hàng trưởng")
    phone_number = fields.Char(string="Số điện thoại")
    branch_id = fields.Many2one(string="Cơ sở", comodel_name="ttb.branch")
    failed_criteria = fields.Char(string="Tiêu chí không đạt")
    violator_employee = fields.Char(string="Nhân viên vi phạm")
    criteria_group = fields.Char(string="Nhóm tiêu chí")
    processing_result  = fields.Char(string="Kết quả xử lý")

    _sql_constraints = [
        ('ticket_code_unique', 'unique(ticket_code)', 'Mã phiếu đã tồn tại. Vui lòng kiểm tra lại!')
    ]
