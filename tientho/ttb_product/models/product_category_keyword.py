# -*- coding: utf-8 -*-
from odoo import models, fields, api, osv

class ProductCategoryKeyword(models.Model):
    """
    Model lưu trữ từ khóa phân loại cho từng danh mục.
    Mỗi bản ghi tương ứng với một từ khóa và điểm số của nó.
    """
    _name = 'product.category.keyword'
    _description = 'Product Category Classification Keyword'
    _order = 'score desc' # Mặc định sắp xếp từ khóa có điểm cao nhất lên đầu

    name = fields.Char(
        string='Keyword',
        required=True,
        index=True,
        help="Từ hoặc cụm từ khóa được trích xuất (ví dụ: 'bút bi', 'tiểu thuyết')."
    )
    
    category_id = fields.Many2one(
        'product.category.training',
        string='Category',
        required=True,
        ondelete='cascade', # Nếu xóa danh mục, xóa luôn các từ khóa của nó
        index=True,
        help="Danh mục sản phẩm mà từ khóa này thuộc về."
    )
    
    score = fields.Float(
        string='TF-IDF Score',
        # required=True,
        # digits=(16, 4), # Lưu 4 chữ số thập phân cho độ chính xác cao
        help="Điểm trọng số TF-IDF của từ khóa. Điểm càng cao, từ khóa càng quan trọng."
    )

    # Ràng buộc duy nhất: Một danh mục không thể có 2 từ khóa giống hệt nhau
    _sql_constraints = [
        ('category_name_uniq', 'unique (category_id, name)', 'Từ khóa này đã tồn tại trong danh mục!')
    ]

class ProductCategoryTraining(models.Model):
    """
    Mở rộng model product.category để dễ dàng truy cập các từ khóa từ giao diện danh mục.
    """
    _name = 'product.category.training'
    _description = 'Danh mục'
    _order = 'parent_id, category_level, name asc'

    name = fields.Char('Tên danh mục')
    category_code = fields.Char('Mã danh mục', index=True)
    parent_id = fields.Many2one('product.category.training', 'Danh mục cha', index=True)
    category_level = fields.Integer('Level', compute='_compute_category_level', store=True)

    keyword_ids = fields.One2many(
        'product.category.keyword',
        'category_id',
        string='Classification Keywords',
        help="Danh sách các từ khóa dùng để tự động phân loại sản phẩm vào danh mục này."
    )
    
    keyword_count = fields.Integer(
        string='Keyword Count',
        compute='_compute_keyword_count',
        store=True
    )

    active = fields.Boolean(default=True)

    @api.depends('parent_id', 'parent_id.category_level')
    def _compute_category_level(self):
        for rec in self:
            rec.category_level = (rec.parent_id.category_level or 0) + 1

    @api.depends('keyword_ids')
    def _compute_keyword_count(self):
        for record in self:
            record.keyword_count = len(record.keyword_ids)

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if not name:
            return super().name_search(name, args, operator, limit)
        domain = args or []
        categories = self.search_fetch(osv.expression.AND([domain, [('category_code', operator, name)]]), ['display_name'], limit=limit)

        if not categories:
            return super().name_search(name, args, operator, limit)
        
        return [(category.id, category.display_name) for category in categories.sudo()]
