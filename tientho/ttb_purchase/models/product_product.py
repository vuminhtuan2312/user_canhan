from odoo import *
class ProductProduct(models.Model):
    _inherit='product.product'


    def _get_filtered_sellers_no_date(self, partner_id=False, quantity=0.0, uom_id=False, params=False):
        self.ensure_one()
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        sellers_filtered = self._prepare_sellers(params)
        sellers = self.env['product.supplierinfo']
        for seller in sellers_filtered:
            # Set quantity in UoM of seller
            quantity_uom_seller = quantity
            if quantity_uom_seller and uom_id and uom_id != seller.product_uom:
                quantity_uom_seller = uom_id._compute_quantity(quantity_uom_seller, seller.product_uom)

            if partner_id and seller.partner_id not in [partner_id, partner_id.parent_id]:
                continue
            if quantity is not None and tools.float_compare(quantity_uom_seller, seller.min_qty, precision_digits=precision) == -1:
                continue
            if seller.product_id and seller.product_id != self:
                continue
            sellers |= seller
        return sellers
