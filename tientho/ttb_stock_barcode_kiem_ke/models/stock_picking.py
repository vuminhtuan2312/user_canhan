from odoo import models, fields, api, _
import logging

from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    warehouse_dest_id = fields.Many2one('stock.warehouse', string="Kho đích")
    create_inventory_picking_ids = fields.One2many('stock.picking', 'origin_id', string='Phiếu điều chuyển')
    origin_id = fields.Many2one('stock.picking', string='Phiếu gốc hậu kiểm lại')
    can_create_inventory_picking = fields.Boolean(string='Cho phép tạo phiếu điều chuyển nhập')
    transfer_state = fields.Selection([
            ('remain', 'Còn tồn'),
            ('done', 'Hết')
        ],
        string='Trạng thái điều chuyển',
        compute='_compute_transfer_state',
        store=True
    )

    @api.depends('move_ids_without_package.remaining_transfer_quantity',
                 'picking_type_id.code')
    def _compute_transfer_state(self):
        for picking in self:
            picking.transfer_state = False

            if picking.picking_type_id.code == 'incoming':
                moves = picking.move_ids_without_package

                if moves:
                    picking.transfer_state = (
                        'remain'
                        if any(m.remaining_transfer_quantity > 0 for m in moves)
                        else 'done'
                    )
    def action_move_to_shelves(self):
        temporary_record = self.env['move.to.shelves.template'].create({
            'stock_picking_id': self.id,
            'branch_ids': self.env['res.users'].browse(self.env.uid).ttb_branch_ids.ids,
            'warehouse_id': self.warehouse_dest_id.id if self.warehouse_dest_id else False,
        })

        return {
            'name': 'Di chuyển kệ',
            'type': 'ir.actions.act_window',
            'res_model': 'move.to.shelves.template',
            'view_mode': 'form',
            'target': 'new',
            'res_id': temporary_record.id,
        }

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        for picking in self:
            if picking.inventory_origin_id and picking.can_create_inventory_picking:
                new_stock_picking = picking.copy({
                    'location_id':     picking.location_dest_id.id,
                    'location_dest_id': picking.inventory_origin_id.warehouse_dest_id.lot_stock_id.id,
                    'can_create_inventory_picking': False
                })
                for line in picking.inventory_origin_id.move_ids:
                    sum_quantity = sum(self.env['stock.move'].search([('product_id', '=', line.product_id.id),
                                                                  ('picking_id', 'in', picking.inventory_origin_id.create_inventory_picking_ids.ids)
                                                                  ]).mapped('quantity'))
                    line.write({
                        'remaining_transfer_quantity': line.quantity - sum_quantity
                    })
            source_picking = picking.inventory_origin_id

            for move in picking.move_ids_without_package:
                source_move = source_picking.move_ids_without_package.filtered(
                    lambda m: m.product_id == move.product_id
                )

                if not source_move:
                    continue

                remaining_qty = source_move.remaining_transfer_quantity

                if remaining_qty < 0:
                    raise UserError(_(
                        "Cảnh báo: Số lượng điều chuyển vượt quá số lượng nhập kho!\n\n"
                        "Chi tiết: Mã sản phẩm [%s] vượt quá %s sản phẩm để điều chuyển. "
                        "Vui lòng kiểm tra lại."
                    ) % (move.product_id.default_code or move.product_id.display_name, abs(remaining_qty)))

        return res
