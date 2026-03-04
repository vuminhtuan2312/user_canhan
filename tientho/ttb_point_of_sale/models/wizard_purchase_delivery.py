from odoo import models, fields, api
from collections import defaultdict
class ReportPurchaseDelivery(models.TransientModel):
    _name = 'wizard.purchase.delivery'
    _description = 'Báo cáo giao hàng thời vụ'

    branch = fields.Many2many('ttb.branch', string='Cơ sở')
    date_start = fields.Date('Từ ngày', required=True)
    date_end = fields.Date('Đến ngày', required=True)

    def action_confirm(self):
        for wizard in self:
            domain = [
                ('order_id.date_order', '>=', wizard.date_start),
                ('order_id.date_order', '<=', wizard.date_end),
                ('order_id.state', 'in', ['purchase', 'done']),
            ]
            if wizard.branch:
                domain.append(('order_id.ttb_branch_id', 'in', wizard.branch.ids))

            lines = self.env['purchase.order.line'].search(domain)

            # Group theo (branch_id, partner_id)
            grouped_data = defaultdict(list)
            for line in lines:
                branch_id = line.order_id.ttb_branch_id.id if line.order_id.ttb_branch_id else False
                partner_id = line.order_id.partner_id.id if line.order_id.partner_id else False
                grouped_data[(branch_id, partner_id)].append(line)

            # Xóa dữ liệu cũ
            self.env['report.purchase.delivery'].search([]).unlink()

            for (branch_id, partner_id), group_lines in grouped_data.items():
                branch = self.env['ttb.branch'].browse(branch_id) if branch_id else False
                partner = self.env['res.partner'].browse(partner_id) if partner_id else False

                so_luong_dat = sum(l.product_qty for l in group_lines)
                gia_tri_dat = sum(l.price_total for l in group_lines)
                so_luong_giao = sum(l.qty_received for l in group_lines)
                avg_price = sum(l.price_unit for l in group_lines) / len(group_lines) if group_lines else 0.0
                gia_tri_giao = so_luong_giao * avg_price
                ty_le_giao = so_luong_giao / so_luong_dat if so_luong_dat else 0.0

                valid_days = [
                    abs((l.date_planned - l.order_id.date_approve).days)
                    for l in group_lines
                    if l.date_planned and l.order_id.date_approve
                ]
                ngay_tb = sum(valid_days) / len(valid_days) if valid_days else 0

                # Tạo line chi tiết
                lines_data = []
                for l in group_lines:
                    lines_data.append((0, 0, {
                        'product_id': l.product_id.id,
                        'qty_order': l.product_qty,
                        'qty_received': l.qty_received,
                        'price_unit': l.price_unit,
                        'value_received': l.qty_received * l.price_unit,
                    }))

                self.env['report.purchase.delivery'].create({
                    'branch': branch.name,
                    'supplier_code': partner.ref,
                    'supplier_name': partner.name,
                    'qty_order': so_luong_dat,
                    'amount_order': gia_tri_dat,
                    'qty_received': so_luong_giao,
                    'amount_received': gia_tri_giao,
                    'rate_delivery': ty_le_giao,
                    'avg_delivery_days': ngay_tb,
                    'line_ids': lines_data,
                })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Báo cáo giao hàng thời vụ',
            'res_model': 'report.purchase.delivery',
            'view_mode': 'list,form',
            'target': 'current',
            'views': [(self.env.ref('ttb_point_of_sale.view_report_purchase_delivery_list').id, 'list'), (self.env.ref('ttb_point_of_sale.view_report_purchase_delivery_form').id, 'form')]
        }
    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}

