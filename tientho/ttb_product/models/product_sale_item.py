from odoo import models, fields
from odoo.exceptions import UserError
from odoo.addons.ttb_tools.ai.product_similar_matcher import find_similar_product, group_similar_product

import logging
_logger = logging.getLogger(__name__)


class ProductSaleItem(models.Model):
    _name = 'product.sale.item'
    _inherit = 'mail.thread'
    _description = 'Sản phẩm bán ra'

    name = fields.Char(string='Tên sản phẩm', index=True)    
    code = fields.Char(string='Mã sản phẩm')
    price = fields.Float(string='Giá bán')
    qty = fields.Float(string='Số lượng bán')
    donvi = fields.Char('Đơn vị tính')
    matched_stock_item_id = fields.Many2one(
        'product.stock.item', string='Sản phẩm kho đã khớp 0', readonly=True, index=True
    )
    matched_stock_item_code = fields.Char('Mã sản phẩm 0', related='matched_stock_item_id.code', store=True)
    diff_name = fields.Float('Tương hợp về tên 0')

    matched_stock_item_id_1 = fields.Many2one(
        'product.stock.item', string='Sản phẩm kho đã khớp 1', readonly=True, index=True
    )
    matched_stock_item_code_1 = fields.Char('Mã sản phẩm 1', related='matched_stock_item_id_1.code', store=True)
    diff_name_1 = fields.Float('Tương hợp về tên 1')

    matched_stock_item_id_2 = fields.Many2one(
        'product.stock.item', string='Sản phẩm kho đã khớp 2', readonly=True, index=True
    )
    matched_stock_item_code_2 = fields.Char('Mã sản phẩm 2', related='matched_stock_item_id_2.code', store=True)
    diff_name_2 = fields.Float('Tương hợp về tên 2')

    # matched 3
    matched_stock_item_id_3 = fields.Many2one(
        'product.stock.item', string='Sản phẩm kho đã khớp 3', readonly=True, index=True
    )
    matched_stock_item_code_3 = fields.Char('Mã sản phẩm 3', related='matched_stock_item_id_3.code', store=True)
    diff_name_3 = fields.Float('Tương hợp về tên 3')

    batch_name = fields.Char('Lô xử lý')

    matched_group_item_id = fields.Many2one(
        'product.sale.item', string='Sản phẩm đại diện nhóm', readonly=True, index=True
    )
    matched_group_item_code = fields.Char('Mã sản phẩm đại diện nhóm', related='matched_group_item_id.code', store=True)
    diff_name_group = fields.Float('Tương hợp nhỏ nhất trong nhóm')

    category_id_level_1 = fields.Many2one('product.category.training', 'MCH 1', index=True, domain="[('category_level', '=', 1)]", tracking=True)
    category_id_level_2 = fields.Many2one('product.category.training', 'MCH 2', index=True, domain="[('category_level', '=', 2)]", tracking=True)
    category_id_level_3 = fields.Many2one('product.category.training', 'MCH 3', index=True, domain="[('category_level', '=', 3)]", tracking=True)
    category_id_level_4 = fields.Many2one('product.category.training', 'MCH 4', index=True, domain="[('category_level', '=', 4)]", tracking=True)
    category_id_level_5 = fields.Many2one('product.category.training', 'MCH 5', index=True, domain="[('category_level', '=', 5)]", tracking=True)
    category_id_level_1_rate = fields.Float('Độ chắc chắn MCH1')
    category_id_level_2_rate = fields.Float('Độ chắc chắn MCH2')
    category_id_level_3_rate = fields.Float('Độ chắc chắn MCH3')
    category_id_level_4_rate = fields.Float('Độ chắc chắn MCH4')
    category_id_level_5_rate = fields.Float('Độ chắc chắn MCH5')
    
    category_id_level_1_type = fields.Char('Loại ai MCH1', help='Manual/ Học máy/ Sản phẩm tương tự / Từ khoá / Other')
    category_id_level_2_type = fields.Char('Loại ai MCH2', help='Manual/ Học máy/ Sản phẩm tương tự / Từ khoá / Other')
    category_id_level_3_type = fields.Char('Loại ai MCH3', help='Manual/ Học máy/ Sản phẩm tương tự / Từ khoá / Other')
    category_id_level_4_type = fields.Char('Loại ai MCH4', help='Manual/ Học máy/ Sản phẩm tương tự / Từ khoá / Other')
    category_id_level_5_type = fields.Char('Loại ai MCH5', help='Manual/ Học máy/ Sản phẩm tương tự / Từ khoá / Other')

    ai_vector = fields.Text(
        string='AI Vector (JSON)',
        copy=False,
    )
    active = fields.Boolean(default=True)

    def find_similar_products(self, price_diff=None, check_stock=True, check_price=True, model_name=False, get_number=1, origin_nibot_products=None, origin_odoo_products=None, batch_size=1000):
        # origin_nibot_products = self.search([('processed', '=', False)])
        lib_ai_product = self.env['ttb.tools'].lib_ai_product()
        _logger.info('Đang Vector hoá')

        if origin_nibot_products is None:
            origin_nibot_products = self.search([])
        lib_ai_product.generate_ai_vector(origin_nibot_products)

        if origin_odoo_products is None:    
            origin_odoo_products = self.env['product.stock.item'].search([])
        lib_ai_product.generate_ai_vector(origin_odoo_products)

        _logger.info('Đã Vector hoá xong')

        nibot_products = [{
            'name': product.name, 
            'ai_vector': product.ai_vector, 
            'price': product.price,
            'qty': product.qty,
        } for product in origin_nibot_products]
        odoo_products = [{
            'name': product.name, 
            'ai_vector': product.ai_vector, 
            'price': product.price,
            'qty_available': product.qty_available,
        } for product in origin_odoo_products]

        matcheds = find_similar_product(nibot_products, odoo_products, 
            price_diff=price_diff, check_stock=check_stock, check_price=check_price, 
            model_name=model_name,
            get_number=get_number,
            batch_size=batch_size
        )
        for nibot_index in matcheds:
            match = matcheds[nibot_index]

            match_index = match['match_index']
            if match_index >= 0:
                match_more = {}
                for i in range(1, get_number):
                    if f'match_index_{i}' in match:
                        odoo_product = origin_odoo_products[match[f'match_index_{i}']]
                        match_more.update({
                            f'matched_stock_item_id_{i}': odoo_product.id,
                            f'diff_name_{i}': match[f'score_{i}']
                        })

                odoo_product = origin_odoo_products[match_index]
                origin_nibot_products[nibot_index].write({
                    'matched_stock_item_id': odoo_product.id,
                    'diff_name': match['score'],
                    # 'processed': True,
                    ** match_more
                })
            # else:
            #     origin_nibot_products[nibot_index].write({
            #         'processed': True,
            #     })

    def group_similar_product(self, source_items=False, model_name=False, score=0.75, scorex=2, batch_size=1000):
        if source_items is None:
            source_items = self.search([])

        lib_ai_product = self.env['ttb.tools'].lib_ai_product()
        lib_ai_product.generate_ai_vector(source_items, auto_commit=True)

        products = [{
            'name': product.name, 
            'price': product.price,
            'qty': product.qty,
            'ai_vector': product.ai_vector,
        } for product in source_items]

        matcheds = group_similar_product(products, model_name, score, scorex, batch_size)

        for nibot_index in matcheds:
            match = matcheds[nibot_index]

            match_index = match['match_index']
            if match_index >= 0:
                odoo_product = source_items[match_index]
                source_items[nibot_index].write({
                    'matched_group_item_id': odoo_product.id,
                    'diff_name_group': match['score'],
                })


    # matched 4
    matched_stock_item_id_4 = fields.Many2one(
        'product.stock.item', string='Sản phẩm kho đã khớp 4', readonly=True, index=True
    )
    matched_stock_item_code_4 = fields.Char('Mã sản phẩm 4', related='matched_stock_item_id_4.code', store=True)
    diff_name_4 = fields.Float('Tương hợp về tên 4')

    # matched 5
    matched_stock_item_id_5 = fields.Many2one(
        'product.stock.item', string='Sản phẩm kho đã khớp 5', readonly=True, index=True
    )
    matched_stock_item_code_5 = fields.Char('Mã sản phẩm 5', related='matched_stock_item_id_5.code', store=True)
    diff_name_5 = fields.Float('Tương hợp về tên 5')

    # matched 6
    matched_stock_item_id_6 = fields.Many2one(
        'product.stock.item', string='Sản phẩm kho đã khớp 6', readonly=True, index=True
    )
    matched_stock_item_code_6 = fields.Char('Mã sản phẩm 6', related='matched_stock_item_id_6.code', store=True)
    diff_name_6 = fields.Float('Tương hợp về tên 6')

    # matched 7
    matched_stock_item_id_7 = fields.Many2one(
        'product.stock.item', string='Sản phẩm kho đã khớp 7', readonly=True, index=True
    )
    matched_stock_item_code_7 = fields.Char('Mã sản phẩm 7', related='matched_stock_item_id_7.code', store=True)
    diff_name_7 = fields.Float('Tương hợp về tên 7')

    # matched 8
    matched_stock_item_id_8 = fields.Many2one(
        'product.stock.item', string='Sản phẩm kho đã khớp 8', readonly=True, index=True
    )
    matched_stock_item_code_8 = fields.Char('Mã sản phẩm 8', related='matched_stock_item_id_8.code', store=True)
    diff_name_8 = fields.Float('Tương hợp về tên 8')

    # matched 9
    matched_stock_item_id_9 = fields.Many2one(
        'product.stock.item', string='Sản phẩm kho đã khớp 9', readonly=True, index=True
    )
    matched_stock_item_code_9 = fields.Char('Mã sản phẩm 9', related='matched_stock_item_id_9.code', store=True)
    diff_name_9 = fields.Float('Tương hợp về tên 9')

    # matched 10
    matched_stock_item_id_10 = fields.Many2one(
        'product.stock.item', string='Sản phẩm kho đã khớp 10', readonly=True, index=True
    )
    matched_stock_item_code_10 = fields.Char('Mã sản phẩm 10', related='matched_stock_item_id_10.code', store=True)
    diff_name_10 = fields.Float('Tương hợp về tên 10')

    # matched 11
    matched_stock_item_id_11 = fields.Many2one(
        'product.stock.item', string='Sản phẩm kho đã khớp 11', readonly=True, index=True
    )
    matched_stock_item_code_11 = fields.Char('Mã sản phẩm 11', related='matched_stock_item_id_11.code', store=True)
    diff_name_11 = fields.Float('Tương hợp về tên 11')

    # matched 12
    matched_stock_item_id_12 = fields.Many2one(
        'product.stock.item', string='Sản phẩm kho đã khớp 12', readonly=True, index=True
    )
    matched_stock_item_code_12 = fields.Char('Mã sản phẩm 12', related='matched_stock_item_id_12.code', store=True)
    diff_name_12 = fields.Float('Tương hợp về tên 12')

    # matched 13
    matched_stock_item_id_13 = fields.Many2one(
        'product.stock.item', string='Sản phẩm kho đã khớp 13', readonly=True, index=True
    )
    matched_stock_item_code_13 = fields.Char('Mã sản phẩm 13', related='matched_stock_item_id_13.code', store=True)
    diff_name_13 = fields.Float('Tương hợp về tên 13')

    # matched 14
    matched_stock_item_id_14 = fields.Many2one(
        'product.stock.item', string='Sản phẩm kho đã khớp 14', readonly=True, index=True
    )
    matched_stock_item_code_14 = fields.Char('Mã sản phẩm 14', related='matched_stock_item_id_14.code', store=True)
    diff_name_14 = fields.Float('Tương hợp về tên 14')

    # matched 15
    matched_stock_item_id_15 = fields.Many2one(
        'product.stock.item', string='Sản phẩm kho đã khớp 15', readonly=True, index=True
    )
    matched_stock_item_code_15 = fields.Char('Mã sản phẩm 15', related='matched_stock_item_id_15.code', store=True)
    diff_name_15 = fields.Float('Tương hợp về tên 15')

    # matched 16
    matched_stock_item_id_16 = fields.Many2one(
        'product.stock.item', string='Sản phẩm kho đã khớp 16', readonly=True, index=True
    )
    matched_stock_item_code_16 = fields.Char('Mã sản phẩm 16', related='matched_stock_item_id_16.code', store=True)
    diff_name_16 = fields.Float('Tương hợp về tên 16')

    # matched 17
    matched_stock_item_id_17 = fields.Many2one(
        'product.stock.item', string='Sản phẩm kho đã khớp 17', readonly=True, index=True
    )
    matched_stock_item_code_17 = fields.Char('Mã sản phẩm 17', related='matched_stock_item_id_17.code', store=True)
    diff_name_17 = fields.Float('Tương hợp về tên 17')

    # matched 18
    matched_stock_item_id_18 = fields.Many2one(
        'product.stock.item', string='Sản phẩm kho đã khớp 18', readonly=True, index=True
    )
    matched_stock_item_code_18 = fields.Char('Mã sản phẩm 18', related='matched_stock_item_id_18.code', store=True)
    diff_name_18 = fields.Float('Tương hợp về tên 18')

    # matched 19
    matched_stock_item_id_19 = fields.Many2one(
        'product.stock.item', string='Sản phẩm kho đã khớp 19', readonly=True, index=True
    )
    matched_stock_item_code_19 = fields.Char('Mã sản phẩm 19', related='matched_stock_item_id_19.code', store=True)
    diff_name_19 = fields.Float('Tương hợp về tên 19')

    # matched 20
    matched_stock_item_id_20 = fields.Many2one(
        'product.stock.item', string='Sản phẩm kho đã khớp 20', readonly=True, index=True
    )
    matched_stock_item_code_20 = fields.Char('Mã sản phẩm 20', related='matched_stock_item_id_20.code', store=True)
    diff_name_20 = fields.Float('Tương hợp về tên 20')

    # matched 21
    matched_stock_item_id_21 = fields.Many2one(
        'product.stock.item', string='Sản phẩm kho đã khớp 21', readonly=True, index=True
    )
    matched_stock_item_code_21 = fields.Char('Mã sản phẩm 21', related='matched_stock_item_id_21.code', store=True)
    diff_name_21 = fields.Float('Tương hợp về tên 21')

    def action_show_point_category_1(self):
        categories = self.env['product.category.training'].search([('category_level', '=', 1)])

        raise UserError(str(  self.env['ttb.tools'].lib_ai_pc().classify_product(self.env, categories, self)))

    def match_mch_by_merchan_learning(self, batch_name, category=False):
        """
        category là cha, sẽ lấy hết các con của nó và huấn luyện theo các con của nó
        Tức là sẽ lấy hết các sản phẩm có danh mục là danh mục con của category, truyền vào hàm huấn luyện
        Trường hợp 1 category mà các sản phẩm của con nó chỉ thuộc về 1 con duy nhất thì không huấn luyện được

        """

        classifier_service = self.env['ttb.tools'].lib_ai_pc()

        _logger.info("Bắt đầu quá trình huấn luyện mô hình phân loại...")

        level = category.category_level if category else 0
        domain = [('product_name', '!=', False)]
        if category:
            domain += [(f'category_id_level_{level}', '=', category.id)]

        training_records = self.env['product.product.category.training'].search(domain)
        if not training_records: return

        domain = [('batch_name', '=', batch_name), (f'category_id_level_{level}', '=', category.id)] if category else []
        products = self.env['product.sale.item'].search(domain)
        product_names = [item.name for item in products]

        category_id = False
        is_multi = False
        for rec in training_records:
            old = category_id
            tmp_id = rec[f'category_id_level_{level+1}'].id
            if tmp_id:
                category_id = tmp_id
            if old and old != category_id:
                is_multi = True
                break

        if not category_id: return

        if not is_multi:
            for item in products:
                if category_id and not item[f'category_id_level_{level+1}']:
                    item.write({
                        f'category_id_level_{level+1}': category_id,
                        f'category_id_level_{level+1}_rate': 1,
                        f'category_id_level_{level+1}_type': 'Học máy',
                    })
        else:
            # Định dạng lại dữ liệu cho service
            training_data = [{
                'product_name': rec['product_name'],
                'category_code': rec[f'category_id_level_{level+1}'].id
            } for rec in training_records]
            _logger.info(f"Đã lấy {len(training_data)} dòng dữ liệu để huấn luyện.")

            # 2. Gọi service để huấn luyện
            try:
                pipeline, acc_train, acc_test, report = classifier_service.train_model(training_data)

                if not pipeline:
                    raise UserError(f"Huấn luyện thất bại: {report}")
            except Exception as e:
                _logger.info(str(e))
                return

            # # 3. Lưu mô hình đã huấn luyện
            # classifier_service.save_pipeline_to_attachment(self.env, pipeline)
            # _logger.info("Đã lưu thành công mô hình vào ir.attachment.")

            

            # 3. Gọi service để dự đoán
            results = classifier_service.predict(pipeline, product_names)

            for item, (category_id, confidence) in zip(products, results):
                # if not category_id:
                #     category_id = self.env.ref('ttb_product.product_category_unclassified').id

                # Các trường hợp:
                # 1. Tương hợp sản phẩm lớn hơn 0.9 mà danh mục khác nhau -> lấy theo danh mục của sản phẩm
                # 2. Tương hợp sản phẩm 0.8 -> 0.9 và điểm danh mục < 0.5: -> lấy theo danh mục của sản phẩm

                # category_type = 'Học máy'
                # update_vals = {}

                # if category_id != item.matched_stock_item_id[f'category_id_level_{level+1}'].id:
                #     sptt_category_id = item.matched_stock_item_id[f'category_id_level_{level+1}']

                    # diff_name = item.diff_name

                    # if item.diff_name >= 0.9 or (item.diff_name >= 0.8 and confidence < 0.5):
                    #     category_id = sptt_category_id.id
                    #     category_type = 'Sản phẩm tương tự'

                    #     recursive_category = sptt_category_id
                    #     for i in range(level, 0, -1):
                    #         update_vals.update({
                    #             f'category_id_level_{i}': recursive_category.parent_id.id,
                    #             f'category_id_level_{i}_type': category_type,
                    #         })

                    #         recursive_category = recursive_category.parent_id
                
                if category_id and not item[f'category_id_level_{level+1}']:
                    item.write({
                        f'category_id_level_{level+1}': category_id,
                        f'category_id_level_{level+1}_rate': confidence,
                        f'category_id_level_{level+1}_type': 'Học máy',
                    })
            # item.write(update_vals)
            
        _logger.info("Hoàn tất phân loại.")

        self.env.cr.commit()

        if not category or category.category_level < 4:
            categories = self.env['product.category.training'].search([('parent_id', '=', category.id)] if category else [('category_level', '=', 1)])
            for sub_category in categories:
                self.match_mch_by_merchan_learning(batch_name, sub_category)


    # Bỏ hàm này
    def action_train_model(self):
        classifier_service = self.env['ttb.tools'].lib_ai_pc()

        _logger.info("Bắt đầu quá trình huấn luyện mô hình phân loại...")

        # 1. Lấy dữ liệu từ Odoo
        training_records = self.env['product.product.category.training'].search(
            [('product_name', '!=', False), ('category_id_level_1', '!=', False)]
        )
        
        # Định dạng lại dữ liệu cho service
        training_data = [{
            'product_name': rec['product_name'],
            'category_code': rec['category_id_level_1'].category_code
        } for rec in training_records]
        
        _logger.info(f"Đã lấy {len(training_data)} dòng dữ liệu để huấn luyện.")

        # 2. Gọi service để huấn luyện
        pipeline, acc_train, acc_test, report = classifier_service.train_model(training_data)

        if not pipeline:
            raise UserError(f"Huấn luyện thất bại: {report}")

        # # 3. Lưu mô hình đã huấn luyện
        # classifier_service.save_pipeline_to_attachment(self.env, pipeline)
        # _logger.info("Đã lưu thành công mô hình vào ir.attachment.")

        product_names = [item.name for item in self]

        _logger.info(f"Bắt đầu phân loại cho {len(product_names)} sản phẩm.")

        # 3. Gọi service để dự đoán
        results = classifier_service.predict(pipeline, product_names)
        print('xxx')

        categories = self.env['product.category.training'].search([('category_level', '=', 1)])
        category_map = {cat.category_code: cat.id for cat in categories}

        for item, (pred_name, confidence) in zip(self, results):
            category_id = category_map.get(pred_name)

            # Các trường hợp:
            # 1. Tương hợp sản phẩm lớn hơn 0.9 mà danh mục khác nhau -> lấy theo danh mục của sản phẩm
            # 2. Tương hợp sản phẩm 0.8 -> 0.9 





            
            if category_id:
                item.write({
                    'category_id_level_1': category_id,
                    'category_id_level_1_rate': confidence
                })
            else:
                _logger.warning(f"Không tìm thấy ID cho danh mục dự đoán '{pred_name}' cho sản phẩm '{item.name}'.")

        _logger.info("Hoàn tất phân loại.")

        # all_category_names = {res[0] for res in results}
        # category_map = {
        #     cat.name: cat.id for cat in self.env['product.product.category.training'].search([('name', 'in', list(all_category_names))])
        # }
