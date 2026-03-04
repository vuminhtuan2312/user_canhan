from odoo import api, fields, models, _
from odoo.exceptions import UserError


class Partner(models.Model):
    _inherit = "res.partner"
    _description = 'Contact'
    state_code = fields.Char(related='state_id.code')
    country_name = fields.Char(related='country_id.name')
    code = fields.Char(string='Mã Odoo')
    product_category = fields.Char(string='Ngành hàng')
    discount_product_category = fields.Char(string='Chiết khấu ngành hàng')
    ref = fields.Char(tracking=True)
    ttb_no_invoice = fields.Boolean(string='Không xuất hóa đơn', default=False,
                                help="Nhà cung cấp này không xuất hóa đơn đỏ cho các đơn hàng mua")
    ttb_show_report = fields.Boolean(string='Hiển thị lên báo cáo', default=True,
                                help="Tích chọn để hiển thị thông tin các đơn mua hàng kinh doanh lên các màn hình báo cáo")
    accountant_id = fields.Many2one('hr.employee', 'Kế toán phụ trách', )

    @api.constrains('ref')
    def _check_ref(self):
        for rec in self:
            if rec.ref and rec.supplier_rank > 0:
                check_ref = self.sudo().with_context(active_test=False).search([('id', '!=', rec.id), ('ref', '=', rec.ref)])
                if check_ref:
                    raise UserError('Mã tham chiếu đã tồn tại, vui lòng kiểm tra lại')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('code', False):
                code = self.env['ir.sequence'].next_by_code('seg.code.res.partner')
                while code:
                    check_code = self.env['res.partner'].search([('code', '=', code)], limit=1)
                    if check_code:
                        code = self.env['ir.sequence'].next_by_code('seg.code.res.partner')
                    else:
                        break
                vals['code'] = code
        return super(Partner, self).create(vals_list)
