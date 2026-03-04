from odoo import models, fields, api

class ParamMapping(models.Model):
    _name = 'param.mapping'
    _description = 'Parameter mapping'
    _order = 'id'

    template_id_ref = fields.Many2one(
        'zalo.template',
        ondelete='cascade'
    )

    name = fields.Char('Tên')
    type = fields.Char('Loại')
    accept_null = fields.Boolean('Chấp nhận giá trị rỗng')
    require = fields.Boolean('Bắt buộc')
    mapping_key = fields.Char(string='Giá trị mapping',help='Key dùng để map dữ liệu khi gửi tin nhắn'
                                   'Sử dụng khi muốn lấy các giá trị từ model khác nối với model gốc')
    table_param_id = fields.Many2one('bizfly.table.map')
    key = fields.Char('Key')
    is_selection_field = fields.Boolean('Là trường lựa chọn')
    param_mapping_line_ids = fields.One2many(
        'param.mapping.line',
        'param_id',
        string='Parameter Mapping Lines',
    )

    def unlink(self):
        for record in self:
            if record.param_mapping_line_ids:
                record.param_mapping_line_ids.unlink()
        return super().unlink()


