from odoo import api, fields, models, _
# from odoo.exceptions import ValidationError


class ProductProduct(models.Model):
    _inherit = "product.product"
    _barcode_field = 'barcode_search'

    barcode_search = fields.Char(string='Trường ảo sinh domain barcode', compute='_compute_barcode_search', search='_search_barcode_search')
    # TODO: Thiện để tạm vào module này để ko phải update module gốc
    barcode_k = fields.Char(index='trigram')
    require_scan = fields.Boolean(
        related="product_tmpl_id.require_scan",
        store=False
    )

    def _compute_barcode_search(self):
        # Không cần làm gì vì đây là trường ảo chỉ để search
        for record in self:
            record.barcode_search = ''

    @api.model
    def _search_barcode_search(self, operator, value):
        value_str = value[0]
        return [
            '|', '|', '|', 
            '|', '|', '|', '|', '|', '|', '|', '|',
            ('barcode', operator, value),
            ('default_code', operator, value),
            ('barcode_vendor', operator, value),
            ('barcode_k', operator, value),

            ('barcode_k', '=like', value_str + ',%'),                        # nằm đầu
            ('barcode_k', '=like', value_str + ' ,%'),                       # nằm đầu + có space
            ('barcode_k', '=like', '%,' + value_str),                        # nằm cuối
            ('barcode_k', '=like', '%, ' + value_str),                       # cuối + có space
            ('barcode_k', '=like', '%,' + value_str + ',%'),                 # nằm giữa
            ('barcode_k', '=like', '%, ' + value_str + ' ,%'),               # nằm giữa + space 2 đầu
            ('barcode_k', '=like', '%, ' + value_str + ',%'),                # nằm giữa + space trái
            ('barcode_k', '=like', '%,' + value_str + ' ,%'),                # nằm giữa + space phải                
        ]

    @api.model
    def _get_fields_stock_barcode(self):
        return super()._get_fields_stock_barcode() + [
            'default_code',
            'barcode_vendor',
            'barcode_k',
            'require_scan',
        ]
    def get_price_pol(self):
        purchase_order_lines = self.env['purchase.order.line'].search([
            ('order_id.effective_date', '!=', False),
            ('product_id', '=', self.id), ('product_qty', '>', 0),
            ('order_id.state', 'in', ['purchase', 'done']),
        ])
        # Sắp xếp các dòng PO theo effective_date giảm dần (mới nhất trước)
        sorted_purchase_order_lines = purchase_order_lines.sorted(
            key=lambda line: line.order_id.effective_date,
            reverse=True
        )

        # Lấy dòng PO mới nhất (nếu có)
        if sorted_purchase_order_lines:
            pol = sorted_purchase_order_lines[0]
        else:
            pol = False
        if pol:
            unit_price = (pol.price_unit or 0) - (pol.ttb_discount_amount or 0) / pol.product_qty
        else:
            unit_price = self.product_tmpl_id.last_price or 0

        return unit_price

    @api.model
    def search(self, domain, offset=0, limit=None, order=None):
        result = super().search(domain, offset=offset, limit=limit, order=order)
        if not result:
            # Kiểm tra domain có trường barcode_search hay không
            has_barcode_search = any(
                (isinstance(cond, (list, tuple)) and cond[0] == "barcode_search")
                for cond in domain
            )

            if has_barcode_search:
                # Gọi search với context with_active_test=False
                result =  super(
                    ProductProduct,
                    self.with_context(active_test=False)
                ).search(domain, offset=offset, limit=limit, order=order)
            if not result:
                barcode_search_cond = False
                for cond in domain:
                    if isinstance(cond, (list, tuple)) and cond[0] == "barcode_search":
                        barcode_search_cond = cond
                        break
                if barcode_search_cond:
                    operator = barcode_search_cond[1]
                    value = barcode_search_cond[2]
                    if value[0].startswith("0"):
                        # Loại bỏ các số 0 ở đầu
                        new_value = value[0][1:]
                        if new_value:
                            new_domain = [
                                ('barcode_search', operator, [new_value])
                            ]
                            domain = ['|'] + new_domain + domain

                            result = super(ProductProduct,self.with_context(active_test=False)).search(domain, offset=offset, limit=limit, order=order)
        return result

class ProductTemplate(models.Model):
    _inherit = "product.template"

    # TODO: Thiện để tạm vào module này để ko phải update module gốc
    barcode_k = fields.Char(index='trigram')
    require_scan = fields.Boolean(
        string="Bắt buộc quét barcode",
        help="Nếu bật, sản phẩm chỉ được tăng số lượng bằng quét barcode"
    )
