from odoo import models, fields, api
from collections import defaultdict

class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    amount_total_all = fields.Monetary(
        string='Tổng tiền các phiếu',
        compute='_compute_amount_total_all',
        currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        'res.currency', string='Currency', compute='_compute_currency_id', store=False
    )

    @api.depends('company_id')
    def _compute_currency_id(self):
        for rec in self:
            rec.currency_id = rec.company_id.currency_id

    def _compute_amount_total_all(self):
        """
        Compute the total amount for all non-cancelled pickings of these picking types.

        This method is optimized by:
        1. Filtering moves by their 'state' ('done'), which is a stored field,
           to efficiently query the database.
        2. Fetching all necessary raw data (price_unit, quantity_done) in a single
           `search_read` call.
        3. Performing the final aggregation in Python to avoid the N+1 problem.
        """

        self.amount_total_all = 0.0
        if not self.ids:
            return

        domain = [
            ('picking_type_id', 'in', self.ids),
            ('state', '=', 'done'),
        ]

        move_data = self.env['stock.move'].search_read(
            domain=domain,
            fields=['picking_type_id', 'price_unit']
        )

        # Bước 4: Tính toán và gom nhóm trong Python.
        totals_by_type = defaultdict(float)

        for move in move_data:
            picking_type_id = move['picking_type_id'][0]
            line_value = move['price_unit']
            totals_by_type[picking_type_id] += line_value

        for rec in self:
            rec.amount_total_all = totals_by_type.get(rec.id, 0.0)

    def get_action_picking_tree_ready_kanban(self):
        self.ensure_one()
        action = self.env.ref('stock_barcode.stock_picking_action_kanban').sudo().read()[0]
        # Lọc phiếu sẵn sàng của loại chứng từ và kho tương ứng
        action['domain'] = [
            ('picking_type_id', '=', self.id),
            ('state', 'in', ['assigned', 'draft']),
            ('picking_type_id.warehouse_id', '=', self.warehouse_id.id)
        ]
        # action['name'] = self.name
        return action

    def get_action_picking_tree_done_kanban(self):
        self.ensure_one()
        action = self.env.ref('stock_barcode.stock_picking_action_kanban').sudo().read()[0]
        # Lọc đúng phiếu đã hoàn thành của loại chứng từ và kho tương ứng
        action['domain'] = [
            ('picking_type_id', '=', self.id),
            ('state', '=', 'done'),
            ('picking_type_id.warehouse_id', '=', self.warehouse_id.id)
        ]
        action['name'] = 'Đã hoàn thành'
        return action

    def get_action_picking_tree_backorder_kaban(self):
        self.ensure_one()
# Lấy action act_window của model stock.picking
        action = self.env.ref('ttb_stock.action_picking_tree_incoming_backorder').sudo().read()[0]
        # Domain chỉ dùng trường của stock.picking
        action['domain'] = [
            ('picking_type_id', '=', self.id),
            ('backorder_id', '!=', False),
            ('picking_type_code', '=', 'incoming'),
        ]
        action['name'] = 'Đơn hàng chậm trễ'
        return action
