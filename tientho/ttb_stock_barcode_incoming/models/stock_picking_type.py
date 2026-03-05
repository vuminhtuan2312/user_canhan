from odoo import fields, models, api
from odoo.osv import expression


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    code = fields.Selection(selection_add=[
        ('inventory_counting', 'Kiểm kê')
    ], ondelete={'inventory_counting': lambda recs: recs.write({'code': 'internal', 'active': False})})

    count_inventory_counting_ready = fields.Integer(compute='_compute_inventory_counting_count')
    count_inventory_recheck_ready = fields.Integer(compute='_compute_inventory_counting_count')
    def _compute_inventory_counting_count(self):
        # inventory_counting
        domains = {
            'count_inventory_counting_ready': [
                ('shelf_location', 'not ilike', 'HẬU KIỂM'),
                '|',
                ('user_id', '=', self.env.uid),
                ('support_user_ids', 'in', self.env.uid),
            ],
            'count_inventory_recheck_ready': [
                ('shelf_location', 'ilike', 'HẬU KIỂM'),
                '|',
                ('user_id', '=', self.env.uid),
                ('support_user_ids', 'in', self.env.uid),
            ],
        }
        for field_name, domain in domains.items():
            data = self.env['stock.picking']._read_group(domain +
                [('state', 'not in', ('done', 'cancel')), ('picking_type_id', 'in', self.ids)],
                ['picking_type_id'], ['__count'])
            count = {picking_type.id: count for picking_type, count in data}
            for record in self:
                record[field_name] = count.get(record.id, 0)

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        # Kiểm tra định dạng: Tên viết tắt kho\Tên loại hoạt động
        if name and ('\\' in name or '/' in name):
            domain = args or []
            separator = '\\' if '\\' in name else '/'
            parts = name.split(separator, 1)
            if len(parts) == 2:
                warehouse_code = parts[0].strip()
                picking_type_name = parts[1].strip()

                search_domain = expression.AND([
                    domain,
                    [
                        ('warehouse_id.code', '=', warehouse_code),
                        ('name', operator, picking_type_name)
                    ]
                ])
                picking_types = self.search(search_domain, limit=limit)

                if picking_types:
                    return [(pt.id, pt.display_name) for pt in picking_types]

        return super().name_search(name, args, operator, limit)


    def get_action_inventory_counting_tree_ready_kanban(self):
        self.ensure_one()
        action = self.env.ref('stock_barcode.stock_picking_action_kanban').sudo().read()[0]
        # Lọc phiếu sẵn sàng của loại chứng từ và kho tương ứng
        action['domain'] = [
            ('picking_type_id', '=', self.id),
            ('state', 'not in', ['done', 'cancel']),
            ('shelf_location', 'not like', 'HẬU KIỂM'),
            '|',
            ('user_id', '=', self.env.uid),
            ('support_user_ids', 'in', self.env.uid)
        ]
        action['search_view_id'] = [
            self.env.ref('ttb_stock_barcode_incoming.stock_barcode_action_search_inventory_counting').id,
            'search'
        ]
        return action

    def get_action_inventory_recheck_tree_ready_kanban(self):
        self.ensure_one()
        action = self.env.ref('stock_barcode.stock_picking_action_kanban').sudo().read()[0]

        action['domain'] = [
            ('picking_type_id', '=', self.id),
            ('state', 'not in', ['done', 'cancel']),
            ('shelf_location', 'like', 'HẬU KIỂM'),
            '|',
            ('user_id', '=', self.env.uid),
            ('support_user_ids', 'in', self.env.uid)
        ]
        action['search_view_id'] = [
            self.env.ref('ttb_stock_barcode_incoming.stock_barcode_action_search_inventory_counting').id,
            'search'
        ]
        return action

    def action_open_inventory_counting(self):
        action = self.env.ref(
            'ttb_stock_barcode_incoming.stock_barcode_action_kanban_inventory_counting'
        ).read()[0]

        allowed_branch_ids = self.env.user.ttb_branch_ids.ids

        action['domain'] = [
            ('code', '=', 'inventory_counting'),
            ('warehouse_id.is_inventory_counting', '=', True),
            ('warehouse_id.ttb_branch_id', 'in', allowed_branch_ids),
        ]

        return action