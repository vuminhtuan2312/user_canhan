from odoo import *
from odoo.exceptions import UserError

class InventoryResultLine(models.Model):
    _inherit = 'inventory.result.lines'

    dummy_id = fields.Char(compute='_compute_dummy_id', inverse='_inverse_dummy_id')

    def _compute_dummy_id(self):
        self.dummy_id = ''

    def _inverse_dummy_id(self):
        pass

    def _get_stock_barcode_data(self):
        session_lines = self.env['inventory.session.lines'].sudo().search([('user_count_id', '=', self.env.user.id)])
        if not session_lines:
            raise UserError('Không có quầy nào đang phân công cho bạn')

        # inventory_result_lines = self.search([
        #     ('inventory_result_id.state', '=', 'count_process'),
        #     ('create_uid', '=', self.env.user.id)
        # ])
        inventory_result_lines = self.env['inventory.result.lines']

        # Fetch all implied products in `self`
        products = self.product_id

        uoms = products.uom_id
        # If UoM setting is active, fetch all UoM's data.
        if self.env.user.has_group('uom.group_uom'):
            uoms |= self.env['uom.uom'].search([])

        # Fetch `stock.location`
        locations = self.inventory_result_id.pid_location_id | session_lines.pid_location_id
        companies = self.env.company

        data = {
            "records": {
                "inventory.session.lines": session_lines.read(session_lines._get_fields_stock_barcode(), load=False),
                "inventory.result.lines": inventory_result_lines.read(self._get_fields_stock_barcode(), load=False),
                # "stock.picking.type": self.picking_type_id.read(self.picking_type_id._get_fields_stock_barcode(), load=False),
                # "stock.move": moves.read(moves._get_fields_stock_barcode(), load=False),
                # "stock.move.line": move_lines.read(move_lines._get_fields_stock_barcode(), load=False),
                "product.product": products.read(products._get_fields_stock_barcode(), load=False),
                "stock.location": locations.read(locations._get_fields_stock_barcode(), load=False),
                "uom.uom": uoms.read(uoms._get_fields_stock_barcode(), load=False),
                "res.company": companies.read(['name']),
            },
            "nomenclature_id": [self.env.company.nomenclature_id.id],
            "user_id": self.env.user.id,
            # Không hiển thị tồn kho hiện tại
            "show_quantity_count": False
            
        }
        return data


    def _get_fields_stock_barcode(self):
        return [
            'product_id',
            'quantity_count',
        ]

    def action_validate(self):
        # làm tạm:
        inventory_result_lines = self.search([
            ('inventory_result_id.state', '=', 'count_process'),
            ('create_uid', '=', self.env.user.id)
        ])
        inventory_result_lines.inventory_result_id.state = 'count_done'

    def barcode_write(self, vals):
        user_id = self.env.user.id
        result_ids = []

        for val in vals:
            pid_location_id = val[2]['location_id']
            pid_location = self.env['stock.location'].browse(pid_location_id)
            inventory_session_line_user_count = self.env['inventory.session.lines'].sudo().search([('pid_location_id', '=', pid_location_id), ('user_count_id', '=', user_id), ('inventory_session_id.state', '=', 'ready')])
            inventory_session_line_check_count = self.env['inventory.session.lines']

            if len(inventory_session_line_user_count) > 1:
                raise UserError('Bạn đang được phân công nhiều phiếu kiểm kê, vui lòng kiểm tra lại')
            elif not inventory_session_line_user_count:
                #Check hậu kiểm
                inventory_session_line_check_count = self.env['inventory.session.lines'].sudo().search([('pid_location_id', '=', pid_location_id), ('user_check_id', '=', user_id), ('inventory_session_id.state', '=', 'ready')])
                if not inventory_session_line_check_count:
                    raise UserError('Bạn không có phiếu kiểm kê, vui lòng kiểm tra lại')
                elif len(inventory_session_line_check_count) > 1:
                    raise UserError('Bạn đang được phân công nhiều phiếu hậu kiểm, vui lòng kiểm tra lại')

            #Check xem quầy đã kiểm kê chưa:
            inventory_result = inventory_session_line_user_count.inventory_result_id
            if inventory_session_line_user_count.status != 'cancel' and inventory_result and len(pid_location.stock_location_detail_line_ids) == len(inventory_result.lines_ids):
                raise UserError('Quầy đã được kiểm kê')
            # Check xem quầy đã kiểm hậu kiểm chưa:
            if inventory_session_line_check_count:
                inventory_result = inventory_session_line_check_count.inventory_result_id
                if inventory_session_line_check_count.status != 'cancel' and inventory_result and all(inventory_result.lines_ids.filtered(lambda x: x.quantity_check > 0 and x.check)):
                    raise UserError('Quầy đã được hậu kiểm')

            line_vals = {
                'product_id': val[2]['product_id'],
                'quantity_count': val[2]['inventory_quantity'],
            }
            stock_location_detail_line = self.env['stock.location.detail.lines'].search([
                '&',
                '|',
                ('destination_location_id', '=', val[2]['location_id']),
                ('stock_location_id', '=', val[2]['location_id']),
                ('product_id', '=', val[2]['product_id'])
            ], limit=1)
            if stock_location_detail_line:
                line_vals['stock_location_detail_lines_id'] = stock_location_detail_line.id

            if val[0] == 1:
                result_id = val[1]
                self.browse(result_id).write(line_vals)
                result_ids.append(result_id)
            elif val[0] == 0:
                if inventory_result and inventory_result.state == "cancel":
                    inventory_result = self.env['inventory.result'].create({
                        'name': 'Kết quả kiểm kê',
                        'branch_id': inventory_session_line_user_count.branch_id.id,
                        'pid_location_id': pid_location_id,
                        'user_count_id': user_id,
                        'user_check_id': inventory_session_line_user_count.user_check_id.id,
                        'session_line_id': inventory_session_line_user_count.id,
                        'session_id': inventory_session_line_user_count.inventory_session_id.id,
                    })
                    inventory_session_line_user_count.inventory_result_id = inventory_result.id
                elif not inventory_result:
                    inventory_result = self.env['inventory.result'].create({
                        'name': 'Kết quả kiểm kê',
                        'branch_id': inventory_session_line_user_count.branch_id.id,
                        'pid_location_id': pid_location_id,
                        'user_count_id': user_id,
                        'user_check_id': inventory_session_line_user_count.user_check_id.id,
                        'session_line_id': inventory_session_line_user_count.id,
                        'session_id': inventory_session_line_user_count.inventory_session_id.id,
                    })
                    inventory_session_line_user_count.inventory_result_id = inventory_result.id
                
                line_vals['inventory_result_id'] = inventory_result.id

                existing_line = self.env['inventory.result.lines'].search([
                    ('inventory_result_id', '=', inventory_result.id),
                    ('product_id', '=', line_vals['product_id']),
                ], limit=1)
                if existing_line:
                    existing_line.quantity_count = line_vals.get('quantity_count', 0)
                    result = existing_line
                else:
                    result = self.create(line_vals)
                result_ids.append(result.id)
        return self.browse(result_ids)._get_stock_barcode_data()


class InventoryResultLine(models.Model):
    _inherit = 'inventory.result'


    @api.model
    def filter_on_barcode(self, barcode):
        reuslt_id = self.search([('name', 'like', barcode)])
        domain = []
        if reuslt_id:
            domain = [('id', 'in', reuslt_id.ids)]
        action = self.env["ir.actions.actions"]._for_xml_id('ttb_stock_barcode_kiem_ke.inventory_result_action_kanban')
        action['domain'] = domain
        return {'action': action}
