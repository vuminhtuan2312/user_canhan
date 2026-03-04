# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class CreateRecheckInventoryWizard(models.TransientModel):
    _name = "create.recheck.inventory.wizard"
    _description = "Xác nhận sinh phiếu kiểm kê lại"

    period_inventory_id = fields.Many2one(
        'period.inventory',
        string="Đợt kiểm kê",

    )
    reason = fields.Text(string='Lý do kiểm kê lại', required=True)

    def action_confirm_recheck(self):
        """Tạo phiếu kiểm kê lại từ wizard"""
        active_id = self.env.context.get('active_id')
        picking = self.env["stock.picking"].browse(active_id)

        if not picking.exists():
            raise UserError("Không tìm thấy phiếu kiểm kê gốc!")

        if picking.inventory_origin_id:
            if picking.inventory_origin_id.is_recheck_inventory_origin:
                raise UserError("Phiếu này đã có phiếu kiểm kê lại, không thể tạo thêm!")
            else:
                raise UserError("Bạn chỉ có thể kiểm kê lại ở phiếu Kiểm kê!!!")

        ids = []
        current = picking

        while current:
            ids.append(current.id)
            current = current.create_inventory_picking

        if len(ids) == 1:
            picking_ids_str = f"({ids[0]})"
        else:
            picking_ids_str = str(tuple(ids))
        sql = f"""
        UPDATE stock_picking
        SET state = 'cancel',
            shelf_location = COALESCE(shelf_location, '') || ' HUỶ KIỂM KÊ LẠI'
        WHERE id IN {picking_ids_str};

        UPDATE stock_move
        SET state = 'cancel'
        WHERE picking_id IN {picking_ids_str};

        UPDATE stock_move_line
        SET state = 'cancel'
        WHERE picking_id IN {picking_ids_str};
        """
        self.env.cr.execute(sql)
        recheck = self.env['stock.picking'].create({
            'picking_type_id': picking.picking_type_id.id,
            'location_id': picking.location_id.id,
            'location_dest_id': picking.location_dest_id.id,
            'scheduled_date': picking.scheduled_date,
            'shelf_location': 'KIỂM KÊ LẠI ' + (picking.shelf_location or picking.name),
            # 'min_products_to_check': picking.min_products_to_check,
            'is_recheck_inventory_origin': True,
            'note': f'Phiếu kiểm kê lại từ phiếu {picking.name}\nLý do: {self.reason}',
            'period_inventory_id': picking.period_inventory_id.id,
            'recheck_inventory_id': picking.id,
            'mch_category_id': picking.mch_category_id.id,
        })

        # Ghi log vào chatter của phiếu gốc
        picking.message_post(
            body=f"Đã tạo phiếu kiểm kê lại: {recheck.name}\nLý do: {self.reason}",
            message_type='notification',
            subtype_xmlid='mail.mt_note'
        )

        # Trả về action mở form view bản ghi vừa tạo
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': recheck.id,  # Bản ghi vừa tạo
            'target': 'current',  # mở cùng tab
        }
