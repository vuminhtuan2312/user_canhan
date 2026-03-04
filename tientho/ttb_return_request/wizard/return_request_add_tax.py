from odoo import models, fields, api


class ReturnrequestAddTax(models.TransientModel):
    _name = 'return.request.add.tax.wizard'
    _description = 'Chọn Thuế mua hàng'

    taxes_id = fields.Many2many(string='Thuế', comodel_name='account.tax')
    tax_country_id = fields.Many2one(comodel_name='res.country',compute='_compute_tax_country_id',compute_sudo=True,)
    company_id = fields.Many2one(comodel_name='res.company')

    @api.model
    def default_get(self, fields_list):
        """Set giá trị mặc định cho company_id và tax_country_id"""
        res = super().default_get(fields_list)
        if 'company_id' in fields_list:
            res['company_id'] = self.env.company.id
        return res

    @api.depends('company_id')
    def _compute_tax_country_id(self):
        for record in self:
            record.tax_country_id = record.company_id.account_fiscal_country_id

    def do(self):
        records = self.env[self._context.get('active_model')].browse(self._context.get('active_ids'))
        records.filtered(lambda x: x.state == 'draft').line_ids.write({'ttb_taxes_id': [(6, 0, self.taxes_id.ids)]})
        return
