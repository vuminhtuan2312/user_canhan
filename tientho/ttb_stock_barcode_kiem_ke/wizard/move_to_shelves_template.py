from datetime import timedelta
from odoo import api, fields, models
from odoo.exceptions import UserError


class MoveToShelvesTemplate(models.TransientModel):
    _name = 'move.to.shelves.template'

    stock_picking_id = fields.Many2one('stock.picking', string='Phiếu vận chuyển', required=True)
    branch_ids = fields.Many2many('ttb.branch', string='Cơ sở')
    branch_id = fields.Many2one('ttb.branch', string='Cơ sở đích', compute='_compute_branch_id', store=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Kho')

    @api.depends('stock_picking_id', 'stock_picking_id.location_dest_id')
    def _compute_branch_id(self):
        for rec in self:
            if rec.stock_picking_id and rec.stock_picking_id.location_dest_id:
                # Lấy warehouse từ location_dest_id
                warehouse = rec.stock_picking_id.location_dest_id.warehouse_id
                if warehouse and warehouse.ttb_branch_id:
                    rec.branch_id = warehouse.ttb_branch_id
                else:
                    rec.branch_id = False
            else:
                rec.branch_id = False

    def action_confirm(self):
        unfinished_line = self.stock_picking_id.move_ids.filtered(lambda line: line.remaining_transfer_quantity )
        if not unfinished_line:
            raise UserError("Tất cả các dòng đã được hoàn thành điều chuyển, không thể tạo phiếu điều chuyển mới.")
        dict_prd_quant = {}
        for line in unfinished_line:
            dict_prd_quant[line.product_id.id] = line.remaining_transfer_quantity

        warehouse_dest_id = self.stock_picking_id.location_dest_id.warehouse_id
        if not warehouse_dest_id:
            raise UserError("Không tìm thấy kho của địa điểm đích.")
        new_picking_type = self.env['stock.picking.type'].search([('code', '=', 'internal'), ('warehouse_id', '=', warehouse_dest_id.id), ('name', 'ilike', 'nội bộ')], limit=1)
        if not new_picking_type:
            raise UserError("Không tìm thấy loại vận chuyển nội bộ cho kho đã chọn.")

        new_stock_picking = self.stock_picking_id.copy({
            'picking_type_id': new_picking_type.id,
            'location_id':     self.stock_picking_id.location_dest_id.id,
            'location_dest_id': warehouse_dest_id.transit_location.id,
            'inventory_origin_id': self.stock_picking_id.id,
            'can_create_inventory_picking': True,
        })
        for line in new_stock_picking.move_ids:
            line.write({
                'quantity': dict_prd_quant[line.product_id.id],
            })
        self.stock_picking_id.write({
            'create_inventory_picking_ids': [(4, new_stock_picking.id)],
            'warehouse_dest_id': self.warehouse_id.id
        })

        return {
            'name': 'Di chuyển kệ',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'target': 'curent',
            'res_id': new_stock_picking.id,
        }