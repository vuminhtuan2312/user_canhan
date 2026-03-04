from odoo import fields, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    id_augges = fields.Integer("ID Augges")
    ma_thue_augges = fields.Char("Mã thuế Augges")
    vao_ra = fields.Selection(string='Vào-ra', selection=[('1', 'Đầu vào'), ('2', 'Đầu ra')])
    khau_tru = fields.Selection(string='Khấu trừ', selection=[('0', 'Không kê khai và nộp thuế'),
                                                              ('1', 'Chịu thuế'),
                                                              ('2', 'Không chịu thuế'),
                                                              ('3', 'Phân bổ'),
                                                              ('4', 'Dự án đầu tư'),
                                                              ('5', 'Không tổng hợp trên tờ khai 01/GTGT'),
                                                              ('6', 'Không tính thuế'),
                                                              ])
