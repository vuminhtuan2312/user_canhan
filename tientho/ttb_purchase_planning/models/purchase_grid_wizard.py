from odoo import models, fields, api, _
from datetime import datetime, timedelta

class PurchaseGridWizard(models.TransientModel):
    _name = 'purchase.grid.wizard'
    _description = 'Purchase Grid Wizard'

    product_ids = fields.Many2many(
        'product.template',
        'purchase_grid_wizard_product_rel',
        'wizard_id',
        'product_id',
        string='Sản phẩm',
    )
    branch_id = fields.Many2one('ttb.branch', string='Cơ sở', required=True)
    # mch_id = fields.Many2one('product.category', string='MCH', required=True)
    past_cycles = fields.Integer(string="Số chu kỳ quá khứ", default=0)
    future_cycles = fields.Integer(string="Số chu kỳ tương lai", default=0)
    mch_id = fields.Many2many('product.category',
                                       string='MCH',
                                       store=True, readonly=False, tracking=True,
                                       )
    # mch_id_1 = fields.Many2one('product.category',
    #                                    string='MCH1',
    #                                    domain="[('parent_id', '=', False),('category_level', '=', 1)]",
    #                                    store=True, readonly=False, tracking=True,
    #                                    )
    # mch_id_2 = fields.Many2one('product.category',
    #                                    string='MCH2',
    #                                    domain="[('parent_id', '=?', mch_id_1),('category_level', '=', 2)]",
    #                                    store=True, readonly=False, tracking=True,
    #                                    )
    # mch_id_3 = fields.Many2one('product.category',
    #                                    string='MCH3',
    #                                    domain="[('parent_id', '=?', mch_id_2),('category_level', '=', 3)]",
    #                                    store=True, readonly=False, tracking=True,
    #                                    )
    # mch_id_4 = fields.Many2one('product.category',
    #                                    string='MCH4',
    #                                    domain="[('parent_id', '=?', mch_id_3),('category_level', '=', 4)]",
    #                                    store=True, readonly=False, tracking=True,
    #                                    )
    # mch_id_5 = fields.Many2one('product.category',
    #                                    string='MCH5',
    #                                    domain="[('parent_id', '=?', mch_id_4),('category_level', '=', 5)]",
    #                                    store=True, readonly=False, tracking=True,
    #                                    )

    # def onchange_level(self, level):
    #     categ_id = self[f'mch_id_{level}']
    #     # Gán lại cha. Chỉ cần gán lại 1 cấp sau đó sẽ có hiệu ứng dây chuyền
    #     if level > 1 and categ_id:
    #         self[f'mch_id_{level - 1}'] = categ_id.parent_id
    #
    #     # Gán cấp con bằng False nếu không thỏa mãn quan hệ cha con.
    #     # Gán tất cả để tính được mch_id
    #     for level_up in range(level + 1, 6):
    #         key = f'mch_id_{level_up}'
    #         key_parent = f'mch_id_{level_up - 1}'
    #
    #         if not self[key_parent] or (self[key] and self[key].parent_id != self[key_parent]):
    #             self[key] = False
    #
    #     for level_categ in range(5, 0, -1):
    #         key = f'mch_id_{level_categ}'
    #         if self[key] or level_categ == 1:
    #             break
    #
    # @api.onchange('mch_id_1')
    # def onchange_level_1(self):
    #     self.onchange_level(1)
    #
    # @api.onchange('mch_id_2')
    # def onchange_level_2(self):
    #     self.onchange_level(2)
    #
    # @api.onchange('mch_id_3')
    # def onchange_level_3(self):
    #     self.onchange_level(3)
    #
    # @api.onchange('mch_id_4')
    # def onchange_level_4(self):
    #     self.onchange_level(4)
    #
    # @api.onchange('mch_id_5')
    # def onchange_level_5(self):
    #     self.onchange_level(5)

    # def action_create_grid(self):
    #     """Tạo dự trù mua hàng"""
    #     self.ensure_one()
    #
    #     # Trả về action để mở view grid với context
    #     return {
    #         'type': 'ir.actions.client',
    #         'tag': 'purchase_grid_view',
    #         'context': {
    #             'default_product_ids': self.product_ids.ids,
    #             'default_product_names': [p.name for p in self.product_ids],
    #             'default_product_codes': [p.default_code for p in self.product_ids],
    #             'default_branch_id': self.branch_id.id,
    #             'default_branch_name': self.branch_id.name,
    #             'default_mch_id': self.mch_id.ids,
    #             'default_mch_id_name': [p.name for p in self.mch_id],
    #             'default_past_cycles': self.past_cycles,
    #             'default_future_cycles': self.future_cycles,
    #         }
    #     }
    def action_create_grid(self):
        self.ensure_one()
        # Product = self.env['product.template']
        stock_move = self.env['stock.move']
        stock_quant = self.env['stock.quant']
        product_product = self.env['product.product']

        today = fields.Date.context_today(self)
        start_of_week = today - timedelta(days=today.weekday())
        periods = []
        period_labels = []
        for i in range(-self.past_cycles, self.future_cycles + 1):
            period_start = start_of_week + timedelta(weeks=i)
            period_end = period_start + timedelta(days=6)
            label = f"{period_start.strftime('%d/%m')} - {period_end.strftime('%d/%m')}"
            periods.append((period_start, period_end, label))
            period_labels.append(label)

        # Xác định index của kỳ hiện tại
        current_period_index = self.past_cycles

        data = {}
        for product in self.product_ids:
            data[product.id] = {}
            product_variants = product_product.search([('product_tmpl_id', '=', product.id)])
            quants = stock_quant.search([
                ('product_id', 'in', product_variants.ids),
                ('location_id.warehouse_id.ttb_branch_id', '=', self.branch_id.id),
            ])
            qty_available = sum(quants.mapped('quantity'))
            opening_current = qty_available
            # Tính nhập xuất từng kỳ
            period_moves = []
            for period_start, period_end, label in periods:
                # Tổng nhập trong kỳ
                incoming_moves = stock_move.search([
                    ('product_id', '=', product.id),
                    ('state', '=', 'done'),
                    ('picking_id.ttb_branch_id', '=', self.branch_id.id),
                    ('picking_id.picking_type_code', '=', 'incoming'),
                    ('date', '>=', period_start),
                    ('date', '<=', period_end),
                ])
                qty_in = sum(m.product_uom_qty for m in incoming_moves)
                # Tổng xuất trong kỳ
                outgoing_moves = stock_move.search([
                    ('product_id', '=', product.id),
                    ('state', '=', 'done'),
                    ('picking_id.ttb_branch_id', '=', self.branch_id.id),
                    ('picking_id.picking_type_code', '=', 'outgoing'),
                    ('date', '>=', period_start),
                    ('date', '<=', period_end),
                ])
                qty_out = sum(m.product_uom_qty for m in outgoing_moves)
                period_moves.append({'in': qty_in, 'out': qty_out})

            # Tính tồn kho cho từng kỳ, bắt đầu từ kỳ hiện tại
            openings = [0] * len(periods)
            closings = [0] * len(periods)
            openings[current_period_index] = opening_current
            closings[current_period_index] = opening_current + period_moves[current_period_index]['in'] - period_moves[current_period_index]['out']

            # Tính các kỳ tương lai
            for i in range(current_period_index + 1, len(periods)):
                openings[i] = closings[i - 1]
                closings[i] = openings[i] + period_moves[i]['in'] - period_moves[i]['out']

            # Tính các kỳ quá khứ
            for i in range(current_period_index - 1, -1, -1):
                closings[i] = openings[i + 1]
                openings[i] = closings[i] - period_moves[i]['in'] + period_moves[i]['out']

            # Gán vào data
            for i, (period_start, period_end, label) in enumerate(periods):
                data[product.id][label] = {
                    'opening': openings[i],
                    'in': period_moves[i]['in'],
                    'out': period_moves[i]['out'],
                    'closing': closings[i],
                }

        return {
            'type': 'ir.actions.client',
            'tag': 'purchase_grid_view',
            'context': {
                'default_product_ids': self.product_ids.ids,
                'default_product_names': [p.name for p in self.product_ids],
                'default_product_codes': [p.default_code for p in self.product_ids],
                'default_branch_id': self.branch_id.id,
                'default_branch_name': self.branch_id.name,
                'default_mch_id': self.mch_id.ids,
                'default_mch_id_name': [p.name for p in self.mch_id],
                'default_past_cycles': self.past_cycles,
                'default_future_cycles': self.future_cycles,
                'periods': period_labels,
                'data': data,
            }
        }

    def action_create_purchase_orders(self, wizard_id, supplier_data):
        """
        Tạo đơn mua hàng từ dự trù
        wizard_id: ID của wizard instance
        supplier_data: {
            'supplier_id': [
                {'product_id': 123, 'quantity': 10},
                {'product_id': 456, 'quantity': 5}
            ]
        }
        """
        wizard = self.browse(wizard_id)
        PurchaseOrder = self.env['purchase.order']
        PurchaseOrderLine = self.env['purchase.order.line']
        
        created_orders = []
        
        for supplier_id, products in supplier_data.items():
            # Tạo đơn mua hàng
            order_vals = {
                'partner_id': int(supplier_id),
                'origin': f'Dự trù mua hàng - {wizard.branch_id.name}',
                'date_order': fields.Datetime.now(),
            }
            
            purchase_order = PurchaseOrder.create(order_vals)
            
            # Tạo các dòng đơn hàng
            for product_data in products:
                line_vals = {
                    'order_id': purchase_order.id,
                    'product_id': product_data['product_id'],
                    'product_qty': product_data['quantity'],
                    'price_unit': 0,  # Giá sẽ được nhập sau
                }
                PurchaseOrderLine.create(line_vals)
            
            created_orders.append(purchase_order.id)
        
        return created_orders

    def create_po_simple(self, branch_id, supplier_data):
        """Method đơn giản để tạo đơn mua hàng"""
        try:
            PurchaseOrder = self.env['purchase.order']
            PurchaseOrderLine = self.env['purchase.order.line']
            Branch = self.env['ttb.branch']
            
            created_orders = []
            branch = Branch.browse(branch_id)
            
            for supplier_id, products in supplier_data.items():
                # Tạo đơn mua hàng
                order_vals = {
                    'partner_id': int(supplier_id),
                    'origin': f'Dự trù mua hàng - {branch.name}',
                    'date_order': fields.Datetime.now(),
                    'ttb_branch_id': branch_id,
                    'picking_type_id': branch_id
                }
                
                purchase_order = PurchaseOrder.create(order_vals)
                
                # Tạo các dòng đơn hàng
                for product_data in products:
                    line_vals = {
                        'order_id': purchase_order.id,
                        'product_id': product_data['product_id'],
                        'product_qty': product_data['quantity'],
                        'price_unit': 0,
                    }
                    PurchaseOrderLine.create(line_vals)
                
                created_orders.append(purchase_order.id)
            
            return created_orders
        except Exception as e:
            return {'error': str(e)}

    def test_method(self):
        """Method test đơn giản"""
        return {'status': 'success', 'message': 'Test method working'}

    def get_suppliers(self):
        """Lấy danh sách nhà cung cấp"""
        suppliers = self.env['res.partner'].search([
            ['supplier_rank', '>', 0]
        ])
        return [{'id': s.id, 'name': s.name} for s in suppliers]

