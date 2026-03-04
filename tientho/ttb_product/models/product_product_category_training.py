from odoo import models, fields
from odoo.addons.ttb_tools.ai import product_category_matcher as ai_pc

class ProductCategoryTraining(models.Model):
    """
    Model lưu trữ dữ liệu thô (tên sản phẩm và tên danh mục tương ứng)
    dùng để làm đầu vào cho thuật toán trích xuất từ khóa phân loại.
    """
    # --- THAY ĐỔI TẠI ĐÂY ---
    _name = 'product.product.category.training'
    _description = 'Product Category Training Data'
    # -----------------------

    _order = 'create_date desc'

    product_code = fields.Char(
        string='Mã sản phẩm',
        # required=True,
        # index=True
    )

    product_name = fields.Char(
        string='Tên sản phẩm',
        # required=True,
        # index=True
    )
    
    category_code = fields.Char(
        string='Mã danh mục (Dữ liệu gốc)',
        # required=True,
        # index=True,
        help="Tên danh mục dạng text từ file import, không phải là một liên kết."
    )

    category_name = fields.Char(
        string='Tên danh mục (Dữ liệu gốc)',
        # required=True,
        # index=True,
        help="Tên danh mục dạng text từ file import, không phải là một liên kết."
    )

    category_id = fields.Many2one('product.category.training', 'Danh mục', index=True)
    category_id_level_1 = fields.Many2one('product.category.training', 'Danh mục MCH1', index=True)
    category_id_level_2 = fields.Many2one('product.category.training', 'Danh mục MCH2', index=True)
    category_id_level_3 = fields.Many2one('product.category.training', 'Danh mục MCH3', index=True)
    category_id_level_4 = fields.Many2one('product.category.training', 'Danh mục MCH4', index=True)
    category_id_level_5 = fields.Many2one('product.category.training', 'Danh mục MCH5', index=True)

    ai_vector = fields.Text(
        string='AI Vector (JSON)',
        copy=False,
    )
    
    active = fields.Boolean(
        default=True,
        help="Bỏ chọn để ẩn bản ghi này mà không cần xóa."
    )
    
    is_processed = fields.Boolean(
        string='Đã xử lý',
        default=False,
        readonly=True,
        copy=False,
        help="Đánh dấu nếu bản ghi này đã được dùng để tạo từ khóa."
    )

    stored_pipeline = fields.Binary(
        string='Trained Pipeline Model',
        help='Serialized scikit-learn model pipeline for text classification.'
    )

    def get_category_level(self, category, level=1):
        while category.category_level != level and category.parent_id:
            category = category.parent_id

        return category

    def process_keyword(self, parent_id=False):
        level = (parent_id.category_level if parent_id else 0) + 1

        if parent_id:
            categories = self.env['product.category.training'].search([('parent_id', '=', parent_id.id)])
        else:
            categories = self.env['product.category.training'].search([('category_level', '=', 1)])

        datas = self.sudo().search([('category_id_level_' + str(level), 'in', categories.ids)])

        # MCH1 -> 5
        # for i in range(1, level+1):
        training_datas = []
        for data in datas:
            # category = self.get_category_level(data.category_id, i)
            category = data['category_id_level_' + str(level)]
            if category and data.product_name:
                training_datas.append({
                    'category_code': category.category_code,
                    'product_name': data.product_name,
                })
        if len(training_datas) > 1:
            ai_pc.extract_keywords_from_data(self.env, training_datas)
            self.env.cr.commit()
        else:
            print(categories)

        for category in categories:
            self.process_keyword(category)

    def process_product(self, batch_name, parent_id=False):
        if parent_id:
            categories = self.env['product.category.training'].search([('parent_id', '=', parent_id.id)])
        else:
            categories = self.env['product.category.training'].search([('category_level', '=', 1)])

        level = 0
        domain = [('batch_name', '=', batch_name)]
        if parent_id:
            level = parent_id.category_level
            domain.append((f'category_id_level_{level}', '=', parent_id.id))

        origin_nibot_products = self.env['product.sale.item'].search(domain)

        if categories and origin_nibot_products:
            self.env['ttb.tools'].lib_ai_pc().classify_product(self.env, categories, origin_nibot_products, f'category_id_level_{level+1}')
            self.env.cr.commit()

        for category in categories:
            self.process_product(batch_name, category)
        
