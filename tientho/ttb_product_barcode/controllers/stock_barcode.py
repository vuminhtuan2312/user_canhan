# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import fields, http, _
from odoo.http import request
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools import pdf, split_every
from odoo.tools.misc import file_open

from odoo.addons.stock_barcode.controllers.stock_barcode import StockBarcodeController


class StockBarcodeProductController(StockBarcodeController):

    def _get_barcode_pdfs(self, barcode_type, domain):
        barcode_pdfs = super()._get_barcode_pdfs(barcode_type, domain)
        if barcode_type != 'product_barcodes':
            return barcode_pdfs
        file_path = get_resource_path('ttb_product_barcode', 'static/img', 'product_barcodes.pdf')
        with file_open(file_path, "rb") as commands_file:
            barcode_pdfs.insert(0, commands_file.read())
        return barcode_pdfs

    def _try_open_product(self, barcode):
        """ If barcode represent a lot, open a form view to show all
        the details of this lot.
        """
        message = ''
        result = request.env['product.product'].with_context(active_test=False).search([
            ('barcode', '=', barcode),
        ], limit=1)
        
        if not result:
            message += ' Không tìm thấy theo barcode. Tìm theo default_code.'
            result = request.env['product.product'].with_context(active_test=False).search([
                ('default_code', '=', barcode),
            ], limit=1)

        if not result:
            message += ' Không tìm thấy theo default_code. Tìm theo barcode_vendor.'
            result = request.env['product.product'].with_context(active_test=False).search([
                ('barcode_vendor', '=', barcode),
            ], limit=1)
        if not result:
            message += ' Không tìm thấy theo barcode_vendor. Tìm theo barcode_k.'
            result = request.env['product.product'].with_context(active_test=False).search([
                ('barcode_k', '=', barcode),
            ], limit=1)

        if not result:
            message += ' Không tìm thấy.'
            request.env['scan.barcode.log'].create({'barcode': barcode, 'is_found': False, 'message': message})
            return {'warning': _('Không tìm thấy sản phẩm có mã barcode: %s', barcode)}
        
        message += f' Found. augges_id: {result.augges_id}, name: {result.name}'
        request.env['scan.barcode.log'].create({'barcode': barcode, 'is_found': True, 'message': message or False, 'product_id': result.id if result else False, 'res_id': result.id if result else False, 'model': 'product.product',})
        
        action = request.env.ref('ttb_product_barcode.action_product_product_form_custom').sudo().read()[0]
        action['res_id'] = result.product_tmpl_id.id
        action['context'] = {'default_barcode': barcode}


        return {
            'action': action
        }
        return False


    @http.route('/product_barcode/scan_from_main_menu', type='json', auth='user')
    def main_menu_product(self, barcode):
        """ Receive a barcode scanned from the main menu and return the product
            action (open an existing / new product) or warning.
        """
        return self._try_open_product(barcode)

        barcode_type = None
        nomenclature = request.env.company.nomenclature_id
        parsed_results = nomenclature.parse_barcode(barcode)
        if parsed_results and nomenclature.is_gs1_nomenclature:
            # search with the last feasible rule
            for result in parsed_results[::-1]:
                if result['rule'].type in ['product', 'package', 'location', 'dest_location']:
                    barcode_type = result['rule'].type
                    break

        # Alias support
        elif parsed_results:
            barcode = parsed_results.get('code', barcode)

        if not barcode_type:
            ret_open_picking = self._try_open_picking(barcode)
            if ret_open_picking:
                return ret_open_picking

            ret_open_picking_type = self._try_open_picking_type(barcode)
            if ret_open_picking_type:
                return ret_open_picking_type

        if request.env.user.has_group('stock.group_stock_multi_locations') and \
           (not barcode_type or barcode_type in ['location', 'dest_location']):
            ret_new_internal_picking = self._try_new_internal_picking(barcode)
            if ret_new_internal_picking:
                return ret_new_internal_picking

        if not barcode_type or barcode_type == 'product':
            ret_open_product_location = self._try_open_product_location(barcode)
            if ret_open_product_location:
                return ret_open_product_location

        if request.env.user.has_group('stock.group_production_lot') and \
           (not barcode_type or barcode_type == 'lot'):
            ret_open_lot = self._try_open_lot(barcode)
            if ret_open_lot:
                return ret_open_lot

        if request.env.user.has_group('stock.group_tracking_lot') and \
           (not barcode_type or barcode_type == 'package'):
            ret_open_package = self._try_open_package(barcode)
            if ret_open_package:
                return ret_open_package

        if request.env.user.has_group('stock.group_stock_multi_locations'):
            return {'warning': _('No picking or location or product corresponding to barcode %(barcode)s', barcode=barcode)}
        else:
            return {'warning': _('No picking or product corresponding to barcode %(barcode)s', barcode=barcode)}