class PurchaseOrderCreator(models.Model):
    _name = 'purchase.order.creator'
    _description = 'Purchase Order Creator'

    @api.model
    def create_purchase_orders(self, branch_id, supplier_data):
        """
        Tạo đơn mua hàng từ dữ liệu được truyền vào
        branch_id: ID của chi nhánh
        supplier_data: {
            'supplier_id': [
                {'product_id': 123, 'quantity': 10},
                {'product_id': 456, 'quantity': 5}
            ]
        }
        """
        PurchaseOrder = self.env['purchase.order']
        PurchaseOrderLine = self.env['purchase.order.line']
        Branch = self.env['ttb.branch']
        
        created_orders = []
        branch = Branch.browse(branch_id)
        
        for supplier_id, products in supplier_data.items():
            # Tạo đơn mua hàng
            order_vals = {
                'partner_id': int(supplier_id),
                'origin': f'Dự trù mua hàng - {branch.name}',
                'date_order': fields.Datetime.now(),
            }
            
            purchase_order = PurchaseOrder.create(order_vals)
            
            # Tạo các dòng đơn hàng
            for product_data in products:
                line_vals = {
                    'order_id': purchase_order.id,
                    'product_id': product_data['product_id'],
                    'product_qty': product_data['quantity'],
                    'price_unit': 0,  # Giá sẽ được nhập sau
                }
                PurchaseOrderLine.create(line_vals)
            
            created_orders.append(purchase_order.id)
        
        return created_orders