import json
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class BrandMapper(models.Model):
    _name = 'tax.branch.mapper'
    _description = 'Bảng map cơ sở (kho) cho hoá đơn'

    name = fields.Char('Tên')
    ttb_branch_id = fields.Many2one('ttb.branch', 'Cơ sở')
    type = fields.Selection([('buy', 'Đầu vào'), ('sale', 'Đầu ra')])

class TaxOutputInvoiceLine(models.Model):
    _name = 'tax.output.invoice.line'
    _description = 'Dòng hoá đơn đầu ra (Thuế)'
    _order = 'invoice_date, invoice_symbol, invoice_number, sequence'
    _rec_name = 'product_id'

    # invoice_id = fields.Many2one('tax.output.invoice', string='Hoá đơn', ondelete='cascade', required=True)
    sequence = fields.Integer(string='STT', default=10)

    invoice_number = fields.Char(string='Số hoá đơn')
    invoice_symbol = fields.Char(string='Ký hiệu hoá đơn')
    invoice_date = fields.Date(string='Ngày hoá đơn')

    product_id = fields.Many2one('product.sale.item', 'Sản phẩm đầu ra', auto_join=True, index=True)
    quantity = fields.Float(string='Số lượng', required=True)
    price_unit = fields.Float('Đơn giá')
    uom = fields.Char(string='Đơn vị tính')
    ttb_branch_id = fields.Many2one('ttb.branch', 'Cơ sở')
    price_total = fields.Float('Thành tiền')
    in_price_total = fields.Float('Thành tiền đầu vào')
    
    buy_product_id = fields.Many2one('product.sale.item', 'Sản phẩm đầu vào', auto_join=True, index=True)
    buy_product_rate = fields.Float(string='Tỉ lệ tương hợp')
    buy_product_level = fields.Char(string='MCH tương hợp')
    # buy_product_skip = fields.Integer(string='Số sản phẩm bỏ qua')
    inventory_quantity = fields.Float(string='Tồn kho tại thời điểm bán')

    best_buy_product_id = fields.Many2one('product.sale.item', 'SP tương hợp cao nhất')
    best_buy_product_rate = fields.Float(string='Tỉ lệ tương hợp SP best')
    best_inventory_quantity = fields.Float(string='Tồn kho SP tương hợp cao nhất')

    state = fields.Selection([('new', 'Chưa xử lý'), ('mapped', 'Đã ghép sản phẩm đầu vào')], 'Trạng thái xử lý', default='new')
    result_state = fields.Selection([
        ('ok', 'Ghép thành công'), 
        ('no_product', 'Không tìm thấy SP đầu vào phù hợp'),
        ('manual_merge', 'Đã ghép thủ công'),
        ('empty', 'Số lượng bán <= 0'),
        ('no_out_product', 'SP đầu ra không xác định'),
        ('no_branch', 'Cơ sở không xác định'),
    ], 'Kết quả xử lý')
    branch_type = fields.Selection([('origin', 'Đầu vào cùng cơ sở'), ('ho', 'Đầu vào từ kho chung')])
    map_info = fields.Text('Thông tin ghép')

    price_rate = fields.Float('Biên lợi nhuận', help='Bằng giá bán chia giá nhập')

    in_line_ids = fields.One2many('ttb.inout.invoice.mapper', 'out_line_id', 'Các dòng hoá đơn đầu vào')

    manual_in_line_id = fields.Many2one('ttb.nimbox.invoice.line', 'Ghép thủ công', compute='compute_manual_in_line_id', inverse='inverse_manual_in_line_id')
    def compute_manual_in_line_id(self):
        manual_choices = self.env['tax.manual.choice'].search([
            ('choice_type', '=', 'merge'),
            ('out_line_id', 'in', self.ids),
        ])

        choice_mapper = {choice.out_line_id.id: choice.in_line_id for choice in manual_choices}
        for rec in self:
            if rec.id in choice_mapper:
                rec.manual_in_line_id = choice_mapper.get(rec.id)

    def inverse_manual_in_line_id(self):
        for rec in self:
            in_line_id = rec.manual_in_line_id

            domain = [('id', '=', in_line_id.id)] + rec._domain_manual_in_line_id()
            in_line_id = self.env['ttb.nimbox.invoice.line'].search(domain, limit=1)
            if not in_line_id:
                continue

            old_merge = self.env['tax.manual.choice'].search([
                ('in_line_id', '=', in_line_id.id),
                ('out_line_id', '=', rec.id),
            ])

            if old_merge:
                raise UserError(f'Dòng {rec.id} đã được lựa chọn ghép thủ công rồi. Vui lòng xoá lựa chọn cũ trước khi thay đổi!')

            self.env['tax.manual.choice'].create({
                'choice_type': 'merge',
                'in_line_id': in_line_id.id,
                'out_line_id': rec.id,
            })

            self.env['ttb.inout.invoice.mapper'].create({
                'in_line_id': in_line_id.id, 
                'out_line_id': rec.id, 
                'quantity': rec.quantity, 
                'diff_rate': 10
            })

            in_line_id.write({
                'soluong_used': in_line_id.soluong_used - rec.quantity,
            })

    domain_manual_in_line_id = fields.Binary('Domain dòng hoá đơn đầu vào (lựa chọn thủ công)', compute='_compute_domain_manual_in_line_id')
    def _domain_manual_in_line_id(self):
        ho_branch = self.env['ttb.branch'].search([('code', 'ilike', 'ho')], limit=1)
        return [
                ('soluong_remain', '>', 0),
                ('price_unit', '<', self.price_unit),
                ('category_id_level_1', '=', self.category_id_level_1.id),
                ('invoice_date', '<=', self.invoice_date),
                '|', 
                    '|', # R1
                    ('ttb_branch_id', '=', self.ttb_branch_id.id),
                    ('nimbox_invoice_id.in_branch_id', '=', self.ttb_branch_id.id),
                    '&', # R2
                    ('ttb_branch_id', '=', ho_branch.id),
                    ('nimbox_invoice_id.in_branch_id', '=', False)
            ]
    def _compute_domain_manual_in_line_id(self):
        for rec in self:
            rec.domain_manual_in_line_id = rec._domain_manual_in_line_id()

    category_id_level_1 = fields.Many2one('product.category.training', 'MCH 1', index=True, related='product_id.category_id_level_1', store=True, readonly=False)
    category_id_level_2 = fields.Many2one('product.category.training', 'MCH 2', index=True, related='product_id.category_id_level_2', store=True, readonly=False)
    category_id_level_3 = fields.Many2one('product.category.training', 'MCH 3', index=True, related='product_id.category_id_level_3', store=True, readonly=False)
    category_id_level_4 = fields.Many2one('product.category.training', 'MCH 4', index=True, related='product_id.category_id_level_4', store=True, readonly=False)
    category_id_level_5 = fields.Many2one('product.category.training', 'MCH 5', index=True, related='product_id.category_id_level_5', store=True, readonly=False)

    active = fields.Boolean(default=True)

    available_in_line_ids = fields.Many2many(
        'ttb.nimbox.invoice.line', 
        string='Các dòng đầu vào thoả mãn',
        compute='_compute_in_line_ids',
    )
    def _compute_in_line_ids(self):
        for rec in self:
            in_lines = self.env['ttb.nimbox.invoice.line'].search([
                ('soluong_remain', '>', 0),
                ('price_unit', '<', rec.price_unit),
                ('category_id_level_1', '=', rec.category_id_level_1.id),
                ('invoice_date', '<=', rec.invoice_date),

                ('nimbox_invoice_id.use_state', '=', True),
                ('nimbox_invoice_id.trang_thai_hd', 'in', ('1','2','5')),
                
                '|',
                ('ttb_branch_id', '=', rec.ttb_branch_id.id),
                ('nimbox_invoice_id.in_branch_id', '=', rec.ttb_branch_id.id),
            ])
        
            rec.available_in_line_ids = in_lines.ids

    available_ho_in_line_ids = fields.Many2many(
        'ttb.nimbox.invoice.line', 
        string='Các dòng HO đầu vào thoả mãn',
        compute='_compute_ho_in_line_ids',
    )
    def _compute_ho_in_line_ids(self):
        ho_branch = self.env['ttb.branch'].search([('code', 'ilike', 'ho')], limit=1)
        for rec in self:
            in_lines = self.env['ttb.nimbox.invoice.line'].search([
                ('soluong_remain', '>', 0),
                ('price_unit', '<', rec.price_unit),
                ('category_id_level_1', '=', rec.category_id_level_1.id),
                ('invoice_date', '<=', rec.invoice_date),
                ('ttb_branch_id', '=', ho_branch.id),
                ('nimbox_invoice_id.in_branch_id', '=', False),
                ('nimbox_invoice_id.use_state', '=', True),
                ('nimbox_invoice_id.trang_thai_hd', 'in', ('1','2','5')),
            ])
        
            rec.available_ho_in_line_ids = in_lines.ids

    def init_inventory_quantity(self, g_data):
        # """
        # Hàm này đọc hoá đơn bán ra đã được ghép và giảm số lượng tồn tương ứng.
        # Bổ sung logic phân bổ vào biến buy_datas để nhảy con trỏ cũng như biết lượng tồn còn bao nhiêu

        # 1/12/25: Bỏ qua hàm init này, chỉ ghép tiếp không cần quan tâm dữ liệu đã ghép.
        # """
        # datas = self.search([('ttb_branch_id', '!=', False), ('state', '=', 'mapped'), ('buy_product_id', '!=', False)])
        # _logger.info('Trừ tồn %s dòng data cũ' % len(datas))
        # for data in datas:
        #     g_data['quantity'][data.ttb_branch_id.id][g_data['p_index'][data.buy_product_id.id]] -= data.quantity

        #     # Phân bổ
        #     self.reconcil_one_product(g_data, data, data.buy_product_id.id, save_db=False)

        # Load lại dữ liệu ttb.inproduct.outproduct.mapper để đánh dấu: sp vào - số sp ra đã được ghép
        if g_data['in_out_product_limit'] > 0:
            lines = self.env['ttb.inproduct.outproduct.mapper'].sudo().search([])
            for line in lines:
                g_data['map_products'][line.in_product_id.id][line.out_product_id.id] = True
        
        # Load lại dữ liệu phân bổ ttb.inout.invoice.mapper để đánh dấu: line vào - số sản phẩm ra đã được ghép
        # if g_data['in_out_invoice_product_limit'] > 0:
        inout_lines = self.env['ttb.inout.invoice.mapper'].sudo().search([])
        for line in inout_lines:
            g_data['map_line_products'][line.in_line_id.id]['out_product_ids'][line.out_product_id.id] = line.quantity

    def get_inventory_quantity(self, data, g_data):
        """
        Hàm này đọc hoá đơn đầu vào và tăng tồn tương ứng vào biến g_data['quantity']
        Ngoài ra lưu danh sách hoá đơn đầu vào tương ứng của kho, sản phẩm vào biến buy_datas
        
        Bổ sung logic với kho chung thì thêm một key -ho_branch_id lưu tồn và danh sách hoá đơn đầu vào

        Hoá đơn đầu vào lấy theo điều kiện:
        - Ngày hoá đơn không lớn hơn ngày bán hàng
        - Trạng thái hoá đơn 1,2,3,5. Bỏ 4: bị thay thế, 6: Huỷ
        - Bỏ một số nhà cung cấp chi phí. Bỏ bằng cách sử dụng trường use_state=True
        """
        if g_data['last_date'] and g_data['last_date'] >= data.invoice_date:
            return

        domain = [
            ('ttb_vendor_invoice_date', '>=', '2024-01-01'),
            ('ttb_vendor_invoice_date', '<=', '2024-12-31'),
            ('ttb_vendor_invoice_date', '<=', data.invoice_date),
            ('trang_thai_hd', 'in', ('1','2','5')),
            ('use_state', '=', True),
        ]
        if g_data['last_date']:
            domain.append(('ttb_vendor_invoice_date', '>', g_data['last_date']))

        buy_invoices = self.env['ttb.nimbox.invoice'].search(domain)
        _logger.info(f"Đang lấy tồn từ {len(buy_invoices)} hoá đơn từ ngày {g_data['last_date']} đến ngày {data.invoice_date}")
        for invoice in buy_invoices:
            if invoice.ttb_branch_id.id == g_data['ho_branch_id']:
                g_data['ho_use_state_invoices'][invoice.id] = invoice.in_branch_id.id

            branch_id = invoice.in_branch_id.id or invoice.ttb_branch_id.id
            if not branch_id: continue
            
            for line in invoice.nimbox_line_ids:
                if line.soluong - line.soluong_used <= 0: continue
                soluong = line.soluong - line.soluong_used
                product_id = line.buy_product_id.id
                if not product_id: continue

                # Logic giới hạn ghép theo dòng hoá đơn
                g_data['map_line_products'][line.id] = {
                    'invoice_id': line.nimbox_invoice_id.id,
                    'branch_id': branch_id,
                    'quantity': soluong,
                    'out_product_ids': g_data['map_line_products'][line.id]['out_product_ids'],
                }
                g_data['map_product_lines'][product_id][line.id] = True

                g_data['quantity'][branch_id][g_data['p_index'][product_id]] += soluong
                # g_data['buy_datas'][branch_id][product_id].append({'line_id': line.id, 'nimbox_invoice_id': line.nimbox_invoice_id.id, 'quantity': soluong})

                # Nếu là hoá đơn chung và chưa được phân kho - Tổ chức riêng 1 biến tồn cho kho chung riêng một biến
                if invoice.ttb_branch_id.id == g_data['ho_branch_id'] and not invoice.in_branch_id:
                    g_data['quantity'][-g_data['ho_branch_id']][g_data['p_index'][product_id]] += soluong
                    # g_data['buy_datas'][-g_data['ho_branch_id']][product_id].append({'line_id': line.id, 'nimbox_invoice_id': line.nimbox_invoice_id.id, 'quantity': soluong})

        g_data['last_date'] = data.invoice_date

    def get_ai_data(self, datas):
        return [{
            'ai_vector': json.loads(data.ai_vector),
            'id': data.id,
        } for data in datas]

    def get_product_mch_dict(self, product):
        return {
            'category_id_level_1': product.category_id_level_1,
            'category_id_level_2': product.category_id_level_2,
            'category_id_level_3': product.category_id_level_3,
            'category_id_level_4': product.category_id_level_4,
            'category_id_level_5': product.category_id_level_5,
        }

    def remove_from_x(self, g_data, buy_invoice_id, data, log=False):
        """
        Loại khỏi X
        """
        if buy_invoice_id not in g_data['ho_use_state_invoices']: 
            if log:
                _logger.info(f'Hoá đơn {buy_invoice_id} không phải kho chung')
            return
        if g_data['ho_use_state_invoices'][buy_invoice_id]: 
            if log:
                _logger.info(f'Hoá đơn {buy_invoice_id} đã được phân kho {g_data["ho_use_state_invoices"][buy_invoice_id]} từ trước')
            return

        _logger.info(f'remove_from_x Cập nhật hoá đơn chung id {buy_invoice_id} sang kho {data.ttb_branch_id.id}')

        if data.ttb_branch_id.id != g_data['ho_branch_id']:
            _logger.info(f'xxx_dac_biet Hoá đơn {buy_invoice_id} được phân kho {data.ttb_branch_id.id}')

        buy_invoice = self.env['ttb.nimbox.invoice'].browse(buy_invoice_id)
        g_data['ho_use_state_invoices'][buy_invoice_id] = data.ttb_branch_id.id
        buy_invoice.in_branch_id = data.ttb_branch_id.id
        for line in buy_invoice.nimbox_line_ids:
            if not line.buy_product_id: continue

            buy_product_id = line.buy_product_id.id
            buy_product_idx = g_data['p_index'][buy_product_id]

            # trừ tồn hoá đơn tương ứng ở kho X
            if line.soluong_used:
                _logger.info('Có lỗi xảy ra remove_from_x line_id %s' % line.id)
            g_data['quantity'][-g_data['ho_branch_id']][buy_product_idx] -= line.soluong

    def remove_from_ho(self, g_data, buy_invoice_id):
        """
        Loại khỏi HO
        """

        if buy_invoice_id not in g_data['ho_use_state_invoices']: return
        if g_data['ho_use_state_invoices'][buy_invoice_id]: return

        _logger.info('remove_from_ho hoá đơn chung id %s' % buy_invoice_id)
        buy_invoice = self.env['ttb.nimbox.invoice'].browse(buy_invoice_id)
        for line in buy_invoice.nimbox_line_ids:
            if not line.buy_product_id: continue

            buy_product_id = line.buy_product_id.id
            buy_product_idx = g_data['p_index'][buy_product_id]

            if line.soluong_used:
                _logger.info('Có lỗi xảy ra remove_from_ho line_id %s' % line.id)
            g_data['quantity'][g_data['ho_branch_id']][buy_product_idx] -= line.soluong

    def insert_to_local(self, g_data, buy_invoice_id, data):
        """
        Đưa dữ liệu buy_invoice_id từ X vào cơ sở được chọn
        """

        if buy_invoice_id not in g_data['ho_use_state_invoices']: 
            _logger.info('insert_to_local hoá đơn chung id %s không phải kho chung' % buy_invoice_id)
            return
        if g_data['ho_use_state_invoices'][buy_invoice_id]: 
            _logger.info('insert_to_local hoá đơn chung id %s đã được phân kho %s từ trước' % (buy_invoice_id, g_data['ho_use_state_invoices'][buy_invoice_id]))
            return

        _logger.info('insert_to_local hoá đơn chung id %s sang kho %s' % (buy_invoice_id, data.ttb_branch_id.id))
        g_data['ho_use_state_invoices'][buy_invoice_id] = data.ttb_branch_id.id

        buy_invoice = self.env['ttb.nimbox.invoice'].browse(buy_invoice_id)
        for line in buy_invoice.nimbox_line_ids:
            if not line.buy_product_id: continue

            # Đánh dấu kho cho line_id
            g_data['map_line_products'][line.id]['branch_id'] = data.ttb_branch_id.id

            buy_product_id = line.buy_product_id.id
            buy_product_idx = g_data['p_index'][buy_product_id]

            # trừ tồn hoá đơn tương ứng ở kho X
            _logger.info('Có lỗi xảy ra insert_to_local line_id %s' % line.id)
            g_data['quantity'][data.ttb_branch_id.id][buy_product_idx] += line.soluong

    # def reconcil_one_product(self, g_data, data, buy_product_id, save_db=True, use_ho=False, found_invoice_id=False, diff_rate=0):
    def reconcil_one_product(self, g_data, data, buy_product_id, use_ho=False, diff_rate=0):
        """ 
        Lấy dòng hoá đơn đầu vào cho đủ số lượng quantity bán ra

        Có xử lý thêm các trường hợp với kho chung:
        1. Đầu ra kho riêng sử dụng đầu vào Kho chung
        - Xoá đầu vào khỏi X gồm đánh dấu, lưu db và trừ tồn
        - Thêm hoá đơn vào Kho riêng

        2. Đầu ra kho chung sử dụng đầu vào Kho chung
        - Xoá đầu vào khỏi X gồm đánh dấu, lưu db và trừ tồn

        Khi phân bổ 
        - nếu đã được đánh dấu thì không dùng
        - nếu là HO sử dụng HO thì đánh dấu lại
        """

        vals_list = []
        quantity = data.quantity
        branch_id = data.ttb_branch_id.id

        if quantity <= 0:
            return

        delete_keys = []
        sale_product_id = data.product_id.id

        # Lượt 1: Quét các line tại cơ sở đã từng ghép sản phẩm ra này trước đó
        for invoice_line_id in g_data['map_product_lines'][buy_product_id]:
            invoice_line_data = g_data['map_line_products'][invoice_line_id]

            if invoice_line_data['branch_id'] != branch_id: continue

            min_quantity = min(quantity, invoice_line_data['quantity'])
            if sale_product_id in invoice_line_data['out_product_ids'] and min_quantity > 0:
                # GHI NHẬN GHÉP
                vals_list.append({'in_line_id': invoice_line_id, 'out_line_id': data.id, 'quantity': min_quantity, 'diff_rate': diff_rate})
                
                invoice_line_data['out_product_ids'][sale_product_id] += min_quantity

                invoice_line_data['quantity'] -= min_quantity
                if invoice_line_data['quantity'] == 0:
                    delete_keys.append(invoice_line_id)

                quantity -= min_quantity
                if quantity <= 0: break

        # Lượt 2: Nếu sử dụng HO thì quét ở HO trước
        for invoice_line_id in g_data['map_product_lines'][buy_product_id] if use_ho and quantity > 0 else []:
            invoice_line_data = g_data['map_line_products'][invoice_line_id]

            invoice_id = invoice_line_data['invoice_id']
            if invoice_id not in g_data['ho_use_state_invoices'] or g_data['ho_use_state_invoices'][invoice_id]: continue

            min_quantity = min(quantity, invoice_line_data['quantity'])
            if min_quantity > 0:
                # GHI NHẬN GHÉP
                vals_list.append({'in_line_id': invoice_line_id, 'out_line_id': data.id, 'quantity': min_quantity, 'diff_rate': diff_rate})
                
                # cập nhật branch cho hoá đơn ho
                invoice_id = invoice_line_data['invoice_id']
                self.update_ho_use(g_data, invoice_id, branch_id)

                invoice_line_data['out_product_ids'][sale_product_id] += min_quantity

                invoice_line_data['quantity'] -= min_quantity
                if invoice_line_data['quantity'] == 0:
                    delete_keys.append(invoice_line_id)

                quantity -= min_quantity
                if quantity <= 0: break

        # Lượt 3: Quét các line tại cơ sở chưa từng ghép sản phẩm ra này trước đó
        for invoice_line_id in g_data['map_product_lines'][buy_product_id] if quantity > 0 else []:
            invoice_line_data = g_data['map_line_products'][invoice_line_id]

            if invoice_line_data['branch_id'] != branch_id: continue

            min_quantity = min(quantity, invoice_line_data['quantity'])
            product_limit_ok = g_data['in_out_invoice_product_limit'] < 0 or len(invoice_line_data['out_product_ids']) < g_data['in_out_invoice_product_limit']
            if min_quantity > 0 and sale_product_id not in invoice_line_data['out_product_ids'] and product_limit_ok:
                # GHI NHẬN GHÉP
                vals_list.append({'in_line_id': invoice_line_id, 'out_line_id': data.id, 'quantity': min_quantity, 'diff_rate': diff_rate})
                
                # Trường hợp HO sử dụng cho HO thì vẫn cần remove_from_x
                invoice_id = invoice_line_data['invoice_id']
                self.update_ho_use(g_data, invoice_id, branch_id)

                invoice_line_data['out_product_ids'][sale_product_id] += min_quantity

                invoice_line_data['quantity'] -= min_quantity
                if invoice_line_data['quantity'] == 0:
                    delete_keys.append(invoice_line_id)

                quantity -= min_quantity
                if quantity <= 0: break

        
        if quantity > 0:
            _logger.info('Không đủ tồn sản phẩm đầu vào để ghép cho dòng hoá đơn đầu ra id %s. Tồn dư: %s' % (data.id, quantity))

        # Xoá cache mà tồn đã về 0
        for invoice_line_id in delete_keys:
            del g_data['map_product_lines'][buy_product_id][invoice_line_id]

        # # while quantity > 0 and g_data['buy_cursor'][branch_id][buy_product_id] < len(g_data['buy_datas'][branch_id][buy_product_id]):
        # while quantity > 0 and g_data['buy_cursor'][branch_id][buy_product_id] < len(g_data['buy_datas'][branch_id][buy_product_id]):
        #     buy_data = g_data['buy_datas'][branch_id][buy_product_id][g_data['buy_cursor'][branch_id][buy_product_id]]
        #     # nhảy qua nếu hoá đơn chung đã dùng ở chỗ khác
        #     used_branch_id = g_data['ho_use_state_invoices'].get(buy_data['nimbox_invoice_id'])
        #     if used_branch_id and used_branch_id != branch_id:
        #         g_data['buy_cursor'][branch_id][buy_product_id] += 1
        #         continue

        #     # GHI NHẬN GHÉP
        #     if save_db:
        #         min_quantity = min(quantity, buy_data['quantity'])
        #         if min_quantity > 0:
        #             vals_list.append({'in_line_id': buy_data['line_id'], 'out_line_id': data.id, 'quantity': min_quantity, 'diff_rate': diff_rate})

        #     self.remove_from_x(g_data, buy_data['nimbox_invoice_id'], data)

        #     if buy_data['quantity'] <= quantity:                    
        #         quantity -= buy_data['quantity']
        #         buy_data['quantity'] = 0
        #         g_data['buy_cursor'][branch_id][buy_product_id] += 1
        #     else:
        #         buy_data['quantity'] -= quantity
        #         quantity = 0

        if vals_list:
            for vals in vals_list:
                in_line = self.env['ttb.nimbox.invoice.line'].browse(vals['in_line_id'])
                in_line.write({'soluong_used': in_line.soluong_used + vals['quantity']})
            self.env['ttb.inout.invoice.mapper'].create(vals_list)

    def find_buy_invoice(self, g_data, buy_product_id, quantity):
        # map_line_products
        # Lấy ở HO tức là dòng hoá đơn đó chưa được dùng lần nào
        for invoice_line_id in g_data['map_product_lines'][buy_product_id]:
            invoice_line_data = g_data['map_line_products'][invoice_line_id]

            if invoice_line_data['branch_id'] != g_data['ho_branch_id']: continue

            if not g_data['ho_use_state_invoices'].get(invoice_line_data['invoice_id']) and invoice_line_data['quantity'] >= quantity:
                if invoice_line_data['out_product_ids']: raise UserError('Dòng hoá đơn đầu vào từ kho chung đã được dùng để ghép sản phẩm đầu ra khác. Vui lòng kiểm tra lại dữ liệu.')
                return invoice_line_data['invoice_id']
        return False

        # for item in g_data['buy_datas'][-g_data['ho_branch_id']][buy_product_id]:
        #     nimbox_invoice_id = item['nimbox_invoice_id']
        #     # Là hoá đơn chung và hoá đơn chung chưa được dùng
        #     if nimbox_invoice_id in g_data['ho_use_state_invoices'] and not g_data['ho_use_state_invoices'][nimbox_invoice_id] and item['quantity'] >= quantity:
        #         return item['nimbox_invoice_id']
        # return False

    def update_ho_use(self, g_data, buy_invoice_id, branch_id):
        # Trường hợp hoá đơn ở HO dùng cho 1 cơ sở khác chứ không phải HO

        if buy_invoice_id not in g_data['ho_use_state_invoices']: 
            # _logger.info(f'update_ho_use Hoá đơn {buy_invoice_id} không phải kho chung')
            return
        if g_data['ho_use_state_invoices'][buy_invoice_id]: 
            # _logger.info(f'update_ho_use Hoá đơn {buy_invoice_id} đã được phân kho {g_data["ho_use_state_invoices"][buy_invoice_id]} từ trước')
            return

        _logger.info(f'update_ho_use Cập nhật hoá đơn chung id {buy_invoice_id} sang kho {branch_id}')

        # cho vào biến đánh dấu
        g_data['ho_use_state_invoices'][buy_invoice_id] = branch_id

        buy_invoice = self.env['ttb.nimbox.invoice'].browse(buy_invoice_id)
        if buy_invoice.in_branch_id:
            _logger.info(f'update_ho_use xxx_dac_biet Hoá đơn {buy_invoice_id} được phân kho {buy_invoice.in_branch_id.id} từ trước')        
        buy_invoice.in_branch_id = branch_id

        for line in buy_invoice.nimbox_line_ids:
            if not line.buy_product_id: continue

            buy_product_id = line.buy_product_id.id
            buy_product_idx = g_data['p_index'][buy_product_id]

            # trừ tồn hoá đơn tương ứng ở kho X
            g_data['quantity'][-g_data['ho_branch_id']][buy_product_idx] -= line.soluong
            
            # chuyển lại branch_id cho line
            g_data['map_line_products'][line.id]['branch_id'] = branch_id

            if branch_id != g_data['ho_branch_id']:
                # trừ tồn ở kho chung do sẽ dùng ở kho khác
                g_data['quantity'][g_data['ho_branch_id']][buy_product_idx] -= line.soluong
                # tăng tồn ở kho khác
                g_data['quantity'][branch_id][buy_product_idx] += line.soluong

    # def update_ho_use(self, g_data, buy_invoice_id, branch_id):
    #     if buy_invoice_id in g_data['ho_use_state_invoices']: return
    #     g_data['ho_use_state_invoices'][buy_invoice.id] = branch_id

    #     _logger.info(f'Cập nhật hoá đơn chung id {buy_invoice_id} sang kho {branch_id}')
    #     buy_invoice = self.env['ttb.nimbox.invoice'].browse(buy_invoice_id)

    #     # cho vào biến đánh dấu
    #     if buy_invoice.in_branch_id.id != branch_id:
    #         buy_invoice.in_branch_id = branch_id

    #     for line in buy_invoice.nimbox_line_ids:
    #         if not line.buy_product_id: continue

    #         buy_product_id = line.buy_product_id.id
    #         buy_product_idx = g_data['p_index'][buy_product_id]

    #         # trừ tồn hoá đơn tương ứng ở kho X
    #         g_data['quantity'][-g_data['ho_branch_id']][buy_product_idx] -= line.soluong
                
    #         # trừ tồn ở kho chung do sẽ dùng ở kho khác
    #         g_data['quantity'][g_data['ho_branch_id']][buy_product_idx] -= line.soluong
            
    #         # tăng tồn ở kho khác
    #         g_data['quantity'][branch_id][buy_product_idx] += line.soluong
    #         buy_cursor = g_data['buy_cursor'][branch_id][buy_product_id]
    #         g_data['buy_datas'][branch_id][buy_product_id].insert(buy_cursor, {'line_id': line.id, 'nimbox_invoice_id': line.nimbox_invoice_id.id, 'quantity': line.soluong})

    def filter_by_product_limit(self, g_data, sale_product_id, in_product_id):
        if sale_product_id in g_data['map_products'][in_product_id]: return True
        if len(g_data['map_products'][in_product_id]) < g_data['in_out_product_limit']: return True

        return False

    def filter_by_invoice_product_limit(self, g_data, ttb_branch_id, sale_product_id, in_product_id, quantity=0):
        sum_quantity = 0

        for invoice_line_id in g_data['map_product_lines'][in_product_id]:
            invoice_line_data = g_data['map_line_products'][invoice_line_id]

            if invoice_line_data['branch_id'] != ttb_branch_id: continue

            if g_data['in_out_invoice_product_limit'] < 0 or sale_product_id in invoice_line_data['out_product_ids'] or len(invoice_line_data['out_product_ids']) < g_data['in_out_invoice_product_limit']:
                sum_quantity += invoice_line_data['quantity']
                if sum_quantity >= quantity:
                    return True

        return False

    def get_in_products(self, limit=1000, batch_size=500, from_date = None, to_date=None, rerun=False):
        _logger.info('Lấy dữ liệu')

        ho_branch = self.env['ttb.branch'].search([('code', 'ilike', 'ho')], limit=1)
        ho_branch_id = ho_branch.id
        g_data = {
            'last_date': False,
            # ko dùng buy_datas nữa chuyển thành dùng map_line_products
            # 'buy_datas': defaultdict(lambda: defaultdict(list)),
            'buy_cursor': defaultdict(lambda: defaultdict(int)),
            'ho_buy_datas': {},
            'ho_branch': ho_branch,
            'ho_branch_id': ho_branch.id,
            'ho_use_state_invoices': {},
            'in_out_price_rate_max': float(self.env['ir.config_parameter'].sudo().get_param('ttb_invoice_custom.in_out_price_rate_max', default='0.98')),
            'in_out_price_rate_min': float(self.env['ir.config_parameter'].sudo().get_param('ttb_invoice_custom.in_out_price_rate_min', default='0')),

            # Lưu các sản phẩm đã map với 1 sản phẩm đầu vào - dùng để giới hạn 1 sp vào chỉ được ghép với 3 sp ra
            'map_products': defaultdict(lambda: defaultdict(int)),
            # Cấu hình tương ứng với điều kiện bên trên
            'in_out_product_limit': int(self.env['ir.config_parameter'].sudo().get_param('ttb_invoice_custom.in_out_product_limit', default='-1')),

            # Lưu các sản phẩm đã map với 1 cặp (sản phẩm đầu vào, dòng hoá đơn đầu vào)
            'map_line_products': defaultdict(lambda: {
                'invoice_id': False,
                'branch_id': False,
                'quantity': 0,
                'out_product_ids': defaultdict(int),
            }),
            'in_out_invoice_product_limit': int(self.env['ir.config_parameter'].sudo().get_param('ttb_invoice_custom.in_out_invoice_product_limit', default='3')),
            # Mảng cache danh sách line chứa sản phẩm
            'map_product_lines': defaultdict(dict),
        }

        self.init_inventory_quantity(g_data)

        def get_in_product_for_line(ttb_branch_id, similarity_map):
            if not ttb_branch_id:
                return False, 0, 0

            # for level in range(4, -1, -1):
            # Chỉ chạy với MCH1. Bỏ qua MCH5,4,3,2
            if data.id == 3013301:
                print('debug')
            for level in range(0, -1, -1):
                sale_mch = map_sale_products[sale_product_id][f'category_id_level_{level+1}'].id if sale_product_id in map_sale_products else False
                if not sale_mch: continue

                price_unit = g_data['in_out_price_rate_max'] * data.price_unit
                if price_unit == 0:
                    price_unit = 1000000000
                price_unit_min = g_data['in_out_price_rate_min'] * data.price_unit

                mask = (g_data['quantity'][ttb_branch_id] >= data.quantity) & (mch[level] == sale_mch) & (buy_prices <= price_unit) & (buy_prices >= price_unit_min)
                # mask_qty = (g_data['quantity'][ttb_branch_id] >= data.quantity)
                # mask_mch = (mch[level] == sale_mch)
                # mask_price = (buy_prices <= price_unit) & (buy_prices >= price_unit_min)
                # mask = mask_qty & mask_mch & mask_price

                count_result = np.count_nonzero(mask)
                # count_qty_mch = np.count_nonzero(mask_qty & mask_mch)
                _logger.info(f"Hoá đơn đầu ra {data.id} Combined Conditions (All OK): {count_result} items remain.")
                # _logger.info(f"Hoá đơn đầu ra {data.id} Condition Qty & MCH: {count_qty_mch} items remain.")

                pass_index = np.where(mask)

                # 1. TẠO CÁC MẶT NẠ RIÊNG BIỆT CHO MỖI ĐIỀU KIỆN
                # mask_qty = (g_data['quantity'][ttb_branch_id] >= data.quantity)
                # mask_mch = (mch[level] == sale_mch)
                # mask_price = (buy_prices <= price_unit)

                if pass_index[0].size <= 0: continue

                if g_data['in_out_product_limit'] > 0:
                    # Bổ sung: Lọc theo giới hạn số lượng sản phẩm được map
                    # 1. Lấy mảng index thực tế từ tuple pass_index
                    indices_to_check = pass_index[0]

                    # 2. Lọc lại các index dựa trên điều kiện của g_data['map_products']
                    # Lưu ý: 'condition_check' là chỗ bạn tự viết logic của mình
                    valid_indices = [
                        idx for idx in indices_to_check 
                        if self.filter_by_product_limit(g_data, sale_product_id, buy_products_list[idx])
                    ]

                    # 3. Cập nhật lại pass_index. 
                    # Cần đóng gói lại thành tuple (np.array,) để tương thích với dòng 323 (similarity_map[pass_index])
                    pass_index = (np.array(valid_indices),)

                    # 4. Kiểm tra lại kích thước sau khi lọc (đề phòng lọc xong rỗng)
                    if pass_index[0].size <= 0: continue

                # Lọc theo giới hạn số lượng sản phẩm được ghép với 1 hoá đơn đầu vào
                if g_data['in_out_invoice_product_limit'] > 0 and ttb_branch_id > 0:
                    # 1. Lấy mảng index thực tế từ tuple pass_index
                    indices_to_check = pass_index[0]

                    # 2. Lọc lại các index dựa trên điều kiện của g_data['map_products']
                    # Lưu ý: 'condition_check' là chỗ bạn tự viết logic của mình
                    valid_indices = [
                        idx for idx in indices_to_check 
                        if self.filter_by_invoice_product_limit(g_data, ttb_branch_id, sale_product_id, buy_products_list[idx], data.quantity)
                    ]

                    # 3. Cập nhật lại pass_index. 
                    # Cần đóng gói lại thành tuple (np.array,) để tương thích với dòng 323 (similarity_map[pass_index])
                    pass_index = (np.array(valid_indices),)

                    # 4. Kiểm tra lại kích thước sau khi lọc (đề phòng lọc xong rỗng)
                    if pass_index[0].size <= 0: continue

                filtered_similarity_values = similarity_map[pass_index]
                best_index_in_filtered = np.argmax(filtered_similarity_values)
                best_index_origin = pass_index[0][best_index_in_filtered]

                return best_index_origin, similarity_map[best_index_origin], level

            _logger.info('Hoá đơn đầu ra id %s tại kho %s không tìm được sản phẩm đầu vào phù hợp' % (data.id, ttb_branch_id))
            # if ttb_branch_id > 0 and sale_mch == 10 and data.available_in_line_ids:
                # _logger.info('có vấn đề')
            return False, 0, 0
        
        # Lấy và khởi tạo sản phẩm đầu vào
        buy_products = self.env['product.sale.item'].search([('batch_name', '=', 'dau_vao'), ('name', '!=', False), ('name', '!=', '')])
        self.env['ttb.tools'].lib_ai_product().generate_ai_vector(buy_products)
        buy_products_list = buy_products.ids
        g_data['p_index'] = {product_id: index for index, product_id in enumerate(buy_products_list)}
        target_vectors = np.array([item['ai_vector'] for item in self.get_ai_data(buy_products)])

        # Tiếp tục xử lý đầu vào 
        # điều kiện 1: theo mch - chuẩn bị trước dữ liệu mch cho đầu vào
        mch_list = [ [], [], [], [], [], ]
        for product in buy_products:
            for level in range(5):
                mch_list[level].append(product[f'category_id_level_{level+1}'].id)
        mch = []
        for level in range(5):
            mch.append(np.array(mch_list[level]))

        # điều kiện 2: giá - chuẩn bị trước dữ liệu giá cho đầu vào
        buy_prices = np.array([product.price for product in buy_products])

        # Lấy và khởi tạo sản phẩm đầu ra
        sale_products = self.env['product.sale.item'].search([('batch_name', '=', 'dau_ra'), ('name', '!=', False), ('name', '!=', '')])
        self.env['ttb.tools'].lib_ai_product().generate_ai_vector(sale_products)
        map_sale_products = {product.id: self.get_product_mch_dict(product) for product in sale_products}

        # Quá trình xử lý
        domain = [
            # ('state', '=', 'new'), 
            ('product_id', '!=', False), 
            ('product_id.name', '!=', False)
        ]
        if not rerun:
            domain.append(('state', '=', 'new'))
        else:
            domain.append(('state', '=', 'mapped'))
            domain.append(('result_state', '!=', 'ok'))

        if from_date:
            domain.append(('invoice_date', '>=', from_date))
        if to_date:
            domain.append(('invoice_date', '<=', to_date))
        datas = self.search(domain, order='invoice_date asc, id asc', limit=limit)
        if not datas: return

        g_data['quantity'] = defaultdict(lambda: np.zeros(len(buy_products)))
        data = datas[0]

        # 1/12/25: Ghi nhận số lượng đã ghép để không cần nạp lại dữ liệu cũ
        # Nạp đầu vào đã ghép
        # self.get_inventory_quantity(data, g_data)
        # Nạp đầu ra đã ghép
        # self.init_inventory_quantity(g_data)
        
        # Xử lý những đầu ra chưa ghép
        for i in range(0, len(datas), batch_size):
            _logger.info(f'Xử lý batch {i}:{i+batch_size}/{len(datas)}')
            batch_datas = datas[i:i+batch_size]

            current_sale_products = batch_datas.filtered(lambda x: x.product_id.id in map_sale_products).mapped('product_id')
            sale_products_idx = {product.id: index for index, product in enumerate(current_sale_products)}

            if not current_sale_products: continue

            _logger.info('Lấy tương đồng')
            source_items = self.get_ai_data(current_sale_products)
            source_vectors = np.array([item['ai_vector'] for item in source_items])
            similarity_maps = cosine_similarity(source_vectors, target_vectors)

            to_create_lines = []

            for data in batch_datas:
                _logger.info('Tìm sản phẩm đầu vào cho dòng hoá đơn %s, %s' % (data.id, data.product_id.name))
                
                sale_product_id = data.product_id.id
                if sale_product_id not in sale_products_idx: 
                    data.write({'state': 'mapped', 'result_state': 'no_out_product'})
                    continue

                if data.quantity <= 0: 
                    data.write({'state': 'mapped', 'result_state': 'empty'})
                    continue

                similarity_map = similarity_maps[sale_products_idx[sale_product_id]]
                best_buy_product_index = np.argmax(similarity_map)
                update_data = {
                    'state': 'mapped',
                    'best_buy_product_id': buy_products_list[best_buy_product_index],
                    'best_buy_product_rate': similarity_map[best_buy_product_index],
                    'best_inventory_quantity': g_data['quantity'][data.ttb_branch_id.id][best_buy_product_index],

                    'buy_product_id': False,
                    'buy_product_rate': False,
                    'inventory_quantity': False,
                    'buy_product_level': False,
                    'branch_type':  False,
                }

                if not data.ttb_branch_id: 
                    data.write({**update_data, 'result_state': 'no_branch'})
                    continue

                if g_data['last_date'] != data.invoice_date:
                    _logger.info('Xử lý đầu vào cho các hoá đơn bán ngày %s' % data.invoice_date)
                self.get_inventory_quantity(data, g_data)

                buy_product_index, diff, level = get_in_product_for_line(data.ttb_branch_id.id, similarity_map)

                use_ho = False
                buy_product_index2 = False
                # nimbox_invoice_id = False

                # Nếu hoá đơn đầu ra không phải kho chung thì thử ghép ở kho chung
                if data.ttb_branch_id.id != g_data['ho_branch_id']:
                    # _logger.info(f'Thử tìm tại kho chung cho hoá đơn {data.id}')
                    buy_product_index2, diff2, level2 = get_in_product_for_line(-g_data['ho_branch_id'], similarity_map)
                    if buy_product_index2 and (level < level2 or (level == level2 and diff < diff2)):
                        _logger.info(f'Hoá đơn {data.id}. Tìm thấy ở kho chung tốt hơn: {buy_products_list[buy_product_index2]}, {diff2}, {level2}')
                        buy_product_index, diff, level = buy_product_index2, diff2, level2
                        use_ho = True
                        # buy_product_id2 = buy_products_list[buy_product_index2]
                        # _logger.info(f'Tìm thấy {buy_product_id2}, {diff2}, {level2}')
                        # nimbox_invoice_id = self.find_buy_invoice(g_data, buy_product_id2, data.quantity)
                        
                        # # Nếu tìm được sản phẩm ở kho chung và rate tốt hơn và tìm được hoá đơn còn đủ nguyên lượng quantity cần bán
                        # if nimbox_invoice_id:
                        #     _logger.info(f'Tìm thấy hoá đơn {nimbox_invoice_id}.')
                        #     buy_product_index, diff, level = buy_product_index2, diff2, level2
                        #     use_ho = True
                        # else:
                        #     _logger.info(f'Không tìm được hoá đơn đủ {data.quantity}')
                    # else:
                    #     _logger.info('Không tìm thấy')

                if buy_product_index:
                    update_data.update({
                        'buy_product_id': buy_products_list[buy_product_index],
                        'buy_product_rate': diff,
                        'inventory_quantity': g_data['quantity'][data.ttb_branch_id.id][buy_product_index],
                        'buy_product_level': f'category_id_level_{level+1}',
                        'branch_type': 'ho' if use_ho else 'origin',
                        'result_state': 'ok',
                    })
                else:
                    update_data['result_state'] = 'no_product'

                # Cập nhật DB
                data.write(update_data)

                # Cập nhật biến trong bộ nhớ:
                # - Trừ tồn bằng với số lượng đã bán ra
                # - Đánh dấu ho nếu sử dụng kho chung
                if buy_product_index:
                    # Trừ tồn sử dụng. Trường hợp lấy từ kho chung thì tồn hoá đơn kho chung sẽ được bổ sung sau.
                    g_data['quantity'][data.ttb_branch_id.id][buy_product_index] -= data.quantity
                    
                    in_product_id = buy_products_list[buy_product_index]
                    # Đánh dấu sản phẩm map sản phẩm
                    if g_data['in_out_product_limit'] > 0:
                        if sale_product_id not in g_data['map_products'][in_product_id]:
                            to_create_lines.append({
                                'in_product_id': in_product_id,
                                'out_product_id': sale_product_id,
                            })

                        g_data['map_products'][in_product_id][sale_product_id] = True

                    # self.reconcil_one_product(g_data, data, in_product_id, use_ho=use_ho, found_invoice_id=nimbox_invoice_id, diff_rate=diff)
                    self.reconcil_one_product(g_data, data, in_product_id, use_ho=use_ho, diff_rate=diff)

            if to_create_lines:
                self.env['ttb.inproduct.outproduct.mapper'].create(to_create_lines)
            self.env.cr.commit()
