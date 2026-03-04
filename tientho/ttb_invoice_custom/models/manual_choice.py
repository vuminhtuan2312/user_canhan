from odoo import api, fields, models


class TaxManualChoice(models.Model):
    _name = 'tax.manual.choice'
    _description = 'Lựa chọn thủ công ghép dòng hoá đơn đầu vào và đầu ra'

    choice_type = fields.Selection([('merge', 'Ghép'), ('delete', 'Bỏ ghép')], string='Loại lựa chọn', required=True)
    in_line_id = fields.Many2one('ttb.nimbox.invoice.line', 'Dòng hoá đơn đầu vào', index=True, required=True, auto_join=True)
    out_line_id = fields.Many2one('tax.output.invoice.line', string='Dòng hoá đơn đầu ra', auto_join=True)
    branch_id = fields.Many2one(string='Cở sở', comodel_name='ttb.branch')
