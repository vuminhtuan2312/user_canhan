from odoo import models, fields

from odoo.exceptions import UserError


class TtbVoucherType(models.Model):
    _name = 'ttb.voucher.type'
    _description = 'Loại ưu đãi'
    _order = 'sequence asc'

    sequence = fields.Integer(default=10)
    name = fields.Char(string='Tên loại ưu đãi', required=True)
    active = fields.Boolean(default=True)

    def action_get_voucher(self):
        self.ensure_one()
        user = self.env.user

        voucher = self.env['ttb.voucher'].search([
            ('ttb_branch_id', 'in', user.ttb_branch_ids.ids),
            ('voucher_type_id', '=', self.id),
            ('expire_date', '>=', fields.Date.today()),
            ('issued', '=', False),
        ], limit=1, order='id asc')

        if not voucher:
            raise UserError('Bạn hiện tại không có Mã ưu đãi, vui lòng liên hệ Công nghệ để thêm')

        voucher.write({
            'issued': True,
            'issue_datetime': fields.Datetime.now(),
        })

        remain = self.env['ttb.voucher'].search_count([
            ('ttb_branch_id', 'in', user.ttb_branch_ids.ids),
            ('voucher_type_id', '=', self.id),
            ('issued', '=', False),
        ])

        return {
            'type': 'ir.actions.act_window',
            'name': 'Mã ưu đãi',
            'res_model': 'ttb.voucher.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_voucher_code': voucher.code,
                'default_remain_qty': remain,
                'default_message': f'Bạn còn lại {remain} mã ưu đãi, vui lòng liên hệ Công nghệ để thêm'
            }
        }
