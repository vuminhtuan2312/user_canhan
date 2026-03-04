# Task 786 comment toàn bộ file này
# from odoo import *
# from odoo import _


# class PosOrderLine(models.Model):
#     _inherit = 'pos.order.line'

    # task 786 Dùng luôn trường qty của base nên ko cần hàm này nữa
    # def _prepare_tax_base_line_values(self):
    #     self = self.filtered(lambda x: x.purchase_invoiced_qty)
    #     return super(PosOrderLine, self)._prepare_tax_base_line_values()

    # Thiện hiểu code dưới đây mục đích thay số lượng xuất hoá đơn từ qty -> purchase_invoiced_qty
    # Task 786 dùng trường qty của base -> không dùng code này nữa
    # def _prepare_base_line_for_taxes_computation(self):
    #     self.ensure_one()
    #     commercial_partner = self.order_id.partner_id.commercial_partner_id
    #     fiscal_position = self.order_id.fiscal_position_id
    #     line = self.with_company(self.order_id.company_id)
    #     account = line.product_id._get_product_accounts()['income'] or self.order_id.config_id.journal_id.default_account_id
    #     if not account:
    #         raise exceptions.UserError(_(
    #             "Vui lòng xác định tài khoản thu nhập cho sản phẩm này: '%(product)s' (id:%(id)d).",
    #             product=line.product_id.name, id=line.product_id.id,
    #         ))

    #     if fiscal_position:
    #         account = fiscal_position.map_account(account)

    #     is_refund_order = line.order_id.amount_total < 0.0
    #     is_refund_line = line.purchase_invoiced_qty * line.price_unit < 0

    #     product_name = line.product_id \
    #         .with_context(lang=line.order_id.partner_id.lang or self.env.user.lang) \
    #         .get_product_multiline_description_sale()

    #     return {
    #         **self.env['account.tax']._prepare_base_line_for_taxes_computation(
    #             line,
    #             partner_id=commercial_partner,
    #             currency_id=self.order_id.currency_id,
    #             rate=self.order_id.currency_rate,
    #             product_id=line.product_id,
    #             tax_ids=line.tax_ids_after_fiscal_position,
    #             price_unit=line.price_unit,
    #             quantity=line.purchase_invoiced_qty * (-1 if is_refund_order else 1),
    #             discount=line.discount,
    #             account_id=account,
    #             is_refund=is_refund_line,
    #             sign=1 if is_refund_order else -1,
    #         ),
    #         'uom_id': line.product_uom_id,
    #         'name': product_name,
    #     }
from odoo import models, fields

class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    promotion_program_name = fields.Char('CTKM')