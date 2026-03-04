from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import timedelta, datetime

# {'branch_id': 'auggest_kho_id'} - Khu bán lẻ
BRANCH_WAREHOUSE_MAPS = {
    14: 8,
    15: 77,
    16: 25,
    17: 11,
    18: 2,
    19: 1,
    20: 39,
    21: 26,
    22: 16,
    23: 13,
    24: 57,
    25: 67,
    26: 58
}

class StockCheckSession(models.Model):
    _name = 'stock.check.session'
    _description = 'Phiên kiểm tồn'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(default=lambda self: self.env['ir.sequence'].next_by_code('stock.check.session'), string='Mã phiên', tracking=True)
    user_id = fields.Many2one(string='Người tạo', comodel_name='res.users', default=lambda self: self.env.uid, readonly=True, tracking=True)
    branch_id = fields.Many2one(string='Cơ sở', comodel_name='ttb.branch', required=True, tracking=True)
    create_date = fields.Datetime(string='Ngày tạo', readonly=True, tracking=True)
    line_ids = fields.One2many(comodel_name='stock.check.line', inverse_name='session_id', string='Danh sách sản phẩm')
    mch5_new_id = fields.Many2one(comodel_name='new.category.mch5', string='MCH5 mới', tracking=True)
    name_mch1 = fields.Char(string='MCH1', tracking=True)
    name_mch3 = fields.Char(string='MCH3', tracking=True)
    active = fields.Boolean(default=True)
    state = fields.Selection(
        string="Trạng thái kiểm",
        selection=[
            ('draft', 'Đang chờ'),
            ('done', 'Hoàn thành')
        ],
        default='draft',
        tracking=True
    )
    augges_state = fields.Selection([
        ('new', 'Chưa xử lý'), 
        ('recompute_qty', 'Đã tính lại lệch'), 
        ('finish', 'Đã tạo phiếu xuất/nhập Augges')
    ], 'Trạng thái Augges', default='new', tracking=True)
    user_by = fields.Many2one('res.users', string='Người thực hiện', tracking=True)
    done_date = fields.Datetime(string='Ngày hoàn thành', readonly=True, tracking=True)
    image_1920 = fields.Image(string="Ảnh sản phẩm", related='line_ids.image_1920', store=True)
    def action_import_barcode_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Import mã vạch',
            'res_model': 'import.barcode.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_session_id': self.id,
            }
        }

    def action_mark_done(self):
        for rec in self:
            if any(line.state_check == 'draft' for line in rec.line_ids):
                raise UserError("Vui lòng kiểm hết sản phẩm trong phiên kiểm.")

            rec.state = 'done'
            rec.done_date = fields.Datetime.now()


    def action_qty_recomputed(self):
        to_updates = self.filtered(lambda x: x.augges_state == 'new')
        if not to_updates: return
        to_updates.line_ids.action_qty_recomputed()
        to_updates.augges_state = 'recompute_qty'

