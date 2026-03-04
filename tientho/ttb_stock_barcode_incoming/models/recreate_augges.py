import pytz
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api

class StockMove(models.Model):
    _inherit = 'stock.move'

    alter_is_cong_don = fields.Boolean(string="Là Cộng dồn (alter)", default=False, help="Đánh dấu là cộng dồn xuống augges nếu không thì là ghi đè")
    cong_don_move_id = fields.Many2one('stock.move', 'Move cộng dồn gốc (alter)')

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    alter_inventory_origin_id = fields.Many2one('stock.picking', 'Phiếu kiểm kê gốc (alter)', index=True)


    def find_alter_inventory_origin_id(self):
        for rec in self:
            if not rec.date_done:
                rec.alter_inventory_origin_id = False
                continue
            
            product_ids = set(rec.move_ids.filtered(lambda x: x.quantity > 0).product_id.ids)
            total_current_products = len(product_ids)

            if not total_current_products: 
                rec.alter_inventory_origin_id = False
                continue

            candidate_moves = self.env['stock.move'].search([
                ('product_id', 'in', list(product_ids)),
                ('picking_id', '!=', rec.id),
                ('picking_id.date_done', '!=', False),
                ('picking_id.date_done', '<', rec.date_done),
                ('picking_id.picking_type_id', '=', rec.picking_type_id.id),
                ('picking_id.period_inventory_id', '=', rec.period_inventory_id.id),
            ])

            candidate_pickings = candidate_moves.mapped('picking_id')

            valid_candidates = self.env['stock.picking']
            for candidate in candidate_pickings:
                candidate_product_ids = set(candidate.move_ids.filtered(lambda x: x.quantity > 0).product_id.ids)
                
                # Tính giao thoa (Intersection)
                common_products = product_ids.intersection(candidate_product_ids)
                count_common = len(common_products)

                overlap_percentage = (count_common / total_current_products) * 100
                
                # Nếu thỏa mãn >= 15%, thêm vào danh sách chờ xếp hạng
                if overlap_percentage >= 15:
                    valid_candidates |= candidate

            valid_candidates.sorted('date_done', reverse=True)

            rec.alter_inventory_origin_id = valid_candidates[:1] if valid_candidates else False

    def create_augges_inventory_counting_record(self, detail_datas, pair_conn=False, check_state=True):
        """
        Tách 2 loại âm, dương
        âm: tạo phiếu nhập
        dương: tạo phiếu xuất
        """
        self.ensure_one()

        if check_state and self.state != 'done':
            raise UserError('Phiếu chưa hoàn thành')

        _logger.info('Tạo lại phiếu nhập Augges cho phiếu kiểm kê odoo id: %s, name: %s', self.id, self.name)
        in_detail_datas = [item for item in detail_datas if item.get('quantity', 0) > 0]
        out_detail_datas = []
        for item in detail_datas:
            qty = item.get('quantity', 0)
            if qty < 0:
                # Tạo bản sao để tránh ảnh hưởng list gốc, đổi dấu thành dương
                new_item = item.copy()
                new_item['quantity'] = abs(qty)
                out_detail_datas.append(new_item)
        if not in_detail_datas and not out_detail_datas:
            _logger.info('Không có dữ liệu để gửi Augges cho phiếu kiểm kê odoo id: %s, name: %s', self.id, self.name)
            return

        owns_conn = False
        conn, cursor = None, None
        if pair_conn:
            conn = pair_conn
        else:
            conn = self.env['ttb.tools'].get_mssql_connection_send()
            owns_conn = True
        cursor = conn.cursor()
        
        master_data = self.prepare_augges_values()

        slnxm_id = False
        if in_detail_datas:
            master_data['ID_Nx'] = 52
            slnxm_id = self.env['ttb.augges'].create_slnx(master_data, in_detail_datas)
            self.id_augges = slnxm_id
        if out_detail_datas:
            master_data['ID_Nx'] = 82
            slnxm_id = self.env['ttb.augges'].create_slnx(master_data, out_detail_datas)
            self.id_augges = slnxm_id

        self.write({
            # 'sp_augges': value_sp,
            'is_sent_augges': True,
        })

        if owns_conn:
            conn.commit()
            cursor.close()
            conn.close()

        _logger.info('Hoàn thành tạo lại phiếu nhập Augges cho phiếu kiểm kê odoo id: %s, name: %s', self.id, self.name)


    def find_origin_move(self, move, path=None, alter=False):
        """
            Tìm move.product_id trong các sản phẩm của stock.picking.
            Nếu không có thì tìm trong phiếu gốc
        """
        path = path or self.env['stock.picking']

        # Kiểm tra tránh trường hợp đệ quy vô hạn
        if not self or self in path: return self.env['stock.move']

        # Tìm trong phiếu hiện tại
        origin = self.move_ids_without_package.filtered(lambda x: x.product_id == move.product_id and x.quantity > 0)
        
        # Nếu không thấy tìm trong phiếu gốc
        if not origin:
            origin_inventory_id = self.origin_inventory_id if not alter else self.alter_inventory_origin_id
            origin = origin_inventory_id.find_origin_move(move, path | self, alter)

        return origin

    def recreate_augges(self, augges_warehouse_id, period_inventory_id, list_date):
        warehouse = self.env['stock.warehouse'].search([('id_augges', '=', augges_warehouse_id)], limit=1)
        if not warehouse:
            raise UserError(f'Không tìm thấy kho Augges với ID: {augges_warehouse_id}')

        # Lấy múi giờ của người dùng (ví dụ: 'Asia/Ho_Chi_Minh') hoặc mặc định UTC
        user_tz = pytz.timezone(self.env.user.tz or 'UTC')

        for date_str in list_date:
            # 1. Chuyển string thành object Date (ví dụ: 2025-12-21)
            date_obj = fields.Date.from_string(date_str)
            
            # 2. Xác định điểm bắt đầu và kết thúc ngày theo múi giờ địa phương
            # Tạo datetime tại 00:00:00 của ngày đó trong múi giờ User
            local_start = user_tz.localize(fields.Datetime.to_datetime(date_obj))
            local_end = local_start + relativedelta(days=1)
            
            # 3. Chuyển ngược về UTC để so sánh với Database (Vì Odoo lưu Datetime là UTC)
            utc_start = local_start.astimezone(pytz.utc).replace(tzinfo=None)
            utc_end = local_end.astimezone(pytz.utc).replace(tzinfo=None)

            # 4. Search tối ưu: Đưa tất cả filter vào Domain (Database level)

            pickings = self.env['stock.picking'].search([
                ('date_done', '>=', utc_start),
                ('date_done', '<', utc_end),
                ('picking_type_id.code', '=', 'inventory_counting'),
                ('location_dest_id.warehouse_id', '=', warehouse.id),
                ('period_inventory_id', '=', period_inventory_id),
            ], order='date_done asc')

            for picking in pickings:
                detail_datas = []

                for line in picking.move_ids_without_package.filtered(lambda x: x.quantity > 0):
                    origin_move = picking.inventory_origin_id.find_origin_move(line) or picking.alter_inventory_origin_id.find_origin_move(line)

                    if origin_move:
                        detail_datas.append(line.prepare_augges_values(line.quantity - sum(origin_move.mapped('quantity'))))
                    elif line.alter_is_cong_don:
                        detail_datas.append(line.prepare_augges_values(line.quantity))
                    else:
                        detail_datas.append(line.prepare_augges_values(line.quantity-line.stock_qty))

                picking.create_augges_inventory_counting_record(detail_datas, pair_conn=False, check_state=False)



