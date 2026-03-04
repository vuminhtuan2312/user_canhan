from odoo import models, fields


class ProductMergeDetail(models.Model):
    _name = "product.merge.detail"
    _description = "Chi tiết các bản ghi bị tác động khi merge sản phẩm"

    merge_id = fields.Many2one('product.merge', string='Merge ID', required=True, ondelete='cascade')
    merge_type = fields.Selection([('augges', 'Augges'), ('odoo', 'Odoo')], string="Loại Merge")
    target_model = fields.Char(string="Đối tượng Merge",)
    record_id = fields.Char(string="ID bản ghi")
    update_field = fields.Char(string="Trường Update")
    old_value = fields.Char(string="Giá trị cũ")
    new_value = fields.Char(string="Giá trị mới")
    extra_info = fields.Text(string="Thông tin bổ sung")
