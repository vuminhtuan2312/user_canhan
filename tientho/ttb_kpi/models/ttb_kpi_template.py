from odoo import api, fields, models, _
from odoo.exceptions import UserError


class TtbKpiTemplate(models.Model):
    _name = 'ttb.kpi.template'
    _description = 'Quy tắc tính KPI '
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Tên', required=True)
    job_ids = fields.Many2many(string='Đối tượng áp dụng', comodel_name='hr.job')
    company_id = fields.Many2one(comodel_name='res.company', string='Công ty', index=True, default=lambda self: self.env.company)
    active = fields.Boolean(string='Hoạt động', default=True)
    line_ids = fields.One2many(string='Danh sách công việc', comodel_name='ttb.kpi.template.line', inverse_name='template_id')
    detail_ids = fields.One2many(string='Chi tiết KPI', comodel_name='ttb.kpi.template.detail', inverse_name='template_id')
    employee_level = fields.Selection([
        ('staff', 'Nhân viên cơ sở'),
        ('manager', 'Quản lý nhà sách'),
        ('branch_manager', 'Giám đốc nhà sách'),
        ('region_manager', 'Quản lý vùng'),
    ], string='Cấp bậc nhân viên', required=True, default='staff')


class TtbKpiTemplateLine(models.Model):
    _name = 'ttb.kpi.template.line'
    _description = 'Chi tiết quy tắc tính KPI '
    _inherit = ['mail.thread', 'mail.activity.mixin']

    template_id = fields.Many2one(string='Quy tắc', comodel_name='ttb.kpi.template', required=True)
    type_id = fields.Many2one(string='Loại KPI', comodel_name='ttb.kpi.type', required=True)
    weight = fields.Float(string='Trọng số')
    min_score = fields.Float(string='Số điểm tối thiểu')
    max_score = fields.Float(string='Số điểm tối đa')
    bonus_rate = fields.Float(string='Tỉ lệ thưởng vượt chỉ tiêu')
    overdue_rate = fields.Float(string='Tỷ lệ phạt phiếu quá hạn')

    @api.constrains('type_id')
    def _check_type_id(self):
        for rec in self:
            check_type = self.env['ttb.kpi.template.line'].search([('id', '!=', rec.id), ('type_id', '=', rec.type_id.id), ('template_id', '=', rec.template_id.id)])
            if check_type:
                raise UserError('Mỗi loại KPI chỉ được cài đặt 1 lần')


class TtbKpiTemplateDetail(models.Model):
    _name = 'ttb.kpi.template.detail'
    _description = 'Chi tiết KPI '
    _inherit = ['mail.thread', 'mail.activity.mixin']

    template_id = fields.Many2one(string='Quy tắc', comodel_name='ttb.kpi.template', required=True)
    type_id = fields.Many2one(string='Loại KPI', comodel_name='ttb.kpi.type', required=True, domain="[('source', '=', 'task')]")
    group = fields.Selection(string='Nhóm đánh giá', selection=[('region_manager', 'Quản lý vùng'), ('branch_mannager', 'Quản lý cơ sở'), ('cross_dot_area_manager', 'Giám đốc vùng chấm chéo'), ('cs', 'Trải nghiệm khách hàng'), ('manager', 'Quản lý trực tiếp')], required=True)
    weight = fields.Float(string='Tỉ lệ')
