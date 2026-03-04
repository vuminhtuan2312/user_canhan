from odoo import api, fields, models, _

import logging
_logger = logging.getLogger(__name__)

# Cấu hình
MODEL_NAME = 'bkai-foundation-models/vietnamese-bi-encoder'
BATCH_SIZE = 1000
# MODEL_NAME = 'all-MiniLM-L6-v2'
# EMBEDDING_CHUNK_SIZE = 1000; SIMILARITY_BLOCK_SIZE = 1000
# NUM_SUGGESTIONS = 10; PRICE_PERCENT_DIFFERENCE = 0.15

class TtbSubstituteProduct(models.Model):
    _name = 'ttb.substitute.product'
    _description = 'Sản phẩm thay thế'
    _rec_name = 'product_id'

    priority = fields.Integer(string='Ưu tiên')
    product_id = fields.Many2one(string='Sản phẩm', comodel_name='product.product')
    different = fields.Float(string='Khác biệt tên')
    different_price = fields.Float('Khác biệt giá')
    product_template_id = fields.Many2one(string='Sản phẩm gốc',comodel_name='product.template', index=True)
    is_ai = fields.Boolean('Ai tạo', default=False)


    """
    Model:
    product_template
    trường: name,
    trường: active
    trường: list_price

    Viết hàm:
    - Lấy ra toàn bộ sản phẩm active
    - Duyệt từng sản phẩm. Thực hiện
    Lượt 1
    + Dùng orm Lấy ra các sản phẩm có độ lệch giá không quá 5%
    + Trong số các sản phẩm lấy được dùng cosine_similarity lấy ra các sản phẩm tương hợp về tên trên 80%
    Lượt 2
    + Dùng orm Lấy ra các sản phẩm có độ lệch giá không quá 10%
    + Trong số các sản phẩm lấy được dùng cosine_similarity lấy ra các sản phẩm tương hợp về tên trên 80%
    Lượt 3
    + Dùng orm Lấy ra các sản phẩm có độ lệch giá không quá 15%
    + Trong số các sản phẩm lấy được dùng cosine_similarity lấy ra các sản phẩm tương hợp về tên trên 80%
    
    Các bản ghi tìm được insert vào model ttb.substitute.product. Theo thứ tự
    - Lượt 1 -> Lượt 2 -> Lượt 3
    - Cùng lượt thì độ tương hợp cao lên trước. Trường lưu độ tương hợp là different

    """


    @api.model
    def generate_substitute_products(self, branch_id=False, pos_date_from=False, pos_date_to=False):
        _logger.info('Bắt đầu tìm sản phẩm thay thế')
        try:
            from sentence_transformers import SentenceTransformer
            from sklearn.metrics.pairwise import cosine_similarity
            import numpy as np
            import sys

            _logger.info("Import thành công SentenceTransformer, sklearn.")
        except ImportError as e:
            _logger.info(f"LỖI IMPORT NGHIÊM TRỌNG: {e}")
            sys.exit(1)

        model = SentenceTransformer(MODEL_NAME)
        _logger.info('Load xong model')

        ProductTemplate = self.env['product.template']
        SubstituteModel = self.env['ttb.substitute.product']
        active_templates = ProductTemplate.search([('active', '=', True)])
        if not active_templates:
            return

        # Tạo mapping nhanh
        template_by_id = {t.id: t for t in active_templates}
        name_list = [t.name or '' for t in active_templates]
        price_list = [t.list_price for t in active_templates]
        template_ids = [t.id for t in active_templates]

        # Encode tất cả tên sản phẩm trước        
        embeddings = []
        for i in range(0, len(name_list), BATCH_SIZE):
            batch = name_list[i:i + BATCH_SIZE]
            batch_embeddings = model.encode(batch, convert_to_tensor=False, show_progress_bar=False)
            embeddings.extend(batch_embeddings)
            _logger.info('Xong batch %s', i)

        embeddings = np.array(embeddings)

        _logger.info('Đã encode xong')

        # Xoá cũ, tạo mới
        # SubstituteModel.search([]).unlink()

        # B1: Dùng read_group lấy product.product có doanh thu
        domain = []
        if branch_id:
            domain += [('order_id.ttb_branch_id', '=', branch_id)]
        if pos_date_from:
            domain += [('order_id.date_order', '>=', pos_date_from)]
        if pos_date_to:
            domain += [('order_id.date_order', '<=', pos_date_to)]
        grouped = self.env['pos.order.line'].read_group(
            domain=domain,
            fields=['product_id'],
            groupby=['product_id']
        )

        # B2: Lấy danh sách product.product ID
        product_ids = [line['product_id'][0] for line in grouped if line.get('product_id')]

        # B3: Ánh xạ sang product.template ID
        browse_template_ids = self.env['product.product'].browse(product_ids).mapped('product_tmpl_id.id')

        # B4: Tạo dict dạng {template_id: template_id}
        template_dict = {tid: tid for tid in browse_template_ids}

        for idx, template in enumerate(active_templates):
            if template.id not in template_dict: continue

            old = SubstituteModel.search([('product_template_id', '=', template.id), ('is_ai', '=', True)])
            if old:
                # Nếu có tính rồi thì không tính lại. Muốn tính lại thì xoá tay
                continue

            # Duyệt từng sản phẩm gốc
            inserts = []
            _logger.info('Xử lý cho sản phẩm %s/%s %s', idx, len(browse_template_ids), template.name)
            base_price = price_list[idx]
            base_embedding = embeddings[idx].reshape(1, -1)

            for priority, percent in enumerate([0.05, 0.10, 0.15], start=1):
                # Tìm các sản phẩm trong ngưỡng giá cho phép
                matched = []
                for jdx, compare_price in enumerate(price_list):
                    if template_ids[jdx] == template.id:
                        continue

                    min_price = base_price * (1 - percent)
                    max_price = base_price * (1 + percent)

                    if min_price <= compare_price and compare_price <= max_price:
                        matched.append(jdx)

                if not matched:
                    continue

                compare_embeddings = embeddings[matched]
                similarities = cosine_similarity(base_embedding, compare_embeddings)[0]

                for sim_score, jdx in sorted(zip(similarities, matched), key=lambda x: -x[0]):
                    if sim_score >= 0.7:
                        delta = abs(compare_price - base_price) / base_price if base_price != 0 else 0
                        inserts.append({
                            'product_template_id': template.id,
                            'product_id': template_by_id[template_ids[jdx]].product_variant_id.id,
                            'priority': priority,
                            'different': round(1 - sim_score, 4),
                            'different_price': delta,
                            'is_ai': True,
                        })
            if inserts:
                SubstituteModel.create(inserts)
                self.env.cr.commit()
        
