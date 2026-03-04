from odoo import api, fields, models

class TtbVoucher(models.Model):
    _name = 'ttb.voucher'
    _description = 'Danh sách mã ưu đãi'

    manager_config_id = fields.Many2one(comodel_name='ttb.voucher.manager', string='Quản lý mã ưu đãi', ondelete='cascade')
    ttb_branch_id = fields.Many2one(comodel_name='ttb.branch', string='Cơ sở')
    code = fields.Text(string='Mã ưu đãi',required=True)
    voucher_type_id = fields.Many2one('ttb.voucher.type', string='Loại mã ưu đãi', domain=[('active', '=', True)])

    issue_datetime = fields.Datetime(string='Ngày phát hành')

    expire_date = fields.Date(string='Ngày hết hạn')

    issued = fields.Boolean(string='Đã phát hành', default=False, help='Đã hiển thị cho quản lý nhà sách')