class StockCheckLine(models.Model):
    _name = 'stock.check.line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Dòng kiểm tồn'

    session_id = fields.Many2one(comodel_name='stock.check.session', string='Phiên kiểm', required=True, readonly=1, tracking=True)
    product_id = fields.Many2one(comodel_name='product.product', string='Sản phẩm', required=True, readonly=1, tracking=True)
    stock_qty = fields.Float(string='Số lượng tồn', readonly=1, tracking=True)
    user_by = fields.Many2one('res.users', string='Người thực hiện', related='session_id.user_by', store=True, tracking=True)
    qty_real = fields.Float(string='Số lượng thực tế', readonly=1, tracking=True)
    diff_qty = fields.Float(string='Lệch', compute='_compute_diff_qty', store=True, readonly=1, help='Số lượng thực tế trừ số lượng lý thuyết', tracking=True)
    barcode = fields.Char(string='Mã vạch', tracking=True)
    state = fields.Selection(string='Trạng thái', related='session_id.state', store=True, readonly=1, tracking=True)
    can_check_inventory = fields.Boolean(
        compute='_compute_can_check_inventory'
    )
    image_1920 = fields.Image(string="Ảnh sản phẩm",compute="_compute_image_1920",store=False)
    last_qty_add = fields.Float(string="SL bổ sung cuối", readonly=1, tracking=True)
    highlight_qty_class = fields.Char(
        compute='_compute_highlight_qty_class',
        string='Qty Color Class',
        store=True,
        tracking=True
    )
    user_perform = fields.Char(string='Người thực hiện', readonly=1, tracking=True)
    code_ncc = fields.Char(string='Mã nhà cung cấp', tracking=True)
    reference_code = fields.Char(string='Mã tham chiếu', tracking=True)
    done_date = fields.Datetime(string="Ngày hoàn thành", related='session_id.done_date', store=True, readonly=1, tracking=True)
    note = fields.Char(string="Ghi chú", tracking=True)
    categ_id = fields.Char(string='MCH5 đề xuất', readonly=1, tracking=True)
    
    diff_qty_recomputed = fields.Float('Lệch tính lại', readonly=1, help='Số lượng thực tế trừ số lượng lý thuyết', tracking=True)
    time_done_real = fields.Datetime(string='Thời gian hoàn thành thực')
    state_check = fields.Selection(
        string='Trạng thái kiểm từng dòng', selection=[
            ('draft', 'Chưa kiểm'),
            ('done', 'Đã kiểm')
        ],
        default='draft', readonly=1)
    def _compute_image_1920(self):
        for line in self:
            image = self.env['ttb.product.image'].search(
                [('product_tmpl_id', '=', line.product_id.product_tmpl_id.id)],
                limit=1
            )
            line.image_1920 = image.image_1920 if image else False

    def augges_recompute_diff_qty(self, id_kho, id_hang):
        done_date = self.done_date
        if not done_date:
            done_date = fields.Datetime.now()
        done_date += timedelta(hours=7)
        
        nam = done_date.strftime("2026")
        ngay_dau_nam = done_date.strftime("260101")
        done_date_str = done_date.strftime("%Y-%m-%d %H:%M:%S")
        done_date_sngay = done_date.strftime("%y%m%d")

        # Tính tồn kho theo ngày, giờ với đầu kỳ tính từ đầu năm
        query = f"""
            SELECT
                ID_Kho,
                ID_Hang,
                SUM(Sl_Cky) AS Sl_Ton
            FROM
                (
                    SELECT
                        HtK.ID_Kho,
                        HtK.ID_Hang,
                        SUM(HtK.So_Luong) AS Sl_Cky
                    FROM
                        HtK
                    WHERE
                        HtK.Nam = {nam}
                        AND HtK.ID_DV = 0
                        AND HtK.Mm = 9
                        AND HtK.ID_Kho IS NOT NULL
                    GROUP BY
                        HtK.ID_Kho,
                        HtK.ID_Hang

                    UNION ALL
                    SELECT
                        SlNxM.ID_Kho,
                        SlNxD.ID_Hang,
                        SUM (
                            CASE WHEN DmNx.Ma_Ct IN ('NK', 'NM', 'PN', 'NS', 'NL') THEN SlNxD.So_Luong ELSE - SlNxD.So_Luong END
                        ) AS Sl_Cky
                    FROM
                        SlNxD
                        LEFT JOIN SlNxM ON SlNxD.ID = SlNxM.ID
                        LEFT JOIN DmNx ON SlNxM.ID_Nx = DmNx.ID
                    WHERE
                        SlNxM.SNgay >= '{ngay_dau_nam}'
                        AND (SlNxM.SNgay < '{done_date_sngay}' OR (SlNxM.SNgay = '{done_date_sngay}' AND SlNxM.InsertDate <= '{done_date_str}'))
                        AND SlNxM.ID_DV = 0
                        AND SlNxD.ID_Kho IS NOT NULL
                        AND SlNxD.ID_Hang IS NOT NULL
                    GROUP BY
                        SlNxM.ID_Kho,
                        SlNxD.ID_Hang

                    UNION ALL
                    SELECT
                        SlBlM.ID_Kho,
                        SlBlD.ID_Hang,
                        SUM(- SlBlD.So_Luong) AS Sl_Cky
                    FROM
                        SlBlD
                        LEFT JOIN SlBlM ON SlBlD.ID = SlBlM.ID
                    WHERE
                        SlBlM.SNgay >= '{ngay_dau_nam}'
                        AND SlBlM.SNgay <= '{done_date_sngay}' AND SlBlM.InsertDate <= '{done_date_str}'
                        AND SlBlM.ID_DV = 0
                        AND ISNULL(SlBlD.ID_Kho, SlBlM.ID_Kho) IS NOT NULL
                        AND SlBlD.ID_Hang IS NOT NULL
                    GROUP BY
                        SlBlM.ID_Kho,
                        SlBlD.ID_Hang

                    UNION ALL
                    SELECT
                        SlDcD.ID_KhoX AS ID_Kho,
                        SlDcD.ID_Hang,
                        SUM(- SlDcD.So_Luong) AS Sl_Cky
                    FROM
                        SlDcD
                        LEFT JOIN SlDcM ON SlDcD.ID = SlDcM.ID
                    WHERE
                        SlDcM.SNgay >= '{ngay_dau_nam}'
                        AND SlDcM.SNgay <= '{done_date_sngay}' AND SlDcM.InsertDate <= '{done_date_str}'
                        AND SlDcM.ID_DV = 0
                        AND SlDcD.ID_KhoX IS NOT NULL
                    GROUP BY
                        SlDcD.ID_KhoX,
                        SlDcD.ID_Hang

                    UNION ALL
                    SELECT
                        SlDcD.ID_KhoN AS ID_Kho,
                        SlDcD.ID_Hang,
                        SUM(SlDcD.So_Luong) AS Sl_Cky
                    FROM
                        SlDcD
                        LEFT JOIN SlDcM ON SlDcD.ID = SlDcM.ID
                    WHERE
                        SlDcM.SNgay >= '{ngay_dau_nam}'
                        AND SlDcM.SNgay <= '{done_date_sngay}' AND SlDcM.InsertDate <= '{done_date_str}'
                        AND SlDcM.ID_DV = 0
                        AND SlDcD.ID_KhoN IS NOT NULL
                    GROUP BY
                        SlDcD.ID_KhoN,
                        SlDcD.ID_Hang
                ) AS Dt_Hang
            WHERE ID_Kho = {id_kho} AND ID_Hang = {id_hang}
            GROUP BY
                ID_Kho,
                ID_Hang
        """

        if self.session_id.branch_id.id != 15 and (self.done_date <= datetime(2025, 7, 20) or self.done_date >= datetime(2025, 8, 6)):
            if self.diff_qty_recomputed != self.diff_qty:
                self.diff_qty_recomputed = self.diff_qty
        else:
            conn = self.env['ttb.tools'].get_mssql_connection()
            cursor = conn.cursor()
            cursor.execute(query)
            columns = [column[0] for column in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

            sl_ton = 0
            for result in results:
                sl_ton = float(result['Sl_Ton'])

            new_value = self.qty_real - sl_ton
            if self.diff_qty_recomputed != new_value:
                self.diff_qty_recomputed = new_value 


    def action_qty_recomputed(self):
        for rec in self:
            branch_id = rec.session_id.branch_id.id
            id_kho = BRANCH_WAREHOUSE_MAPS.get(branch_id)
            id_hang = rec.product_id.augges_id

            if not id_kho or not id_hang:
                raise UserError('Không có thông tin kho hoặc sản phẩm')

            rec.augges_recompute_diff_qty(id_kho, id_hang)

    @api.depends('qty_real')
    def _compute_highlight_qty_class(self):
        for rec in self:
            if rec.qty_real > 0:
                rec.highlight_qty_class = 'badge bg-success'
            else:
                rec.highlight_qty_class = 'badge bg-secondary'

    def _compute_can_check_inventory(self):
        self.can_check_inventory = False
        if self.session_id.user_by.id == self.env.uid:
            self.can_check_inventory = True

    def open_check_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Cập nhật tồn',
            'res_model': 'check.inventory.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_line_id': self.id,
                'default_qty_real': self.qty_real
            }
        }

    @api.depends('qty_real', 'stock_qty')
    def _compute_diff_qty(self):
        for line in self:
            line.diff_qty = (line.qty_real or 0.0) - (line.stock_qty or 0.0)

    def open_add_qty_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Nhập bổ sung',
            'res_model': 'add.qty.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_line_id': self.id,
            }
        }
    def open_adjust_mch5_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Điều chỉnh MCH5',
            'res_model': 'adjust.mch5.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_line_id': self.id,
            }
        }
