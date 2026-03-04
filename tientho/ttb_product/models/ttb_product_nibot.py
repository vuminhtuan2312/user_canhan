from odoo import api, fields, models, _
from odoo.addons.ttb_tools.ai.product_similar_matcher import find_similar_product

import logging
_logger = logging.getLogger(__name__)

class ProductNibot(models.Model):
    _name = 'ttb.product.nibot'
    _description = 'Sản phẩm Nibot'

    name = fields.Char('Tên sản phẩm Nibot')
    price = fields.Float('Giá nhập Nibot')
    product_id = fields.Many2one('product.template', 'Sản phẩm Odoo')
    price_odoo = fields.Float('Giá nhập Odoo', related='product_id.standard_price')
    diff_name = fields.Float('Tương hợp về tên')
    processed = fields.Boolean('Đã xử lý', default=False)

    name_origin = fields.Char('Tên sản phẩm Nibot (gốc)')
    note = fields.Char('Ghi chú')

    def find_similar_products(self):
        # origin_nibot_products = self.search([('processed', '=', False)])
        origin_nibot_products = self.search([])
        origin_odoo_products = self.env['product.template'].search([])

        nibot_products = [{'name': product.name, 'price': product.price} for product in origin_nibot_products]
        odoo_products = [{'name': product.name, 'price': product.standard_price} for product in origin_odoo_products]

        matcheds = find_similar_product(nibot_products, odoo_products)
        for nibot_index in matcheds:
            match = matcheds[nibot_index]

            match_index = match['match_index']
            if match_index >= 0:
                odoo_product = origin_odoo_products[match_index]
                origin_nibot_products[nibot_index].write({
                    'product_id': odoo_product.id,
                    'diff_name': match['score'],
                    'processed': True,
                })
            else:
                origin_nibot_products[nibot_index].write({
                    'processed': True,
                })
