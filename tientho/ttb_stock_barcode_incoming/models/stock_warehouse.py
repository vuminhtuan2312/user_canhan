from odoo import models, fields, _


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    ic_type_id = fields.Many2one('stock.picking.type', 'Hoạt động Kiểm kê', check_company=True, copy=False)
    ic_loc_id = fields.Many2one('stock.location', string='Địa điểm kiểm kê', check_company=True)

    is_inventory_counting = fields.Boolean('Kho kiểm kê', default=True)

    # các hàm bắt chước module mrp
    # Lưu ý: hàm _create_missing_locations
    # Lưu ý: hàm: _create_or_update_sequences_and_picking_types này khả năng hữu dụng
    # Ví dụ:
    # warehouses = self.env['stock.warehouse'].search([('pos_type_id', '=', False)])
    #     for warehouse in warehouses:
    #         new_vals = warehouse._create_or_update_sequences_and_picking_types()
    #         warehouse.write(new_vals)

    def _get_locations_values(self, vals, code=False):
        values = super()._get_locations_values(vals, code=code)
        def_values = self.default_get(['company_id'])
        code = vals.get('code') or code or ''
        code = code.replace(' ', '').upper()
        
        company_id = vals.get('company_id', def_values['company_id'])
        values.update({
            'ic_loc_id': {
                'name': _('Kiểm kê'),
                'active': True,
                'usage': 'internal',
                'barcode': self._valid_barcode(code + 'KK', company_id)
            },
        })
        return values

    def _get_picking_type_create_values(self, max_sequence):
        data, next_sequence = super()._get_picking_type_create_values(max_sequence)

        data.update({
            'ic_type_id': {
                'name': _('Kiểm kê'),
                'code': 'inventory_counting',
                # 'use_create_lots': True,
                # 'use_existing_lots': True,
                'default_location_src_id': self.env.ref('stock.stock_location_suppliers').id,
                'default_location_dest_id': self.ic_loc_id.id,
                'sequence': next_sequence + 1,
                'sequence_code': 'KK',
                'company_id': self.company_id.id,
            },
        })

        return data, max_sequence + 1

    def _get_picking_type_update_values(self):
        data = super()._get_picking_type_update_values()
        data.update({
            'ic_type_id': {
                'active': self.active,
                'code': 'inventory_counting',
                'barcode': self.code.replace(" ", "").upper() + "KK",
                'default_location_src_id': self.env.ref('stock.stock_location_suppliers').id,
                'default_location_dest_id': self.ic_loc_id.id,
            },
        })
        return data

    def _get_sequence_values(self, name=False, code=False):
        values = super()._get_sequence_values(name=name, code=code)
        values.update({
            'ic_type_id': {'name': _('%(name)s Sequence Kiểm kê', name=self.name), 'prefix': self.code + '/' + (self.ic_type_id.sequence_code or 'KK') + '/', 'padding': 5, 'company_id': self.company_id.id},
        })
        return values
