from odoo import *
from odoo import api, Command, fields, models, SUPERUSER_ID, _
from odoo.exceptions import UserError, ValidationError
import math
import logging

_logger = logging.getLogger(__name__)


class PrioritizeBranch(models.TransientModel):
    _name = 'prioritize.branch'
    _description = 'Prioritize Branch'

    po_id = fields.Many2one('purchase.order', string='Đơn mua hàng', required=True)
    stock_picking_id = fields.Many2one('stock.picking', string='Phiếu nhập kho', required=True)
    goods_distribution_ticket_template_id = fields.Many2one('goods.distribution.ticket.template', string='Mẫu phiếu chia hàng',)
    prioritize_branch_ids = fields.One2many('prioritize.branch.line', 'prioritize_branch_id', string='Chi tiết ưu tiên')

    @api.onchange('goods_distribution_ticket_template_id')
    def onchange_goods_distribution_ticket_template_id(self):
        if self.goods_distribution_ticket_template_id:
            lines_to_create = []
            for line in self.goods_distribution_ticket_template_id.goods_distribution_ticket_template_line_ids:
                line_values = {
                    'branch_id': line.branch_id.id,
                    'prioritize': line.prioritize,
                    'proportion': line.proportion,
                }
                lines_to_create.append((0, 0, line_values))
            if lines_to_create:
                self.prioritize_branch_ids = [(5, 0, 0)] + lines_to_create
        else:
            self.prioritize_branch_ids = [(5, 0, 0)]

    def _calculate_qty_balance(self, quantity):
        qty_balance = quantity
        for line in self.prioritize_branch_ids:
            qty_balance = qty_balance - math.floor(quantity * line.proportion / 100)
        return qty_balance


    def _calculate_qty_per_branch(self, qty_balance, prioritize_branch):
        if qty_balance == 0: return 0, 0
        if qty_balance > 0 and prioritize_branch == 0:
            raise UserError(_('Phát sinh số dư sản phẩm sau khi chia đều sản phẩm. Vui lòng thiết lập thứ tự ưu tiên cho các cơ sở!'))
        qty_per_branch = qty_balance // prioritize_branch
        qty_qty_balance = qty_balance % prioritize_branch
        return qty_per_branch, qty_qty_balance

    def button_confirm(self):
        self.ensure_one()
        line_values = []
        prioritize_branch = len(self.prioritize_branch_ids.filtered(lambda x: x.prioritize > 0))
        #chia hàng theo từng sản phẩm
        for line in self.stock_picking_id.move_ids:
            #số dư sau khi chia
            qty_balance = self._calculate_qty_balance(line.product_uom_qty)
            #tính số lượng chia đều cho các cơ sở ưu tiên và số lượng còn dư sẽ chia theo thứ tự ưu tiên
            qty_per_branch, qty_per_branch_prioritize = self._calculate_qty_per_branch(qty_balance, prioritize_branch)

            #chia hàng cho các cơ sở
            for branch in self.prioritize_branch_ids:
                if branch.prioritize > 0:
                    product_qty = math.floor(line.product_uom_qty * branch.proportion / 100) + qty_per_branch + 1 if qty_per_branch_prioritize > 0 else math.floor(line.product_uom_qty * branch.proportion / 100) + qty_per_branch
                    qty_per_branch_prioritize = qty_per_branch_prioritize - 1 if qty_per_branch_prioritize > 0 else 0
                else:
                    product_qty = math.floor(line.product_uom_qty * branch.proportion / 100)

                line_value = {
                    'product_id': line.product_id.id,
                    'branch_id': branch.branch_id.id,
                    'product_qty': product_qty,
                    'actual_qty': product_qty,
                    'po_line_id': line.purchase_line_id.id,
                }
                line_values.append((0, 0, line_value))
        ticket = self.env['goods.distribution.ticket'].create({
            'po_id': self.po_id.id,
            'stock_picking_id': self.stock_picking_id.id,
            'goods_distribution_ticket_line_ids': line_values,
        })
        self.stock_picking_id.has_ticket = True

        return {
            'name': 'Phiếu chia hàng cơ sở',
            'type': 'ir.actions.act_window',
            'res_model': 'goods.distribution.ticket',
            'view_mode': 'form',
            'res_id': ticket.id,
            'target': 'current',
        }

class PrioritizeBranchLine(models.TransientModel):
    _name = 'prioritize.branch.line'
    _description = 'Prioritize Branch Line'
    _order = 'prioritize, branch_id'

    prioritize_branch_id = fields.Many2one('prioritize.branch', string='Phiếu ưu tiên', required=True, ondelete='cascade')
    branch_id = fields.Many2one('ttb.branch', string='Chi nhánh')
    prioritize = fields.Integer(string='Thứ tự ưu tiên')
    proportion = fields.Float(string='Tỷ lệ (%)')

