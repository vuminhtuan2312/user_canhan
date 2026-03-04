from odoo import Command, models, fields, api, _, http
from odoo.http import request
from odoo.addons.stock_barcode.controllers.stock_barcode import StockBarcodeController

class StockBarcodeIncomingController(StockBarcodeController):

    @http.route('/stock_barcode/get_barcode_data', type='json', auth='user')
    def get_barcode_data(self, model, res_id):
        result = super().get_barcode_data(model, res_id)
        if result['data']['records']['stock.picking']:
            stock = request.env['stock.picking'].browse(result['data']['records']['stock.picking'][0].get('id'))
            if stock.picking_type_id.code == 'inventory_counting':
                if result['data']['records']['stock.move.line']:
                    for line in result['data']['records']['stock.move.line']:
                        move_id = line.get("move_id")
                        if move_id:
                            move = request.env['stock.move'].browse(move_id)
                            picking_name = move.picking_id.name
                            if 'kcl' in picking_name:
                                line['kcl'] = True
                            else:
                                line['kcl'] = False
                            if move.picking_id.inventory_origin_id:
                                diff_qty = sum(move.picking_id.inventory_origin_id.move_ids_without_package.filtered(lambda l: l.product_id == move.product_id).mapped('diff_qty'))
                            else:
                                diff_qty = move.diff_qty
                            line['diff_qty'] = diff_qty
                        line['create_user_login'] = request.env['res.users'].browse(line['create_uid']).login
                        line['login_user'] = request.env.user.login

                if result['data']['records']['stock.picking']:
                        if not stock.move_line_ids and stock.move_ids_without_package:
                            for line in stock.move_ids_without_package:
                                for move_line in line.move_line_ids:
                                    move_line.write({'picking_id': stock.id})
        return result
