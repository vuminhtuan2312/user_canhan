from odoo import api, fields, models, _
# from odoo.exceptions import ValidationError


class ProductProduct(models.Model):
    _inherit = "product.product"

    ttb_product_variant_image_ids = fields.One2many(
        string="Extra Variant Images",
        comodel_name='ttb.product.image',
        inverse_name='product_variant_id',
    )

    # def _get_stock_barcode_data(self):
    #     locations = self.env['stock.location']
    #     company_id = self.env.company.id
    #     package_types = self.env['stock.package.type']
    #     if not self:  # `self` is an empty recordset when we open the inventory adjustment.
    #         if self.env.user.has_group('stock.group_stock_multi_locations'):
    #             locations = self.env['stock.location'].search([('usage', 'in', ['internal', 'transit']), ('company_id', '=', company_id)], order='id')
    #         else:
    #             locations = self.env['stock.warehouse'].search([('company_id', '=', company_id)], limit=1).lot_stock_id
    #         self = self.env['stock.quant'].search([('user_id', '=?', self.env.user.id), ('location_id', 'in', locations.ids), ('inventory_date', '<=', fields.Date.today())])
    #         if self.env.user.has_group('stock.group_tracking_lot'):
    #             package_types = package_types.search([])

    #     data = self.with_context(display_default_code=False, barcode_view=True).get_stock_barcode_data_records()
    #     if locations:
    #         data["records"]["stock.location"] = locations.read(locations._get_fields_stock_barcode(), load=False)
    #     if package_types:
    #         data["records"]["stock.package.type"] = package_types.read(package_types._get_fields_stock_barcode(), load=False)
    #     data['line_view_id'] = self.env.ref('stock_barcode.stock_quant_barcode').id
    #     return data
