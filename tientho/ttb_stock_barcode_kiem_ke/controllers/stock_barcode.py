# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime
from odoo import http
from odoo.http import request
from odoo.addons.stock_barcode.controllers.stock_barcode import StockBarcodeController


class TtbStockBarcodeController(StockBarcodeController):

    @http.route()
    def get_specific_barcode_data(self, **kwargs):
        user_id = request.env.user
        result = super().get_specific_barcode_data(**kwargs)
        if result.get('stock.location', False):
            pid_location_id = result.get('stock.location')[0].get('id')
            pid_location = request.env['stock.location'].browse(pid_location_id)
            #Check xem có cài đặt kiểm kê
            inventory_session_line_user_count = request.env['inventory.session.lines'].sudo().search([('pid_location_id', '=', pid_location_id), ('user_count_id', '=', user_id.id), ('inventory_session_id.state', '=', 'ready')])
            inventory_session_line_check_count = request.env['inventory.session.lines']
            msg = ''
            if len(inventory_session_line_user_count) > 1:
                msg = 'Bạn đang được phân công nhiều phiếu kiểm kê, vui lòng kiểm tra lại'
            elif not inventory_session_line_user_count:
                #Check hậu kiểm
                inventory_session_line_check_count = request.env['inventory.session.lines'].sudo().search([('pid_location_id', '=', pid_location_id), ('user_check_id', '=', user_id.id), ('inventory_session_id.state', '=', 'ready')])
                if not inventory_session_line_check_count:
                    msg = 'Bạn không có phiếu kiểm kê, vui lòng kiểm tra lại'
                elif len(inventory_session_line_check_count) > 1:
                    msg = 'Bạn đang được phân công nhiều phiếu hậu kiểm, vui lòng kiểm tra lại'
            #Check xem quầy đã kiểm kê chưa:
            if inventory_session_line_user_count:
                inventory_result = inventory_session_line_user_count.inventory_result_id
                line = inventory_session_line_user_count[0]
                if line.status != 'cancel' and inventory_result and len(
                        pid_location.stock_location_detail_line_ids) == len(inventory_result.lines_ids):
                    msg = 'Quầy đã được kiểm kê'
            # Check xem quầy đã kiểm hậu kiểm chưa:
            if inventory_session_line_check_count:
                inventory_result = inventory_session_line_check_count.inventory_result_id
                if inventory_session_line_check_count.status != 'cancel' and inventory_result and all(inventory_result.lines_ids.filtered(lambda x: x.quantity_check > 0 and x.check)):
                    msg = 'Quầy đã được hậu kiểm'
            if msg:
                result['stock.location'] = []
        return result

    # @http.route()
    # def get_barcode_data(self, model, res_id):
    #     old_res_id = res_id
    #     if model == 'stock.picking' and res_id:
    #         picking = request.env[model].search([('state', '=', 'assigned')], limit=1)
    #         if picking:
    #             res_id = picking.id
    #     res = super().get_barcode_data(model, res_id)
    #     res_id = old_res_id
    #     return res
