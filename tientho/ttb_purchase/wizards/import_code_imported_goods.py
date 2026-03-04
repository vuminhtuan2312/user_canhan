from odoo.exceptions import UserError
from odoo import api, fields, models
from collections import defaultdict

class ImportCodeImportedGoods(models.TransientModel):
    _name = 'import.code.imported.goods'
    _description = 'Nhập mã hàng nhập khẩu'

    name = fields.Many2one('ttb.purchase.request', string='Tên đơn hàng')
    line_ids = fields.One2many(
        comodel_name='import.code.imported.goods.line',
        inverse_name='imported_goods_id',
        string='Dòng mã hàng nhập khẩu'
    )
    def action_import_code(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'import',
            'target': 'new',
            'name': 'Nhập mã NCC',
            'params': {
                'context': {'default_imported_goods_id': self.id},
                'active_model': 'import.code.imported.goods.line',
            }
        }

    def action_confirm_imported_code(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError("Vui lòng thêm mã hàng nhập khẩu trước khi xác nhận.")

        vals = {}
        for line in self.line_ids:
            vals[line.description] = line.code

        purchase_request = self.name
        for line in purchase_request.line_ids:
            if line.description in vals:
                line.write({
                    'item': vals[line.description]
                })
        return {
            'name': ('Purchase Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'ttb.purchase.request',
            'view_mode': 'form',
            'res_id': purchase_request.id,
            'target': 'current',
        }

class ImportCodeImportedGoodsLine(models.TransientModel):
    _name = 'import.code.imported.goods.line'
    _description = 'Dòng mã hàng nhập khẩu'

    imported_goods_id = fields.Many2one(
        comodel_name='import.code.imported.goods',
        string='Mã hàng nhập khẩu'
    )
    description = fields.Char(string='Mô tả', required=True)
    code = fields.Char(string='Mã NCC', required=True)