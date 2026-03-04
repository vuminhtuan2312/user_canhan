from odoo import api, fields, models, _

class TtbCancelReason(models.Model):
    _name = 'ttb.cancel.reason'
    _description = 'Lý do hủy phiếu đánh giá'


    name = fields.Char(string='Lý do', required=True, translate=True)