"""
SQL tính trường alter_is_cong_don

WITH moves AS (
    SELECT 
        sm.id AS move_id, 
        sm.product_id, 
        sp.id AS picking_id, 
        sp.date_done, 
        sp.picking_type_id, 
        sp.period_inventory_id
    FROM stock_move sm
    JOIN stock_picking sp ON sp.id = sm.picking_id
    JOIN stock_picking_type spt ON spt.id = sp.picking_type_id
    WHERE spt.code = 'inventory_counting'
      AND sp.date_done IS NOT NULL
      AND sp.period_inventory_id IS NOT NULL
      AND sm.quantity > 0
      and sp.picking_type_id != 2488
),
ranked_duplicates AS (
    SELECT 
        m1.move_id AS m1_move_id,
        m1.picking_id AS m1_picking_id,
        m1.date_done AS m1_date_done,
        -- Lấy toàn bộ thông tin từ m2
        m2.move_id AS m2_move_id,
        m2.picking_id AS m2_picking_id,
        m2.date_done AS m2_date_done,
        m2.picking_type_id AS m2_picking_type_id,
        m2.period_inventory_id AS m2_period_inventory_id,
        -- Đánh số thứ tự: m2 nào có date_done lớn nhất (gần m1 nhất) sẽ là 1
        ROW_NUMBER() OVER (
            PARTITION BY m1.move_id 
            ORDER BY m2.date_done DESC, m2.move_id DESC
        ) as rn
    FROM moves m1
    JOIN moves m2 ON m1.product_id = m2.product_id 
                 AND m1.move_id != m2.move_id
                 AND m1.period_inventory_id = m2.period_inventory_id -- Theo logic ảnh 3
                 AND m1.picking_type_id = m2.picking_type_id        -- Theo logic ảnh 3
    WHERE m2.date_done < m1.date_done
)
SELECT 
    m1_move_id,
    m1_picking_id,
    m1_date_done,
    m2_move_id,
    m2_picking_id,
    m2_date_done,
    m2_picking_type_id,
    m2_period_inventory_id
FROM ranked_duplicates
WHERE rn = 1; -- Chỉ lấy bản ghi m2 gần nhất cho mỗi m1
"""



                    






