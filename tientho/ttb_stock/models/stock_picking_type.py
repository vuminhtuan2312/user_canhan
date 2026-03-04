from odoo import *


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    ttb_type = fields.Selection(related='warehouse_id.ttb_type')
    ttb_branch_id = fields.Many2one(related='warehouse_id.ttb_branch_id')

    def get_action_picking_tree_late(self):
        if self.code == 'incoming':
            return self._get_action('ttb_stock.action_picking_tree_incoming_late')
        return super().get_action_picking_tree_late()

    def get_action_picking_tree_backorder(self):
        if self.code == 'incoming':
            return self._get_action('ttb_stock.action_picking_tree_incoming_backorder')
        return super().get_action_picking_tree_backorder()

    def get_action_picking_tree_waiting(self):
        if self.code == 'incoming':
            return self._get_action('ttb_stock.action_picking_tree_incoming_waiting')
        return super().get_action_picking_tree_waiting()

    def get_action_picking_tree_ready(self):
        if self.code == 'incoming':
            return self._get_action('ttb_stock.action_picking_tree_incoming_ready')
        return super().get_action_picking_tree_ready()

    def get_stock_picking_action_picking_type(self):
        if self.code == 'incoming':
            return self._get_action('ttb_stock.stock_picking_action_incoming_picking_type')
        return super().get_stock_picking_action_picking_type()
