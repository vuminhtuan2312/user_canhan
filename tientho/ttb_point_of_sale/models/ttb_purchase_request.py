from odoo import api, fields, models

class TtbPurchaseRequest(models.Model):
    _inherit = 'ttb.purchase.request'

    report_pr_id = fields.Many2one(comodel_name='ttb.report.pos.action', string='Phiếu báo cáo PR')
