from odoo import api, fields, models, _


class TtbTaskTemplate(models.Model):
    _name = 'ttb.task.template'
    _description = 'Cài đặt nhiệm vụ'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Tên', required=True)
    job_ids = fields.Many2many(string='Đối tượng áp dụng', comodel_name='hr.job')
    area_ids = fields.Many2many(string='Khu vực áp dụng', comodel_name='ttb.area')
    branch_ids = fields.Many2many(string='Cơ sở áp dụng', comodel_name='ttb.branch')
    kpi_type_id = fields.Many2one(string='Loại KPI', comodel_name='ttb.kpi.type')
    categ_ids = fields.Many2many(string='Quầy', comodel_name='product.category', domain="[('category_level', '=', 1)]")
    date_from = fields.Date(string='Từ ngày', required=True)
    date_to = fields.Date(string='Đến ngày', required=True)
    line_ids = fields.One2many(string='Danh sách công việc', comodel_name='ttb.task.template.line', inverse_name='template_id')
    company_id = fields.Many2one(comodel_name='res.company', string='Công ty', index=True, default=lambda self: self.env.company)
    show_check_list_fields = fields.Boolean(compute="_compute_show_check_list_fields")
    active = fields.Boolean(default=True)
    @api.depends('kpi_type_id.code')
    def _compute_show_check_list_fields(self):
        for rec in self:
            rec.show_check_list_fields = False
            if rec.kpi_type_id.is_checklist:
                rec.show_check_list_fields = True
    @api.model
    def default_get(self, fields):
        result = super(TtbTaskTemplate, self).default_get(fields)
        if self._context.get('kpi_type_id', False) == 'VM':
            result['kpi_type_id'] = self.env.ref('ttb_kpi.ttb_kpi_type_vm')
        if self._context.get('kpi_type_id', False) == 'VS':
            result['kpi_type_id'] = self.env.ref('ttb_kpi.ttb_kpi_type_vs')
        if self._context.get('kpi_type_id', False) == 'CSKH':
            result['kpi_type_id'] = self.env.ref('ttb_kpi.ttb_kpi_type_cskh')
        return result


class TtbTaskTemplateLine(models.Model):
    _name = 'ttb.task.template.line'
    _description = 'Chi tiết cài đặt nhiệm vụ'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    template_id = fields.Many2one(string='Cài đặt nhiệm vụ', comodel_name='ttb.task.template')
    category_id = fields.Many2one(string='Danh mục công việc', comodel_name='ttb.task.category')
    sequence = fields.Integer(string='STT', compute='_compute_sequence_number', store=True, precompute=True, readonly=False)

    @api.depends('template_id')
    def _compute_sequence_number(self):
        for rec in self:
            rec.sequence = len(rec.template_id.line_ids)

    name = fields.Text(string='Nhiệm vụ', required=True)
    requirement = fields.Text(string='Yêu cầu cần đạt', required=True)
    frequency = fields.Integer(string='Tần xuất', required=True, default=1)
    period = fields.Selection(string='Chu kỳ', selection=[('day', 'Ngày'), ('week', 'Tuần'), ('month', 'Tháng')], required=True, default='day')
    applied_job_ids = fields.Many2many(string='Áp dụng riêng', comodel_name='hr.job')
    kpi_type_id = fields.Many2one(string='Loại KPI', comodel_name='ttb.kpi.type', related='template_id.kpi_type_id')
    kpi_type = fields.Many2one(string='Tính KPI', comodel_name='ttb.kpi.type', compute='_compute_kpi_type', store=True, precompute=True, readonly=False, domain="[('id', '=', kpi_type_id)]")
    rate = fields.Float(string='Tỉ trọng')
    cluster = fields.Char(string='Cụm')
    standard = fields.Many2many(string='Tiêu chuẩn', comodel_name='ttb.task.template.line.standard')
    rate_cluster = fields.Float(string='Tỉ trọng của cụm')
    criteria = fields.Char(string='Tiêu chí')
    @api.depends('kpi_type_id')
    def _compute_kpi_type(self):
        for rec in self:
            rec.kpi_type = rec.kpi_type_id

class TtbTaskTemplateLineStandard(models.Model):
    _name = 'ttb.task.template.line.standard'
    _description = 'Tiêu chuẩn chấm'

    name = fields.Char(string='Tên tiêu chuẩn')