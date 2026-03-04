import ast
from odoo import api, fields, models, _
from datetime import datetime, timedelta
import pytz

class TtbPopupFilteredBase(models.AbstractModel):
    _name = 'ttb.popup.filtered.base'
    _description = 'Lọc báo cáo CRM base'

    def _get_default_config(self):
        return self.env['ttb.report.config'].sudo().get_config()

    branch_ids = fields.Many2many('ttb.branch', string='Chi nhánh', domain=[('has_report', '=', True)])
    date_filter = fields.Selection([
        ('today', 'Hôm nay'),
        ('yesterday', 'Hôm qua'),
        ('this_week', 'Tuần này'),
        ('last_week', 'Tuần trước'),
        ('this_month', 'Tháng này'),
        ('last_month', 'Tháng trước'),
        ('custom', 'Trong khoảng')
    ], string='Ngày tạo', default='this_month')
    date_from = fields.Datetime(string='Từ ngày')
    date_to = fields.Datetime(string='Đến ngày')

    @api.onchange('date_filter')
    def _onchange_date_filter(self):
        user_tz = pytz.timezone(self.env.user.tz or 'Asia/Ho_Chi_Minh')
        today = datetime.now(user_tz)

        def make_naive(dt):
            return dt.astimezone(pytz.utc).replace(tzinfo=None)

        start = False
        end = False
        if self.date_filter == 'today':
            start = today.replace(hour=0, minute=0, second=0, microsecond=0)
            end = today.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif self.date_filter == 'yesterday':
            ytd = today - timedelta(days=1)
            start = ytd.replace(hour=0, minute=0, second=0, microsecond=0)
            end = ytd.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif self.date_filter == 'this_week':
            start = (today - timedelta(days=today.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
            end = (start + timedelta(days=6)).replace(hour=23, minute=59, second=59, microsecond=999999)
        elif self.date_filter == 'last_week':
            start = (today - timedelta(days=today.weekday() + 7)).replace(hour=0, minute=0, second=0, microsecond=0)
            end = (start + timedelta(days=6)).replace(hour=23, minute=59, second=59, microsecond=999999)
        elif self.date_filter == 'this_month':
            start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
            end = (next_month - timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=999999)
        elif self.date_filter == 'last_month':
            first_this_month = today.replace(day=1)
            last_month_end = first_this_month - timedelta(days=1)
            start = last_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = last_month_end.replace(hour=23, minute=59, second=59, microsecond=999999)

        self.date_from = make_naive(start) if start else False
        self.date_to = make_naive(end) if end else False

    def get_last_config(self):
        return self.search([('create_uid', '=', self.env.user.id)], limit=1, order='id desc') or self.create({})

    def get_selected_brands(self, full=False):
        Branch = self.env['ttb.branch']
        Region = self.env.get('ttb.region')
        U = self.env.user
        has_report = [('has_report', '=', True)]

        # --- Full view: Admin / ép full / TNKH (manager & TN CSKH) ---
        if (
                full
                or U.has_group('base.group_system')
                or U.has_group('ttb_kpi.group_ttb_kpi_tnkh_manager')
                or U.has_group('ttb_kpi.group_ttb_kpi_tn_cskh')
                or U.has_group('ttb_kpi.group_ttb_kpi_nv_cskh')
        ):
            return (self.branch_ids and self.branch_ids.filtered('has_report')) \
                or Branch.search(has_report)

        allowed = Branch.browse()

        # 1) Cơ sở gán trực tiếp cho user (M2M)
        if getattr(U, 'ttb_branch_ids', False):
            allowed |= U.ttb_branch_ids

        # 2) QLCS / GĐCS:
        if 'manager_id' in Branch._fields and U.has_group('ttb_kpi.group_ttb_kpi_warehouse_manager'):
            allowed |= Branch.search([('manager_id', '=', U.id)])
        if 'director_id' in Branch._fields and U.has_group('ttb_kpi.group_ttb_kpi_warehouse_director'):
            allowed |= Branch.search([('director_id', '=', U.id)])

        # 3) Giám đốc vùng (VHKD): gom branch theo vùng
        if Region and U.has_group('ttb_kpi.group_ttb_kpi_vhkd_director'):
            regions = Region.browse()
            emp = U.employee_id
            if emp and hasattr(emp, 'ttb_region_ids') and emp.ttb_region_ids:
                regions |= emp.ttb_region_ids
            if 'manager_id' in Region._fields:
                regions |= Region.search([('manager_id', '=', U.id)])
            if 'director_id' in Region._fields:
                regions |= Region.search([('director_id', '=', U.id)])
            if regions and 'region_id' in Branch._fields:
                allowed |= Branch.search([('region_id', 'in', regions.ids)])

        # 4) Chỉ giữ branch có has_report
        allowed = allowed.filtered(lambda b: getattr(b, 'has_report', False))

        # 5) Nếu wizard đã chọn branch_ids -> lấy giao
        if self.branch_ids:
            selected = self.branch_ids.filtered(lambda b: getattr(b, 'has_report', False))
            allowed = allowed and (allowed & selected) or selected

        return allowed or Branch.browse()

    def get_report(self):
        report_id = self.env.context.get('default_report_id') or self.env.context.get('active_id')
        if report_id:
            report = self.env['helpdesk.crm.report'].browse(report_id)
        else:
            report = self.env['helpdesk.crm.report']
        return report

    def action_popup(self):
        return {
            'name': self._description,
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.get_last_config().id,
            'target': 'new',
        }

    def btn_reset(self):
        return {
            'name': self._description,
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }
